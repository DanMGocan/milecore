"""PostgreSQL database layer using psycopg v3 with connection pooling.

All tenant-scoped functions accept an ``instance_id`` parameter that sets a
PostgreSQL session variable (``app.current_instance_id``) so that Row-Level
Security policies can filter rows automatically.
"""

from __future__ import annotations

import re
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

# Global tables that are NOT tenant-scoped (excluded from schema DDL, table
# listings, and the reset operation).
_GLOBAL_TABLES = frozenset({
    "auth_users",
    "instances",
    "instance_memberships",
    "instance_invitations",
})

# Tables that must never be dropped/truncated and require WHERE on UPDATE/DELETE.
_PROTECTED_TABLES = _GLOBAL_TABLES | frozenset({
    "audit_log",
    "approval_rules",
    "pending_approvals",
    "chat_sessions",
    "chat_messages",
    "app_settings",
    "ticket_timeline",
    "checklist_responses",
    "inspection_records",
    "procurement_updates",
    "service_request_task_progress",
})

# SQL patterns that are always blocked through execute_query / validate_query.
_BLOCKED_SQL_PATTERNS = [
    re.compile(r"\bDROP\s+(TABLE|SCHEMA|INDEX|VIEW|FUNCTION|TRIGGER)\b", re.IGNORECASE),
    re.compile(r"\bTRUNCATE\b", re.IGNORECASE),
    re.compile(r"\bALTER\s+TABLE\s+\w+\s+DROP\b", re.IGNORECASE),
    re.compile(r"\bALTER\s+TABLE\s+\w+\s+RENAME\b", re.IGNORECASE),
]


def _check_sql_safety(sql: str) -> str | None:
    """Return an error message if *sql* is blocked, otherwise ``None``."""
    for pattern in _BLOCKED_SQL_PATTERNS:
        if pattern.search(sql):
            return f"Blocked: destructive SQL operation is not allowed ({pattern.pattern})"

    # DELETE / UPDATE on protected tables must have a WHERE clause.
    sql_stripped = sql.strip()
    sql_upper = sql_stripped.upper()

    delete_match = re.match(r"DELETE\s+FROM\s+(\w+)", sql_stripped, re.IGNORECASE)
    if delete_match:
        table = delete_match.group(1).lower()
        if table in _PROTECTED_TABLES and "WHERE" not in sql_upper:
            return f"Blocked: DELETE FROM {table} requires a WHERE clause"

    update_match = re.match(r"UPDATE\s+(\w+)", sql_stripped, re.IGNORECASE)
    if update_match:
        table = update_match.group(1).lower()
        if table in _PROTECTED_TABLES and "WHERE" not in sql_upper:
            return f"Blocked: UPDATE {table} requires a WHERE clause"

    return None


# ---------------------------------------------------------------------------
# Connection pool
# ---------------------------------------------------------------------------
_pool: ConnectionPool | None = None


def init_pool(dsn: str, *, min_size: int = 5, max_size: int = 20) -> None:
    """Create the global connection pool.

    Must be called once at application startup before any database access.

    Args:
        dsn: PostgreSQL connection string
             (e.g. ``"postgresql://user:pass@host:5432/dbname"``).
        min_size: Minimum number of connections kept open.
        max_size: Maximum number of connections the pool will create.
    """
    global _pool
    if _pool is not None:
        return  # Already initialised – idempotent
    _pool = ConnectionPool(
        conninfo=dsn,
        min_size=min_size,
        max_size=max_size,
        kwargs={"row_factory": dict_row},
    )


