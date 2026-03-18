import io
import json
import re
import time
import uuid
from datetime import date
from typing import Any, Generator

import anthropic
from openpyxl import Workbook

from backend.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_API_KEY_SPARE,
    CLAUDE_MODEL,
    BREVO_SENDER_EMAIL,
    BREVO_SENDER_NAME,
)
from backend.database import execute_query, get_home_site, get_schema_ddl, validate_query
from backend.email_sender import send_email as smtp_send_email
from backend.prompts import SYSTEM_TEMPLATE, TOOLS

_TABLE_RE = re.compile(
    r"(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM|INTO)\s+(\w+)",
    re.IGNORECASE,
)

_OP_KEYWORDS = {"INSERT", "UPDATE", "DELETE"}


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
_schema_cache: str | None = None


def _get_cached_schema() -> str:
    global _schema_cache
    if _schema_cache is None:
        _schema_cache = get_schema_ddl()
    return _schema_cache


def clear_schema_cache() -> None:
    global _schema_cache
    _schema_cache = None


def clear_prompt_cache() -> None:
    _prompt_cache["approval"] = None
    _prompt_cache["home_site"] = None
    _prompt_cache["ts"] = 0


def _build_approval_section() -> str:
    rules = execute_query("SELECT id, description FROM approval_rules WHERE is_active = 1")
    count_result = execute_query("SELECT COUNT(*) as count FROM pending_approvals WHERE status = 'pending'")
    pending_count = count_result["rows"][0]["count"] if count_result.get("rows") else 0

    if not rules.get("rows"):
        return f"No approval rules configured. All write operations execute immediately.\nPending approvals: {pending_count}"

    lines = ["Active approval rules:"]
    for rule in rules["rows"]:
        lines.append(f"  - Rule #{rule['id']}: {rule['description']}")
    lines.append(f"Pending approvals awaiting review: {pending_count}")
    return "\n".join(lines)


def _build_home_site_section() -> str:
    site = get_home_site()
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


def _build_current_user_section(current_user: dict[str, Any] | None) -> str:
    if not current_user:
        return (
            "CURRENT USER:\n"
            "No current user record was resolved for this request. Do not infer personal details."
        )

    lines = [
        "CURRENT USER:",
        f"- person_id: {current_user['person_id']}",
        f"- name: {current_user['display_name']}",
        f"- username: {current_user['username']}",
        f"- role: {current_user['role']}",
        f"- email: {current_user['email'] or 'not set'}",
        f"- phone: {current_user['phone'] or 'not set'}",
        f"- title: {current_user['role_title'] or 'not set'}",
        f"- department: {current_user['department'] or 'not set'}",
        f"- site_id: {current_user['site_id'] if current_user['site_id'] is not None else 'not set'}",
        f"- site_name: {current_user['site_name'] or 'not set'}",
        f"- team_id: {current_user['team_id'] if current_user['team_id'] is not None else 'not set'}",
        f"- team_name: {current_user['team_name'] or 'not set'}",
    ]
    return "\n".join(lines)


_prompt_cache: dict = {"approval": None, "home_site": None, "ts": 0}


def _build_system_prompt(user_role: str = "admin", current_user: dict[str, Any] | None = None) -> str:
    now = time.time()
    if now - _prompt_cache["ts"] > 60:
        _prompt_cache["approval"] = _build_approval_section()
        _prompt_cache["home_site"] = _build_home_site_section()
        _prompt_cache["ts"] = now
    return SYSTEM_TEMPLATE.format(
        schema_ddl=_get_cached_schema(),
        today=date.today().isoformat(),
        sender_name=BREVO_SENDER_NAME,
        sender_email=BREVO_SENDER_EMAIL,
        home_site_section=_prompt_cache["home_site"],
        user_role_section=_build_user_role_section(user_role),
        current_user_section=_build_current_user_section(current_user),
        approval_section=_prompt_cache["approval"],
    )


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


