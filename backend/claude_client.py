import json
from datetime import date
from typing import Any, Generator

import anthropic

from backend.config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    BREVO_SENDER_EMAIL,
    BREVO_SENDER_NAME,
)
from backend.database import execute_query, get_home_site, get_schema_ddl, validate_query
from backend.email_sender import send_email as smtp_send_email
from backend.prompts import SYSTEM_TEMPLATE, TOOLS

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

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
            "No home site is configured yet. Your FIRST priority before anything else is to help the user set one.\n"
            'Ask: "What site is this MileCore instance for? Give me the client name and city (e.g., Workday Dublin or Google Paris)."\n'
            "When they answer, INSERT the client into companies (type='client'), then INSERT the site into sites (with client_id and city, and name as 'ClientName CityName'), "
            "then INSERT into app_settings (key='home_site_id', value=the new site's id).\n"
            "Do NOT process any other requests until the home site is set."
        )
    return (
        "HOME SITE:\n"
        f"This instance serves {site['client_name']} in {site['city']} (site_id: {site['id']}). "
        "Default all operations to this site unless the user specifies otherwise."
    )


def _build_user_role_section(user_role: str) -> str:
    if user_role == "admin":
        return (
            "USER ROLE:\n"
            "The current user is an admin. They can manage approval rules and review pending approvals."
        )
    return (
        "USER ROLE:\n"
        "The current user is a standard user. They CANNOT manage approval rules or review/approve "
        "pending approvals. If they attempt these actions, politely tell them this requires admin access."
    )


def _build_system_prompt(user_role: str = "admin") -> str:
    return SYSTEM_TEMPLATE.format(
        schema_ddl=_get_cached_schema(),
        today=date.today().isoformat(),
        sender_name=BREVO_SENDER_NAME,
        sender_email=BREVO_SENDER_EMAIL,
        home_site_section=_build_home_site_section(),
        user_role_section=_build_user_role_section(user_role),
        approval_section=_build_approval_section(),
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

        if user_role != "admin" and tool_name in ADMIN_ONLY_TOOLS:
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": json.dumps({"error": "This action requires admin access."}),
            })
            continue

        if tool_name in ("execute_sql", "create_table"):
            sql = block["input"]["sql"]
            explanation = block["input"].get("explanation", "")
            result = execute_query(sql)

            sql_log.append({
                "tool": tool_name,
                "sql": sql,
                "explanation": explanation,
                "result": result,
            })

            if tool_name == "create_table":
                clear_schema_cache()
            elif tool_name == "execute_sql":
                sql_upper = sql.strip().upper()
                if sql_upper.startswith(("CREATE", "DROP", "ALTER")):
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
                result = execute_query(
                    "INSERT INTO pending_approvals (sql_statement, explanation, matched_rule_id, matched_rule_description) VALUES (?, ?, ?, ?)",
                    [inp["sql"], inp["explanation"], inp["matched_rule_id"], inp["matched_rule_description"]],
                )
                result["queued"] = True
                result["approval_id"] = result.get("lastrowid")

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
            from backend.routes.upload import generate_import_sql

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
                    # Check if any approval rules are active
                    rules = execute_query("SELECT id, description FROM approval_rules WHERE is_active = 1")
                    if rules.get("rows"):
                        # Approval rules exist — queue for approval
                        first_rule = rules["rows"][0]
                        approval_result = execute_query(
                            "INSERT INTO pending_approvals (sql_statement, explanation, matched_rule_id, matched_rule_description) VALUES (?, ?, ?, ?)",
                            [gen["sql"], inp.get("explanation", f"CSV import: {gen['total_rows']} rows into {gen['table']}"),
                             first_rule["id"], first_rule["description"]],
                        )
                        result = {
                            "queued": True,
                            "approval_id": approval_result.get("lastrowid"),
                            "total_rows": gen["total_rows"],
                            "message": f"Import of {gen['total_rows']} rows into {gen['table']} queued for approval",
                        }
                    else:
                        # No rules — execute directly
                        result = execute_query(gen["sql"])
                        result["rows_inserted"] = result.get("rowcount", 0)
                        result["skipped"] = gen["skipped"]

            sql_log.append({
                "tool": tool_name,
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

    return tool_results


def chat_stream(user_message: str, history: list[dict[str, Any]], state: dict[str, Any], user_role: str = "admin") -> Generator[str, None, None]:
    """Stream a chat response as SSE events.

    Yields SSE-formatted strings (event: type\\ndata: json\\n\\n).
    Populates state["history"] with the updated message history when done.
    """
    system_prompt = _build_system_prompt(user_role)
    messages = list(history) + [{"role": "user", "content": user_message}]
    sql_log: list[dict[str, Any]] = []

    while True:
        with client.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        ) as stream:
            for text_chunk in stream.text_stream:
                yield f"event: token\ndata: {json.dumps({'text': text_chunk})}\n\n"
            response = stream.get_final_message()

        assistant_content = _build_content(response)
        messages.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason == "end_turn":
            state["history"] = messages
            yield f"event: done\ndata: {json.dumps({'sql_executed': sql_log})}\n\n"
            return

        if response.stop_reason == "tool_use":
            tool_results = _execute_tools(assistant_content, sql_log, user_role)
            # Notify frontend about each SQL operation
            for entry in sql_log[len(sql_log) - len(tool_results):]:
                yield f"event: sql\ndata: {json.dumps(entry)}\n\n"
            messages.append({"role": "user", "content": tool_results})


def chat(user_message: str, history: list[dict[str, Any]], user_role: str = "admin") -> dict[str, Any]:
    """Non-streaming chat (kept as fallback)."""
    system_prompt = _build_system_prompt(user_role)
    messages = list(history) + [{"role": "user", "content": user_message}]
    sql_log: list[dict[str, Any]] = []

    while True:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

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