def shutdown_pool() -> None:
    """Close the global pool and release all connections."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def _get_pool() -> ConnectionPool:
    """Return the global pool, raising if it has not been initialised."""
    if _pool is None:
        raise RuntimeError(
            "Connection pool has not been initialised. Call init_pool() first."
        )
    return _pool


# ---------------------------------------------------------------------------
# Backward-compatibility: get_connection()
# ---------------------------------------------------------------------------

def get_connection() -> psycopg.Connection:
    """Return a connection from the pool.

    This is exported for files that still call ``get_connection()`` directly
    (e.g. dashboard.py, sessions.py).  Callers are responsible for closing /
    returning the connection (the pool context manager is preferred).
    """
    return _get_pool().getconn()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_instance(conn: psycopg.Connection, instance_id: int | None) -> None:
    """Set the ``app.current_instance_id`` session variable for RLS.

    The ``true`` parameter to ``set_config`` means the value is reset at
    transaction end.
    """
    if instance_id is not None:
        conn.execute(
            "SELECT set_config('app.current_instance_id', %s, true)",
            [str(instance_id)],
        )


def _translate_placeholders(sql: str) -> str:
    """Replace ``?`` placeholders with ``%s`` for psycopg.

    Only bare ``?`` tokens are replaced — occurrences inside string literals
    or identifiers are left alone.
    """
    # Fast path: nothing to translate
    if "?" not in sql:
        return sql

    # Walk the SQL character-by-character so we can skip string literals.
    out: list[str] = []
    i = 0
    length = len(sql)
    while i < length:
        ch = sql[i]
        if ch == "'":
            # Skip single-quoted string literal
            j = i + 1
            while j < length:
                if sql[j] == "'" and j + 1 < length and sql[j + 1] == "'":
                    j += 2  # escaped quote
                elif sql[j] == "'":
                    j += 1
                    break
                else:
                    j += 1
            out.append(sql[i:j])
            i = j
        elif ch == '"':
            # Skip double-quoted identifier
            j = i + 1
            while j < length:
                if sql[j] == '"' and j + 1 < length and sql[j + 1] == '"':
                    j += 2  # escaped quote
                elif sql[j] == '"':
                    j += 1
                    break
                else:
                    j += 1
            out.append(sql[i:j])
            i = j
        elif ch == "?":
            out.append("%s")
            i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Core query execution
# ---------------------------------------------------------------------------

def execute_query(
    sql: str,
    params: list | None = None,
    instance_id: int | None = None,
    *,
    _unsafe: bool = False,
) -> dict[str, Any]:
    """Execute a SQL statement and return results as a dict.

    For SELECT / PRAGMA-like queries the return dict contains:
        ``{"columns": [...], "rows": [...], "rowcount": N}``

    For write statements (INSERT / UPDATE / DELETE / CREATE / …):
        ``{"rowcount": N, "lastrowid": M}``

    On error:
        ``{"error": "message"}``

    If the SQL is an INSERT that does not already contain a ``RETURNING``
    clause, ``RETURNING id`` is appended automatically so that ``lastrowid``
    is populated.

    Args:
        sql: SQL statement.  May use ``?`` placeholders (translated to ``%s``).
        params: Optional bind parameters.
        instance_id: Tenant id — sets the RLS session variable.
    """
    if not _unsafe:
        safety_error = _check_sql_safety(sql)
        if safety_error:
            return {"error": safety_error}

    pool = _get_pool()
    sql_pg = _translate_placeholders(sql)
    sql_stripped = sql_pg.strip().upper()

    # Auto-append RETURNING id for INSERT when not already present
    is_insert = sql_stripped.startswith("INSERT")
    if is_insert and "RETURNING" not in sql_stripped:
        sql_pg = sql_pg.rstrip().rstrip(";") + " RETURNING id"

    with pool.connection() as conn:
        _set_instance(conn, instance_id)
        try:
            cur = conn.execute(sql_pg, params or [])

            if sql_stripped.startswith(("SELECT", "PRAGMA", "WITH")):
                columns = [desc.name for desc in cur.description] if cur.description else []
                rows = cur.fetchall()  # list[dict] thanks to dict_row
                return {"columns": columns, "rows": rows, "rowcount": len(rows)}

            # Write operation
            lastrowid: int | None = None
            if is_insert and cur.description:
                row = cur.fetchone()
                if row is not None:
                    # dict_row → {"id": <value>}
                    lastrowid = row.get("id") if isinstance(row, dict) else row[0]

            conn.commit()

            result: dict[str, Any] = {
                "rowcount": cur.rowcount if cur.rowcount and cur.rowcount >= 0 else 0,
                "lastrowid": lastrowid,
            }

            # Auto audit log for write operations
            _log_audit(conn, sql, lastrowid, instance_id)

            return result
        except Exception as e:
            conn.rollback()
            return {"error": str(e)}


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

def _log_audit(
    conn: psycopg.Connection,
    sql: str,
    lastrowid: int | None,
    instance_id: int | None,
) -> None:
    """Auto-populate ``audit_log`` for INSERT / UPDATE / DELETE operations.

    Uses the same connection so that the audit row is part of the same
    transaction context.  Failures are silently swallowed so as not to
    break the primary operation.
    """
    sql_upper = sql.strip().upper()

    # Avoid recursion — don't log writes to audit_log itself
    if "AUDIT_LOG" in sql_upper:
        return

    action: str | None = None
    table_name: str | None = None

    if sql_upper.startswith("INSERT"):
        action = "INSERT"
        match = re.search(r"INSERT\s+INTO\s+(\w+)", sql, re.IGNORECASE)
        if match:
            table_name = match.group(1)
    elif sql_upper.startswith("UPDATE"):
        action = "UPDATE"
        match = re.search(r"UPDATE\s+(\w+)", sql, re.IGNORECASE)
        if match:
            table_name = match.group(1)
    elif sql_upper.startswith("DELETE"):
        action = "DELETE"
        match = re.search(r"DELETE\s+FROM\s+(\w+)", sql, re.IGNORECASE)
        if match:
            table_name = match.group(1)

    if action and table_name:
        entity_id = lastrowid if lastrowid else 0
        try:
            _set_instance(conn, instance_id)
            conn.execute(
                "INSERT INTO audit_log (entity_type, entity_id, action, instance_id) "
                "VALUES (%s, %s, %s, %s)",
                [table_name, entity_id, action, instance_id],
            )
            conn.commit()
        except Exception:
            pass  # Don't fail the main operation if audit logging fails


# ---------------------------------------------------------------------------
# Query validation (dry-run via SAVEPOINT)
# ---------------------------------------------------------------------------

def validate_query(
    sql: str,
    params: list | None = None,
    instance_id: int | None = None,
) -> dict[str, Any]:
    """Dry-run a write query inside a SAVEPOINT.

    Returns ``{"valid": True, "rowcount": N}`` on success or
    ``{"valid": False, "error": "…"}`` on failure.  The database is never
    modified.
    """
    safety_error = _check_sql_safety(sql)
    if safety_error:
        return {"valid": False, "error": safety_error}

    pool = _get_pool()
    sql_pg = _translate_placeholders(sql)

    with pool.connection() as conn:
        _set_instance(conn, instance_id)
        try:
            conn.execute("SAVEPOINT validation")
            cur = conn.execute(sql_pg, params or [])
            rowcount = cur.rowcount if cur.rowcount and cur.rowcount >= 0 else 0
            conn.execute("ROLLBACK TO SAVEPOINT validation")
            conn.execute("RELEASE SAVEPOINT validation")
            return {"valid": True, "rowcount": rowcount}
        except Exception as e:
            try:
                conn.execute("ROLLBACK TO SAVEPOINT validation")
                conn.execute("RELEASE SAVEPOINT validation")
            except Exception:
                conn.rollback()
            return {"valid": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Schema introspection
# ---------------------------------------------------------------------------

# Columns present on every table — omitted from DDL to save tokens.
_SKIP_COLUMNS = {"instance_id", "id", "created_at", "updated_at"}

# One-line annotations with purpose + key enum values for each table.
_TABLE_ANNOTATIONS: dict[str, str] = {
    "sites": "-- Client sites/buildings. status: active|inactive",
    "floors": "-- Physical floors in a site. status: active|inactive",
    "zones": "-- Named areas within a floor. zone_type: general|office|common_area|restricted|storage|technical|reception|outdoor. status: active|inactive",
    "rooms": "-- Rooms/spaces in a site (linked via site_id, floor_id, zone_id). has_av (bool), capacity (int). status: active|inactive",
    "desks": "-- Hot desks. has_monitor, has_docking_station (bool). status: active|inactive",
    "parking_spaces": "-- Parking spots. space_type: standard|accessible|ev_charging|motorcycle. status: active|inactive",
    "lockers": "-- Storage lockers. locker_size: small|standard|large. status: active|inactive",
    "bookings": "-- Reservations for rooms/desks/parking/lockers/assets. resource_type: room|desk|parking_space|locker|asset. status: confirmed|cancelled|completed|no_show. source: chat|email",
    "companies": "-- Organisations. type: employer|client|vendor. category: hardware|software|services|telecom|av|facilities. status: active|inactive",
    "people": "-- All people. Link via employer_id (employee), client_id (client contact), vendor_id (vendor rep). is_user=1 → app user. team_role: lead|member|backup. user_role: user|admin|owner. status: active|inactive",
    "teams": "-- Named groups. team_type: support|av|operations|management",
    "pto": "-- PTO/leave records. leave_type: pto|sick|personal|bereavement|other",
    "assets": "-- Equipment. asset_type: laptop|desktop|monitor|printer|docking_station|av_equipment|network_device|phone|peripheral|other. lifecycle_status: active|deployed|spare|in_repair|pending_disposal|decommissioned|disposed|lost. ownership_type: company|leased|byod. criticality: low|medium|high|critical",
    "asset_relationships": "-- Parent/child links. relationship_type: connected_to|part_of|bundled_with|replaced_by",
    "asset_status_history": "-- Auto-logged lifecycle changes. Include changed_by_person_id and reason on manual changes",
    "asset_assignments": "-- Assignment history. Close old (end_date) before inserting new",
    "licenses": "-- Software licenses. license_type: perpetual|subscription|oem|volume|site|open_source. status: active|expired|cancelled",
    "software_installations": "-- Software on assets. Update licenses.seats_used on install/remove",
    "asset_documents": "-- Files attached to assets. document_type: warranty|invoice|manual|certificate|photo|general",
    "disposal_records": "-- Asset disposal. disposal_method: recycled|donated|sold|destroyed|returned_to_vendor|other",
    "tickets": "-- Support tickets. ticket_type: incident|service_request|question|access_request. priority: low|medium|high|critical. status: open|in_progress|pending|resolved|closed. source: walk_in|email|chat|phone|self_service",
    "ticket_replies": "-- Ticket email replies. direction: outbound|inbound",
    "ticket_watchers": "-- CC/watchers on tickets",
    "ticket_attachments": "-- Files attached to tickets",
    "ticket_timeline": "-- Ticket event audit trail. event_type: status_changed|priority_changed|assigned|replied|watcher_added|watcher_removed|attachment_added",
    "technical_issues": "-- Diagnosed technical problems. issue_type: hardware|software|network|av|printing|access|other. severity: low|medium|high|critical. recurrence_status: one_off|intermittent|recurring|resolved",
    "issue_occurrences": "-- Individual sightings of a technical issue. outcome: resolved|workaround_applied|escalated|unresolved",
    "events": "-- Scheduled events. event_type: meeting|outage|maintenance|audit|vendor_visit|training|deployment|other. status: planned|in_progress|completed|cancelled. impact_level: none|low|medium|high",
    "event_participants": "-- People in events. participant_role: organizer|attendee|presenter|observer. attendance_status: confirmed|tentative|declined|attended|no_show",
    "event_assets": "-- Assets for events. usage_role: primary|backup|demo|deployment",
    "notes": "-- Freeform notes. note_type: general|handover|follow_up|observation|escalation. visibility: internal|client_visible",
    "work_logs": "-- Technician work records. action_type: troubleshooting|repair|installation|configuration|inspection|consultation|escalation|other",
    "inventory_items": "-- Spare parts catalog. item_type: spare_part|consumable|cable|adapter|peripheral|component. unit_of_measure: each|box|pack|roll",
    "inventory_stock": "-- Stock levels per item per site/room. Always insert inventory_transaction when changing",
    "inventory_transactions": "-- Stock movement log. transaction_type: check_in|check_out|restock|transfer|write_off|adjustment",
    "changes": "-- Change management. change_type: standard|emergency|normal. risk_level: low|medium|high. status: planned|approved|in_progress|completed|rolled_back|cancelled",
    "vendor_contracts": "-- Contracts/SLAs. contract_type: support|lease|maintenance|subscription|project. status: active|expired|pending_renewal|terminated",
    "projects": "-- Project tracking. status: planned|active|on_hold|completed|cancelled. priority: low|medium|high|critical. category: infrastructure|operations|maintenance|deployment|migration|other",
    "project_members": "-- People in projects. role: manager|contributor|stakeholder|observer",
    "project_tasks": "-- Work items in a project. Nestable via parent_task_id. status: todo|in_progress|done|blocked|cancelled. priority: low|medium|high|critical",
    "project_updates": "-- Progress log entries. update_type: progress|blocker|decision|milestone|general",
    "project_expenses": "-- Budget line items. category: hardware|software|services|labor|travel|other",
    "project_links": "-- Links project to other entities. entity_type = table name, entity_id = record id",
    "knowledge_articles": "-- Troubleshooting guides/SOPs. article_type: troubleshooting|how_to|sop|reference|faq. status: draft|published|archived",
    "misc_knowledge": "-- Operational knowledge. AI generates keywords from content",
    "workflows": "-- Step-by-step procedures. status: draft|published|archived",
    "tags": "-- Tag definitions",
    "entity_tags": "-- Tag assignments. entity_type = table name, entity_id = record id",
    "audit_log": "-- Auto-logged data changes (read-only). action: INSERT|UPDATE|DELETE",
    "reminders": "-- Email reminders. recurrence: one_time|daily|weekly|monthly. status: active|paused|cancelled|completed",
    "maintenance_tasks": "-- Reusable maintenance templates. category: hvac|electrical|plumbing|fire_safety|elevator|cleaning|it_infrastructure|av_equipment|security|structural|landscaping|general",
    "checklist_templates": "-- Reusable checklist definitions. checklist_type: maintenance|inspection|safety|audit|commissioning|decommission",
    "checklist_template_items": "-- Items in a checklist. item_type: pass_fail|yes_no|numeric|text|photo|rating",
    "maintenance_plans": "-- Recurring maintenance schedules. plan_type: preventive|predictive|corrective|condition_based. recurrence: daily|weekly|biweekly|monthly|quarterly|semi_annual|annual|custom",
    "maintenance_plan_tasks": "-- Junction: tasks in plans",
    "inspections": "-- Recurring inspection schedules. inspection_type: safety|compliance|routine|condition|regulatory|quality",
    "work_orders": "-- Maintenance work instances. wo_type: preventive|corrective|emergency|inspection|condition_based. status: open|scheduled|in_progress|on_hold|completed|cancelled|overdue. source: manual|scheduled|ticket|inspection_failure",
    "inspection_records": "-- Performed inspections. overall_result: pass|fail|partial|na",
    "checklist_responses": "-- Checklist answers for work orders or inspections",
    "work_order_parts": "-- Inventory consumed during maintenance",
    "service_catalog": "-- Available services. category: onboarding|offboarding|workplace|it_access|equipment|facilities|av_support|security|moves|general. status: active|inactive|archived",
    "service_request_templates": "-- Form fields for service requests. field_type: text|textarea|date|datetime|number|select|person|site|room|desk|asset|boolean",
    "request_fulfillment_tasks": "-- Template fulfillment steps for a service",
    "service_requests": "-- Submitted service requests. status: submitted|pending_approval|approved|in_progress|on_hold|completed|cancelled|rejected",
    "service_request_task_progress": "-- Fulfillment task completion tracking. status: pending|in_progress|completed|skipped|blocked",
}


def get_schema_ddl(instance_id: int | None = None) -> str:
    """Build a compact schema reference for the AI.

    Uses a one-line-per-table format with boilerplate columns (id,
    instance_id, created_at, updated_at) and DEFAULT clauses omitted
    to minimise token count.
    """
    pool = _get_pool()

    with pool.connection() as conn:
        _set_instance(conn, instance_id)
        cur = conn.execute(
            """
            SELECT table_name, column_name, data_type,
                   is_nullable, column_default, ordinal_position
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
            """
        )
        rows = cur.fetchall()

    # Group columns by table
    tables: dict[str, list[dict]] = {}
    for row in rows:
        tname = row["table_name"]
        if tname in _GLOBAL_TABLES:
            continue
        if row["column_name"] in _SKIP_COLUMNS:
            continue
        tables.setdefault(tname, []).append(row)

    header = "-- All tables include: id (PK), instance_id, created_at, updated_at (omitted below)\n"
    lines: list[str] = [header]
    for tname in sorted(tables):
        annotation = _TABLE_ANNOTATIONS.get(tname, "")
        cols = []
        for col in tables[tname]:
            parts = [col["column_name"], col["data_type"].upper()]
            if col["is_nullable"] == "NO":
                parts.append("NOT NULL")
            cols.append(" ".join(parts))
        line = f"{tname}: {', '.join(cols)}" if cols else tname
        if annotation:
            line = f"{annotation}\n{line}"
        lines.append(line)

    return "\n\n".join(lines)


def get_tables(instance_id: int | None = None) -> list[str]:
    """Return a sorted list of public table names, excluding global tables."""
    pool = _get_pool()

    with pool.connection() as conn:
        _set_instance(conn, instance_id)
        cur = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
        rows = cur.fetchall()

    return [r["table_name"] for r in rows if r["table_name"] not in _GLOBAL_TABLES]


def get_table_schema(table_name: str) -> list[dict[str, Any]]:
    """Return column metadata for *table_name*.

    Each dict contains: ``name``, ``type``, ``notnull``, ``pk``,
    ``default_value``.
    """
    if not re.match(r"^\w+$", table_name):
        return []

    pool = _get_pool()

    with pool.connection() as conn:
        cur = conn.execute(
            """
            SELECT c.column_name, c.data_type, c.is_nullable, c.column_default,
                   CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END AS is_pk
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                WHERE tc.table_name = %s
                    AND tc.constraint_type = 'PRIMARY KEY'
            ) pk ON pk.column_name = c.column_name
            WHERE c.table_name = %s AND c.table_schema = 'public'
            ORDER BY c.ordinal_position
            """,
            [table_name, table_name],
        )
        rows = cur.fetchall()

    return [
        {
            "name": row["column_name"],
            "type": row["data_type"],
            "notnull": row["is_nullable"] == "NO",
            "pk": bool(row["is_pk"]),
            "default_value": row["column_default"],
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Table data access
# ---------------------------------------------------------------------------

def get_table_rows(
    table_name: str,
    limit: int = 50,
    offset: int = 0,
    instance_id: int | None = None,
) -> dict[str, Any]:
    """Return paginated rows from *table_name*.

    Returns ``{"columns": [...], "rows": [...], "total": N}``.
    """
    if not re.match(r"^\w+$", table_name):
        return {"error": "Invalid table name"}

    pool = _get_pool()

    with pool.connection() as conn:
        _set_instance(conn, instance_id)

        # Total count
        count_cur = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM {table_name} WHERE instance_id = %s",
            [instance_id],
        )
        total = count_cur.fetchone()["cnt"]

        cur = conn.execute(
            f"SELECT * FROM {table_name} WHERE instance_id = %s "
            f"LIMIT %s OFFSET %s",
            [instance_id, limit, offset],
        )
        columns = [desc.name for desc in cur.description] if cur.description else []
        rows = cur.fetchall()

    return {"columns": columns, "rows": rows, "total": total}


def get_all_table_rows(
    table_name: str,
    instance_id: int | None = None,
) -> tuple[list[str], list[tuple]]:
    """Return ``(column_names, rows)`` for all rows in *table_name*.

    Rows are returned as tuples for backward compatibility with the Excel
    export code.
    """
    if not re.match(r"^\w+$", table_name):
        return [], []

    pool = _get_pool()

    with pool.connection() as conn:
        _set_instance(conn, instance_id)
        cur = conn.execute(
            f"SELECT * FROM {table_name} WHERE instance_id = %s",
            [instance_id],
        )
        columns = [desc.name for desc in cur.description] if cur.description else []
        rows = cur.fetchall()

    # Convert dict rows to tuples
    return columns, [tuple(r[c] for c in columns) for r in rows]


# ---------------------------------------------------------------------------
# Home site
# ---------------------------------------------------------------------------

def get_home_site(instance_id: int | None = None) -> dict[str, Any] | None:
    """Return the configured home site or ``None``."""
    pool = _get_pool()

    with pool.connection() as conn:
        _set_instance(conn, instance_id)
        cur = conn.execute(
            "SELECT s.id, s.name, c.name AS client_name, s.city "
            "FROM app_settings a "
            "JOIN sites s ON s.id = CAST(a.value AS INTEGER) "
            "LEFT JOIN companies c ON s.client_id = c.id "
            "WHERE a.key = 'home_site_id' AND a.instance_id = %s",
            [instance_id],
        )
        row = cur.fetchone()

    if row is None:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "client_name": row["client_name"],
        "city": row["city"],
    }


# ---------------------------------------------------------------------------
# Database initialisation / reset
# ---------------------------------------------------------------------------

def init_db(schema_path: str) -> None:
    """Initialise the database from a SQL schema file.

    Drops and recreates the public schema so the database always matches
    the current schema file exactly.  Safe to call on every startup.
    """
    with open(schema_path, "r") as f:
        schema_sql = f.read()

    pool = _get_pool()

    with pool.connection() as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        conn.commit()

        # Split on semicolons but respect $$-quoted blocks (e.g. trigger functions)
        statements = []
        current = []
        in_dollar_quote = False
        for line in schema_sql.splitlines():
            stripped = line.strip()
            # Track $$ delimiters
            count = stripped.count('$$')
            if count % 2 == 1:
                in_dollar_quote = not in_dollar_quote
            current.append(line)
            if not in_dollar_quote and stripped.endswith(';'):
                stmt = '\n'.join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
        for stmt in statements:
            conn.execute(stmt)
        conn.commit()


def reset_instance(instance_id: int) -> None:
    """Delete all tenant-scoped data for *instance_id*.

    Tables are deleted in an order that respects foreign-key constraints
    (children first).  This replaces the old ``reset_db`` which dropped and
    recreated tables.
    """
    # Ordered from leaf tables (most dependent) to parent tables.
    tenant_tables = [
        "procurement_updates",
        "procurement_requests",
        "work_order_parts",
        "checklist_responses",
        "work_orders",
        "inspection_records",
        "inspections",
        "maintenance_plan_tasks",
        "maintenance_plans",
        "checklist_template_items",
        "checklist_templates",
        "maintenance_tasks",
        "reminders",
        "bookings",
        "project_links",
        "project_expenses",
        "project_updates",
        "project_tasks",
        "project_members",
        "projects",
        "audit_log",
        "chat_messages",
        "chat_sessions",
        "pending_approvals",
        "approval_rules",
        "inventory_transactions",
        "work_logs",
        "workflows",
        "notes",
        "changes",
        "events",
        "ticket_replies",
        "ticket_watchers",
        "ticket_attachments",
        "ticket_timeline",
        "technical_issues",
        "tickets",
        "disposal_records",
        "asset_documents",
        "software_installations",
        "licenses",
        "asset_assignments",
        "asset_status_history",
        "asset_relationships",
        "assets",
        "inventory_items",
        "rooms",
        "desks",
        "parking_spaces",
        "lockers",
        "zones",
        "floors",
        "people",
        "teams",
        "sites",
        "companies",
        "app_settings",
    ]

    pool = _get_pool()

    with pool.connection() as conn:
        _set_instance(conn, instance_id)
        for table in tenant_tables:
            try:
                conn.execute(
                    f"DELETE FROM {table} WHERE instance_id = %s",
                    [instance_id],
                )
            except Exception:
                pass  # Table may not exist yet
        conn.commit()


reset_db = reset_instance
