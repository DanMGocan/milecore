from fastapi import APIRouter, Depends

from backend.auth import InstanceContext, get_current_instance
from backend.database import execute_query

router = APIRouter(prefix="/reminders")


@router.get("")
def list_reminders(ctx: InstanceContext = Depends(get_current_instance)):
    result = execute_query(
        "SELECT r.id, r.title, r.message, r.remind_at, r.recurrence, r.status, "
        "r.notify_email, r.notify_person_id, r.created_by_person_id, r.last_sent_at, r.created_at, "
        "p.first_name || ' ' || p.last_name AS notify_person_name "
        "FROM reminders r "
        "LEFT JOIN people p ON r.notify_person_id = p.id AND p.instance_id = r.instance_id "
        "WHERE r.status IN ('active', 'paused') "
        "ORDER BY r.remind_at",
        instance_id=ctx.instance_id,
    )
    return {"reminders": result.get("rows", [])}


@router.delete("/{reminder_id}")
def cancel_reminder(reminder_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    result = execute_query(
        "UPDATE reminders SET status = 'cancelled' WHERE id = ? AND instance_id = ?",
        [reminder_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if result.get("rowcount", 0) == 0:
        return {"ok": False, "error": "Reminder not found"}
    return {"ok": True}
