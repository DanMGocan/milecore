from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.auth import InstanceContext, get_current_instance
from backend.claude_client import clear_prompt_cache, clear_schema_cache
from backend.config import APP_URL, SCHEMA_PATH
from backend.email_sender import send_email
from backend.database import execute_query, reset_instance
from initial_seed import seed_initial_data

router = APIRouter(prefix="/dashboard")


def _query(sql: str, params: list | None = None, instance_id: int = 1) -> list[dict]:
    result = execute_query(sql, params, instance_id=instance_id)
    return result.get("rows", [])


def _count(sql: str, instance_id: int = 1) -> int:
    result = execute_query(sql, instance_id=instance_id)
    rows = result.get("rows", [])
    if rows:
        # Return the first column value of the first row
        first_row = rows[0]
        if isinstance(first_row, dict):
            return list(first_row.values())[0]
    return 0


@router.get("/overview")
async def overview(ctx: InstanceContext = Depends(get_current_instance)):
    row = _query(
        "SELECT "
        "(SELECT COUNT(*) FROM assets WHERE lifecycle_status = 'active' AND instance_id = ?) AS active_assets, "
        "(SELECT COUNT(*) FROM tickets WHERE status IN ('open', 'in_progress') AND instance_id = ?) AS open_tickets, "
        "(SELECT COUNT(*) FROM technical_issues WHERE resolution IS NULL AND instance_id = ?) AS open_issues, "
        "(SELECT COUNT(*) FROM events WHERE DATE(start_time) BETWEEN DATE('now', 'weekday 1', '-7 days') AND DATE('now', '+7 days') AND instance_id = ?) AS events_this_week, "
        "(SELECT COUNT(*) FROM technical_issues WHERE important=1 AND instance_id = ?) + "
        "(SELECT COUNT(*) FROM tickets WHERE important=1 AND instance_id = ?) + "
        "(SELECT COUNT(*) FROM events WHERE important=1 AND instance_id = ?) + "
        "(SELECT COUNT(*) FROM notes WHERE important=1 AND instance_id = ?) + "
        "(SELECT COUNT(*) FROM changes WHERE important=1 AND instance_id = ?) + "
        "(SELECT COUNT(*) FROM work_logs WHERE important=1 AND instance_id = ?) + "
        "(SELECT COUNT(*) FROM assets WHERE important=1 AND instance_id = ?) + "
        "(SELECT COUNT(*) FROM inventory_transactions WHERE important=1 AND instance_id = ?) + "
        "(SELECT COUNT(*) FROM projects WHERE important=1 AND instance_id = ?) AS important_items",
        [ctx.instance_id, ctx.instance_id, ctx.instance_id, ctx.instance_id,
         ctx.instance_id, ctx.instance_id, ctx.instance_id, ctx.instance_id,
         ctx.instance_id, ctx.instance_id, ctx.instance_id, ctx.instance_id,
         ctx.instance_id],
        instance_id=ctx.instance_id,
    )[0]
    push = _query(
        "SELECT value FROM app_settings WHERE key = 'last_push_at' AND instance_id = ?",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    row["last_push"] = push[0]["value"] if push else None
    return row


@router.get("/usage")
async def instance_usage(ctx: InstanceContext = Depends(get_current_instance)):
    """Return the current instance's query usage and limits."""
    result = execute_query(
        "SELECT name, tier, query_count, query_limit, email_addon, daily_reports_addon, "
        "status, query_pool_reset_at FROM instances WHERE id = ?",
        [ctx.instance_id],
        instance_id=None,
    )
    if not result.get("rows"):
        return {"error": "Instance not found"}
    row = result["rows"][0]

    # Count active members for pool breakdown
    member_result = execute_query(
        "SELECT COUNT(*) as cnt FROM instance_memberships WHERE instance_id = ?",
        [ctx.instance_id],
        instance_id=None,
    )
    seat_count = member_result["rows"][0]["cnt"] if member_result.get("rows") else 1

    return {
        "instance_name": row["name"],
        "tier": row["tier"],
        "query_count": row["query_count"],
        "query_limit": row["query_limit"],
        "queries_remaining": max(0, row["query_limit"] - row["query_count"]),
        "email_addon": row["email_addon"],
        "daily_reports_addon": row["daily_reports_addon"],
        "status": row["status"],
        "query_pool_reset_at": str(row["query_pool_reset_at"]) if row.get("query_pool_reset_at") else None,
        "seat_count": seat_count,
        "base_queries": seat_count * 250,
    }


@router.get("/assets-by-period")
async def assets_by_period(ctx: InstanceContext = Depends(get_current_instance)):
    data = _query(
        "SELECT DATE(created_at) as date, COUNT(*) as count FROM assets "
        "WHERE created_at IS NOT NULL AND instance_id = ? "
        "GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 30",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    data.reverse()
    return {"data": data}


@router.get("/issues-summary")
async def issues_summary(ctx: InstanceContext = Depends(get_current_instance)):
    by_status = _query(
        "SELECT status, COUNT(*) as count FROM tickets WHERE instance_id = ? GROUP BY status ORDER BY count DESC",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    by_severity = _query(
        "SELECT severity, COUNT(*) as count FROM technical_issues "
        "WHERE severity IS NOT NULL AND instance_id = ? GROUP BY severity ORDER BY count DESC",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return {"by_status": by_status, "by_severity": by_severity}


@router.get("/vendor-visits")
async def vendor_visits(ctx: InstanceContext = Depends(get_current_instance)):
    data = _query(
        "SELECT status, COUNT(*) as count FROM events "
        "WHERE (LOWER(event_type) LIKE '%vendor%' OR LOWER(event_type) LIKE '%visit%') AND instance_id = ? "
        "GROUP BY status",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return {"data": data}


@router.get("/staff-per-site")
async def staff_per_site(ctx: InstanceContext = Depends(get_current_instance)):
    data = _query(
        "SELECT s.name as site, COUNT(p.id) as count "
        "FROM sites s LEFT JOIN people p ON p.site_id = s.id AND p.employer_id IS NOT NULL AND p.status = 'active' AND p.instance_id = ? "
        "WHERE s.instance_id = ? "
        "GROUP BY s.id, s.name ORDER BY count DESC",
        [ctx.instance_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return {"data": data}


@router.post("/reset-database")
async def reset_database(ctx: InstanceContext = Depends(get_current_instance)):
    try:
        reset_instance(ctx.instance_id)
        seed_initial_data()
        clear_schema_cache()
        clear_prompt_cache()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# --- User Management ---

@router.get("/users")
async def list_users(ctx: InstanceContext = Depends(get_current_instance)):
    users = _query(
        "SELECT id, first_name, last_name, email, username, user_role, role_title, status, motto "
        "FROM people WHERE is_user = 1 AND instance_id = ? ORDER BY id",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return {"users": users}


class AddUserRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    role: str = "user"
    requesting_person_id: int


@router.post("/users")
async def add_user(req: AddUserRequest, ctx: InstanceContext = Depends(get_current_instance)):
    if req.role not in ("user", "admin"):
        return {"error": "Role must be 'user' or 'admin'"}

    requester = _query(
        "SELECT user_role FROM people WHERE id = ? AND is_user = 1 AND instance_id = ?",
        [req.requesting_person_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if not requester:
        return {"error": "Requesting user not found"}
    requester_role = requester[0]["user_role"]

    if req.role == "admin" and requester_role != "owner":
        return {"error": "Only the owner can add admins"}
    if requester_role not in ("owner", "admin"):
        return {"error": "Only owner or admin can add users"}

    base_username = req.first_name.lower().strip()
    username = base_username
    suffix = 1
    while _query(
        "SELECT 1 FROM people WHERE username = ? AND instance_id = ?",
        [username, ctx.instance_id],
        instance_id=ctx.instance_id,
    ):
        suffix += 1
        username = f"{base_username}{suffix}"

    result = execute_query(
        "INSERT INTO people (first_name, last_name, email, is_user, username, user_role, status, instance_id) "
        "VALUES (?, ?, ?, 1, ?, ?, 'active', ?)",
        [req.first_name.strip(), req.last_name.strip(), req.email.strip(), username, req.role, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    new_id = result.get("lastrowid")

    email_result = send_email(
        to_email=req.email.strip(),
        subject=f"You've been added to TrueCore.cloud as {req.role}",
        body=(
            f"Hi {req.first_name.strip()},\n\n"
            f"You've been added to TrueCore.cloud as a {req.role}.\n"
            f"Your username is: {username}\n\n"
            f"Access TrueCore.cloud here: {APP_URL}\n\n"
            f"-- TrueCore.cloud"
        ),
        to_name=f"{req.first_name.strip()} {req.last_name.strip()}",
    )

    return {"ok": True, "person_id": new_id, "username": username, "email_sent": email_result}


@router.delete("/users/{person_id}")
async def remove_user(person_id: int, requesting_person_id: int = Query(...), ctx: InstanceContext = Depends(get_current_instance)):
    target = _query(
        "SELECT user_role FROM people WHERE id = ? AND is_user = 1 AND instance_id = ?",
        [person_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if not target:
        return {"error": "User not found"}
    if target[0]["user_role"] == "owner":
        return {"error": "Cannot remove the owner"}

    requester = _query(
        "SELECT user_role FROM people WHERE id = ? AND is_user = 1 AND instance_id = ?",
        [requesting_person_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if not requester:
        return {"error": "Requesting user not found"}
    requester_role = requester[0]["user_role"]
    target_role = target[0]["user_role"]

    if requester_role == "admin" and target_role == "admin":
        return {"error": "Admins cannot remove other admins"}
    if requester_role not in ("owner", "admin"):
        return {"error": "Insufficient permissions"}

    execute_query(
        "UPDATE people SET is_user = 0, status = 'inactive' WHERE id = ? AND instance_id = ?",
        [person_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    return {"ok": True}


class ChangeRoleRequest(BaseModel):
    new_role: str
    requesting_person_id: int


@router.patch("/users/{person_id}/role")
async def change_user_role(person_id: int, req: ChangeRoleRequest, ctx: InstanceContext = Depends(get_current_instance)):
    if req.new_role not in ("user", "admin"):
        return {"error": "Role must be 'user' or 'admin'"}

    requester = _query(
        "SELECT user_role FROM people WHERE id = ? AND is_user = 1 AND instance_id = ?",
        [req.requesting_person_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if not requester or requester[0]["user_role"] != "owner":
        return {"error": "Only the owner can change roles"}

    target = _query(
        "SELECT user_role FROM people WHERE id = ? AND is_user = 1 AND instance_id = ?",
        [person_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if not target:
        return {"error": "User not found"}
    if target[0]["user_role"] == "owner":
        return {"error": "Cannot change the owner's role"}

    execute_query(
        "UPDATE people SET user_role = ? WHERE id = ? AND instance_id = ?",
        [req.new_role, person_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    return {"ok": True}


class UpdateMottoRequest(BaseModel):
    motto: str
    requesting_person_id: int


@router.patch("/users/{person_id}/motto")
async def update_motto(person_id: int, req: UpdateMottoRequest, ctx: InstanceContext = Depends(get_current_instance)):
    if req.requesting_person_id != person_id:
        return {"error": "You can only update your own motto"}

    motto = req.motto.strip()[:200]

    execute_query(
        "UPDATE people SET motto = ? WHERE id = ? AND instance_id = ?",
        [motto, person_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    return {"ok": True}
