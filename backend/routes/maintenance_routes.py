"""Preventive maintenance, work orders, inspections, and checklists REST API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth import InstanceContext, get_current_instance
from backend.database import execute_query

router = APIRouter(prefix="/maintenance")


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class CreateMaintenanceTaskBody(BaseModel):
    name: str
    description: str | None = None
    category: str = "general"
    estimated_duration_minutes: int | None = None
    required_skills: str | None = None
    required_tools: str | None = None
    instructions: str | None = None
    safety_notes: str | None = None
    vendor_id: int | None = None
    estimated_cost: float | None = None
    asset_type_filter: str | None = None


class CreateChecklistTemplateBody(BaseModel):
    name: str
    description: str | None = None
    checklist_type: str = "maintenance"
    category: str | None = None


class AddChecklistItemBody(BaseModel):
    item_text: str
    item_type: str = "pass_fail"
    is_required: bool = True
    sort_order: int = 0
    numeric_min: float | None = None
    numeric_max: float | None = None
    numeric_unit: str | None = None
    help_text: str | None = None
    failure_creates_ticket: bool = False


class CreateMaintenancePlanBody(BaseModel):
    name: str
    description: str | None = None
    plan_type: str = "preventive"
    priority: str = "medium"
    recurrence: str = "monthly"
    custom_interval_days: int | None = None
    start_date: str
    end_date: str | None = None
    lead_time_days: int = 3
    seasonal_months: str | None = None
    exclude_weekends: bool = True
    site_id: int | None = None
    room_id: int | None = None
    asset_id: int | None = None
    assigned_team_id: int | None = None
    assigned_person_id: int | None = None
    vendor_id: int | None = None
    checklist_template_id: int | None = None
    compliance_standard: str | None = None
    regulatory_reference: str | None = None
    task_ids: list[int] | None = None


class CreateWorkOrderBody(BaseModel):
    title: str
    description: str | None = None
    wo_type: str = "preventive"
    priority: str = "medium"
    site_id: int | None = None
    room_id: int | None = None
    asset_id: int | None = None
    assigned_team_id: int | None = None
    assigned_person_id: int | None = None
    vendor_id: int | None = None
    due_date: str | None = None
    checklist_template_id: int | None = None
    estimated_cost: float | None = None
    estimated_duration_minutes: int | None = None


class CreateInspectionBody(BaseModel):
    name: str
    description: str | None = None
    inspection_type: str = "routine"
    priority: str = "medium"
    recurrence: str = "monthly"
    custom_interval_days: int | None = None
    start_date: str
    end_date: str | None = None
    lead_time_days: int = 1
    site_id: int | None = None
    room_id: int | None = None
    asset_id: int | None = None
    assigned_person_id: int | None = None
    assigned_team_id: int | None = None
    checklist_template_id: int | None = None
    compliance_standard: str | None = None
    regulatory_reference: str | None = None
    certification_required: bool = False


class CreateInspectionRecordBody(BaseModel):
    title: str
    description: str | None = None
    priority: str = "medium"
    inspector_person_id: int | None = None
    site_id: int | None = None
    room_id: int | None = None
    asset_id: int | None = None
    scheduled_date: str | None = None
    due_date: str | None = None
    checklist_template_id: int | None = None
    compliance_standard: str | None = None


class SubmitChecklistResponsesBody(BaseModel):
    responses: list[dict]


class CompleteWorkOrderBody(BaseModel):
    findings: str | None = None
    resolution: str | None = None
    actual_duration_minutes: int | None = None
    actual_cost: float | None = None
    follow_up_needed: bool = False
    follow_up_notes: str | None = None


class CompleteInspectionRecordBody(BaseModel):
    overall_result: str
    findings: str | None = None
    corrective_actions: str | None = None
    follow_up_needed: bool = False
    follow_up_notes: str | None = None


class RecordPartsBody(BaseModel):
    inventory_item_id: int
    quantity_used: int = 1
    unit_cost: float | None = None
    notes: str | None = None


class AddPlanTaskBody(BaseModel):
    maintenance_task_id: int
    sort_order: int = 0
    is_required: bool = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_404(table: str, record_id: int, instance_id: int, label: str = "Record") -> dict:
    result = execute_query(
        f"SELECT * FROM {table} WHERE id = ? AND instance_id = ?",
        [record_id, instance_id],
        instance_id=instance_id,
    )
    if not result.get("rows"):
        raise HTTPException(status_code=404, detail=f"{label} #{record_id} not found")
    return result["rows"][0]


def _submit_checklist_responses(
    responses: list[dict],
    instance_id: int,
    person_id: int,
    parent_record: dict,
    parent_id_col: str,
    parent_id: int,
) -> list[int]:
    """Shared logic for submitting checklist responses for WOs or inspection records."""
    tickets_created = []
    for resp in responses:
        item_id = resp.get("checklist_template_item_id")
        if not item_id:
            continue

        item_result = execute_query(
            "SELECT item_type, numeric_min, numeric_max, item_text, "
            "failure_creates_ticket FROM checklist_template_items "
            "WHERE id = ? AND instance_id = ?",
            [item_id, instance_id],
            instance_id=instance_id,
        )
        if not item_result.get("rows"):
            continue
        item = item_result["rows"][0]

        col_map = {
            "pass_fail": "response_pass_fail",
            "yes_no": "response_yes_no",
            "numeric": "response_numeric",
            "text": "response_text",
            "photo": "response_photo_path",
            "rating": "response_rating",
        }
        response_col = col_map.get(item["item_type"], "response_text")
        response_val = resp.get("response_value")

        is_within_spec = None
        if item["item_type"] == "numeric" and response_val is not None:
            val = float(response_val)
            in_range = True
            if item.get("numeric_min") is not None and val < float(item["numeric_min"]):
                in_range = False
            if item.get("numeric_max") is not None and val > float(item["numeric_max"]):
                in_range = False
            is_within_spec = in_range

        is_failure = False
        if item["item_type"] == "pass_fail" and response_val == "fail":
            is_failure = True
        elif item["item_type"] == "yes_no" and response_val == "no":
            is_failure = True
        elif is_within_spec is False:
            is_failure = True

        execute_query(
            f"INSERT INTO checklist_responses "
            f"(instance_id, {parent_id_col}, checklist_template_item_id, "
            f"{response_col}, is_within_spec, is_flagged, notes, "
            f"responded_by_person_id) "
            f"VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                instance_id, parent_id, item_id,
                response_val, is_within_spec, is_failure,
                resp.get("notes"), person_id,
            ],
            instance_id=instance_id,
        )

        if is_failure and item.get("failure_creates_ticket"):
            ticket_result = execute_query(
                "INSERT INTO tickets (instance_id, ticket_type, title, description, "
                "priority, status, source, site_id, room_id, asset_id) "
                "VALUES (?, 'incident', ?, ?, 'high', 'open', 'inspection', "
                "?, ?, ?)",
                [
                    instance_id,
                    f"Failed inspection: {item['item_text']}",
                    f"Auto-generated from checklist. "
                    f"Item '{item['item_text']}' failed. Notes: {resp.get('notes', 'N/A')}",
                    parent_record.get("site_id"),
                    parent_record.get("room_id"),
                    parent_record.get("asset_id"),
                ],
                instance_id=instance_id,
            )
            if ticket_result.get("lastrowid"):
                ticket_id = ticket_result["lastrowid"]
                execute_query(
                    f"UPDATE checklist_responses SET generated_ticket_id = ? "
                    f"WHERE {parent_id_col} = ? AND checklist_template_item_id = ? "
                    f"AND instance_id = ?",
                    [ticket_id, parent_id, item_id, instance_id],
                    instance_id=instance_id,
                )
                tickets_created.append(ticket_id)

    return tickets_created


# ===========================================================================
# MAINTENANCE TASKS (templates)
# ===========================================================================

@router.get("/tasks")
async def list_maintenance_tasks(ctx: InstanceContext = Depends(get_current_instance)):
    result = execute_query(
        "SELECT * FROM maintenance_tasks WHERE instance_id = ? AND is_active = TRUE "
        "ORDER BY name",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


@router.post("/tasks")
async def create_maintenance_task(
    body: CreateMaintenanceTaskBody,
    ctx: InstanceContext = Depends(get_current_instance),
):
    result = execute_query(
        "INSERT INTO maintenance_tasks (instance_id, name, description, category, "
        "estimated_duration_minutes, required_skills, required_tools, instructions, "
        "safety_notes, vendor_id, estimated_cost, asset_type_filter, created_by_person_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ctx.instance_id, body.name, body.description, body.category,
            body.estimated_duration_minutes, body.required_skills, body.required_tools,
            body.instructions, body.safety_notes, body.vendor_id, body.estimated_cost,
            body.asset_type_filter, ctx.person_id,
        ],
        instance_id=ctx.instance_id,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return {"id": result.get("lastrowid"), "success": True}


@router.get("/tasks/{task_id}")
async def get_maintenance_task(
    task_id: int,
    ctx: InstanceContext = Depends(get_current_instance),
):
    return _get_or_404("maintenance_tasks", task_id, ctx.instance_id, "Maintenance task")


@router.patch("/tasks/{task_id}")
async def update_maintenance_task(
    task_id: int,
    body: dict,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("maintenance_tasks", task_id, ctx.instance_id, "Maintenance task")
    allowed = {
        "name", "description", "category", "estimated_duration_minutes",
        "required_skills", "required_tools", "instructions", "safety_notes",
        "vendor_id", "estimated_cost", "asset_type_filter", "is_active", "important",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [task_id, ctx.instance_id]
    execute_query(
        f"UPDATE maintenance_tasks SET {set_clause} WHERE id = ? AND instance_id = ?",
        params,
        instance_id=ctx.instance_id,
    )
    return {"success": True}


@router.delete("/tasks/{task_id}")
async def delete_maintenance_task(
    task_id: int,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("maintenance_tasks", task_id, ctx.instance_id, "Maintenance task")
    execute_query(
        "UPDATE maintenance_tasks SET is_active = FALSE WHERE id = ? AND instance_id = ?",
        [task_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return {"success": True}


# ===========================================================================
# CHECKLIST TEMPLATES
# ===========================================================================

@router.get("/checklists")
async def list_checklist_templates(ctx: InstanceContext = Depends(get_current_instance)):
    result = execute_query(
        "SELECT * FROM checklist_templates WHERE instance_id = ? AND is_active = TRUE "
        "ORDER BY name",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


@router.post("/checklists")
async def create_checklist_template(
    body: CreateChecklistTemplateBody,
    ctx: InstanceContext = Depends(get_current_instance),
):
    result = execute_query(
        "INSERT INTO checklist_templates (instance_id, name, description, "
        "checklist_type, category, created_by_person_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [ctx.instance_id, body.name, body.description, body.checklist_type,
         body.category, ctx.person_id],
        instance_id=ctx.instance_id,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return {"id": result.get("lastrowid"), "success": True}


@router.get("/checklists/{checklist_id}")
async def get_checklist_template(
    checklist_id: int,
    ctx: InstanceContext = Depends(get_current_instance),
):
    checklist = _get_or_404("checklist_templates", checklist_id, ctx.instance_id, "Checklist")
    items_result = execute_query(
        "SELECT * FROM checklist_template_items WHERE checklist_template_id = ? "
        "AND instance_id = ? ORDER BY sort_order",
        [checklist_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    checklist["items"] = items_result.get("rows", [])
    return checklist


@router.patch("/checklists/{checklist_id}")
async def update_checklist_template(
    checklist_id: int,
    body: dict,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("checklist_templates", checklist_id, ctx.instance_id, "Checklist")
    allowed = {"name", "description", "checklist_type", "category", "is_active"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    # Increment version on content changes
    if any(k in updates for k in ("name", "description", "checklist_type", "category")):
        updates_sql = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [checklist_id, ctx.instance_id]
        execute_query(
            f"UPDATE checklist_templates SET {updates_sql}, version = version + 1 "
            f"WHERE id = ? AND instance_id = ?",
            params,
            instance_id=ctx.instance_id,
        )
    else:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [checklist_id, ctx.instance_id]
        execute_query(
            f"UPDATE checklist_templates SET {set_clause} WHERE id = ? AND instance_id = ?",
            params,
            instance_id=ctx.instance_id,
        )
    return {"success": True}


@router.post("/checklists/{checklist_id}/items")
async def add_checklist_item(
    checklist_id: int,
    body: AddChecklistItemBody,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("checklist_templates", checklist_id, ctx.instance_id, "Checklist")
    result = execute_query(
        "INSERT INTO checklist_template_items (instance_id, checklist_template_id, "
        "sort_order, item_text, item_type, is_required, numeric_min, numeric_max, "
        "numeric_unit, help_text, failure_creates_ticket) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ctx.instance_id, checklist_id, body.sort_order, body.item_text,
            body.item_type, body.is_required, body.numeric_min, body.numeric_max,
            body.numeric_unit, body.help_text, body.failure_creates_ticket,
        ],
        instance_id=ctx.instance_id,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    # Increment checklist version
    execute_query(
        "UPDATE checklist_templates SET version = version + 1 WHERE id = ? AND instance_id = ?",
        [checklist_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return {"id": result.get("lastrowid"), "success": True}


@router.patch("/checklists/{checklist_id}/items/{item_id}")
async def update_checklist_item(
    checklist_id: int,
    item_id: int,
    body: dict,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("checklist_template_items", item_id, ctx.instance_id, "Checklist item")
    allowed = {
        "item_text", "item_type", "is_required", "sort_order",
        "numeric_min", "numeric_max", "numeric_unit", "help_text", "failure_creates_ticket",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [item_id, ctx.instance_id]
    execute_query(
        f"UPDATE checklist_template_items SET {set_clause} WHERE id = ? AND instance_id = ?",
        params,
        instance_id=ctx.instance_id,
    )
    return {"success": True}


@router.delete("/checklists/{checklist_id}/items/{item_id}")
async def delete_checklist_item(
    checklist_id: int,
    item_id: int,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("checklist_template_items", item_id, ctx.instance_id, "Checklist item")
    execute_query(
        "DELETE FROM checklist_template_items WHERE id = ? AND instance_id = ?",
        [item_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return {"success": True}


# ===========================================================================
# MAINTENANCE PLANS
# ===========================================================================

@router.get("/plans")
async def list_maintenance_plans(ctx: InstanceContext = Depends(get_current_instance)):
    result = execute_query(
        "SELECT mp.*, "
        "(SELECT COUNT(*) FROM maintenance_plan_tasks mpt "
        " WHERE mpt.maintenance_plan_id = mp.id AND mpt.instance_id = mp.instance_id) AS task_count "
        "FROM maintenance_plans mp "
        "WHERE mp.instance_id = ? AND mp.status != 'archived' "
        "ORDER BY mp.next_due_date",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


@router.post("/plans")
async def create_maintenance_plan(
    body: CreateMaintenancePlanBody,
    ctx: InstanceContext = Depends(get_current_instance),
):
    result = execute_query(
        "INSERT INTO maintenance_plans (instance_id, name, description, plan_type, "
        "priority, recurrence, custom_interval_days, start_date, end_date, "
        "next_due_date, lead_time_days, seasonal_months, exclude_weekends, "
        "site_id, room_id, asset_id, assigned_team_id, assigned_person_id, "
        "vendor_id, checklist_template_id, compliance_standard, "
        "regulatory_reference, created_by_person_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ctx.instance_id, body.name, body.description, body.plan_type,
            body.priority, body.recurrence, body.custom_interval_days,
            body.start_date, body.end_date, body.start_date,
            body.lead_time_days, body.seasonal_months, body.exclude_weekends,
            body.site_id, body.room_id, body.asset_id, body.assigned_team_id,
            body.assigned_person_id, body.vendor_id, body.checklist_template_id,
            body.compliance_standard, body.regulatory_reference, ctx.person_id,
        ],
        instance_id=ctx.instance_id,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    plan_id = result.get("lastrowid")

    # Add tasks if provided
    if body.task_ids:
        for i, task_id in enumerate(body.task_ids):
            execute_query(
                "INSERT INTO maintenance_plan_tasks (instance_id, maintenance_plan_id, "
                "maintenance_task_id, sort_order) VALUES (?, ?, ?, ?)",
                [ctx.instance_id, plan_id, task_id, i],
                instance_id=ctx.instance_id,
            )

    return {"id": plan_id, "success": True}


@router.get("/plans/{plan_id}")
async def get_maintenance_plan(
    plan_id: int,
    ctx: InstanceContext = Depends(get_current_instance),
):
    plan = _get_or_404("maintenance_plans", plan_id, ctx.instance_id, "Maintenance plan")
    tasks_result = execute_query(
        "SELECT mpt.*, mt.name AS task_name, mt.category, mt.estimated_duration_minutes "
        "FROM maintenance_plan_tasks mpt "
        "JOIN maintenance_tasks mt ON mpt.maintenance_task_id = mt.id "
        "AND mt.instance_id = mpt.instance_id "
        "WHERE mpt.maintenance_plan_id = ? AND mpt.instance_id = ? "
        "ORDER BY mpt.sort_order",
        [plan_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    plan["tasks"] = tasks_result.get("rows", [])
    return plan


@router.patch("/plans/{plan_id}")
async def update_maintenance_plan(
    plan_id: int,
    body: dict,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("maintenance_plans", plan_id, ctx.instance_id, "Maintenance plan")
    allowed = {
        "name", "description", "plan_type", "priority", "recurrence",
        "custom_interval_days", "end_date", "next_due_date", "lead_time_days",
        "seasonal_months", "exclude_weekends", "site_id", "room_id", "asset_id",
        "assigned_team_id", "assigned_person_id", "vendor_id", "checklist_template_id",
        "compliance_standard", "regulatory_reference", "status", "important",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [plan_id, ctx.instance_id]
    execute_query(
        f"UPDATE maintenance_plans SET {set_clause} WHERE id = ? AND instance_id = ?",
        params,
        instance_id=ctx.instance_id,
    )
    return {"success": True}


@router.post("/plans/{plan_id}/tasks")
async def add_plan_task(
    plan_id: int,
    body: AddPlanTaskBody,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("maintenance_plans", plan_id, ctx.instance_id, "Maintenance plan")
    result = execute_query(
        "INSERT INTO maintenance_plan_tasks (instance_id, maintenance_plan_id, "
        "maintenance_task_id, sort_order, is_required) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT DO NOTHING",
        [ctx.instance_id, plan_id, body.maintenance_task_id, body.sort_order, body.is_required],
        instance_id=ctx.instance_id,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return {"success": True}


@router.delete("/plans/{plan_id}/tasks/{task_id}")
async def remove_plan_task(
    plan_id: int,
    task_id: int,
    ctx: InstanceContext = Depends(get_current_instance),
):
    execute_query(
        "DELETE FROM maintenance_plan_tasks "
        "WHERE maintenance_plan_id = ? AND maintenance_task_id = ? AND instance_id = ?",
        [plan_id, task_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return {"success": True}


@router.post("/plans/{plan_id}/generate")
async def manually_generate_work_order(
    plan_id: int,
    ctx: InstanceContext = Depends(get_current_instance),
):
    """Manually trigger work order generation from a maintenance plan."""
    plan = _get_or_404("maintenance_plans", plan_id, ctx.instance_id, "Maintenance plan")

    checklist_version = None
    if plan.get("checklist_template_id"):
        ver = execute_query(
            "SELECT version FROM checklist_templates WHERE id = ? AND instance_id = ?",
            [plan["checklist_template_id"], ctx.instance_id],
            instance_id=ctx.instance_id,
        )
        if ver.get("rows"):
            checklist_version = ver["rows"][0]["version"]

    result = execute_query(
        "INSERT INTO work_orders (instance_id, title, description, wo_type, "
        "priority, maintenance_plan_id, source, site_id, room_id, asset_id, "
        "assigned_team_id, assigned_person_id, vendor_id, "
        "checklist_template_id, checklist_template_version) "
        "VALUES (?, ?, ?, 'preventive', ?, ?, 'manual', ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ctx.instance_id, f"PM: {plan['name']}", plan.get("description"),
            plan.get("priority", "medium"), plan["id"],
            plan.get("site_id"), plan.get("room_id"), plan.get("asset_id"),
            plan.get("assigned_team_id"), plan.get("assigned_person_id"),
            plan.get("vendor_id"), plan.get("checklist_template_id"), checklist_version,
        ],
        instance_id=ctx.instance_id,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return {"id": result.get("lastrowid"), "success": True}


# ===========================================================================
# WORK ORDERS
# ===========================================================================

@router.get("/work-orders")
async def list_work_orders(
    status: str | None = None,
    ctx: InstanceContext = Depends(get_current_instance),
):
    sql = "SELECT * FROM work_orders WHERE instance_id = ?"
    params: list = [ctx.instance_id]
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY created_at DESC"
    result = execute_query(sql, params, instance_id=ctx.instance_id)
    return result.get("rows", [])


@router.post("/work-orders")
async def create_work_order(
    body: CreateWorkOrderBody,
    ctx: InstanceContext = Depends(get_current_instance),
):
    checklist_version = None
    if body.checklist_template_id:
        ver = execute_query(
            "SELECT version FROM checklist_templates WHERE id = ? AND instance_id = ?",
            [body.checklist_template_id, ctx.instance_id],
            instance_id=ctx.instance_id,
        )
        if ver.get("rows"):
            checklist_version = ver["rows"][0]["version"]

    result = execute_query(
        "INSERT INTO work_orders (instance_id, title, description, wo_type, "
        "priority, source, site_id, room_id, asset_id, assigned_team_id, "
        "assigned_person_id, vendor_id, due_date, checklist_template_id, "
        "checklist_template_version, estimated_cost, estimated_duration_minutes) "
        "VALUES (?, ?, ?, ?, ?, 'manual', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ctx.instance_id, body.title, body.description, body.wo_type,
            body.priority, body.site_id, body.room_id, body.asset_id,
            body.assigned_team_id, body.assigned_person_id, body.vendor_id,
            body.due_date, body.checklist_template_id, checklist_version,
            body.estimated_cost, body.estimated_duration_minutes,
        ],
        instance_id=ctx.instance_id,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return {"id": result.get("lastrowid"), "success": True}


@router.get("/work-orders/{wo_id}")
async def get_work_order(
    wo_id: int,
    ctx: InstanceContext = Depends(get_current_instance),
):
    wo = _get_or_404("work_orders", wo_id, ctx.instance_id, "Work order")
    responses = execute_query(
        "SELECT cr.*, cti.item_text, cti.item_type "
        "FROM checklist_responses cr "
        "JOIN checklist_template_items cti ON cr.checklist_template_item_id = cti.id "
        "WHERE cr.work_order_id = ? AND cr.instance_id = ? "
        "ORDER BY cti.sort_order",
        [wo_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    wo["checklist_responses"] = responses.get("rows", [])
    parts = execute_query(
        "SELECT wop.*, ii.name AS item_name, ii.sku "
        "FROM work_order_parts wop "
        "JOIN inventory_items ii ON wop.inventory_item_id = ii.id "
        "AND ii.instance_id = wop.instance_id "
        "WHERE wop.work_order_id = ? AND wop.instance_id = ?",
        [wo_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    wo["parts"] = parts.get("rows", [])
    return wo


@router.patch("/work-orders/{wo_id}")
async def update_work_order(
    wo_id: int,
    body: dict,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("work_orders", wo_id, ctx.instance_id, "Work order")
    allowed = {
        "title", "description", "wo_type", "priority", "status",
        "assigned_team_id", "assigned_person_id", "vendor_id", "vendor_reference",
        "due_date", "scheduled_start", "scheduled_end", "actual_start", "actual_end",
        "estimated_cost", "actual_cost", "estimated_duration_minutes",
        "actual_duration_minutes", "findings", "resolution",
        "follow_up_needed", "follow_up_notes", "important",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [wo_id, ctx.instance_id]
    execute_query(
        f"UPDATE work_orders SET {set_clause} WHERE id = ? AND instance_id = ?",
        params,
        instance_id=ctx.instance_id,
    )
    return {"success": True}


@router.post("/work-orders/{wo_id}/checklist")
async def submit_wo_checklist(
    wo_id: int,
    body: SubmitChecklistResponsesBody,
    ctx: InstanceContext = Depends(get_current_instance),
):
    wo = _get_or_404("work_orders", wo_id, ctx.instance_id, "Work order")
    tickets = _submit_checklist_responses(
        body.responses, ctx.instance_id, ctx.person_id,
        wo, "work_order_id", wo_id,
    )
    return {"success": True, "tickets_created": tickets}


@router.get("/work-orders/{wo_id}/checklist")
async def get_wo_checklist(
    wo_id: int,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("work_orders", wo_id, ctx.instance_id, "Work order")
    result = execute_query(
        "SELECT cr.*, cti.item_text, cti.item_type, cti.sort_order "
        "FROM checklist_responses cr "
        "JOIN checklist_template_items cti ON cr.checklist_template_item_id = cti.id "
        "WHERE cr.work_order_id = ? AND cr.instance_id = ? "
        "ORDER BY cti.sort_order",
        [wo_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


@router.post("/work-orders/{wo_id}/parts")
async def record_wo_parts(
    wo_id: int,
    body: RecordPartsBody,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("work_orders", wo_id, ctx.instance_id, "Work order")
    result = execute_query(
        "INSERT INTO work_order_parts (instance_id, work_order_id, inventory_item_id, "
        "quantity_used, unit_cost, notes) VALUES (?, ?, ?, ?, ?, ?)",
        [ctx.instance_id, wo_id, body.inventory_item_id, body.quantity_used,
         body.unit_cost, body.notes],
        instance_id=ctx.instance_id,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return {"id": result.get("lastrowid"), "success": True}


@router.get("/work-orders/{wo_id}/parts")
async def get_wo_parts(
    wo_id: int,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("work_orders", wo_id, ctx.instance_id, "Work order")
    result = execute_query(
        "SELECT wop.*, ii.name AS item_name, ii.sku "
        "FROM work_order_parts wop "
        "JOIN inventory_items ii ON wop.inventory_item_id = ii.id "
        "AND ii.instance_id = wop.instance_id "
        "WHERE wop.work_order_id = ? AND wop.instance_id = ?",
        [wo_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


@router.post("/work-orders/{wo_id}/complete")
async def complete_work_order(
    wo_id: int,
    body: CompleteWorkOrderBody,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("work_orders", wo_id, ctx.instance_id, "Work order")
    execute_query(
        "UPDATE work_orders SET status = 'completed', findings = ?, resolution = ?, "
        "actual_duration_minutes = ?, actual_cost = ?, follow_up_needed = ?, "
        "follow_up_notes = ?, completed_by_person_id = ?, actual_end = NOW() "
        "WHERE id = ? AND instance_id = ?",
        [
            body.findings, body.resolution, body.actual_duration_minutes,
            body.actual_cost, body.follow_up_needed, body.follow_up_notes,
            ctx.person_id, wo_id, ctx.instance_id,
        ],
        instance_id=ctx.instance_id,
    )
    return {"success": True}


# ===========================================================================
# INSPECTIONS (recurring schedules)
# ===========================================================================

@router.get("/inspections")
async def list_inspections(ctx: InstanceContext = Depends(get_current_instance)):
    result = execute_query(
        "SELECT * FROM inspections WHERE instance_id = ? AND status != 'archived' "
        "ORDER BY next_due_date",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


@router.post("/inspections")
async def create_inspection(
    body: CreateInspectionBody,
    ctx: InstanceContext = Depends(get_current_instance),
):
    result = execute_query(
        "INSERT INTO inspections (instance_id, name, description, inspection_type, "
        "priority, recurrence, custom_interval_days, start_date, end_date, "
        "next_due_date, lead_time_days, site_id, room_id, asset_id, "
        "assigned_person_id, assigned_team_id, checklist_template_id, "
        "compliance_standard, regulatory_reference, certification_required, "
        "created_by_person_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ctx.instance_id, body.name, body.description, body.inspection_type,
            body.priority, body.recurrence, body.custom_interval_days,
            body.start_date, body.end_date, body.start_date,
            body.lead_time_days, body.site_id, body.room_id, body.asset_id,
            body.assigned_person_id, body.assigned_team_id,
            body.checklist_template_id, body.compliance_standard,
            body.regulatory_reference, body.certification_required, ctx.person_id,
        ],
        instance_id=ctx.instance_id,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return {"id": result.get("lastrowid"), "success": True}


@router.get("/inspections/{inspection_id}")
async def get_inspection(
    inspection_id: int,
    ctx: InstanceContext = Depends(get_current_instance),
):
    insp = _get_or_404("inspections", inspection_id, ctx.instance_id, "Inspection")
    records = execute_query(
        "SELECT * FROM inspection_records WHERE inspection_id = ? AND instance_id = ? "
        "ORDER BY scheduled_date DESC LIMIT 20",
        [inspection_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    insp["recent_records"] = records.get("rows", [])
    return insp


@router.patch("/inspections/{inspection_id}")
async def update_inspection(
    inspection_id: int,
    body: dict,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("inspections", inspection_id, ctx.instance_id, "Inspection")
    allowed = {
        "name", "description", "inspection_type", "priority", "recurrence",
        "custom_interval_days", "end_date", "next_due_date", "lead_time_days",
        "site_id", "room_id", "asset_id", "assigned_person_id", "assigned_team_id",
        "checklist_template_id", "compliance_standard", "regulatory_reference",
        "certification_required", "status", "important",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [inspection_id, ctx.instance_id]
    execute_query(
        f"UPDATE inspections SET {set_clause} WHERE id = ? AND instance_id = ?",
        params,
        instance_id=ctx.instance_id,
    )
    return {"success": True}


@router.post("/inspections/{inspection_id}/generate")
async def manually_generate_inspection_record(
    inspection_id: int,
    ctx: InstanceContext = Depends(get_current_instance),
):
    insp = _get_or_404("inspections", inspection_id, ctx.instance_id, "Inspection")
    checklist_version = None
    if insp.get("checklist_template_id"):
        ver = execute_query(
            "SELECT version FROM checklist_templates WHERE id = ? AND instance_id = ?",
            [insp["checklist_template_id"], ctx.instance_id],
            instance_id=ctx.instance_id,
        )
        if ver.get("rows"):
            checklist_version = ver["rows"][0]["version"]

    result = execute_query(
        "INSERT INTO inspection_records (instance_id, inspection_id, title, "
        "description, priority, source, inspector_person_id, site_id, room_id, "
        "asset_id, scheduled_date, due_date, checklist_template_id, "
        "checklist_template_version, compliance_standard) "
        "VALUES (?, ?, ?, ?, ?, 'manual', ?, ?, ?, ?, CURRENT_DATE, "
        "CURRENT_DATE + INTERVAL '5 days', ?, ?, ?)",
        [
            ctx.instance_id, insp["id"], f"Inspection: {insp['name']}",
            insp.get("description"), insp.get("priority", "medium"),
            insp.get("assigned_person_id"), insp.get("site_id"),
            insp.get("room_id"), insp.get("asset_id"),
            insp.get("checklist_template_id"), checklist_version,
            insp.get("compliance_standard"),
        ],
        instance_id=ctx.instance_id,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return {"id": result.get("lastrowid"), "success": True}


# ===========================================================================
# INSPECTION RECORDS
# ===========================================================================

@router.get("/inspection-records")
async def list_inspection_records(
    status: str | None = None,
    ctx: InstanceContext = Depends(get_current_instance),
):
    sql = "SELECT * FROM inspection_records WHERE instance_id = ?"
    params: list = [ctx.instance_id]
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY created_at DESC"
    result = execute_query(sql, params, instance_id=ctx.instance_id)
    return result.get("rows", [])


@router.post("/inspection-records")
async def create_inspection_record(
    body: CreateInspectionRecordBody,
    ctx: InstanceContext = Depends(get_current_instance),
):
    checklist_version = None
    if body.checklist_template_id:
        ver = execute_query(
            "SELECT version FROM checklist_templates WHERE id = ? AND instance_id = ?",
            [body.checklist_template_id, ctx.instance_id],
            instance_id=ctx.instance_id,
        )
        if ver.get("rows"):
            checklist_version = ver["rows"][0]["version"]

    result = execute_query(
        "INSERT INTO inspection_records (instance_id, title, description, priority, "
        "source, inspector_person_id, site_id, room_id, asset_id, "
        "scheduled_date, due_date, checklist_template_id, "
        "checklist_template_version, compliance_standard) "
        "VALUES (?, ?, ?, ?, 'manual', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ctx.instance_id, body.title, body.description, body.priority,
            body.inspector_person_id, body.site_id, body.room_id, body.asset_id,
            body.scheduled_date, body.due_date, body.checklist_template_id,
            checklist_version, body.compliance_standard,
        ],
        instance_id=ctx.instance_id,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return {"id": result.get("lastrowid"), "success": True}


@router.get("/inspection-records/{record_id}")
async def get_inspection_record(
    record_id: int,
    ctx: InstanceContext = Depends(get_current_instance),
):
    record = _get_or_404("inspection_records", record_id, ctx.instance_id, "Inspection record")
    responses = execute_query(
        "SELECT cr.*, cti.item_text, cti.item_type "
        "FROM checklist_responses cr "
        "JOIN checklist_template_items cti ON cr.checklist_template_item_id = cti.id "
        "WHERE cr.inspection_record_id = ? AND cr.instance_id = ? "
        "ORDER BY cti.sort_order",
        [record_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    record["checklist_responses"] = responses.get("rows", [])
    return record


@router.patch("/inspection-records/{record_id}")
async def update_inspection_record(
    record_id: int,
    body: dict,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("inspection_records", record_id, ctx.instance_id, "Inspection record")
    allowed = {
        "title", "description", "priority", "status", "inspector_person_id",
        "reviewer_person_id", "scheduled_date", "performed_date", "due_date",
        "overall_result", "findings", "corrective_actions",
        "follow_up_needed", "follow_up_notes", "certification_number", "important",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [record_id, ctx.instance_id]
    execute_query(
        f"UPDATE inspection_records SET {set_clause} WHERE id = ? AND instance_id = ?",
        params,
        instance_id=ctx.instance_id,
    )
    return {"success": True}


@router.post("/inspection-records/{record_id}/checklist")
async def submit_ir_checklist(
    record_id: int,
    body: SubmitChecklistResponsesBody,
    ctx: InstanceContext = Depends(get_current_instance),
):
    record = _get_or_404("inspection_records", record_id, ctx.instance_id, "Inspection record")
    tickets = _submit_checklist_responses(
        body.responses, ctx.instance_id, ctx.person_id,
        record, "inspection_record_id", record_id,
    )
    return {"success": True, "tickets_created": tickets}


@router.get("/inspection-records/{record_id}/checklist")
async def get_ir_checklist(
    record_id: int,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("inspection_records", record_id, ctx.instance_id, "Inspection record")
    result = execute_query(
        "SELECT cr.*, cti.item_text, cti.item_type, cti.sort_order "
        "FROM checklist_responses cr "
        "JOIN checklist_template_items cti ON cr.checklist_template_item_id = cti.id "
        "WHERE cr.inspection_record_id = ? AND cr.instance_id = ? "
        "ORDER BY cti.sort_order",
        [record_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


@router.post("/inspection-records/{record_id}/complete")
async def complete_inspection_record(
    record_id: int,
    body: CompleteInspectionRecordBody,
    ctx: InstanceContext = Depends(get_current_instance),
):
    _get_or_404("inspection_records", record_id, ctx.instance_id, "Inspection record")
    status = "failed" if body.overall_result == "fail" else "completed"
    execute_query(
        "UPDATE inspection_records SET status = ?, overall_result = ?, findings = ?, "
        "corrective_actions = ?, follow_up_needed = ?, follow_up_notes = ?, "
        "performed_date = CURRENT_DATE WHERE id = ? AND instance_id = ?",
        [
            status, body.overall_result, body.findings, body.corrective_actions,
            body.follow_up_needed, body.follow_up_notes, record_id, ctx.instance_id,
        ],
        instance_id=ctx.instance_id,
    )
    return {"success": True}


# ===========================================================================
# REPORTS
# ===========================================================================

@router.get("/asset/{asset_id}/history")
async def asset_maintenance_history(
    asset_id: int,
    ctx: InstanceContext = Depends(get_current_instance),
):
    """Full maintenance and inspection history for an asset."""
    wos = execute_query(
        "SELECT id, wo_number, title, wo_type, status, priority, due_date, "
        "actual_end, findings, resolution "
        "FROM work_orders WHERE asset_id = ? AND instance_id = ? "
        "ORDER BY created_at DESC",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    irs = execute_query(
        "SELECT id, title, status, overall_result, scheduled_date, performed_date, "
        "findings, corrective_actions "
        "FROM inspection_records WHERE asset_id = ? AND instance_id = ? "
        "ORDER BY created_at DESC",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return {
        "work_orders": wos.get("rows", []),
        "inspection_records": irs.get("rows", []),
    }


@router.get("/overdue")
async def overdue_items(ctx: InstanceContext = Depends(get_current_instance)):
    wos = execute_query(
        "SELECT id, wo_number, title, priority, due_date "
        "FROM work_orders WHERE status = 'overdue' AND instance_id = ? "
        "ORDER BY due_date",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    irs = execute_query(
        "SELECT id, title, priority, due_date "
        "FROM inspection_records WHERE status = 'scheduled' AND due_date < CURRENT_DATE "
        "AND instance_id = ? ORDER BY due_date",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return {
        "work_orders": wos.get("rows", []),
        "inspection_records": irs.get("rows", []),
    }


@router.get("/stats")
async def maintenance_stats(ctx: InstanceContext = Depends(get_current_instance)):
    result = execute_query(
        "SELECT "
        "(SELECT COUNT(*) FROM work_orders WHERE status IN ('open','scheduled','in_progress') "
        " AND instance_id = ?) AS active_work_orders, "
        "(SELECT COUNT(*) FROM work_orders WHERE status = 'overdue' "
        " AND instance_id = ?) AS overdue_work_orders, "
        "(SELECT COUNT(*) FROM work_orders WHERE status = 'completed' "
        " AND instance_id = ?) AS completed_work_orders, "
        "(SELECT COUNT(*) FROM maintenance_plans WHERE status = 'active' "
        " AND instance_id = ?) AS active_plans, "
        "(SELECT COUNT(*) FROM inspections WHERE status = 'active' "
        " AND instance_id = ?) AS active_inspections, "
        "(SELECT COUNT(*) FROM inspection_records WHERE status = 'scheduled' "
        " AND due_date < CURRENT_DATE AND instance_id = ?) AS overdue_inspections",
        [ctx.instance_id] * 6,
        instance_id=ctx.instance_id,
    )
    if result.get("rows"):
        return result["rows"][0]
    return {}
