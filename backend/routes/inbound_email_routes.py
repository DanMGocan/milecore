"""Inbound email webhook + whitelist CRUD routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.auth import InstanceContext, get_current_instance
from backend.config import BREVO_INBOUND_WEBHOOK_SECRET
from backend.database import execute_query
from backend.inbound_email import process_inbound_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inbound")


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class AddSenderBody(BaseModel):
    pattern: str
    pattern_type: str = "domain"  # 'email' or 'domain'


# ---------------------------------------------------------------------------
# Webhook (unauthenticated — verified by shared secret)
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def inbound_webhook(request: Request):
    """Brevo inbound email webhook. Always returns 200."""
    # Verify shared secret if configured
    if BREVO_INBOUND_WEBHOOK_SECRET:
        secret = request.headers.get("X-Webhook-Secret") or request.query_params.get("secret")
        if secret != BREVO_INBOUND_WEBHOOK_SECRET:
            logger.warning("Inbound webhook: invalid secret")
            return JSONResponse(content={"received": True})

    try:
        payload = await request.json()
    except Exception:
        logger.error("Inbound webhook: invalid JSON body")
        return JSONResponse(content={"received": True})

    try:
        result = process_inbound_email(payload)
        logger.info("Inbound email processed: %s", result.get("status"))
    except Exception as e:
        logger.exception("Inbound webhook processing error: %s", e)

    return JSONResponse(content={"received": True})


# ---------------------------------------------------------------------------
# Whitelist CRUD (authenticated, owner/admin only)
# ---------------------------------------------------------------------------

@router.get("/senders")
async def list_senders(ctx: InstanceContext = Depends(get_current_instance)):
    """List whitelist entries for the current instance."""
    if ctx.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owner or admin can view sender whitelist")

    result = execute_query(
        "SELECT id, pattern, pattern_type, added_by_auth_user_id, created_at "
        "FROM inbound_email_senders WHERE instance_id = ? ORDER BY created_at DESC",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return {"senders": result.get("rows", [])}


@router.post("/senders")
async def add_sender(body: AddSenderBody, ctx: InstanceContext = Depends(get_current_instance)):
    """Add a sender pattern to the whitelist."""
    if ctx.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owner or admin can manage sender whitelist")

    if body.pattern_type not in ("email", "domain"):
        raise HTTPException(status_code=400, detail="pattern_type must be 'email' or 'domain'")

    pattern = body.pattern.strip().lower()
    if not pattern:
        raise HTTPException(status_code=400, detail="Pattern cannot be empty")

    result = execute_query(
        "INSERT INTO inbound_email_senders (instance_id, pattern, pattern_type, added_by_auth_user_id) "
        "VALUES (?, ?, ?, ?)",
        [ctx.instance_id, pattern, body.pattern_type, ctx.auth_user_id],
        instance_id=ctx.instance_id,
    )
    if result.get("error"):
        if "unique" in result["error"].lower() or "duplicate" in result["error"].lower():
            raise HTTPException(status_code=409, detail="This pattern already exists for this instance")
        raise HTTPException(status_code=400, detail=result["error"])

    return {"id": result.get("lastrowid"), "pattern": pattern, "pattern_type": body.pattern_type}


@router.delete("/senders/{sender_id}")
async def delete_sender(sender_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    """Remove a sender pattern from the whitelist."""
    if ctx.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owner or admin can manage sender whitelist")

    result = execute_query(
        "DELETE FROM inbound_email_senders WHERE id = ? AND instance_id = ?",
        [sender_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if result.get("rowcount", 0) == 0:
        raise HTTPException(status_code=404, detail="Sender pattern not found")

    return {"deleted": True}


# ---------------------------------------------------------------------------
# Audit log (authenticated, owner/admin only)
# ---------------------------------------------------------------------------

@router.get("/emails")
async def list_inbound_emails(ctx: InstanceContext = Depends(get_current_instance)):
    """List recent inbound emails for the current instance."""
    if ctx.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owner or admin can view inbound email log")

    result = execute_query(
        "SELECT id, sender_email, sender_name, subject, status, ticket_id, "
        "error_message, received_at FROM inbound_emails "
        "WHERE instance_id = ? ORDER BY received_at DESC LIMIT 100",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return {"emails": result.get("rows", [])}
