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
from backend.database import execute_query, get_home_site, get_schema_ddl
from backend.email_sender import send_email as smtp_send_email

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


def _build_home_site_section() -> str:
    site = get_home_site()
    if site is None:
        return (
            "HOME SITE:\n"
            "No home site is configured yet. Your FIRST priority before anything else is to help the user set one.\n"
            'Ask: "What site is this MileCore instance for? Give me the client name and city (e.g., Workday Dublin or Google Paris)."\n'
            "When they answer, INSERT the site into the sites table (with client_name and city, and name as 'ClientName CityName'), "
            "then INSERT into app_settings (key='home_site_id', value=the new site's id).\n"
            "Do NOT process any other requests until the home site is set."
        )
    return (
        "HOME SITE:\n"
        f"This instance serves {site['client_name']} in {site['city']} (site_id: {site['id']}). "
        "Default all operations to this site unless the user specifies otherwise."
    )


def _build_system_prompt() -> str:
    return SYSTEM_TEMPLATE.format(
        schema_ddl=_get_cached_schema(),
        today=date.today().isoformat(),
        sender_name=BREVO_SENDER_NAME,
        sender_email=BREVO_SENDER_EMAIL,
        home_site_section=_build_home_site_section(),
    )


TOOLS = [
    {
        "name": "execute_sql",
        "description": (
            "Execute a SQL query against the SQLite database. "
            "Use SELECT for retrieving data, INSERT for storing new data, "
            "UPDATE for modifying existing data, DELETE for removing data. "
            "Always use the correct table and column names from the schema provided. "
            "For dates, use ISO 8601 format (YYYY-MM-DD). "
            "You can call this tool multiple times to perform multi-step operations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "The SQL query to execute",
                },
                "explanation": {
                    "type": "string",
                    "description": "Brief explanation of what this query does",
                },
            },
            "required": ["sql", "explanation"],
        },
    },
    {
        "name": "create_table",
        "description": (
            "Create a new table in the database when the user wants to store data "
            "that doesn't fit any existing table. Check the schema first — the database "
            "already has 25+ tables covering most site operations scenarios. "
            "Only use this if the data truly doesn't fit anywhere."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "The CREATE TABLE SQL statement",
                },
                "explanation": {
                    "type": "string",
                    "description": "Why this new table is needed",
                },
            },
            "required": ["sql", "explanation"],
        },
    },
    {
        "name": "send_email",
        "description": (
            "Send an email to a recipient via SMTP. "
            "Before calling this tool, ALWAYS look up the recipient's email address "
            "from the people table using execute_sql first. "
            "Only call this tool when you have a confirmed email address."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "to_email": {
                    "type": "string",
                    "description": "The recipient's email address",
                },
                "to_name": {
                    "type": "string",
                    "description": "The recipient's display name (optional)",
                },
                "subject": {
                    "type": "string",
                    "description": "The email subject line",
                },
                "body": {
                    "type": "string",
                    "description": "The plain text email body",
                },
            },
            "required": ["to_email", "subject", "body"],
        },
    },
]

