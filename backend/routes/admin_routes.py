"""Platform admin endpoints — cross-tenant overview for the platform owner."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.auth import AuthUser, get_current_user
from backend.config import ADMIN_EMAIL
from backend.database import execute_query

router = APIRouter(prefix="/admin")


async def require_platform_admin(request: Request) -> AuthUser:
    user = await get_current_user(request)
    if user.email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Platform admin access required")
    return user


@router.get("/stats")
async def admin_stats(_user: AuthUser = Depends(require_platform_admin)):
    users = execute_query("SELECT COUNT(*) AS cnt FROM auth_users", instance_id=None)
    instances = execute_query("SELECT COUNT(*) AS cnt FROM instances", instance_id=None)
    active = execute_query(
        "SELECT COUNT(*) AS cnt FROM instances WHERE status = 'active'",
        instance_id=None,
    )
    queries = execute_query(
        "SELECT COALESCE(SUM(query_count), 0) AS cnt FROM instances",
        instance_id=None,
    )
    tokens = execute_query(
        "SELECT COALESCE(SUM(total_input_tokens), 0) AS input, "
        "COALESCE(SUM(total_output_tokens), 0) AS output, "
        "COALESCE(SUM(cache_creation_tokens), 0) AS cache_creation, "
        "COALESCE(SUM(cache_read_tokens), 0) AS cache_read "
        "FROM query_token_log",
        instance_id=None,
    )
    purchases = execute_query(
        "SELECT COUNT(*) AS cnt FROM query_pack_purchases",
        instance_id=None,
    )

    token_row = tokens["rows"][0] if tokens.get("rows") else {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}
    return {
        "total_users": users["rows"][0]["cnt"] if users.get("rows") else 0,
        "total_instances": instances["rows"][0]["cnt"] if instances.get("rows") else 0,
        "active_instances": active["rows"][0]["cnt"] if active.get("rows") else 0,
        "total_queries": queries["rows"][0]["cnt"] if queries.get("rows") else 0,
        "total_input_tokens": token_row["input"],
        "total_output_tokens": token_row["output"],
        "total_cache_creation_tokens": token_row["cache_creation"],
        "total_cache_read_tokens": token_row["cache_read"],
        "total_purchases": purchases["rows"][0]["cnt"] if purchases.get("rows") else 0,
    }


@router.get("/users")
async def admin_users(_user: AuthUser = Depends(require_platform_admin)):
    result = execute_query(
        "SELECT u.id, u.email, u.display_name, u.email_verified, u.created_at, "
        "COUNT(m.id) AS instance_count "
        "FROM auth_users u "
        "LEFT JOIN instance_memberships m ON m.auth_user_id = u.id "
        "GROUP BY u.id ORDER BY u.created_at DESC",
        instance_id=None,
    )
    rows = result.get("rows", [])
    for r in rows:
        if r.get("created_at"):
            r["created_at"] = str(r["created_at"])
    return {"users": rows}


@router.get("/instances")
async def admin_instances(_user: AuthUser = Depends(require_platform_admin)):
    result = execute_query(
        "SELECT i.id, i.name, i.tier, i.status, i.query_count, i.query_limit, "
        "i.email_addon, i.inbound_email_addon, i.daily_reports_addon, i.created_at, "
        "COUNT(m.id) AS member_count, "
        "bo.email AS owner_email "
        "FROM instances i "
        "LEFT JOIN instance_memberships m ON m.instance_id = i.id "
        "LEFT JOIN auth_users bo ON bo.id = i.billing_owner_id "
        "GROUP BY i.id, bo.email ORDER BY i.created_at DESC",
        instance_id=None,
    )
    rows = result.get("rows", [])
    for r in rows:
        if r.get("created_at"):
            r["created_at"] = str(r["created_at"])
        r["addons"] = []
        if r.pop("email_addon", False):
            r["addons"].append("email")
        if r.pop("inbound_email_addon", False):
            r["addons"].append("inbound_email")
        if r.pop("daily_reports_addon", False):
            r["addons"].append("daily_reports")
    return {"instances": rows}


@router.get("/payments")
async def admin_payments(_user: AuthUser = Depends(require_platform_admin)):
    purchases = execute_query(
        "SELECT p.id, p.queries_added, p.created_at, "
        "u.email AS user_email, i.name AS instance_name "
        "FROM query_pack_purchases p "
        "JOIN auth_users u ON u.id = p.purchased_by_auth_user_id "
        "JOIN instances i ON i.id = p.instance_id "
        "ORDER BY p.created_at DESC LIMIT 100",
        instance_id=None,
    )
    subs = execute_query(
        "SELECT se.id, se.event_type, se.details, se.created_at, "
        "i.name AS instance_name "
        "FROM subscription_events se "
        "JOIN instances i ON i.id = se.instance_id "
        "ORDER BY se.created_at DESC LIMIT 100",
        instance_id=None,
    )
    for row in purchases.get("rows", []):
        if row.get("created_at"):
            row["created_at"] = str(row["created_at"])
    for row in subs.get("rows", []):
        if row.get("created_at"):
            row["created_at"] = str(row["created_at"])
    return {
        "purchases": purchases.get("rows", []),
        "subscription_events": subs.get("rows", []),
    }


@router.get("/token-usage")
async def admin_token_usage(
    days: int = Query(default=30, ge=1, le=365),
    _user: AuthUser = Depends(require_platform_admin),
):
    result = execute_query(
        "SELECT DATE(created_at) AS date, "
        "SUM(total_input_tokens) AS input_tokens, "
        "SUM(total_output_tokens) AS output_tokens, "
        "SUM(cache_creation_tokens) AS cache_creation_tokens, "
        "SUM(cache_read_tokens) AS cache_read_tokens, "
        "SUM(api_calls) AS api_calls, "
        "SUM(queries_consumed) AS queries "
        "FROM query_token_log "
        "WHERE created_at >= NOW() - MAKE_INTERVAL(days => ?) "
        "GROUP BY DATE(created_at) ORDER BY date",
        [days],
        instance_id=None,
    )
    rows = result.get("rows", [])
    for r in rows:
        if r.get("date"):
            r["date"] = str(r["date"])
    return {"data": rows}
