import re
import sqlite3
import threading
from typing import Any

from backend.config import DATABASE_PATH

_lock = threading.Lock()
_connection: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA foreign_keys=ON")
    return _connection


def close_connection() -> None:
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


def get_schema_ddl() -> str:
    conn = get_connection()
    cursor = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL ORDER BY name"
    )
    statements = [row[0] for row in cursor.fetchall()]
    return ";\n\n".join(statements) + ";" if statements else ""


def execute_query(sql: str, params: list | None = None) -> dict[str, Any]:
    conn = get_connection()
    sql_stripped = sql.strip().upper()

    with _lock:
        try:
            cursor = conn.execute(sql, params or [])

            if sql_stripped.startswith("SELECT") or sql_stripped.startswith("PRAGMA"):
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = [dict(row) for row in cursor.fetchall()]
                return {"columns": columns, "rows": rows, "rowcount": len(rows)}
            else:
                conn.commit()
                result = {"rowcount": cursor.rowcount, "lastrowid": cursor.lastrowid}

                # Auto audit log for write operations
                _log_audit(sql, cursor.lastrowid)

                return result
        except Exception as e:
            conn.rollback()
            return {"error": str(e)}


def _log_audit(sql: str, lastrowid: int | None) -> None:
    """Auto-populate audit_log for INSERT/UPDATE/DELETE operations."""
    sql_upper = sql.strip().upper()

    # Don't log audit_log writes to avoid recursion
    if "AUDIT_LOG" in sql_upper:
        return

    # Extract table name and action
    action = None
    table_name = None

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
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO audit_log (entity_type, entity_id, action) VALUES (?, ?, ?)",
                [table_name, entity_id, action],
            )
            conn.commit()
        except Exception:
            pass  # Don't fail the main operation if audit logging fails


def validate_query(sql: str, params: list | None = None) -> dict[str, Any]:
    """Dry-run a write query using SAVEPOINT. Returns success or error without committing."""
    conn = get_connection()
    with _lock:
        try:
            conn.execute("SAVEPOINT validation")
            cursor = conn.execute(sql, params or [])
            rowcount = cursor.rowcount
            conn.execute("ROLLBACK TO validation")
            conn.execute("RELEASE validation")
            return {"valid": True, "rowcount": rowcount}
        except Exception as e:
            try:
                conn.execute("ROLLBACK TO validation")
                conn.execute("RELEASE validation")
            except Exception:
                conn.rollback()
            return {"valid": False, "error": str(e)}


def get_home_site() -> dict[str, Any] | None:
    """Return the configured home site or None."""
    conn = get_connection()
    cursor = conn.execute(
        "SELECT s.id, s.name, c.name as client_name, s.city "
        "FROM app_settings a JOIN sites s ON s.id = CAST(a.value AS INTEGER) "
        "LEFT JOIN companies c ON s.client_id = c.id "
        "WHERE a.key = 'home_site_id'"
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "client_name": row[2], "city": row[3]}


def get_tables() -> list[str]:
    conn = get_connection()
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    return [row[0] for row in cursor.fetchall()]


def get_table_schema(table_name: str) -> list[dict[str, Any]]:
    conn = get_connection()
    # Validate table name to prevent injection
    if not re.match(r"^\w+$", table_name):
        return []
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    return [
        {
            "cid": row[0],
            "name": row[1],
            "type": row[2],
            "notnull": bool(row[3]),
            "default_value": row[4],
            "pk": bool(row[5]),
        }
        for row in cursor.fetchall()
    ]


def get_table_rows(table_name: str, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    if not re.match(r"^\w+$", table_name):
        return {"error": "Invalid table name"}

    conn = get_connection()
    with _lock:
        # Get total count
        count_cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        total = count_cursor.fetchone()[0]

        cursor = conn.execute(f"SELECT rowid, * FROM {table_name} LIMIT ? OFFSET ?", [limit, offset])
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [dict(row) for row in cursor.fetchall()]

    return {"columns": columns, "rows": rows, "total": total}


def init_db(schema_path: str) -> None:
    """Initialize database from schema file."""
    with open(schema_path, "r") as f:
        schema_sql = f.read()

    conn = get_connection()
    conn.executescript(schema_sql)
    conn.commit()


def migrate_db(schema_path: str) -> None:
    """Apply schema migrations idempotently on an existing database."""
    # Re-run schema (all CREATE TABLE IF NOT EXISTS, safe on existing DB)
    init_db(schema_path)

    # Add important column to tables that may not have it yet
    conn = get_connection()
    important_tables = [
        "technical_issues", "requests", "events", "notes",
        "changes", "work_logs", "assets", "inventory_transactions",
    ]
    for table in important_tables:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN important INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            pass  # Column already exists