def _execute_tools(assistant_content: list[dict], sql_log: list[dict], user_role: str = "admin") -> list[dict]:
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

            # Check if this is a data write that should go through approval
            is_data_write = sql_upper.startswith(("INSERT", "UPDATE", "DELETE"))
            if is_data_write and tool_name == "execute_sql":
                rules = execute_query("SELECT id, description FROM approval_rules WHERE is_active = 1")
                matched_rule = _find_matching_rule(sql, rules.get("rows") or [])
                if matched_rule:
                    validation = validate_query(sql)
                    if not validation.get("valid"):
                        result = {"error": f"SQL validation failed: {validation['error']}"}
                    else:
                        ins = execute_query(
                            "INSERT INTO pending_approvals (sql_statement, explanation, matched_rule_id, matched_rule_description) VALUES (?, ?, ?, ?)",
                            [sql, explanation, matched_rule["id"], matched_rule["description"]],
                        )
                        result = {
                            "queued": True,
                            "executed": False,
                            "approval_id": ins.get("lastrowid"),
                            "matched_rule": matched_rule["description"],
                            "message": "This query was NOT executed. It has been queued for admin approval because it matched an active approval rule. Tell the user their request is pending approval.",
                        }
                    sql_log.append({"tool": tool_name, "sql": sql, "explanation": explanation, "result": result})
                    tool_results.append({"type": "tool_result", "tool_use_id": block["id"], "content": json.dumps(result)})
                    continue

            result = execute_query(sql)

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
                "content": json.dumps(result),
            })

        elif tool_name == "manage_approval_rules":
            inp = block["input"]
            action = inp["action"]

            if action == "add":
                desc = inp.get("description", "")
                result = execute_query(
                    "INSERT INTO approval_rules (description) VALUES (?)",
                    [desc],
                )
                result["rule_id"] = result.get("lastrowid")
            elif action == "list":
                result = execute_query(
                    "SELECT id, description, is_active, created_at FROM approval_rules ORDER BY id"
                )
            elif action == "remove":
                rule_id = inp.get("rule_id")
                result = execute_query(
                    "UPDATE approval_rules SET is_active = 0 WHERE id = ?",
                    [rule_id],
                )
            else:
                result = {"error": f"Unknown action: {action}"}

            sql_log.append({"tool": tool_name, "action": action, "result": result})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": json.dumps(result),
            })

        elif tool_name == "submit_for_approval":
            inp = block["input"]
            validation = validate_query(inp["sql"])
            if not validation.get("valid"):
                result = {"error": f"SQL validation failed: {validation['error']}"}
            else:
                ins = execute_query(
                    "INSERT INTO pending_approvals (sql_statement, explanation, matched_rule_id, matched_rule_description) VALUES (?, ?, ?, ?)",
                    [inp["sql"], inp["explanation"], inp["matched_rule_id"], inp["matched_rule_description"]],
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
                "content": json.dumps(result),
            })

        elif tool_name == "review_approvals":
            inp = block["input"]
            action = inp["action"]

            if action == "list":
                result = execute_query(
                    "SELECT id, sql_statement, explanation, matched_rule_description, status, created_at FROM pending_approvals WHERE status = 'pending' ORDER BY created_at"
                )
            elif action == "approve":
                approval_id = inp.get("approval_id")
                approval = execute_query(
                    "SELECT sql_statement FROM pending_approvals WHERE id = ? AND status = 'pending'",
                    [approval_id],
                )
                if approval.get("rows"):
                    stored_sql = approval["rows"][0]["sql_statement"]
                    exec_result = execute_query(stored_sql)
                    if "error" in exec_result:
                        execute_query(
                            "UPDATE pending_approvals SET status = 'failed', review_note = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
                            [f"Execution failed: {exec_result['error']}", approval_id],
                        )
                        result = {"approved": False, "approval_id": approval_id, "execution_error": exec_result["error"]}
                    else:
                        execute_query(
                            "UPDATE pending_approvals SET status = 'approved', review_note = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
                            [inp.get("note", ""), approval_id],
                        )
                        result = {"approved": True, "approval_id": approval_id, "execution_result": exec_result}
                else:
                    result = {"error": f"Approval #{approval_id} not found or already reviewed"}
            elif action == "reject":
                approval_id = inp.get("approval_id")
                execute_query(
                    "UPDATE pending_approvals SET status = 'rejected', review_note = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
                    [inp.get("note", ""), approval_id],
                )
                result = {"rejected": True, "approval_id": approval_id}
            else:
                result = {"error": f"Unknown action: {action}"}

            sql_log.append({"tool": tool_name, "action": action, "result": result})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": json.dumps(result),
            })

        elif tool_name == "import_csv":
            from backend.routes.upload import generate_import_sql, remove_staged_file

            inp = block["input"]
            gen = generate_import_sql(inp["file_id"], inp["table"], inp["column_mapping"])

            if "error" in gen:
                result = gen
            else:
                # Validate the SQL before queuing or executing
                validation = validate_query(gen["sql"])
                if not validation.get("valid"):
                    result = {"error": f"SQL validation failed: {validation['error']}"}
                else:
                    # Check if any approval rules match this import
                    rules = execute_query("SELECT id, description FROM approval_rules WHERE is_active = 1")
                    matched_rule = _find_matching_rule(gen["sql"], rules.get("rows") or [])
                    if matched_rule:
                        approval_result = execute_query(
                            "INSERT INTO pending_approvals (sql_statement, explanation, matched_rule_id, matched_rule_description) VALUES (?, ?, ?, ?)",
                            [gen["sql"], inp.get("explanation", f"CSV import: {gen['total_rows']} rows into {gen['table']}"),
                             matched_rule["id"], matched_rule["description"]],
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
                        result = execute_query(gen["sql"])
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
                "content": json.dumps(result),
            })

        elif tool_name == "send_email":
            inp = block["input"]
            result = smtp_send_email(
                to_email=inp["to_email"],
                subject=inp["subject"],
                body=inp["body"],
                to_name=inp.get("to_name", ""),
            )

            sql_log.append({
                "tool": "send_email",
                "action": f"Email to {inp['to_email']}: {inp['subject']}",
                "result": result,
            })

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": json.dumps(result),
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
                    query_result = execute_query(sheet_def["sql"])
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
                "content": json.dumps(result),
            })

    return tool_results


