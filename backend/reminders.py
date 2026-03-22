"""Background processor for due reminders — sends email notifications."""

from datetime import datetime, timezone

from backend.database import execute_query
from backend.email_sender import send_email


def process_due_reminders() -> int:
    """Check for due reminders and send notification emails.

    Returns the number of reminders processed.
    """
    # Bypass RLS (instance_id=None) to query across all instances
    result = execute_query(
        "SELECT r.id, r.instance_id, r.title, r.message, r.recurrence, "
        "r.notify_email, r.notify_person_id, r.created_by_person_id "
        "FROM reminders r "
        "WHERE r.status = 'active' AND r.remind_at <= NOW() "
        "ORDER BY r.remind_at "
        "LIMIT 100",
        instance_id=None,
    )
    rows = result.get("rows", [])
    if not rows:
        return 0

    processed = 0
    for reminder in rows:
        try:
            body = f"Reminder: {reminder['title']}"
            if reminder.get("message"):
                body += f"\n\n{reminder['message']}"
            body += "\n\n— TrueCore.cloud Reminders"

            email_result = send_email(
                to_email=reminder["notify_email"],
                subject=f"Reminder: {reminder['title']}",
                body=body,
            )

            if email_result.get("success"):
                if reminder["recurrence"] == "one_time":
                    execute_query(
                        "UPDATE reminders SET status = 'completed', last_sent_at = NOW() "
                        "WHERE id = ? AND instance_id = ?",
                        [reminder["id"], reminder["instance_id"]],
                        instance_id=reminder["instance_id"],
                    )
                else:
                    # Bump remind_at forward based on recurrence
                    interval = _recurrence_interval(reminder["recurrence"])
                    execute_query(
                        "UPDATE reminders SET remind_at = remind_at + ?::interval, "
                        "last_sent_at = NOW() WHERE id = ? AND instance_id = ?",
                        [interval, reminder["id"], reminder["instance_id"]],
                        instance_id=reminder["instance_id"],
                    )
                processed += 1
            else:
                print(f"[reminders] Email failed for reminder {reminder['id']}: {email_result.get('error')}")
        except Exception as e:
            print(f"[reminders] Error processing reminder {reminder['id']}: {e}")

    return processed


def _recurrence_interval(recurrence: str) -> str:
    """Return a PostgreSQL interval string for the given recurrence type."""
    return {
        "daily": "1 day",
        "weekly": "7 days",
        "monthly": "1 month",
    }.get(recurrence, "1 day")
