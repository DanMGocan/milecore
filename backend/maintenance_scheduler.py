"""Background scheduler for preventive maintenance plans and inspections.

Generates work orders from due maintenance plans and inspection records
from due inspections. Runs cross-tenant (instance_id=None) then processes
each instance individually.
"""

from backend.database import execute_query
from backend.email_sender import send_email


def process_due_maintenance_plans() -> int:
    """Check for maintenance plans that need work orders generated.

    Returns the number of work orders created.
    """
    result = execute_query(
        "SELECT mp.id, mp.instance_id, mp.name, mp.description, mp.priority, "
        "mp.recurrence, mp.custom_interval_days, mp.next_due_date, "
        "mp.lead_time_days, mp.site_id, mp.room_id, mp.asset_id, "
        "mp.assigned_team_id, mp.assigned_person_id, mp.vendor_id, "
        "mp.checklist_template_id, mp.seasonal_months, mp.end_date "
        "FROM maintenance_plans mp "
        "WHERE mp.status = 'active' "
        "AND mp.next_due_date <= CURRENT_DATE + (mp.lead_time_days || ' days')::interval "
        "AND (mp.last_generated_at IS NULL "
        "     OR mp.last_generated_at < mp.next_due_date - (mp.lead_time_days || ' days')::interval) "
        "LIMIT 50",
        instance_id=None,
    )
    rows = result.get("rows", [])
    if not rows:
        return 0

    created = 0
    for plan in rows:
        try:
            # Check seasonal filter
            if plan.get("seasonal_months"):
                from datetime import datetime
                current_month = datetime.now().month
                allowed = [int(m.strip()) for m in plan["seasonal_months"].split(",")]
                if current_month not in allowed:
                    _advance_next_due_date(plan)
                    continue

            # Check end_date
            if plan.get("end_date") and str(plan["next_due_date"]) > str(plan["end_date"]):
                execute_query(
                    "UPDATE maintenance_plans SET status = 'completed' "
                    "WHERE id = ? AND instance_id = ?",
                    [plan["id"], plan["instance_id"]],
                    instance_id=plan["instance_id"],
                )
                continue

            # Get checklist version if applicable
            checklist_version = None
            if plan.get("checklist_template_id"):
                ver_result = execute_query(
                    "SELECT version FROM checklist_templates WHERE id = ? AND instance_id = ?",
                    [plan["checklist_template_id"], plan["instance_id"]],
                    instance_id=plan["instance_id"],
                )
                if ver_result.get("rows"):
                    checklist_version = ver_result["rows"][0]["version"]

            # Get task names for WO description
            tasks_result = execute_query(
                "SELECT mt.name FROM maintenance_plan_tasks mpt "
                "JOIN maintenance_tasks mt ON mpt.maintenance_task_id = mt.id "
                "AND mt.instance_id = mpt.instance_id "
                "WHERE mpt.maintenance_plan_id = ? AND mpt.instance_id = ? "
                "ORDER BY mpt.sort_order",
                [plan["id"], plan["instance_id"]],
                instance_id=plan["instance_id"],
            )
            task_names = [r["name"] for r in tasks_result.get("rows", [])]
            task_desc = "\n".join(f"- {t}" for t in task_names) if task_names else ""

            wo_description = plan.get("description") or ""
            if task_desc:
                wo_description += f"\n\nTasks:\n{task_desc}"

            # Create work order
            wo_result = execute_query(
                "INSERT INTO work_orders (instance_id, title, description, wo_type, "
                "priority, status, maintenance_plan_id, source, site_id, room_id, "
                "asset_id, assigned_team_id, assigned_person_id, vendor_id, "
                "checklist_template_id, checklist_template_version, due_date) "
                "VALUES (?, ?, ?, 'preventive', ?, 'open', ?, 'scheduled', "
                "?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    plan["instance_id"],
                    f"PM: {plan['name']}",
                    wo_description.strip() or None,
                    plan["priority"],
                    plan["id"],
                    plan.get("site_id"),
                    plan.get("room_id"),
                    plan.get("asset_id"),
                    plan.get("assigned_team_id"),
                    plan.get("assigned_person_id"),
                    plan.get("vendor_id"),
                    plan.get("checklist_template_id"),
                    checklist_version,
                    str(plan["next_due_date"]),
                ],
                instance_id=plan["instance_id"],
            )

            if wo_result.get("error"):
                print(f"[maintenance] WO creation error for plan {plan['id']}: {wo_result['error']}")
                continue

            # Create reminder for assigned person
            if plan.get("assigned_person_id"):
                person_result = execute_query(
                    "SELECT email, first_name FROM people "
                    "WHERE id = ? AND instance_id = ?",
                    [plan["assigned_person_id"], plan["instance_id"]],
                    instance_id=plan["instance_id"],
                )
                if person_result.get("rows") and person_result["rows"][0].get("email"):
                    person = person_result["rows"][0]
                    execute_query(
                        "INSERT INTO reminders (instance_id, title, message, "
                        "remind_at, recurrence, notify_email, notify_person_id) "
                        "VALUES (?, ?, ?, ?, 'one_time', ?, ?)",
                        [
                            plan["instance_id"],
                            f"Maintenance due: {plan['name']}",
                            f"Work order created for: {plan['name']}. Due: {plan['next_due_date']}",
                            str(plan["next_due_date"]),
                            person["email"],
                            plan["assigned_person_id"],
                        ],
                        instance_id=plan["instance_id"],
                    )

            _advance_next_due_date(plan)
            created += 1

        except Exception as e:
            print(f"[maintenance] Error processing plan {plan['id']}: {e}")

    return created


