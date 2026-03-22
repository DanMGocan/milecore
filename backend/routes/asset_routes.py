"""Asset lifecycle REST API: CRUD, lifecycle transitions, assignments,
software/licenses, documents, and disposal."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from backend.auth import InstanceContext, get_current_instance
from backend.database import execute_query
from backend.s3_storage import download_image, delete_image

import boto3
from backend.config import (
    S3_ACCESS_KEY, S3_BUCKET, S3_ENDPOINT, S3_REGION, S3_SECRET_KEY,
    TICKET_ATTACHMENT_MAX_SIZE_MB,
)

router = APIRouter(prefix="/assets")

# ---------------------------------------------------------------------------
# Lifecycle state machine
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[str, set[str]] = {
    "active": {"deployed", "spare", "in_repair", "decommissioned", "lost"},
    "deployed": {"active", "spare", "in_repair", "pending_disposal", "lost"},
    "spare": {"deployed", "pending_disposal", "decommissioned"},
    "in_repair": {"active", "spare", "decommissioned", "pending_disposal"},
    "pending_disposal": {"disposed", "active"},
    "decommissioned": {"pending_disposal", "disposed"},
    "lost": {"active"},
    "disposed": set(),
}

ALL_STATUSES = set(VALID_TRANSITIONS.keys())

# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class CreateAssetBody(BaseModel):
    asset_tag: str | None = None
    serial_number: str | None = None
    hostname: str | None = None
    asset_type: str
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    operating_system: str | None = None
    purchase_date: str | None = None
    purchase_cost: float | None = None
    warranty_expiry: str | None = None
    warranty_type: str | None = None
    lifecycle_status: str = "active"
    ownership_type: str | None = None
    vendor_id: int | None = None
    site_id: int | None = None
    room_id: int | None = None
    assigned_to_person_id: int | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    criticality: str = "low"
    replacement_due_date: str | None = None
    notes: str | None = None
    important: bool = False


class UpdateAssetBody(BaseModel):
    asset_tag: str | None = None
    serial_number: str | None = None
    hostname: str | None = None
    asset_type: str | None = None
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    operating_system: str | None = None
    purchase_date: str | None = None
    purchase_cost: float | None = None
    warranty_expiry: str | None = None
    warranty_type: str | None = None
    ownership_type: str | None = None
    vendor_id: int | None = None
    site_id: int | None = None
    room_id: int | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    criticality: str | None = None
    replacement_due_date: str | None = None
    notes: str | None = None
    important: bool | None = None


class TransitionBody(BaseModel):
    new_status: str
    reason: str | None = None


class AssignBody(BaseModel):
    person_id: int
    notes: str | None = None


class InstallSoftwareBody(BaseModel):
    software_name: str
    version: str | None = None
    license_id: int | None = None
    installed_by_person_id: int | None = None
    notes: str | None = None


class CreateLicenseBody(BaseModel):
    name: str
    vendor_id: int | None = None
    license_key: str | None = None
    license_type: str = "perpetual"
    seat_count: int | None = None
    cost: float | None = None
    cost_currency: str = "EUR"
    purchase_date: str | None = None
    expiry_date: str | None = None
    notes: str | None = None


class UpdateLicenseBody(BaseModel):
    name: str | None = None
    vendor_id: int | None = None
    license_key: str | None = None
    license_type: str | None = None
    seat_count: int | None = None
    cost: float | None = None
    cost_currency: str | None = None
    purchase_date: str | None = None
    expiry_date: str | None = None
    notes: str | None = None
    status: str | None = None


class DisposeBody(BaseModel):
    disposal_method: str
    authorized_by_person_id: int | None = None
    performed_by_person_id: int | None = None
    certificate_reference: str | None = None
    proceeds: float | None = None
    proceeds_currency: str = "EUR"
    data_wiped: bool = False
    data_wipe_method: str | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_asset_or_404(asset_id: int, instance_id: int) -> dict:
    result = execute_query(
        "SELECT * FROM assets WHERE id = ? AND instance_id = ?",
        [asset_id, instance_id],
        instance_id=instance_id,
    )
    if not result.get("rows"):
        raise HTTPException(status_code=404, detail=f"Asset #{asset_id} not found")
    return result["rows"][0]


def _upload_document_to_s3(instance_id: int, asset_id: int, file_id: str,
                           file_bytes: bytes, content_type: str) -> str:
    """Upload raw file to S3 under assets path. Returns s3_key."""
    ext = content_type.split("/")[-1] if "/" in content_type else "bin"
    s3_key = f"assets/{instance_id}/{asset_id}/{file_id}.{ext}"

    client = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
    )
    client.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=file_bytes, ContentType=content_type)
    return s3_key


# ---------------------------------------------------------------------------
# Asset CRUD
# ---------------------------------------------------------------------------

@router.get("/")
async def list_assets(
    ctx: InstanceContext = Depends(get_current_instance),
    lifecycle_status: str | None = None,
    asset_type: str | None = None,
    criticality: str | None = None,
    site_id: int | None = None,
    assigned_to_person_id: int | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    conditions = ["a.instance_id = ?"]
    params: list = [ctx.instance_id]

    if lifecycle_status:
        conditions.append("a.lifecycle_status = ?")
        params.append(lifecycle_status)
    if asset_type:
        conditions.append("a.asset_type = ?")
        params.append(asset_type)
    if criticality:
        conditions.append("a.criticality = ?")
        params.append(criticality)
    if site_id is not None:
        conditions.append("a.site_id = ?")
        params.append(site_id)
    if assigned_to_person_id is not None:
        conditions.append("a.assigned_to_person_id = ?")
        params.append(assigned_to_person_id)
    if search:
        conditions.append(
            "(a.asset_tag ILIKE ? OR a.serial_number ILIKE ? OR a.hostname ILIKE ? "
            "OR a.brand ILIKE ? OR a.model ILIKE ? OR a.notes ILIKE ?)"
        )
        like = f"%{search}%"
        params.extend([like] * 6)

    where = " AND ".join(conditions)
    offset = (page - 1) * per_page

    count_result = execute_query(
        f"SELECT COUNT(*) AS total FROM assets a WHERE {where}",
        params[:],
        instance_id=ctx.instance_id,
    )
    total = count_result["rows"][0]["total"] if count_result.get("rows") else 0

    params.extend([per_page, offset])
    result = execute_query(
        f"SELECT a.*, "
        f"p.first_name || ' ' || COALESCE(p.last_name, '') AS assigned_to_name, "
        f"s.name AS site_name, "
        f"c.name AS vendor_name "
        f"FROM assets a "
        f"LEFT JOIN people p ON a.assigned_to_person_id = p.id AND p.instance_id = a.instance_id "
        f"LEFT JOIN sites s ON a.site_id = s.id AND s.instance_id = a.instance_id "
        f"LEFT JOIN companies c ON a.vendor_id = c.id AND c.instance_id = a.instance_id "
        f"WHERE {where} "
        f"ORDER BY a.updated_at DESC "
        f"LIMIT ? OFFSET ?",
        params,
        instance_id=ctx.instance_id,
    )
    return {"rows": result.get("rows", []), "total": total, "page": page, "per_page": per_page}


@router.get("/stats")
async def asset_stats(ctx: InstanceContext = Depends(get_current_instance)):
    status_result = execute_query(
        "SELECT lifecycle_status, COUNT(*) AS count FROM assets "
        "WHERE instance_id = ? GROUP BY lifecycle_status",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    by_status = {r["lifecycle_status"]: r["count"] for r in status_result.get("rows", [])}

    criticality_result = execute_query(
        "SELECT criticality, COUNT(*) AS count FROM assets "
        "WHERE instance_id = ? AND lifecycle_status NOT IN ('disposed', 'decommissioned') "
        "GROUP BY criticality",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    by_criticality = {r["criticality"]: r["count"] for r in criticality_result.get("rows", [])}

    warranty_result = execute_query(
        "SELECT COUNT(*) AS count FROM assets "
        "WHERE instance_id = ? AND warranty_expiry IS NOT NULL "
        "AND warranty_expiry <= CURRENT_DATE + INTERVAL '30 days' "
        "AND lifecycle_status NOT IN ('disposed', 'decommissioned')",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    warranty_expiring = warranty_result["rows"][0]["count"] if warranty_result.get("rows") else 0

    license_result = execute_query(
        "SELECT COUNT(*) AS count FROM licenses "
        "WHERE instance_id = ? AND status = 'active' "
        "AND expiry_date IS NOT NULL AND expiry_date <= CURRENT_DATE + INTERVAL '30 days'",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    licenses_expiring = license_result["rows"][0]["count"] if license_result.get("rows") else 0

    return {
        "by_status": by_status,
        "by_criticality": by_criticality,
        "warranty_expiring_30d": warranty_expiring,
        "licenses_expiring_30d": licenses_expiring,
    }


@router.get("/{asset_id}")
async def get_asset(asset_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    result = execute_query(
        "SELECT a.*, "
        "p.first_name || ' ' || COALESCE(p.last_name, '') AS assigned_to_name, "
        "s.name AS site_name, "
        "c.name AS vendor_name "
        "FROM assets a "
        "LEFT JOIN people p ON a.assigned_to_person_id = p.id AND p.instance_id = a.instance_id "
        "LEFT JOIN sites s ON a.site_id = s.id AND s.instance_id = a.instance_id "
        "LEFT JOIN companies c ON a.vendor_id = c.id AND c.instance_id = a.instance_id "
        "WHERE a.id = ? AND a.instance_id = ?",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if not result.get("rows"):
        raise HTTPException(status_code=404, detail=f"Asset #{asset_id} not found")
    return result["rows"][0]


@router.get("/{asset_id}/full")
async def get_asset_full(asset_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    asset = _get_asset_or_404(asset_id, ctx.instance_id)

    history = execute_query(
        "SELECT ash.*, p.first_name || ' ' || COALESCE(p.last_name, '') AS changed_by_name "
        "FROM asset_status_history ash "
        "LEFT JOIN people p ON ash.changed_by_person_id = p.id AND p.instance_id = ash.instance_id "
        "WHERE ash.asset_id = ? AND ash.instance_id = ? ORDER BY ash.created_at DESC LIMIT 50",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    assignments = execute_query(
        "SELECT aa.*, "
        "p1.first_name || ' ' || COALESCE(p1.last_name, '') AS assigned_to_name, "
        "p2.first_name || ' ' || COALESCE(p2.last_name, '') AS assigned_by_name "
        "FROM asset_assignments aa "
        "LEFT JOIN people p1 ON aa.assigned_to_person_id = p1.id AND p1.instance_id = aa.instance_id "
        "LEFT JOIN people p2 ON aa.assigned_by_person_id = p2.id AND p2.instance_id = aa.instance_id "
        "WHERE aa.asset_id = ? AND aa.instance_id = ? ORDER BY aa.start_date DESC LIMIT 50",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    software = execute_query(
        "SELECT si.*, l.name AS license_name "
        "FROM software_installations si "
        "LEFT JOIN licenses l ON si.license_id = l.id AND l.instance_id = si.instance_id "
        "WHERE si.asset_id = ? AND si.instance_id = ? ORDER BY si.installed_date DESC",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    documents = execute_query(
        "SELECT id, document_name, document_type, content_type, file_size_bytes, notes, created_at "
        "FROM asset_documents WHERE asset_id = ? AND instance_id = ? ORDER BY created_at DESC",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    tickets = execute_query(
        "SELECT id, ticket_number, title, status, priority, opened_at "
        "FROM tickets WHERE asset_id = ? AND instance_id = ? ORDER BY opened_at DESC LIMIT 20",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    work_orders = execute_query(
        "SELECT id, wo_number, title, status, priority, due_date "
        "FROM work_orders WHERE asset_id = ? AND instance_id = ? ORDER BY created_at DESC LIMIT 20",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    disposal = execute_query(
        "SELECT * FROM disposal_records WHERE asset_id = ? AND instance_id = ?",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    return {
        "asset": asset,
        "status_history": history.get("rows", []),
        "assignments": assignments.get("rows", []),
        "software": software.get("rows", []),
        "documents": documents.get("rows", []),
        "tickets": tickets.get("rows", []),
        "work_orders": work_orders.get("rows", []),
        "disposal": disposal["rows"][0] if disposal.get("rows") else None,
    }


@router.post("/")
async def create_asset(body: CreateAssetBody, ctx: InstanceContext = Depends(get_current_instance)):
    if body.lifecycle_status not in ALL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid lifecycle_status: {body.lifecycle_status}")

    fields = [
        "instance_id", "asset_type", "lifecycle_status", "criticality", "important",
    ]
    values = [ctx.instance_id, body.asset_type, body.lifecycle_status, body.criticality, body.important]

    optional = {
        "asset_tag": body.asset_tag, "serial_number": body.serial_number,
        "hostname": body.hostname, "brand": body.brand, "model": body.model,
        "category": body.category, "operating_system": body.operating_system,
        "purchase_date": body.purchase_date, "purchase_cost": body.purchase_cost,
        "warranty_expiry": body.warranty_expiry, "warranty_type": body.warranty_type,
        "ownership_type": body.ownership_type, "vendor_id": body.vendor_id,
        "site_id": body.site_id, "room_id": body.room_id,
        "assigned_to_person_id": body.assigned_to_person_id,
        "ip_address": body.ip_address, "mac_address": body.mac_address,
        "replacement_due_date": body.replacement_due_date, "notes": body.notes,
    }
    for col, val in optional.items():
        if val is not None:
            fields.append(col)
            values.append(val)

    placeholders = ", ".join(["?"] * len(fields))
    col_list = ", ".join(fields)

    result = execute_query(
        f"INSERT INTO assets ({col_list}) VALUES ({placeholders}) RETURNING id",
        values,
        instance_id=ctx.instance_id,
    )
    asset_id = result["rows"][0]["id"]

    # If assigned, create initial assignment record
    if body.assigned_to_person_id is not None:
        execute_query(
            "INSERT INTO asset_assignments (instance_id, asset_id, assigned_to_person_id, assigned_by_person_id) "
            "VALUES (?, ?, ?, ?)",
            [ctx.instance_id, asset_id, body.assigned_to_person_id, ctx.person_id],
            instance_id=ctx.instance_id,
        )

    return {"id": asset_id}


@router.patch("/{asset_id}")
async def update_asset(asset_id: int, body: UpdateAssetBody, ctx: InstanceContext = Depends(get_current_instance)):
    _get_asset_or_404(asset_id, ctx.instance_id)

    updates = []
    params = []
    data = body.model_dump(exclude_none=True)
    if not data:
        return {"message": "No changes"}

    for col, val in data.items():
        updates.append(f"{col} = ?")
        params.append(val)

    params.extend([asset_id, ctx.instance_id])
    execute_query(
        f"UPDATE assets SET {', '.join(updates)} WHERE id = ? AND instance_id = ?",
        params,
        instance_id=ctx.instance_id,
    )
    return {"success": True, "changes": len(updates)}


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------

@router.post("/{asset_id}/transition")
async def transition_asset(asset_id: int, body: TransitionBody, ctx: InstanceContext = Depends(get_current_instance)):
    asset = _get_asset_or_404(asset_id, ctx.instance_id)
    current = asset.get("lifecycle_status", "active")

    if body.new_status not in ALL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.new_status}")

    allowed = VALID_TRANSITIONS.get(current, set())
    if body.new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{current}' to '{body.new_status}'. "
                   f"Allowed: {sorted(allowed) if allowed else 'none (terminal state)'}",
        )

    # Update asset status (trigger auto-inserts into asset_status_history)
    execute_query(
        "UPDATE assets SET lifecycle_status = ? WHERE id = ? AND instance_id = ?",
        [body.new_status, asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    # Enrich the trigger-created history row with person and reason
    execute_query(
        "UPDATE asset_status_history SET changed_by_person_id = ?, reason = ? "
        "WHERE id = (SELECT id FROM asset_status_history "
        "WHERE asset_id = ? AND instance_id = ? ORDER BY created_at DESC LIMIT 1)",
        [ctx.person_id, body.reason, asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    return {"success": True, "old_status": current, "new_status": body.new_status}


@router.get("/{asset_id}/status-history")
async def get_status_history(asset_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    _get_asset_or_404(asset_id, ctx.instance_id)
    result = execute_query(
        "SELECT ash.*, p.first_name || ' ' || COALESCE(p.last_name, '') AS changed_by_name "
        "FROM asset_status_history ash "
        "LEFT JOIN people p ON ash.changed_by_person_id = p.id AND p.instance_id = ash.instance_id "
        "WHERE ash.asset_id = ? AND ash.instance_id = ? ORDER BY ash.created_at DESC",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------

@router.post("/{asset_id}/assign")
async def assign_asset(asset_id: int, body: AssignBody, ctx: InstanceContext = Depends(get_current_instance)):
    _get_asset_or_404(asset_id, ctx.instance_id)

    # Verify target person exists
    person = execute_query(
        "SELECT id FROM people WHERE id = ? AND instance_id = ?",
        [body.person_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if not person.get("rows"):
        raise HTTPException(status_code=404, detail="Person not found")

    # Close any current open assignment
    execute_query(
        "UPDATE asset_assignments SET end_date = CURRENT_DATE "
        "WHERE asset_id = ? AND instance_id = ? AND end_date IS NULL",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    # Create new assignment
    execute_query(
        "INSERT INTO asset_assignments (instance_id, asset_id, assigned_to_person_id, assigned_by_person_id, notes) "
        "VALUES (?, ?, ?, ?, ?)",
        [ctx.instance_id, asset_id, body.person_id, ctx.person_id, body.notes],
        instance_id=ctx.instance_id,
    )

    # Update asset's current assignment
    execute_query(
        "UPDATE assets SET assigned_to_person_id = ? WHERE id = ? AND instance_id = ?",
        [body.person_id, asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    return {"success": True}


@router.post("/{asset_id}/unassign")
async def unassign_asset(asset_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    _get_asset_or_404(asset_id, ctx.instance_id)

    execute_query(
        "UPDATE asset_assignments SET end_date = CURRENT_DATE "
        "WHERE asset_id = ? AND instance_id = ? AND end_date IS NULL",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    execute_query(
        "UPDATE assets SET assigned_to_person_id = NULL WHERE id = ? AND instance_id = ?",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    return {"success": True}


@router.get("/{asset_id}/assignments")
async def get_assignments(asset_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    _get_asset_or_404(asset_id, ctx.instance_id)
    result = execute_query(
        "SELECT aa.*, "
        "p1.first_name || ' ' || COALESCE(p1.last_name, '') AS assigned_to_name, "
        "p2.first_name || ' ' || COALESCE(p2.last_name, '') AS assigned_by_name "
        "FROM asset_assignments aa "
        "LEFT JOIN people p1 ON aa.assigned_to_person_id = p1.id AND p1.instance_id = aa.instance_id "
        "LEFT JOIN people p2 ON aa.assigned_by_person_id = p2.id AND p2.instance_id = aa.instance_id "
        "WHERE aa.asset_id = ? AND aa.instance_id = ? ORDER BY aa.start_date DESC",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


# ---------------------------------------------------------------------------
# Software installations
# ---------------------------------------------------------------------------

@router.get("/{asset_id}/software")
async def list_software(asset_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    _get_asset_or_404(asset_id, ctx.instance_id)
    result = execute_query(
        "SELECT si.*, l.name AS license_name, l.license_type "
        "FROM software_installations si "
        "LEFT JOIN licenses l ON si.license_id = l.id AND l.instance_id = si.instance_id "
        "WHERE si.asset_id = ? AND si.instance_id = ? ORDER BY si.installed_date DESC",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


@router.post("/{asset_id}/software")
async def install_software(asset_id: int, body: InstallSoftwareBody, ctx: InstanceContext = Depends(get_current_instance)):
    _get_asset_or_404(asset_id, ctx.instance_id)

    # If linked to a license, increment seats_used
    if body.license_id is not None:
        lic = execute_query(
            "SELECT id, seat_count, seats_used FROM licenses WHERE id = ? AND instance_id = ?",
            [body.license_id, ctx.instance_id],
            instance_id=ctx.instance_id,
        )
        if not lic.get("rows"):
            raise HTTPException(status_code=404, detail="License not found")
        license_row = lic["rows"][0]
        if license_row.get("seat_count") is not None:
            if (license_row.get("seats_used") or 0) >= license_row["seat_count"]:
                raise HTTPException(status_code=400, detail="No available license seats")

        execute_query(
            "UPDATE licenses SET seats_used = COALESCE(seats_used, 0) + 1 WHERE id = ? AND instance_id = ?",
            [body.license_id, ctx.instance_id],
            instance_id=ctx.instance_id,
        )

    result = execute_query(
        "INSERT INTO software_installations "
        "(instance_id, asset_id, software_name, version, license_id, installed_by_person_id, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id",
        [ctx.instance_id, asset_id, body.software_name, body.version,
         body.license_id, body.installed_by_person_id or ctx.person_id, body.notes],
        instance_id=ctx.instance_id,
    )
    return {"id": result["rows"][0]["id"]}


@router.delete("/{asset_id}/software/{installation_id}")
async def remove_software(asset_id: int, installation_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    result = execute_query(
        "SELECT id, license_id FROM software_installations "
        "WHERE id = ? AND asset_id = ? AND instance_id = ?",
        [installation_id, asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if not result.get("rows"):
        raise HTTPException(status_code=404, detail="Software installation not found")

    license_id = result["rows"][0].get("license_id")

    execute_query(
        "DELETE FROM software_installations WHERE id = ? AND instance_id = ?",
        [installation_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    # Decrement seats_used if linked to a license
    if license_id is not None:
        execute_query(
            "UPDATE licenses SET seats_used = GREATEST(COALESCE(seats_used, 0) - 1, 0) "
            "WHERE id = ? AND instance_id = ?",
            [license_id, ctx.instance_id],
            instance_id=ctx.instance_id,
        )

    return {"success": True}


# ---------------------------------------------------------------------------
# Licenses
# ---------------------------------------------------------------------------

@router.get("/licenses/expiring")
async def licenses_expiring(
    ctx: InstanceContext = Depends(get_current_instance),
    days: int = Query(30, ge=1, le=365),
):
    result = execute_query(
        "SELECT l.*, c.name AS vendor_name FROM licenses l "
        "LEFT JOIN companies c ON l.vendor_id = c.id AND c.instance_id = l.instance_id "
        "WHERE l.instance_id = ? AND l.status = 'active' "
        "AND l.expiry_date IS NOT NULL AND l.expiry_date <= CURRENT_DATE + ? * INTERVAL '1 day' "
        "ORDER BY l.expiry_date ASC",
        [ctx.instance_id, days],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


@router.get("/licenses/list")
async def list_licenses(
    ctx: InstanceContext = Depends(get_current_instance),
    status: str | None = None,
):
    conditions = ["l.instance_id = ?"]
    params: list = [ctx.instance_id]
    if status:
        conditions.append("l.status = ?")
        params.append(status)

    where = " AND ".join(conditions)
    result = execute_query(
        f"SELECT l.*, c.name AS vendor_name FROM licenses l "
        f"LEFT JOIN companies c ON l.vendor_id = c.id AND c.instance_id = l.instance_id "
        f"WHERE {where} ORDER BY l.name ASC",
        params,
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


@router.post("/licenses")
async def create_license(body: CreateLicenseBody, ctx: InstanceContext = Depends(get_current_instance)):
    result = execute_query(
        "INSERT INTO licenses "
        "(instance_id, name, vendor_id, license_key, license_type, seat_count, "
        "cost, cost_currency, purchase_date, expiry_date, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
        [ctx.instance_id, body.name, body.vendor_id, body.license_key,
         body.license_type, body.seat_count, body.cost, body.cost_currency,
         body.purchase_date, body.expiry_date, body.notes],
        instance_id=ctx.instance_id,
    )
    return {"id": result["rows"][0]["id"]}


@router.patch("/licenses/{license_id}")
async def update_license(license_id: int, body: UpdateLicenseBody, ctx: InstanceContext = Depends(get_current_instance)):
    existing = execute_query(
        "SELECT id FROM licenses WHERE id = ? AND instance_id = ?",
        [license_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if not existing.get("rows"):
        raise HTTPException(status_code=404, detail="License not found")

    data = body.model_dump(exclude_none=True)
    if not data:
        return {"message": "No changes"}

    updates = []
    params = []
    for col, val in data.items():
        updates.append(f"{col} = ?")
        params.append(val)

    params.extend([license_id, ctx.instance_id])
    execute_query(
        f"UPDATE licenses SET {', '.join(updates)} WHERE id = ? AND instance_id = ?",
        params,
        instance_id=ctx.instance_id,
    )
    return {"success": True}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@router.post("/{asset_id}/documents")
async def upload_document(
    asset_id: int,
    file: UploadFile = File(...),
    ctx: InstanceContext = Depends(get_current_instance),
    document_type: str = "general",
    notes: str | None = None,
):
    _get_asset_or_404(asset_id, ctx.instance_id)

    content = await file.read()
    max_bytes = TICKET_ATTACHMENT_MAX_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File too large. Max {TICKET_ATTACHMENT_MAX_SIZE_MB} MB")

    file_id = str(uuid.uuid4())
    content_type = file.content_type or "application/octet-stream"
    s3_key = _upload_document_to_s3(ctx.instance_id, asset_id, file_id, content, content_type)

    execute_query(
        "INSERT INTO asset_documents "
        "(instance_id, asset_id, document_name, document_type, s3_key, content_type, "
        "file_size_bytes, uploaded_by_person_id, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [ctx.instance_id, asset_id, file.filename or "document", document_type,
         s3_key, content_type, len(content), ctx.person_id, notes],
        instance_id=ctx.instance_id,
    )

    return {"document_name": file.filename, "file_size_bytes": len(content)}


@router.get("/{asset_id}/documents")
async def list_documents(asset_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    _get_asset_or_404(asset_id, ctx.instance_id)
    result = execute_query(
        "SELECT id, document_name, document_type, content_type, file_size_bytes, notes, created_at "
        "FROM asset_documents WHERE asset_id = ? AND instance_id = ? ORDER BY created_at DESC",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])


@router.get("/{asset_id}/documents/{doc_id}")
async def download_document(asset_id: int, doc_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    result = execute_query(
        "SELECT s3_key, document_name, content_type FROM asset_documents "
        "WHERE id = ? AND asset_id = ? AND instance_id = ?",
        [doc_id, asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if not result.get("rows"):
        raise HTTPException(status_code=404, detail="Document not found")
    row = result["rows"][0]
    data, ct = download_image(row["s3_key"])
    return Response(
        content=data,
        media_type=row.get("content_type") or ct,
        headers={"Content-Disposition": f'inline; filename="{row["document_name"]}"'},
    )


@router.delete("/{asset_id}/documents/{doc_id}")
async def delete_document(asset_id: int, doc_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    result = execute_query(
        "SELECT s3_key FROM asset_documents WHERE id = ? AND asset_id = ? AND instance_id = ?",
        [doc_id, asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if not result.get("rows"):
        raise HTTPException(status_code=404, detail="Document not found")

    delete_image(result["rows"][0]["s3_key"])

    execute_query(
        "DELETE FROM asset_documents WHERE id = ? AND instance_id = ?",
        [doc_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return {"success": True}


# ---------------------------------------------------------------------------
# Disposal
# ---------------------------------------------------------------------------

@router.post("/{asset_id}/dispose")
async def dispose_asset(asset_id: int, body: DisposeBody, ctx: InstanceContext = Depends(get_current_instance)):
    asset = _get_asset_or_404(asset_id, ctx.instance_id)
    current = asset.get("lifecycle_status", "active")

    if current not in ("pending_disposal", "decommissioned"):
        raise HTTPException(
            status_code=400,
            detail=f"Asset must be in 'pending_disposal' or 'decommissioned' status to dispose. "
                   f"Current status: '{current}'",
        )

    # Check no existing disposal record
    existing = execute_query(
        "SELECT id FROM disposal_records WHERE asset_id = ? AND instance_id = ?",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    if existing.get("rows"):
        raise HTTPException(status_code=400, detail="Disposal record already exists for this asset")

    execute_query(
        "INSERT INTO disposal_records "
        "(instance_id, asset_id, disposal_method, authorized_by_person_id, performed_by_person_id, "
        "certificate_reference, proceeds, proceeds_currency, data_wiped, data_wipe_method, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [ctx.instance_id, asset_id, body.disposal_method,
         body.authorized_by_person_id or ctx.person_id,
         body.performed_by_person_id, body.certificate_reference,
         body.proceeds, body.proceeds_currency,
         body.data_wiped, body.data_wipe_method, body.notes],
        instance_id=ctx.instance_id,
    )

    # Transition to disposed (trigger records history)
    execute_query(
        "UPDATE assets SET lifecycle_status = 'disposed' WHERE id = ? AND instance_id = ?",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    # Enrich the history row
    execute_query(
        "UPDATE asset_status_history SET changed_by_person_id = ?, reason = ? "
        "WHERE id = (SELECT id FROM asset_status_history "
        "WHERE asset_id = ? AND instance_id = ? ORDER BY created_at DESC LIMIT 1)",
        [ctx.person_id, f"Disposed: {body.disposal_method}", asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    # Close any open assignment
    execute_query(
        "UPDATE asset_assignments SET end_date = CURRENT_DATE "
        "WHERE asset_id = ? AND instance_id = ? AND end_date IS NULL",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    execute_query(
        "UPDATE assets SET assigned_to_person_id = NULL WHERE id = ? AND instance_id = ?",
        [asset_id, ctx.instance_id],
        instance_id=ctx.instance_id,
    )

    return {"success": True}


@router.get("/disposals/list")
async def list_disposals(ctx: InstanceContext = Depends(get_current_instance)):
    result = execute_query(
        "SELECT dr.*, a.asset_tag, a.serial_number, a.hostname, a.asset_type, a.brand, a.model, "
        "p1.first_name || ' ' || COALESCE(p1.last_name, '') AS authorized_by_name, "
        "p2.first_name || ' ' || COALESCE(p2.last_name, '') AS performed_by_name "
        "FROM disposal_records dr "
        "JOIN assets a ON dr.asset_id = a.id AND a.instance_id = dr.instance_id "
        "LEFT JOIN people p1 ON dr.authorized_by_person_id = p1.id AND p1.instance_id = dr.instance_id "
        "LEFT JOIN people p2 ON dr.performed_by_person_id = p2.id AND p2.instance_id = dr.instance_id "
        "WHERE dr.instance_id = ? ORDER BY dr.disposal_date DESC",
        [ctx.instance_id],
        instance_id=ctx.instance_id,
    )
    return result.get("rows", [])
