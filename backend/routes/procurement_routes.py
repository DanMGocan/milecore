"""Procurement / Purchase Request REST API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.auth import InstanceContext, get_current_instance
from backend.database import execute_query

router = APIRouter(prefix="/procurement")

VALID_TRANSITIONS = {
    "pending": {"approved", "cancelled"},
    "approved": {"ordered", "cancelled"},
    "ordered": {"received", "cancelled"},
    "received": set(),
    "cancelled": {"pending"},
}


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class CreateProcurementBody(BaseModel):
    item_description: str
    value: float | None = None
    brand: str | None = None
    model: str | None = None
    vendor: str | None = None
    notes: str | None = None


class UpdateProcurementBody(BaseModel):
    status: str | None = None
    value: float | None = None
    vendor: str | None = None
    notes: str | None = None


class AddUpdateBody(BaseModel):
    note: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_request_or_404(request_id: int, instance_id: int) -> dict:
    result = execute_query(
        "SELECT id, item_description, status, value, vendor, brand, model, "
        "notes, requested_by_person_id, reviewed_by_person_id "
        "FROM procurement_requests WHERE id = ? AND instance_id = ?",
        [request_id, instance_id],
        instance_id=instance_id,
    )
    if not result.get("rows"):
        raise HTTPException(status_code=404, detail=f"Procurement request #{request_id} not found")
    return result["rows"][0]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("")
async def create_procurement_request(
    body: CreateProcurementBody,
    ctx: InstanceContext = Depends(get_current_instance),
):
    if not ctx.person_id:
        raise HTTPException(status_code=400, detail="Your account must be linked to a person record to create requests")

    result = execute_query(
        "INSERT INTO procurement_requests "
        "(instance_id, requested_by_person_id, item_description, value, brand, model, vendor, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [ctx.instance_id, ctx.person_id, body.item_description, body.value,
         body.brand, body.model, body.vendor, body.notes],
        instance_id=ctx.instance_id,
    )
    new_id = result.get("lastrowid")

    execute_query(
        "INSERT INTO procurement_updates "
        "(instance_id, procurement_request_id, author_person_id, event_type, note) "
        "VALUES (?, ?, ?, 'created', ?)",
        [ctx.instance_id, new_id, ctx.person_id, body.notes],
        instance_id=ctx.instance_id,
    )

    return {"id": new_id}


@router.get("")
async def list_procurement_requests(
    status: str | None = Query(None),
    ctx: InstanceContext = Depends(get_current_instance),
):
    sql = (
        "SELECT pr.id, pr.item_description, pr.value, pr.vendor, pr.brand, pr.model, "
        "pr.status, pr.notes, pr.created_at, pr.updated_at, "
        "p.first_name || ' ' || COALESCE(p.last_name, '') AS requested_by_name "
        "FROM procurement_requests pr "
        "LEFT JOIN people p ON pr.requested_by_person_id = p.id AND p.instance_id = pr.instance_id "
    )
    params = []
    if status:
        sql += "WHERE pr.status = ? "
        params.append(status)
    sql += "ORDER BY pr.created_at DESC"

    result = execute_query(sql, params, instance_id=ctx.instance_id)
    return result.get("rows", [])


@router.get("/{request_id}")
async def get_procurement_request(
    request_id: int,
    ctx: InstanceContext = Depends(get_current_instance),
):
    result = execute_query(
        "SELECT pr.*, "
        "p.first_name || ' ' || COALESCE(p.last_name, '') AS requested_by_name, "
        "rp.first_name || ' ' || COALESCE(rp.last_name, '') AS reviewed_by_name "
        "FROM procurement_requests pr "
        "LEFT JOIN people p ON pr.requested_by_person_id = p.id AND p.instance_id = pr.instance_id "
        "LEFT JOIN people rp ON pr.reviewed_by_person_id = rp.id AND rp.instance_id = pr.instance_id "
        "WHERE pr.id = ? AND pr.instance_id = ?",
        [request_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if not result.get("rows"):
        raise HTTPException(status_code=404, detail=f"Procurement request #{request_id} not found")
    request_row = result["rows"][0]

    updates = execute_query(
        "SELECT pu.id, pu.event_type, pu.old_value, pu.new_value, pu.note, pu.created_at, "
        "p.first_name || ' ' || COALESCE(p.last_name, '') AS author_name "
        "FROM procurement_updates pu "
        "LEFT JOIN people p ON pu.author_person_id = p.id AND p.instance_id = pu.instance_id "
        "WHERE pu.procurement_request_id = ? AND pu.instance_id = ? "
        "ORDER BY pu.created_at ASC",
        [request_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    request_row["updates"] = updates.get("rows", [])
    return request_row


@router.patch("/{request_id}")
async def update_procurement_request(
    request_id: int,
    body: UpdateProcurementBody,
    ctx: InstanceContext = Depends(get_current_instance),
):
    req = _get_request_or_404(request_id, ctx.instance_id)

    updates = []
    params = []
    timeline_entries = []

    if body.status is not None and body.status != req.get("status"):
        current = req.get("status", "pending")
        allowed = VALID_TRANSITIONS.get(current, set())
        if body.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot change status from '{current}' to '{body.status}'. "
                       f"Allowed: {', '.join(sorted(allowed)) or 'none (terminal state)'}",
            )
        updates.append("status = ?")
        params.append(body.status)
        timeline_entries.append(("status_changed", current, body.status))

        if body.status in ("approved", "cancelled"):
            updates.append("reviewed_by_person_id = ?")
            params.append(ctx.person_id)
            updates.append("reviewed_at = NOW()")

    if body.value is not None and body.value != req.get("value"):
        updates.append("value = ?")
        params.append(body.value)
        timeline_entries.append(("value_changed", str(req.get("value", "")), str(body.value)))

    if body.vendor is not None and body.vendor != req.get("vendor"):
        updates.append("vendor = ?")
        params.append(body.vendor)
        timeline_entries.append(("vendor_changed", req.get("vendor", ""), body.vendor))

    if body.notes is not None and body.notes != req.get("notes"):
        updates.append("notes = ?")
        params.append(body.notes)

    if not updates:
        return {"message": "No changes"}

    updates.append("updated_at = NOW()")
    params.extend([request_id, ctx.instance_id])
    execute_query(
        f"UPDATE procurement_requests SET {', '.join(updates)} WHERE id = ? AND instance_id = ?",
        params,
        instance_id=ctx.instance_id,
    )

    for event_type, old_val, new_val in timeline_entries:
        execute_query(
            "INSERT INTO procurement_updates "
            "(instance_id, procurement_request_id, author_person_id, event_type, old_value, new_value) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [ctx.instance_id, request_id, ctx.person_id, event_type, old_val, new_val],
            instance_id=ctx.instance_id,
        )

    return {"success": True, "changes": len(updates) - 1}  # -1 for updated_at


@router.post("/{request_id}/updates")
async def add_procurement_update(
    request_id: int,
    body: AddUpdateBody,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_request_or_404(request_id, ctx.instance_id)

    execute_query(
        "INSERT INTO procurement_updates "
        "(instance_id, procurement_request_id, author_person_id, event_type, note) "
        "VALUES (?, ?, ?, 'note_added', ?)",
        [ctx.instance_id, request_id, ctx.person_id, body.note],
        instance_id=ctx.instance_id,
    )

    execute_query(
        "UPDATE procurement_requests SET updated_at = NOW() WHERE id = ? AND instance_id = ?",
        [request_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    return {"success": True}