def process_due_inspections() -> int:
    """Check for inspections that need inspection records generated.

    Returns the number of inspection records created.
    """
    result = execute_query(
        "SELECT i.id, i.instance_id, i.name, i.description, i.priority, "
        "i.recurrence, i.custom_interval_days, i.next_due_date, "
        "i.lead_time_days, i.site_id, i.room_id, i.asset_id, "
        "i.assigned_person_id, i.assigned_team_id, "
        "i.checklist_template_id, i.compliance_standard, i.end_date "
        "FROM inspections i "
        "WHERE i.status = 'active' "
        "AND i.next_due_date <= CURRENT_DATE + (i.lead_time_days || ' days')::interval "
        "AND (i.last_generated_at IS NULL "
        "     OR i.last_generated_at < i.next_due_date - (i.lead_time_days || ' days')::interval) "
        "LIMIT 50",
        instance_id=None,
    )
    rows = result.get("rows", [])
    if not rows:
        return 0

    created = 0
    for insp in rows:
        try:
            if insp.get("end_date") and str(insp["next_due_date"]) > str(insp["end_date"]):
                execute_query(
                    "UPDATE inspections SET status = 'completed' "
                    "WHERE id = ? AND instance_id = ?",
                    [insp["id"], insp["instance_id"]],
                    instance_id=insp["instance_id"],
                )
                continue

            # Get checklist version
            checklist_version = None
            if insp.get("checklist_template_id"):
                ver_result = execute_query(
                    "SELECT version FROM checklist_templates WHERE id = ? AND instance_id = ?",
                    [insp["checklist_template_id"], insp["instance_id"]],
                    instance_id=insp["instance_id"],
                )
                if ver_result.get("rows"):
                    checklist_version = ver_result["rows"][0]["version"]

            # Create inspection record
            ir_result = execute_query(
                "INSERT INTO inspection_records (instance_id, inspection_id, title, "
                "description, priority, status, source, inspector_person_id, "
                "site_id, room_id, asset_id, scheduled_date, due_date, "
                "checklist_template_id, checklist_template_version, compliance_standard) "
                "VALUES (?, ?, ?, ?, ?, 'scheduled', 'scheduled', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    insp["instance_id"],
                    insp["id"],
                    f"Inspection: {insp['name']}",
                    insp.get("description"),
                    insp["priority"],
                    insp.get("assigned_person_id"),
                    insp.get("site_id"),
                    insp.get("room_id"),
                    insp.get("asset_id"),
                    str(insp["next_due_date"]),
                    str(insp["next_due_date"]),
                    insp.get("checklist_template_id"),
                    checklist_version,
                    insp.get("compliance_standard"),
                ],
                instance_id=insp["instance_id"],
            )

            if ir_result.get("error"):
                print(f"[maintenance] Inspection record error for inspection {insp['id']}: {ir_result['error']}")
                continue

            # Create reminder for inspector
            if insp.get("assigned_person_id"):
                person_result = execute_query(
                    "SELECT email, first_name FROM people "
                    "WHERE id = ? AND instance_id = ?",
                    [insp["assigned_person_id"], insp["instance_id"]],
                    instance_id=insp["instance_id"],
                )
                if person_result.get("rows") and person_result["rows"][0].get("email"):
                    person = person_result["rows"][0]
                    execute_query(
                        "INSERT INTO reminders (instance_id, title, message, "
                        "remind_at, recurrence, notify_email, notify_person_id) "
                        "VALUES (?, ?, ?, ?, 'one_time', ?, ?)",
                        [
                            insp["instance_id"],
                            f"Inspection due: {insp['name']}",
                            f"Inspection scheduled: {insp['name']}. Due: {insp['next_due_date']}",
                            str(insp["next_due_date"]),
                            person["email"],
                            insp["assigned_person_id"],
                        ],
                        instance_id=insp["instance_id"],
                    )

            _advance_next_due_date(insp, table="inspections")
            created += 1

        except Exception as e:
            print(f"[maintenance] Error processing inspection {insp['id']}: {e}")

    return created


def check_overdue_work_orders() -> int:
    """Mark open/scheduled work orders past their due date as overdue."""
    result = execute_query(
        "UPDATE work_orders SET status = 'overdue' "
        "WHERE status IN ('open', 'scheduled') "
        "AND due_date < CURRENT_DATE",
        instance_id=None,
        _unsafe=True,
    )
    return result.get("rowcount", 0)


def _advance_next_due_date(record: dict, table: str = "maintenance_plans") -> None:
    """Move the record's next_due_date forward by its recurrence interval."""
    interval = _recurrence_interval(
        record["recurrence"], record.get("custom_interval_days")
    )
    execute_query(
        f"UPDATE {table} SET "
        "next_due_date = next_due_date + ?::interval, "
        "last_generated_at = NOW() "
        "WHERE id = ? AND instance_id = ?",
        [interval, record["id"], record["instance_id"]],
        instance_id=record["instance_id"],
    )


def _recurrence_interval(recurrence: str, custom_days: int | None = None) -> str:
    """Return a PostgreSQL interval string for the given recurrence type."""
    intervals = {
        "daily": "1 day",
        "weekly": "7 days",
        "biweekly": "14 days",
        "monthly": "1 month",
        "quarterly": "3 months",
        "semi_annual": "6 months",
        "annual": "1 year",
    }
    if recurrence == "custom" and custom_days:
        return f"{custom_days} days"
    return intervals.get(recurrence, "1 month")
