import json
import os

from fastapi import APIRouter

from backend.config import SCHEMA_PATH

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_last_push() -> str | None:
    path = os.path.join(_PROJECT_ROOT, "last_push.json")
    try:
        with open(path) as f:
            return json.load(f).get("timestamp")
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None
from backend.database import get_connection, _lock, reset_db

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
    return {
        "active_assets": _count("SELECT COUNT(*) FROM assets WHERE lifecycle_status = 'active'"),
        "open_requests": _count("SELECT COUNT(*) FROM requests WHERE status IN ('open', 'in_progress')"),
        "open_issues": _count("SELECT COUNT(*) FROM technical_issues WHERE resolution IS NULL"),
        "events_this_week": _count(
            "SELECT COUNT(*) FROM events "
            "WHERE DATE(start_time) BETWEEN DATE('now', 'weekday 1', '-7 days') AND DATE('now', '+7 days')"
        ),
        "important_items": _count(
            "SELECT ("
            "(SELECT COUNT(*) FROM technical_issues WHERE important=1) + "
            "(SELECT COUNT(*) FROM requests WHERE important=1) + "
            "(SELECT COUNT(*) FROM events WHERE important=1) + "
            "(SELECT COUNT(*) FROM notes WHERE important=1) + "
            "(SELECT COUNT(*) FROM changes WHERE important=1) + "
            "(SELECT COUNT(*) FROM work_logs WHERE important=1) + "
            "(SELECT COUNT(*) FROM assets WHERE important=1) + "
            "(SELECT COUNT(*) FROM inventory_transactions WHERE important=1)"
            ")"
        ),
        "last_push": _get_last_push(),
    }


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


@router.post("/reset-database")
async def reset_database():
    try:
        reset_db(SCHEMA_PATH)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