SYSTEM_TEMPLATE = """You are MileCore, an intelligent AI database assistant for technical site operations. You help IT support teams, tech bar technicians, AV support teams, and workplace technology teams store and retrieve operational information.

You interact with a SQLite database using SQL queries. The database tracks the full operational lifecycle:
Person reports problem → Request created → Asset involved → Issue diagnosed → Work performed → Resolution recorded → Knowledge captured.

{home_site_section}

CURRENT DATABASE SCHEMA:
{schema_ddl}

INSTRUCTIONS:
- When the user wants to STORE information, determine the correct table(s) and generate INSERT statements using the execute_sql tool.
- When the user wants to RETRIEVE information, generate SELECT statements. Use JOINs when data spans multiple tables.
- When storing data that spans multiple tables (e.g., a person reporting an issue about an asset), perform multiple INSERT operations in sequence.
- If data doesn't fit any existing table (rare — the schema is comprehensive), use the create_table tool first.
- If the user's request is ambiguous, ask a clarifying question rather than guessing.
- Never DROP tables or DELETE data unless the user explicitly asks.
- For dates, use ISO 8601 format (YYYY-MM-DD). For timestamps, use YYYY-MM-DD HH:MM:SS.
- When searching, use LIKE with wildcards for flexible text matching.
- If a query returns no results, say so clearly and suggest what the user might try instead.
- TIME-BASED STATUS QUERIES: When the user asks about records within a time range based on a status (e.g. "assets decommissioned last month", "requests closed this week"), use the `updated_at` column to filter by when the status change happened. Always combine the status filter with the date range on `updated_at`. For example, decommissioned assets in March: `WHERE lifecycle_status = 'decommissioned' AND updated_at >= '2026-03-01' AND updated_at < '2026-04-01'`. Use the same pattern for requests (status + opened_at/closed_at/resolved_at), events (status + start_time), etc. Be consistent — the same question must always produce the same query logic.

FORMATTING:
- Write in natural, conversational sentences — like a helpful coworker, not a report generator.
- NEVER use markdown tables (no pipes or dashes grids). Present structured data in short bullet lists or flowing sentences.
- Use bold (**text**) sparingly for key values like names, statuses, or dates.
- Keep confirmations brief: "Done! I added..." or "Here's what I found:" followed by a few bullet points.
- For query results with many rows, use a compact list format, not a table.
- Today's date is {today}. Use this for relative date references like "today", "tomorrow", "yesterday".

INTENT GUIDANCE:
- Issues/problems with devices → technical_issues table
- Support tickets/requests → requests table
- Operational notes → notes table
- Events/meetings/outages → events table
- Technician work records → work_logs table
- Equipment/devices → assets table
- Spare parts/consumables → inventory_items + inventory_stock tables
- Troubleshooting guides → knowledge_articles table
- People/contacts → people table (use site_id to link to their site when location is mentioned)
- Locations/rooms → locations table (linked to sites)
- Sending emails → send_email tool (look up email from people table first)

IMPORTANT FLAG:
- The following tables have an `important` column (INTEGER, 0 or 1): technical_issues, requests, events, notes, changes, work_logs, assets, inventory_transactions.
- When the user says something is "important", "flag this", "mark as important", or "high priority" (in the context of flagging), set important=1 on the relevant record.
- When the user asks to see "important items" or "flagged items", query WHERE important = 1.
- When inserting new records that the user explicitly describes as important, set important=1.
- To unflag, set important=0.

SITE SUPERVISORS & DAILY REPORTS:
- People with person_type or role_title containing "supervisor" or "site manager" are considered site supervisors.
- A daily report is automatically sent every morning to site supervisors with: new issues, vendor visits, and important-flagged items.
- When adding people who are supervisors, use person_type='site_supervisor' so they receive daily reports.

EMAIL:
- When the user asks to send an email, FIRST use execute_sql to look up the recipient's email address from the people table.
- If the person is not found or has no email on file, tell the user and do NOT call send_email.
- If you find the email, call the send_email tool with the resolved address, a clear subject line, and the message body.
- Always tell the user who you are emailing and what the message says.
- The sender is always {sender_name} ({sender_email}) — you cannot change this.

SCOPE — IMPORTANT:
You are strictly a workplace IT and site operations assistant. You must ONLY respond to queries related to:
- IT support, technical issues, assets, devices, and equipment
- Site operations, facilities, locations, and rooms
- Support requests, tickets, and work logs
- People, teams, and contacts in a workplace context
- Inventory, spare parts, and consumables
- Events, meetings, outages, and change management
- Vendors, contracts, and SLAs
- Knowledge articles and troubleshooting guides
- Sending work-related emails to people in the system

If a user asks something outside this scope — personal questions, general knowledge, creative writing, coding help, opinions, news, entertainment, homework, or anything unrelated to IT site operations — politely decline and redirect them. Example response:
"I'm MileCore, your site operations assistant — I'm built to help with IT support, assets, requests, and workplace operations. I can't help with that, but is there anything site-ops related I can assist with?"

Do NOT comply with off-topic requests even if the user insists. Stay in your lane.
"""


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


def _execute_tools(assistant_content: list[dict], sql_log: list[dict]) -> list[dict]:
    """Execute tool calls and return tool_result messages. Mutates sql_log."""
    tool_results = []
    for block in assistant_content:
        if block["type"] != "tool_use":
            continue

        tool_name = block["name"]

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


def chat_stream(user_message: str, history: list[dict[str, Any]], state: dict[str, Any]) -> Generator[str, None, None]:
    """Stream a chat response as SSE events.

    Yields SSE-formatted strings (event: type\\ndata: json\\n\\n).
    Populates state["history"] with the updated message history when done.
    """
    system_prompt = _build_system_prompt()
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
            tool_results = _execute_tools(assistant_content, sql_log)
            # Notify frontend about each SQL operation
            for entry in sql_log[len(sql_log) - len(tool_results):]:
                yield f"event: sql\ndata: {json.dumps(entry)}\n\n"
            messages.append({"role": "user", "content": tool_results})


def chat(user_message: str, history: list[dict[str, Any]]) -> dict[str, Any]:
    """Non-streaming chat (kept as fallback)."""
    system_prompt = _build_system_prompt()
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
            tool_results = _execute_tools(assistant_content, sql_log)
            messages.append({"role": "user", "content": tool_results})
