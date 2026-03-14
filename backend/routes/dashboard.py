import json
import os

from fastapi import APIRouter

from backend.claude_client import clear_prompt_cache, clear_schema_cache
from backend.config import SCHEMA_PATH
from backend.database import _lock, get_connection, reset_db
from initial_seed import seed_initial_data

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_last_push() -> str | None:
    path = os.path.join(_PROJECT_ROOT, "last_push.json")
    try:
        with open(path) as f:
            return json.load(f).get("timestamp")
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None

router = APIRouter(prefix="/dashboard")


def _query(sql: str, params: list | None = None) -> list[dict]:
    conn = get_connection()
    with _lock:
        cursor = conn.execute(sql, params or [])
        columns = [d[0] for d in cursor.description] if cursor.description else []
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _count(sql: str) -> int:
    conn = get_connection()
    with _lock:
        return conn.execute(sql).fetchone()[0]


@router.get("/overview")
async def overview():
    row = _query(
        "SELECT "
        "(SELECT COUNT(*) FROM assets WHERE lifecycle_status = 'active') AS active_assets, "
        "(SELECT COUNT(*) FROM requests WHERE status IN ('open', 'in_progress')) AS open_requests, "
        "(SELECT COUNT(*) FROM technical_issues WHERE resolution IS NULL) AS open_issues, "
        "(SELECT COUNT(*) FROM events WHERE DATE(start_time) BETWEEN DATE('now', 'weekday 1', '-7 days') AND DATE('now', '+7 days')) AS events_this_week, "
        "(SELECT COUNT(*) FROM technical_issues WHERE important=1) + "
        "(SELECT COUNT(*) FROM requests WHERE important=1) + "
        "(SELECT COUNT(*) FROM events WHERE important=1) + "
        "(SELECT COUNT(*) FROM notes WHERE important=1) + "
        "(SELECT COUNT(*) FROM changes WHERE important=1) + "
        "(SELECT COUNT(*) FROM work_logs WHERE important=1) + "
        "(SELECT COUNT(*) FROM assets WHERE important=1) + "
        "(SELECT COUNT(*) FROM inventory_transactions WHERE important=1) AS important_items"
    )[0]
    row["last_push"] = _get_last_push()
    return row


@router.get("/assets-by-period")
async def assets_by_period():
    data = _query(
        "SELECT DATE(created_at) as date, COUNT(*) as count FROM assets "
        "WHERE created_at IS NOT NULL "
        "GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 30"
    )
    data.reverse()
    return {"data": data}


@router.get("/issues-summary")
async def issues_summary():
    by_status = _query(
        "SELECT status, COUNT(*) as count FROM requests GROUP BY status ORDER BY count DESC"
    )
    by_severity = _query(
        "SELECT severity, COUNT(*) as count FROM technical_issues "
        "WHERE severity IS NOT NULL GROUP BY severity ORDER BY count DESC"
    )
    return {"by_status": by_status, "by_severity": by_severity}


@router.get("/vendor-visits")
async def vendor_visits():
    data = _query(
        "SELECT status, COUNT(*) as count FROM events "
        "WHERE LOWER(event_type) LIKE '%vendor%' OR LOWER(event_type) LIKE '%visit%' "
        "GROUP BY status"
    )
    return {"data": data}


@router.get("/staff-per-site")
async def staff_per_site():
    data = _query(
        "SELECT s.name as site, COUNT(p.id) as count "
        "FROM sites s LEFT JOIN people p ON p.site_id = s.id AND p.employer_id IS NOT NULL AND p.status = 'active' "
        "GROUP BY s.id, s.name ORDER BY count DESC"
    )
    return {"data": data}


@router.post("/seed-demo")
async def seed_demo():
    """Seed the database with demo data from the xlsx file."""
    import openpyxl

    xlsx_path = os.path.join(_PROJECT_ROOT, "dummy_files", "demo_full_import.xlsx")
    if not os.path.exists(xlsx_path):
        return {"ok": False, "error": "Demo data file not found"}

    try:
        wb = openpyxl.load_workbook(xlsx_path)
        conn = get_connection()

        # Insert order respects FK constraints
        sheet_order = [
            "companies", "sites", "rooms", "people", "assets",
            "requests", "technical_issues", "events", "inventory_items",
        ]

        total_inserted = 0

        with _lock:
            for table_name in sheet_order:
                if table_name not in wb.sheetnames:
                    continue
                ws = wb[table_name]
                headers = [cell.value for cell in ws[1]]
                if not headers:
                    continue

                cols = ", ".join(headers)
                placeholders = ", ".join(["?"] * len(headers))

                for row_idx in range(2, ws.max_row + 1):
                    values = [cell.value for cell in ws[row_idx]]
                    conn.execute(
                        f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})",
                        values,
                    )
                    total_inserted += 1

            conn.commit()

        clear_schema_cache()
        clear_prompt_cache()

        return {"ok": True, "total_inserted": total_inserted}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/reset-database")
async def reset_database():
    try:
        reset_db(SCHEMA_PATH)
        seed_initial_data()
        clear_schema_cache()
        clear_prompt_cache()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