def chat_stream(
    user_message: str,
    history: list[dict[str, Any]],
    state: dict[str, Any],
    user_role: str = "admin",
    current_user: dict[str, Any] | None = None,
) -> Generator[str, None, None]:
    """Stream a chat response as SSE events.

    Yields SSE-formatted strings (event: type\\ndata: json\\n\\n).
    Populates state["history"] with the updated message history when done.
    """
    system_prompt = _build_system_prompt(user_role, current_user)
    messages = list(history) + [{"role": "user", "content": user_message}]
    sql_log: list[dict[str, Any]] = []

    while True:
        try:
            with _get_client().messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=4096,
                system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                tools=TOOLS,
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

        assistant_content = _build_content(response)
        messages.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason == "end_turn":
            state["history"] = messages
            yield f"event: done\ndata: {json.dumps({'sql_executed': sql_log})}\n\n"
            return

        if response.stop_reason == "tool_use":
            sql_log_before = len(sql_log)
            tool_results = _execute_tools(assistant_content, sql_log, user_role)
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
) -> dict[str, Any]:
    """Non-streaming chat (kept as fallback)."""
    system_prompt = _build_system_prompt(user_role, current_user)
    messages = list(history) + [{"role": "user", "content": user_message}]
    sql_log: list[dict[str, Any]] = []

    while True:
        try:
            response = _get_client().messages.create(
                model=CLAUDE_MODEL,
                max_tokens=4096,
                system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                tools=TOOLS,
                messages=messages,
            )
        except (anthropic.RateLimitError, anthropic.AuthenticationError) as exc:
            if _swap_to_spare():
                continue
            raise exc

        assistant_content = _build_content(response)
        messages.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason == "end_turn":
            text_parts = [b["text"] for b in assistant_content if b["type"] == "text"]
            return {
                "response": "\n".join(text_parts),
                "sql_executed": sql_log,
                "history": messages,
            }

        if response.stop_reason == "tool_use":
            tool_results = _execute_tools(assistant_content, sql_log, user_role)
            messages.append({"role": "user", "content": tool_results})
