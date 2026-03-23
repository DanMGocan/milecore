import io
import json
import math
import os
import re
import time
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generator

import anthropic
from openpyxl import Workbook

from collections import defaultdict

from backend.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_API_KEY_SPARE,
    CLAUDE_MODEL,
    BREVO_SENDER_EMAIL,
    BREVO_SENDER_NAME,
    EMAIL_RATE_LIMIT_PER_HOUR,
    MAX_HISTORY_MESSAGES,
    MAX_TOOL_RESULT_CHARS,
    QUERY_TOKEN_THRESHOLD,
)
from backend.database import execute_query, get_home_site, get_schema_ddl, validate_query
from backend.email_sender import send_email as smtp_send_email
from backend.routes.upload import get_chat_attachment_path, resolve_s3_attachment_for_email
from backend.prompts import SYSTEM_STATIC, CONTEXT_TEMPLATE, TOOLS

_TABLE_RE = re.compile(
    r"(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM|INTO)\s+(\w+)",
    re.IGNORECASE,
)

_OP_KEYWORDS = {"INSERT", "UPDATE", "DELETE"}


def _json_default(obj: Any) -> Any:
    """Handle non-serializable types from DB results."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _dumps(obj: Any) -> str:
    return json.dumps(obj, default=_json_default)


# ---------------------------------------------------------------------------
# Token-optimization helpers
# ---------------------------------------------------------------------------

_ADMIN_TOOLS = {"manage_approval_rules", "review_approvals"}
_OWNER_TOOLS = {"invite_user"}


def _filter_tools(user_role: str) -> list[dict]:
    """Return the TOOLS list filtered by user role."""
    if user_role == "owner":
        return TOOLS
    if user_role == "admin":
        return [t for t in TOOLS if t["name"] not in _OWNER_TOOLS]
    return [t for t in TOOLS if t["name"] not in (_ADMIN_TOOLS | _OWNER_TOOLS)]


def _trim_history(history: list[dict], max_messages: int) -> list[dict]:
    """Keep only the last *max_messages* entries from conversation history."""
    if len(history) <= max_messages:
        return history
    return history[-max_messages:]


def _truncate_tool_results(tool_results: list[dict], max_chars: int) -> None:
    """Truncate oversized tool-result content strings in-place."""
    for tr in tool_results:
        content = tr.get("content")
        if isinstance(content, str) and len(content) > max_chars:
            tr["content"] = content[:max_chars] + "... [truncated]"


def _find_matching_rule(sql: str, rules: list[dict]) -> dict | None:
    """Return the first approval rule whose description matches the SQL, or None."""
    sql_upper = sql.strip().upper()
    op = next((kw for kw in _OP_KEYWORDS if sql_upper.startswith(kw)), None)
    m = _TABLE_RE.search(sql)
    table = m.group(1).lower() if m else None

    for rule in rules:
        desc = rule["description"].upper()
        op_match = op and op in desc
        table_match = table and table.upper() in desc
        if op_match and table_match:
            return rule
    return None


_primary_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
_spare_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY_SPARE) if ANTHROPIC_API_KEY_SPARE else None
_active_client: anthropic.Anthropic = _primary_client


def _get_client() -> anthropic.Anthropic:
    return _active_client


def _swap_to_spare() -> bool:
    """Switch to spare client. Returns True if swap succeeded."""
    global _active_client
    if _spare_client and _active_client is _primary_client:
        _active_client = _spare_client
        print("[claude_client] Switched to spare API key")
        return True
    return False

# In-memory store for generated files: {file_id: (filename, bytes, created_ts)}
_generated_files: dict[str, tuple[str, bytes, float]] = {}
_MAX_GENERATED_FILES = 100
_FILE_TTL_SECONDS = 3600  # 1 hour

# Email rate limiting: per-instance send timestamps
_email_send_times: dict[int, list[float]] = defaultdict(list)


def _check_email_rate_limit(instance_id: int) -> bool:
    """Return True if under the rate limit, False if exceeded."""
    now = time.time()
    window = 3600  # 1 hour
    times = _email_send_times[instance_id]
    _email_send_times[instance_id] = [t for t in times if now - t < window]
    return len(_email_send_times[instance_id]) < EMAIL_RATE_LIMIT_PER_HOUR


def _record_email_send(instance_id: int) -> None:
    """Record that an email was sent for rate limiting."""
    _email_send_times[instance_id].append(time.time())


def _cleanup_generated_files() -> None:
    """Remove expired files and cap total count."""
    now = time.time()
    expired = [fid for fid, (_, _, ts) in _generated_files.items() if now - ts > _FILE_TTL_SECONDS]
    for fid in expired:
        del _generated_files[fid]
    if len(_generated_files) > _MAX_GENERATED_FILES:
        by_age = sorted(_generated_files, key=lambda k: _generated_files[k][2])
        for fid in by_age[: len(_generated_files) - _MAX_GENERATED_FILES]:
            del _generated_files[fid]


def get_generated_file(file_id: str) -> tuple[str, bytes] | None:
    entry = _generated_files.get(file_id)
    if entry is None:
        return None
    return (entry[0], entry[1])


# Schema DDL cache — cleared when tables are created/dropped
_schema_cache: dict[int, str] = {}


def _get_cached_schema(instance_id) -> str:
    global _schema_cache
    if instance_id not in _schema_cache:
        _schema_cache[instance_id] = get_schema_ddl(instance_id=instance_id)
    return _schema_cache[instance_id]


def clear_schema_cache() -> None:
    global _schema_cache
    _schema_cache.clear()


def clear_prompt_cache() -> None:
    _prompt_cache.clear()


def _build_approval_section(instance_id) -> str:
    rules = execute_query("SELECT id, description FROM approval_rules WHERE is_active = 1", instance_id=instance_id)
    count_result = execute_query("SELECT COUNT(*) as count FROM pending_approvals WHERE status = 'pending'", instance_id=instance_id)
    pending_count = count_result["rows"][0]["count"] if count_result.get("rows") else 0

    if not rules.get("rows"):
        return f"No approval rules configured. All write operations execute immediately.\nPending approvals: {pending_count}"

    lines = ["Active approval rules:"]
    for rule in rules["rows"]:
        lines.append(f"  - Rule #{rule['id']}: {rule['description']}")
    lines.append(f"Pending approvals awaiting review: {pending_count}")
    return "\n".join(lines)


def _build_home_site_section(instance_id) -> str:
    site = get_home_site(instance_id=instance_id)
    if site is None:
        return (
            "HOME SITE:\n"
            "No home site is configured in app_settings. This should not happen in normal startup because bootstrap seeding sets one.\n"
            "Do not ask the user to configure a home site. Continue normally and prefer explicit site mentions from the user when needed."
        )
    site_label = site['client_name'] or site['name']
    return (
        "HOME SITE:\n"
        f"This instance serves {site_label} in {site['city']} (site_id: {site['id']}). "
        "Default all operations to this site unless the user specifies otherwise."
    )


def _build_user_role_section(user_role: str) -> str:
    if user_role in ("admin", "owner"):
        return (
            "USER ROLE:\n"
            "The current user is an admin. They can manage approval rules and review pending approvals."
        )
    return (
        "USER ROLE:\n"
        "The current user is a standard user. They CANNOT manage approval rules or review/approve "
        "pending approvals. If they attempt these actions, politely tell them this requires admin access."
    )


_PROMPT_SECTION_RE = re.compile(
    r"(INSTRUCTIONS|SYSTEM|USER ROLE|CURRENT USER|CRITICAL|SCHEMA|IMPORTANT|FORMATTING|TABLE GUIDE)",
    re.IGNORECASE,
)


def _sanitize_profile_field(value: str | None, max_len: int = 100) -> str:
    """Sanitize a user-editable profile field before inserting into the system prompt."""
    if not value:
        return "not set"
    s = str(value)[:max_len]
    s = s.replace("\n", " ").replace("\r", " ")
    s = _PROMPT_SECTION_RE.sub("", s)
    return s.strip() or "not set"


def _build_current_user_section(current_user: dict[str, Any] | None) -> str:
    if not current_user:
        return (
            "CURRENT USER:\n"
            "No current user record was resolved for this request. Do not infer personal details."
        )

    lines = [
        "CURRENT USER:",
        f"- person_id: {current_user['person_id']}",
        f"- name: {_sanitize_profile_field(current_user['display_name'])}",
        f"- username: {_sanitize_profile_field(current_user['username'])}",
        f"- role: {current_user['role']}",
        f"- email: {_sanitize_profile_field(current_user['email'])}",
        f"- phone: {_sanitize_profile_field(current_user['phone'])}",
        f"- title: {_sanitize_profile_field(current_user['role_title'])}",
        f"- department: {_sanitize_profile_field(current_user['department'])}",
        f"- site_id: {current_user['site_id'] if current_user['site_id'] is not None else 'not set'}",
        f"- site_name: {_sanitize_profile_field(current_user['site_name'])}",
        f"- team_id: {current_user['team_id'] if current_user['team_id'] is not None else 'not set'}",
        f"- team_name: {_sanitize_profile_field(current_user['team_name'])}",
    ]
    return "\n".join(lines)


_prompt_cache: dict[int, dict] = {}


def _build_system_blocks(user_role: str = "admin", current_user: dict[str, Any] | None = None, instance_id: int = 1) -> list[dict]:
    """Return two system content blocks: static (cached) + dynamic context (uncached).

    The static block is byte-for-byte identical across all users, roles, and
    instances, maximising Anthropic prompt cache reuse.
    """
    now = time.time()
    cache = _prompt_cache.get(instance_id, {})
    if now - cache.get("ts", 0) > 60:
        cache["approval"] = _build_approval_section(instance_id)
        cache["home_site"] = _build_home_site_section(instance_id)
        cache["ts"] = now
        _prompt_cache[instance_id] = cache
    context = CONTEXT_TEMPLATE.format(
        instance_id=instance_id,
        today=date.today().isoformat(),
        sender_name=BREVO_SENDER_NAME,
        sender_email=BREVO_SENDER_EMAIL,
        home_site_section=cache["home_site"],
        user_role_section=_build_user_role_section(user_role),
        current_user_section=_build_current_user_section(current_user),
        approval_section=cache["approval"],
        schema_ddl=_get_cached_schema(instance_id),
    )
    return [
        {"type": "text", "text": SYSTEM_STATIC, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": context},
    ]


def _build_content(response) -> list[dict[str, Any]]:
    """Convert API response content blocks to serializable dicts."""
    content = []
    for block in response.content:
        if block.type == "text":
            content.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            content.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
    return content


def _execute_tools(assistant_content: list[dict], sql_log: list[dict], user_role: str = "admin", instance_id: int = 1, current_user: dict[str, Any] | None = None) -> list[dict]:
    """Execute tool calls and return tool_result messages. Mutates sql_log."""
    ADMIN_ONLY_TOOLS = {"manage_approval_rules", "review_approvals"}
    tool_results = []
    for block in assistant_content:
        if block["type"] != "tool_use":
            continue

        tool_name = block["name"]

        if user_role not in ("admin", "owner") and tool_name in ADMIN_ONLY_TOOLS:
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": json.dumps({"error": "This action requires admin access."}),
            })
            continue

        if tool_name in ("execute_sql", "create_table"):
            sql = block["input"]["sql"]
            explanation = block["input"].get("explanation", "")
            sql_upper = sql.strip().upper()

            # Block destructive DDL from the AI early with a clear message
            if tool_name == "execute_sql" and sql_upper.startswith(("DROP", "TRUNCATE", "ALTER")):
                result = {"error": "DROP, TRUNCATE, and ALTER statements are system-blocked and cannot be executed."}
                sql_log.append({"tool": tool_name, "sql": sql, "explanation": explanation, "result": result})
                tool_results.append({"type": "tool_result", "tool_use_id": block["id"], "content": _dumps(result)})
                continue
            if tool_name == "create_table" and not sql_upper.startswith("CREATE"):
                result = {"error": "The create_table tool can only be used for CREATE TABLE statements."}
                sql_log.append({"tool": tool_name, "sql": sql, "explanation": explanation, "result": result})
                tool_results.append({"type": "tool_result", "tool_use_id": block["id"], "content": _dumps(result)})
                continue

            # Check if this is a data write that should go through approval
            is_data_write = sql_upper.startswith(("INSERT", "UPDATE", "DELETE"))
            if is_data_write and tool_name == "execute_sql":
                rules = execute_query("SELECT id, description FROM approval_rules WHERE is_active = 1", instance_id=instance_id)
                matched_rule = _find_matching_rule(sql, rules.get("rows") or [])
                if matched_rule:
                    validation = validate_query(sql, instance_id=instance_id)
                    if not validation.get("valid"):
                        result = {"error": f"SQL validation failed: {validation['error']}"}
                    else:
                        ins = execute_query(
                            "INSERT INTO pending_approvals (sql_statement, explanation, matched_rule_id, matched_rule_description) VALUES (?, ?, ?, ?)",
                            [sql, explanation, matched_rule["id"], matched_rule["description"]],
                            instance_id=instance_id,
                        )
                        result = {
                            "queued": True,
                            "executed": False,
                            "approval_id": ins.get("lastrowid"),
                            "matched_rule": matched_rule["description"],
                            "message": "This query was NOT executed. It has been queued for admin approval because it matched an active approval rule. Tell the user their request is pending approval.",
                        }
                    sql_log.append({"tool": tool_name, "sql": sql, "explanation": explanation, "result": result})
                    tool_results.append({"type": "tool_result", "tool_use_id": block["id"], "content": _dumps(result)})
                    continue

            result = execute_query(sql, instance_id=instance_id)

            sql_log.append({
                "tool": tool_name,
                "sql": sql,
                "explanation": explanation,
                "result": result,
            })

            if tool_name == "create_table":
                clear_schema_cache()
            elif sql_upper.startswith(("CREATE", "DROP", "ALTER")):
                clear_schema_cache()

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": _dumps(result),
            })

        elif tool_name == "manage_approval_rules":
            inp = block["input"]
            action = inp["action"]

            if action == "add":
                desc = inp.get("description", "")
                result = execute_query(
                    "INSERT INTO approval_rules (description) VALUES (?)",
                    [desc],
                    instance_id=instance_id,
                )
                result["rule_id"] = result.get("lastrowid")
            elif action == "list":
                result = execute_query(
                    "SELECT id, description, is_active, created_at FROM approval_rules ORDER BY id",
                    instance_id=instance_id,
                )
            elif action == "remove":
                rule_id = inp.get("rule_id")
                result = execute_query(
                    "UPDATE approval_rules SET is_active = 0 WHERE id = ?",
                    [rule_id],
                    instance_id=instance_id,
                )
            else:
                result = {"error": f"Unknown action: {action}"}

            sql_log.append({"tool": tool_name, "action": action, "result": result})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": _dumps(result),
            })

        elif tool_name == "submit_for_approval":
            inp = block["input"]
            validation = validate_query(inp["sql"], instance_id=instance_id)
            if not validation.get("valid"):
                result = {"error": f"SQL validation failed: {validation['error']}"}
            else:
                ins = execute_query(
                    "INSERT INTO pending_approvals (sql_statement, explanation, matched_rule_id, matched_rule_description) VALUES (?, ?, ?, ?)",
                    [inp["sql"], inp["explanation"], inp["matched_rule_id"], inp["matched_rule_description"]],
                    instance_id=instance_id,
                )
                result = {
                    "queued": True,
                    "executed": False,
                    "approval_id": ins.get("lastrowid"),
                    "matched_rule": inp["matched_rule_description"],
                    "message": "This query was NOT executed. It has been queued for admin approval because it matched an active approval rule. Tell the user their request is pending approval.",
                }

            sql_log.append({"tool": tool_name, "action": "queued", "result": result})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": _dumps(result),
            })

        elif tool_name == "review_approvals":
            inp = block["input"]
            action = inp["action"]

            if action == "list":
                result = execute_query(
                    "SELECT id, sql_statement, explanation, matched_rule_description, status, created_at FROM pending_approvals WHERE status = 'pending' ORDER BY created_at",
                    instance_id=instance_id,
                )
            elif action == "approve":
                approval_id = inp.get("approval_id")
                approval = execute_query(
                    "SELECT sql_statement FROM pending_approvals WHERE id = ? AND status = 'pending'",
                    [approval_id],
                    instance_id=instance_id,
                )
                if approval.get("rows"):
                    stored_sql = approval["rows"][0]["sql_statement"]
                    exec_result = execute_query(stored_sql, instance_id=instance_id)
                    if "error" in exec_result:
                        execute_query(
                            "UPDATE pending_approvals SET status = 'failed', review_note = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
                            [f"Execution failed: {exec_result['error']}", approval_id],
                            instance_id=instance_id,
                        )
                        result = {"approved": False, "approval_id": approval_id, "execution_error": exec_result["error"]}
                    else:
                        execute_query(
                            "UPDATE pending_approvals SET status = 'approved', review_note = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
                            [inp.get("note", ""), approval_id],
                            instance_id=instance_id,
                        )
                        result = {"approved": True, "approval_id": approval_id, "execution_result": exec_result}
                else:
                    result = {"error": f"Approval #{approval_id} not found or already reviewed"}
            elif action == "reject":
                approval_id = inp.get("approval_id")
                execute_query(
                    "UPDATE pending_approvals SET status = 'rejected', review_note = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
                    [inp.get("note", ""), approval_id],
                    instance_id=instance_id,
                )
                result = {"rejected": True, "approval_id": approval_id}
            else:
                result = {"error": f"Unknown action: {action}"}

            sql_log.append({"tool": tool_name, "action": action, "result": result})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": _dumps(result),
            })

        elif tool_name == "import_csv":
            from backend.routes.upload import generate_import_sql, remove_staged_file

            inp = block["input"]
            gen = generate_import_sql(inp["file_id"], inp["table"], inp["column_mapping"])

            if "error" in gen:
                result = gen
            else:
                # Validate the SQL before queuing or executing
                validation = validate_query(gen["sql"], instance_id=instance_id)
                if not validation.get("valid"):
                    result = {"error": f"SQL validation failed: {validation['error']}"}
                else:
                    # Check if any approval rules match this import
                    rules = execute_query("SELECT id, description FROM approval_rules WHERE is_active = 1", instance_id=instance_id)
                    matched_rule = _find_matching_rule(gen["sql"], rules.get("rows") or [])
                    if matched_rule:
                        approval_result = execute_query(
                            "INSERT INTO pending_approvals (sql_statement, explanation, matched_rule_id, matched_rule_description) VALUES (?, ?, ?, ?)",
                            [gen["sql"], inp.get("explanation", f"CSV import: {gen['total_rows']} rows into {gen['table']}"),
                             matched_rule["id"], matched_rule["description"]],
                            instance_id=instance_id,
                        )
                        # Queued successfully — remove staged file
                        remove_staged_file(inp["file_id"])
                        result = {
                            "queued": True,
                            "executed": False,
                            "approval_id": approval_result.get("lastrowid"),
                            "matched_rule": matched_rule["description"],
                            "total_rows": gen["total_rows"],
                            "message": f"This import was NOT executed. Import of {gen['total_rows']} rows into {gen['table']} has been queued for admin approval. Tell the user their request is pending approval.",
                        }
                    else:
                        # No rules — execute directly
                        result = execute_query(gen["sql"], instance_id=instance_id)
                        result["rows_inserted"] = result.get("rowcount", 0)
                        result["skipped"] = gen["skipped"]
                        # Only remove staged file after successful execution
                        if "error" not in result:
                            remove_staged_file(inp["file_id"])

            sql_log.append({
                "tool": tool_name,
                "sql": gen.get("sql", ""),
                "explanation": inp.get("explanation", ""),
                "result": result,
            })
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": _dumps(result),
            })

        elif tool_name == "send_email":
            inp = block["input"]

            # Check if email addon is enabled for this instance
            addon_check = execute_query(
                "SELECT email_addon, email_signature FROM instances WHERE id = ?",
                [instance_id],
                instance_id=None,
            )
            if addon_check.get("rows") and not addon_check["rows"][0].get("email_addon"):
                result = {"error": "Email addon is not enabled for this instance. The instance owner can enable it from the billing section in the dashboard ($4.99/mo)."}
                sql_log.append({"tool": "send_email", "action": f"Email to {inp['to_email']}: {inp['subject']}", "result": result})
                tool_results.append({"type": "tool_result", "tool_use_id": block["id"], "content": _dumps(result)})
                continue

            # Rate limit check
            if not _check_email_rate_limit(instance_id):
                result = {"error": f"Email rate limit exceeded. Maximum {EMAIL_RATE_LIMIT_PER_HOUR} emails per hour per instance. Please try again later."}
                sql_log.append({"tool": "send_email", "action": f"Email to {inp['to_email']}: {inp['subject']} (rate limited)", "result": result})
                tool_results.append({"type": "tool_result", "tool_use_id": block["id"], "content": _dumps(result)})
                continue

            # Append email signature if set
            body = inp["body"]
            if addon_check.get("rows") and addon_check["rows"][0].get("email_signature"):
                body = body + "\n\n" + addon_check["rows"][0]["email_signature"]

            # Resolve file attachments if provided (download from S3 to temp)
            email_attachments = None
            temp_files = []
            file_ids = inp.get("attachment_file_ids") or []
            if file_ids:
                email_attachments = []
                for fid in file_ids:
                    resolved = resolve_s3_attachment_for_email(fid, instance_id)
                    if resolved:
                        email_attachments.append(resolved)
                        temp_files.append(resolved["path"])

            result = smtp_send_email(
                to_email=inp["to_email"],
                subject=inp["subject"],
                body=body,
                to_name=inp.get("to_name", ""),
                attachments=email_attachments,
            )
            _record_email_send(instance_id)

            # Clean up temp files
            for tf in temp_files:
                try:
                    os.remove(tf)
                except OSError:
                    pass

            att_note = f" (+{len(email_attachments)} attachment(s))" if email_attachments else ""
            sql_log.append({
                "tool": "send_email",
                "action": f"Email to {inp['to_email']}: {inp['subject']}{att_note}",
                "result": result,
            })

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": _dumps(result),
            })

        elif tool_name == "generate_excel":
            inp = block["input"]
            filename = inp["filename"].strip()
            if not filename.endswith(".xlsx"):
                filename = filename + ".xlsx"
            sheets = inp.get("sheets", [])

            # Validate all queries are SELECT
            invalid = [s for s in sheets if not s["sql"].strip().upper().startswith("SELECT")]
            if invalid:
                result = {"error": "Only SELECT queries are allowed in generate_excel."}
            else:
                wb = Workbook()
                wb.remove(wb.active)
                sheet_summaries = []
                error = None

                for sheet_def in sheets:
                    query_result = execute_query(sheet_def["sql"], instance_id=instance_id)
                    if "error" in query_result:
                        error = query_result["error"]
                        break
                    ws = wb.create_sheet(title=sheet_def["name"][:31])
                    rows = query_result.get("rows", [])
                    if rows:
                        headers = list(rows[0].keys())
                        ws.append(headers)
                        for row in rows:
                            ws.append([row.get(h) for h in headers])
                    else:
                        ws.append(["No data"])
                    sheet_summaries.append({"name": sheet_def["name"], "row_count": len(rows)})

                if error:
                    result = {"error": error}
                else:
                    buf = io.BytesIO()
                    wb.save(buf)
                    file_bytes = buf.getvalue()
                    file_id = str(uuid.uuid4())
                    _cleanup_generated_files()
                    _generated_files[file_id] = (filename, file_bytes, time.time())
                    download_url = f"/api/downloads/{file_id}"
                    result = {
                        "success": True,
                        "file_id": file_id,
                        "filename": filename,
                        "download_url": download_url,
                        "sheets": sheet_summaries,
                    }

            sql_log.append({
                "tool": "generate_excel",
                "filename": filename,
                "result": result,
            })
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": _dumps(result),
            })

        elif tool_name == "manage_reminders":
            inp = block["input"]
            action = inp["action"]

            if action == "create":
                title = inp.get("title", "")
                message = inp.get("message", "")
                remind_at = inp.get("remind_at", "")
                recurrence = inp.get("recurrence", "one_time")
                target_person_id = inp.get("target_person_id")

                if not title or not remind_at:
                    result = {"error": "title and remind_at are required for creating a reminder"}
                else:
                    # Resolve target email
                    if target_person_id:
                        person = execute_query(
                            "SELECT id, first_name, last_name, email FROM people WHERE id = ?",
                            [target_person_id],
                            instance_id=instance_id,
                        )
                    elif current_user and current_user.get("person_id"):
                        person = execute_query(
                            "SELECT id, first_name, last_name, email FROM people WHERE id = ?",
                            [current_user["person_id"]],
                            instance_id=instance_id,
                        )
                    else:
                        person = {"rows": []}

                    if not person.get("rows") or not person["rows"][0].get("email"):
                        result = {"error": "Could not find an email address for the target person. Make sure they have an email set in the people table."}
                    else:
                        p = person["rows"][0]
                        notify_email = p["email"]
                        notify_person_id = p["id"]
                        created_by = current_user["person_id"] if current_user and current_user.get("person_id") else None

                        ins = execute_query(
                            "INSERT INTO reminders (instance_id, title, message, remind_at, recurrence, notify_email, notify_person_id, created_by_person_id) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            [instance_id, title, message, remind_at, recurrence, notify_email, notify_person_id, created_by],
                            instance_id=instance_id,
                        )
                        if "error" in ins:
                            result = ins
                        else:
                            result = {
                                "success": True,
                                "reminder_id": ins.get("lastrowid"),
                                "title": title,
                                "remind_at": remind_at,
                                "recurrence": recurrence,
                                "notify_email": notify_email,
                                "notify_person": f"{p['first_name']} {p['last_name']}",
                            }

            elif action == "list":
                result = execute_query(
                    "SELECT r.id, r.title, r.message, r.remind_at, r.recurrence, r.status, "
                    "r.notify_email, r.last_sent_at, "
                    "p.first_name || ' ' || p.last_name AS notify_person_name "
                    "FROM reminders r "
                    "LEFT JOIN people p ON r.notify_person_id = p.id AND p.instance_id = r.instance_id "
                    "WHERE r.status IN ('active', 'paused') "
                    "ORDER BY r.remind_at",
                    instance_id=instance_id,
                )

            elif action == "cancel":
                reminder_id = inp.get("reminder_id")
                if not reminder_id:
                    result = {"error": "reminder_id is required for cancelling a reminder"}
                else:
                    upd = execute_query(
                        "UPDATE reminders SET status = 'cancelled' WHERE id = ?",
                        [reminder_id],
                        instance_id=instance_id,
                    )
                    if upd.get("rowcount", 0) == 0:
                        result = {"error": f"Reminder #{reminder_id} not found or already cancelled"}
                    else:
                        result = {"success": True, "cancelled_id": reminder_id}
            else:
                result = {"error": f"Unknown action: {action}"}

            sql_log.append({"tool": tool_name, "action": action, "result": result})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": _dumps(result),
            })

        elif tool_name == "invite_user":
            inp = block["input"]
            email = inp["email"].strip().lower()
            name = inp.get("name", "").strip()
            role = inp.get("role", "user")

            if user_role != "owner":
                result = {"error": "Only the instance owner can invite users."}
            elif role not in ("user", "admin"):
                result = {"error": "Role must be 'user' or 'admin'."}
            else:
                # Check if invitation already exists
                existing = execute_query(
                    "SELECT id, status FROM instance_invitations WHERE instance_id = ? AND email = ?",
                    [instance_id, email],
                    instance_id=None,
                )
                if existing.get("rows") and existing["rows"][0]["status"] == "pending":
                    result = {"error": f"An invitation for {email} is already pending."}
                else:
                    # Create or update invitation
                    if existing.get("rows"):
                        execute_query(
                            "UPDATE instance_invitations SET status = 'pending', role = ?, "
                            "expires_at = NOW() + INTERVAL '7 days' WHERE instance_id = ? AND email = ?",
                            [role, instance_id, email],
                            instance_id=None,
                        )
                    else:
                        execute_query(
                            "INSERT INTO instance_invitations (instance_id, email, role) VALUES (?, ?, ?)",
                            [instance_id, email, role],
                            instance_id=None,
                        )

                    # Send invitation email
                    from backend.config import APP_URL
                    email_result = smtp_send_email(
                        to_email=email,
                        subject=f"You're invited to join TrueCore.cloud",
                        body=(
                            f"Hi {name},\n\n"
                            f"You've been invited to join a TrueCore.cloud instance as a {role}.\n\n"
                            f"To accept this invitation:\n"
                            f"1. Go to {APP_URL}\n"
                            f"2. Sign up with this email address ({email})\n"
                            f"3. Click 'Join an Instance' to accept\n\n"
                            f"This invitation expires in 7 days.\n\n"
                            f"— TrueCore.cloud"
                        ),
                        to_name=name,
                    )
                    result = {
                        "success": True,
                        "email": email,
                        "role": role,
                        "email_sent": email_result,
                        "message": f"Invitation sent to {name} ({email}) as {role}.",
                    }

            sql_log.append({"tool": "invite_user", "action": f"Invite {email}", "result": result})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": _dumps(result),
            })

        elif tool_name == "reply_to_ticket":
            inp = block["input"]
            ticket_id = inp["ticket_id"]
            reply_body = inp["body"]
            update_status = inp.get("update_status")

            # Check email addon
            addon_check = execute_query(
                "SELECT email_addon, email_signature, inbound_email_addon FROM instances WHERE id = ?",
                [instance_id],
                instance_id=None,
            )
            if addon_check.get("rows") and not addon_check["rows"][0].get("email_addon"):
                result = {"error": "Email addon is not enabled for this instance."}
                sql_log.append({"tool": "reply_to_ticket", "action": f"Reply to ticket #{ticket_id}", "result": result})
                tool_results.append({"type": "tool_result", "tool_use_id": block["id"], "content": _dumps(result)})
                continue

            # Rate limit
            if not _check_email_rate_limit(instance_id):
                result = {"error": f"Email rate limit exceeded ({EMAIL_RATE_LIMIT_PER_HOUR}/hr)."}
                sql_log.append({"tool": "reply_to_ticket", "action": f"Reply to ticket #{ticket_id} (rate limited)", "result": result})
                tool_results.append({"type": "tool_result", "tool_use_id": block["id"], "content": _dumps(result)})
                continue

            # Look up ticket
            ticket_row = execute_query(
                "SELECT t.id, t.title, t.status, t.email_thread_id, t.requester_person_id, "
                "p.email AS requester_email, p.first_name AS requester_name "
                "FROM tickets t LEFT JOIN people p ON t.requester_person_id = p.id AND p.instance_id = t.instance_id "
                "WHERE t.id = ? AND t.instance_id = ?",
                [ticket_id, instance_id],
                instance_id=instance_id,
            )
            if not ticket_row.get("rows"):
                result = {"error": f"Ticket #{ticket_id} not found."}
                sql_log.append({"tool": "reply_to_ticket", "action": f"Reply to ticket #{ticket_id}", "result": result})
                tool_results.append({"type": "tool_result", "tool_use_id": block["id"], "content": _dumps(result)})
                continue

            ticket = ticket_row["rows"][0]
            requester_email = ticket.get("requester_email")
            if not requester_email:
                result = {"error": f"Ticket #{ticket_id} has no requester email on file."}
                sql_log.append({"tool": "reply_to_ticket", "action": f"Reply to ticket #{ticket_id}", "result": result})
                tool_results.append({"type": "tool_result", "tool_use_id": block["id"], "content": _dumps(result)})
                continue

            # Gather watchers
            watchers = execute_query(
                "SELECT p.email FROM ticket_watchers tw "
                "JOIN people p ON tw.person_id = p.id AND p.instance_id = tw.instance_id "
                "WHERE tw.ticket_id = ? AND tw.instance_id = ? AND p.email IS NOT NULL",
                [ticket_id, instance_id],
                instance_id=instance_id,
            )
            cc_emails = [w["email"] for w in (watchers.get("rows") or []) if w.get("email")]

            # Append email signature
            body = reply_body
            inst_row = addon_check.get("rows", [{}])[0]
            if inst_row.get("email_signature"):
                body = body + "\n\n" + inst_row["email_signature"]

            # Resolve attachments (download from S3 to temp for email)
            email_attachments = None
            temp_files = []
            file_ids = inp.get("attachment_file_ids") or []
            if file_ids:
                email_attachments = []
                for fid in file_ids:
                    resolved = resolve_s3_attachment_for_email(fid, instance_id)
                    if resolved:
                        email_attachments.append(resolved)
                        temp_files.append(resolved["path"])

            # Build threading headers
            from backend.config import INBOUND_EMAIL_DOMAIN
            thread_id = ticket.get("email_thread_id") or ""
            slug_row = execute_query(
                "SELECT slug FROM instances WHERE id = ?", [instance_id], instance_id=None,
            )
            slug = slug_row["rows"][0]["slug"] if slug_row.get("rows") else "unknown"
            reply_to_addr = f"{slug}+{ticket_id}@{INBOUND_EMAIL_DOMAIN}"

            email_result = smtp_send_email(
                to_email=requester_email,
                subject=f"Re: [Ticket #{ticket_id}] {ticket.get('title', '')}",
                body=body,
                to_name=ticket.get("requester_name", ""),
                reply_to_address=reply_to_addr,
                in_reply_to=thread_id,
                references=thread_id,
                cc_emails=cc_emails if cc_emails else None,
                attachments=email_attachments,
            )
            _record_email_send(instance_id)

            # Record reply
            execute_query(
                "INSERT INTO ticket_replies (instance_id, ticket_id, reply_body, reply_by_person_id, "
                "reply_to_email, direction) VALUES (?, ?, ?, ?, ?, 'outbound')",
                [instance_id, ticket_id, reply_body, person_id, requester_email],
                instance_id=instance_id,
            )

            # Timeline entry
            execute_query(
                "INSERT INTO ticket_timeline (instance_id, ticket_id, event_type, actor_person_id, "
                "detail) VALUES (?, ?, 'replied', ?, ?)",
                [instance_id, ticket_id, person_id, reply_body[:200]],
                instance_id=instance_id,
            )

            # Save attachments to ticket_attachments via S3
            if file_ids:
                from backend.s3_storage import upload_image as s3_upload_image
                for fid in file_ids:
                    chat_meta = get_chat_attachment_path(fid, instance_id)
                    if not chat_meta or not chat_meta.get("s3_key"):
                        continue
                    # Re-download from chat S3 path and re-upload to ticket path
                    from backend.s3_storage import download_image as s3_download
                    img_data, img_ct = s3_download(chat_meta["s3_key"])
                    s3_result = s3_upload_image(
                        instance_id=instance_id,
                        ticket_id=ticket_id,
                        file_id=fid,
                        image_bytes=img_data,
                        original_filename=chat_meta.get("filename", "image"),
                        content_type=img_ct,
                    )
                    execute_query(
                        "INSERT INTO ticket_attachments (instance_id, ticket_id, filename, original_filename, "
                        "content_type, file_size_bytes, storage_path, uploaded_by_person_id) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        [instance_id, ticket_id, os.path.basename(s3_result["s3_key"]),
                         chat_meta.get("filename", "image"), s3_result["content_type"],
                         s3_result["file_size_bytes"], s3_result["s3_key"], person_id],
                        instance_id=instance_id,
                    )
                    execute_query(
                        "INSERT INTO ticket_timeline (instance_id, ticket_id, event_type, actor_person_id, "
                        "detail) VALUES (?, ?, 'attachment_added', ?, ?)",
                        [instance_id, ticket_id, person_id, chat_meta.get("filename", "image")],
                        instance_id=instance_id,
                    )

            # Clean up temp files from email attachments
            for tf in temp_files:
                try:
                    os.remove(tf)
                except OSError:
                    pass

            # Optionally update status
            if update_status and update_status != ticket.get("status"):
                old_status = ticket.get("status", "open")
                execute_query(
                    "UPDATE tickets SET status = ? WHERE id = ? AND instance_id = ?",
                    [update_status, ticket_id, instance_id],
                    instance_id=instance_id,
                )
                execute_query(
                    "INSERT INTO ticket_timeline (instance_id, ticket_id, event_type, actor_person_id, "
                    "old_value, new_value) VALUES (?, ?, 'status_changed', ?, ?, ?)",
                    [instance_id, ticket_id, person_id, old_status, update_status],
                    instance_id=instance_id,
                )

            cc_note = f" (CC: {', '.join(cc_emails)})" if cc_emails else ""
            att_note = f" (+{len(email_attachments)} attachment(s))" if email_attachments else ""
            result = {
                "success": True,
                "message": f"Reply sent to {requester_email}{cc_note}{att_note}",
                "email_result": email_result,
            }

            sql_log.append({
                "tool": "reply_to_ticket",
                "action": f"Reply to ticket #{ticket_id} → {requester_email}{cc_note}{att_note}",
                "result": result,
            })
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": _dumps(result),
            })

    return tool_results


def _increment_query_count(instance_id: int) -> dict | None:
    """Increment the query count for an instance. Returns error dict if limit exceeded."""
    result = execute_query(
        "SELECT query_count, query_limit FROM instances WHERE id = ?",
        [instance_id],
        instance_id=None,
    )
    if not result.get("rows"):
        return {"error": "Instance not found"}

    row = result["rows"][0]
    if row["query_count"] >= row["query_limit"]:
        return {
            "error": "Query limit reached",
            "query_count": row["query_count"],
            "query_limit": row["query_limit"],
            "message": "This instance has reached its query limit. Please upgrade your plan to continue.",
        }

    execute_query(
        "UPDATE instances SET query_count = query_count + 1 WHERE id = ?",
        [instance_id],
        instance_id=None,
    )
    return None


def _charge_extra_queries(instance_id: int, extra: int) -> None:
    """Charge additional queries for token-heavy requests (fire-and-forget)."""
    if extra <= 0:
        return
    execute_query(
        "UPDATE instances SET query_count = query_count + ? WHERE id = ?",
        [extra, instance_id],
        instance_id=None,
    )


def chat_stream(
    user_message: str,
    history: list[dict[str, Any]],
    state: dict[str, Any],
    user_role: str = "admin",
    current_user: dict[str, Any] | None = None,
    instance_id: int = 1,
) -> Generator[str, None, None]:
    """Stream a chat response as SSE events.

    Yields SSE-formatted strings (event: type\\ndata: json\\n\\n).
    Populates state["history"] with the updated message history when done.
    """
    # Check query limit before processing
    limit_error = _increment_query_count(instance_id)
    if limit_error:
        yield f"event: token\ndata: {json.dumps({'text': limit_error['message']})}\n\n"
        yield f"event: done\ndata: {json.dumps({'sql_executed': []})}\n\n"
        return

    system_blocks = _build_system_blocks(user_role, current_user, instance_id=instance_id)
    messages = _trim_history(list(history), MAX_HISTORY_MESSAGES) + [{"role": "user", "content": user_message}]
    filtered_tools = _filter_tools(user_role)
    sql_log: list[dict[str, Any]] = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_creation_tokens = 0
    total_cache_read_tokens = 0
    api_calls = 0

    while True:
        try:
            with _get_client().messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=4096,
                system=system_blocks,
                tools=filtered_tools,
                messages=messages,
            ) as stream:
                for text_chunk in stream.text_stream:
                    yield f"event: token\ndata: {json.dumps({'text': text_chunk})}\n\n"
                response = stream.get_final_message()
        except (anthropic.RateLimitError, anthropic.AuthenticationError) as exc:
            if _swap_to_spare():
                yield f"event: token\ndata: {json.dumps({'text': ''})}\n\n"
                continue
            raise exc

        api_calls += 1
        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens
        total_cache_creation_tokens += getattr(response.usage, "cache_creation_input_tokens", 0)
        total_cache_read_tokens += getattr(response.usage, "cache_read_input_tokens", 0)
        assistant_content = _build_content(response)
        messages.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason == "end_turn":
            state["history"] = messages
            total_tokens = total_input_tokens + total_output_tokens + total_cache_creation_tokens + total_cache_read_tokens
            queries_consumed = max(1, math.ceil(total_tokens / QUERY_TOKEN_THRESHOLD))
            extra = queries_consumed - 1
            if extra > 0:
                _charge_extra_queries(instance_id, extra)
            execute_query(
                "INSERT INTO query_token_log (instance_id, total_input_tokens, total_output_tokens, cache_creation_tokens, cache_read_tokens, api_calls, queries_consumed) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [instance_id, total_input_tokens, total_output_tokens, total_cache_creation_tokens, total_cache_read_tokens, api_calls, queries_consumed],
                instance_id=None,
            )
            yield f"event: done\ndata: {json.dumps({'sql_executed': sql_log, 'tokens_used': total_tokens, 'queries_consumed': queries_consumed})}\n\n"
            return

        if response.stop_reason == "tool_use":
            sql_log_before = len(sql_log)
            tool_results = _execute_tools(assistant_content, sql_log, user_role, instance_id=instance_id, current_user=current_user)
            _truncate_tool_results(tool_results, MAX_TOOL_RESULT_CHARS)
            # Notify frontend about each SQL/file operation
            for entry in sql_log[sql_log_before:]:
                if entry.get("tool") == "generate_excel":
                    yield f"event: file\ndata: {json.dumps(entry)}\n\n"
                else:
                    yield f"event: sql\ndata: {json.dumps(entry)}\n\n"
            messages.append({"role": "user", "content": tool_results})


def chat(
    user_message: str,
    history: list[dict[str, Any]],
    user_role: str = "admin",
    current_user: dict[str, Any] | None = None,
    instance_id: int = 1,
) -> dict[str, Any]:
    """Non-streaming chat (kept as fallback)."""
    # Check query limit before processing
    limit_error = _increment_query_count(instance_id)
    if limit_error:
        return {
            "response": limit_error["message"],
            "sql_executed": [],
            "history": list(history) + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": [{"type": "text", "text": limit_error["message"]}]},
            ],
        }

    system_blocks = _build_system_blocks(user_role, current_user, instance_id=instance_id)
    messages = _trim_history(list(history), MAX_HISTORY_MESSAGES) + [{"role": "user", "content": user_message}]
    filtered_tools = _filter_tools(user_role)
    sql_log: list[dict[str, Any]] = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_creation_tokens = 0
    total_cache_read_tokens = 0
    api_calls = 0

    while True:
        try:
            response = _get_client().messages.create(
                model=CLAUDE_MODEL,
                max_tokens=4096,
                system=system_blocks,
                tools=filtered_tools,
                messages=messages,
            )
        except (anthropic.RateLimitError, anthropic.AuthenticationError) as exc:
            if _swap_to_spare():
                continue
            raise exc

        api_calls += 1
        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens
        total_cache_creation_tokens += getattr(response.usage, "cache_creation_input_tokens", 0)
        total_cache_read_tokens += getattr(response.usage, "cache_read_input_tokens", 0)
        assistant_content = _build_content(response)
        messages.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason == "end_turn":
            text_parts = [b["text"] for b in assistant_content if b["type"] == "text"]
            total_tokens = total_input_tokens + total_output_tokens + total_cache_creation_tokens + total_cache_read_tokens
            queries_consumed = max(1, math.ceil(total_tokens / QUERY_TOKEN_THRESHOLD))
            extra = queries_consumed - 1
            if extra > 0:
                _charge_extra_queries(instance_id, extra)
            execute_query(
                "INSERT INTO query_token_log (instance_id, total_input_tokens, total_output_tokens, cache_creation_tokens, cache_read_tokens, api_calls, queries_consumed) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [instance_id, total_input_tokens, total_output_tokens, total_cache_creation_tokens, total_cache_read_tokens, api_calls, queries_consumed],
                instance_id=None,
            )
            return {
                "response": "\n".join(text_parts),
                "sql_executed": sql_log,
                "history": messages,
                "tokens_used": total_tokens,
                "queries_consumed": queries_consumed,
            }

        if response.stop_reason == "tool_use":
            tool_results = _execute_tools(assistant_content, sql_log, user_role, instance_id=instance_id, current_user=current_user)
            _truncate_tool_results(tool_results, MAX_TOOL_RESULT_CHARS)
            messages.append({"role": "user", "content": tool_results})
