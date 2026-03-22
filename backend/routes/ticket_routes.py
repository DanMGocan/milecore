"""Ticket management REST API: attachments, timeline, watchers, updates."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from backend.auth import InstanceContext, get_current_instance
from backend.config import (
    TICKET_ATTACHMENT_ALLOWED_TYPES,
    TICKET_ATTACHMENT_MAX_SIZE_MB,
)
from backend.database import execute_query
from backend.s3_storage import upload_image, download_image

router = APIRouter(prefix="/tickets")


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class AddWatcherBody(BaseModel):
    person_id: int


class UpdateTicketBody(BaseModel):
    priority: str | None = None
    status: str | None = None
    assigned_person_id: int | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_ticket_or_404(ticket_id: int, instance_id: int) -> dict:
    result = execute_query(
        "SELECT id, title, status, priority, assigned_person_id FROM tickets WHERE id = ? AND instance_id = ?",
        [ticket_id, instance_id],
        instance_id=instance_id,
    )
    if not result.get("rows"):
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found")
    return result["rows"][0]


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------

@router.post("/{ticket_id}/attachments")
async def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_ticket_or_404(ticket_id, ctx.instance_id)

    if not file.content_type or file.content_type not in TICKET_ATTACHMENT_ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"File type '{file.content_type}' not allowed")

    content = await file.read()
    max_bytes = TICKET_ATTACHMENT_MAX_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File too large. Max {TICKET_ATTACHMENT_MAX_SIZE_MB} MB")

    file_id = str(uuid.uuid4())
    original_filename = file.filename or "image"

    result = upload_image(
        instance_id=ctx.instance_id,
        ticket_id=ticket_id,
        file_id=file_id,
        image_bytes=content,
        original_filename=original_filename,
        content_type=file.content_type,
    )

    execute_query(
        "INSERT INTO ticket_attachments (instance_id, ticket_id, filename, original_filename, "
        "content_type, file_size_bytes, storage_path, uploaded_by_person_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [ctx.instance_id, ticket_id, f"{file_id}.avif", original_filename,
         result["content_type"], result["file_size_bytes"], result["s3_key"], ctx.person_id],
        instance_id=ctx.instance_id,
    )
    execute_query(
        "INSERT INTO ticket_timeline (instance_id, ticket_id, event_type, actor_person_id, detail) "
        "VALUES (?, ?, 'attachment_added', ?, ?)",
        [ctx.instance_id, ticket_id, ctx.person_id, original_filename],
        instance_id=ctx.instance_id,
    )

    return {"filename": original_filename, "content_type": result["content_type"], "file_size_bytes": result["file_size_bytes"]}


@router.get("/{ticket_id}/attachments")
async def list_attachments(ticket_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    _get_ticket_or_404(ticket_id, ctx.instance_id)
    result = execute_query(
        "SELECT id, original_filename, content_type, file_size_bytes, created_at "
        "FROM ticket_attachments WHERE ticket_id = ? AND instance_id = ? ORDER BY created_at",
        [ticket_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


@router.get("/{ticket_id}/attachments/{attachment_id}")
async def download_attachment(ticket_id: int, attachment_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    result = execute_query(
        "SELECT storage_path, original_filename, content_type FROM ticket_attachments "
        "WHERE id = ? AND ticket_id = ? AND instance_id = ?",
        [attachment_id, ticket_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if not result.get("rows"):
        raise HTTPException(status_code=404, detail="Attachment not found")
    row = result["rows"][0]
    data, ct = download_image(row["storage_path"])
    return Response(
        content=data,
        media_type=ct,
        headers={"Content-Disposition": f'inline; filename="{row["original_filename"]}"'},
    )


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

@router.get("/{ticket_id}/timeline")
async def get_timeline(ticket_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    _get_ticket_or_404(ticket_id, ctx.instance_id)
    result = execute_query(
        "SELECT tt.id, tt.event_type, tt.old_value, tt.new_value, tt.detail, tt.related_id, "
        "tt.created_at, p.first_name || ' ' || COALESCE(p.last_name, '') AS actor_name "
        "FROM ticket_timeline tt "
        "LEFT JOIN people p ON tt.actor_person_id = p.id AND p.instance_id = tt.instance_id "
        "WHERE tt.ticket_id = ? AND tt.instance_id = ? "
        "ORDER BY tt.created_at ASC",
        [ticket_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


# ---------------------------------------------------------------------------
# Replies
# ---------------------------------------------------------------------------

@router.get("/{ticket_id}/replies")
async def get_replies(ticket_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    _get_ticket_or_404(ticket_id, ctx.instance_id)
    result = execute_query(
        "SELECT tr.id, tr.reply_body, tr.direction, tr.reply_to_email, tr.created_at, "
        "p.first_name || ' ' || COALESCE(p.last_name, '') AS author_name "
        "FROM ticket_replies tr "
        "LEFT JOIN people p ON tr.reply_by_person_id = p.id AND p.instance_id = tr.instance_id "
        "WHERE tr.ticket_id = ? AND tr.instance_id = ? "
        "ORDER BY tr.created_at ASC",
        [ticket_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


# ---------------------------------------------------------------------------
# Watchers
# ---------------------------------------------------------------------------

@router.get("/{ticket_id}/watchers")
async def get_watchers(ticket_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    _get_ticket_or_404(ticket_id, ctx.instance_id)
    result = execute_query(
        "SELECT tw.id, tw.person_id, p.first_name, p.last_name, p.email, tw.created_at "
        "FROM ticket_watchers tw "
        "JOIN people p ON tw.person_id = p.id AND p.instance_id = tw.instance_id "
        "WHERE tw.ticket_id = ? AND tw.instance_id = ? "
        "ORDER BY tw.created_at",
        [ticket_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


@router.post("/{ticket_id}/watchers")
async def add_watcher(ticket_id: int, body: AddWatcherBody, ctx: InstanceContext = Depends(get_current_instance)):
    _get_ticket_or_404(ticket_id, ctx.instance_id)

    # Verify person exists
    person = execute_query(
        "SELECT id, first_name, last_name FROM people WHERE id = ? AND instance_id = ?",
        [body.person_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if not person.get("rows"):
        raise HTTPException(status_code=404, detail="Person not found")
    p = person["rows"][0]

    result = execute_query(
        "INSERT INTO ticket_watchers (instance_id, ticket_id, person_id, added_by_person_id) "
        "VALUES (?, ?, ?, ?) ON CONFLICT (ticket_id, person_id) DO NOTHING",
        [ctx.instance_id, ticket_id, body.person_id, ctx.person_id],
        instance_id=ctx.instance_id,
    )
    if result.get("rowcount", 0) > 0:
        name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
        execute_query(
            "INSERT INTO ticket_timeline (instance_id, ticket_id, event_type, actor_person_id, detail) "
            "VALUES (?, ?, 'watcher_added', ?, ?)",
            [ctx.instance_id, ticket_id, ctx.person_id, name],
            instance_id=ctx.instance_id,
        )
    return {"success": True}


@router.delete("/{ticket_id}/watchers/{watcher_id}")
async def remove_watcher(ticket_id: int, watcher_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    # Look up watcher to log name
    watcher = execute_query(
        "SELECT tw.id, p.first_name, p.last_name FROM ticket_watchers tw "
        "JOIN people p ON tw.person_id = p.id AND p.instance_id = tw.instance_id "
        "WHERE tw.id = ? AND tw.ticket_id = ? AND tw.instance_id = ?",
        [watcher_id, ticket_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if not watcher.get("rows"):
        raise HTTPException(status_code=404, detail="Watcher not found")
    w = watcher["rows"][0]
    name = f"{w.get('first_name', '')} {w.get('last_name', '')}".strip()

    execute_query(
        "DELETE FROM ticket_watchers WHERE id = ? AND ticket_id = ? AND instance_id = ?",
        [watcher_id, ticket_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    execute_query(
        "INSERT INTO ticket_timeline (instance_id, ticket_id, event_type, actor_person_id, detail) "
        "VALUES (?, ?, 'watcher_removed', ?, ?)",
        [ctx.instance_id, ticket_id, ctx.person_id, name],
        instance_id=ctx.instance_id,
    )
    return {"success": True}


# ---------------------------------------------------------------------------
# Ticket update (priority, status, assignment)
# ---------------------------------------------------------------------------

@router.patch("/{ticket_id}")
async def update_ticket(ticket_id: int, body: UpdateTicketBody, ctx: InstanceContext = Depends(get_current_instance)):
    ticket = _get_ticket_or_404(ticket_id, ctx.instance_id)

    updates = []
    params = []
    timeline_entries = []

    if body.priority is not None and body.priority != ticket.get("priority"):
        updates.append("priority = ?")
        params.append(body.priority)
        timeline_entries.append(("priority_changed", ticket.get("priority", ""), body.priority))

    if body.status is not None and body.status != ticket.get("status"):
        updates.append("status = ?")
        params.append(body.status)
        timeline_entries.append(("status_changed", ticket.get("status", ""), body.status))

    if body.assigned_person_id is not None and body.assigned_person_id != ticket.get("assigned_person_id"):
        updates.append("assigned_person_id = ?")
        params.append(body.assigned_person_id)
        timeline_entries.append(("assigned", str(ticket.get("assigned_person_id", "")), str(body.assigned_person_id)))

    if not updates:
        return {"message": "No changes"}

    params.extend([ticket_id, ctx.instance_id])
    execute_query(
        f"UPDATE tickets SET {', '.join(updates)} WHERE id = ? AND instance_id = ?",
        params,
        instance_id=ctx.instance_id,
    )

    for event_type, old_val, new_val in timeline_entries:
        execute_query(
            "INSERT INTO ticket_timeline (instance_id, ticket_id, event_type, actor_person_id, old_value, new_value) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [ctx.instance_id, ticket_id, event_type, ctx.person_id, old_val, new_val],
            instance_id=ctx.instance_id,
        )

    return {"success": True, "changes": len(updates)}
