"""Instance management endpoints: create, list, join, select, members."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.auth import (
    AuthUser,
    InstanceContext,
    get_current_instance,
    get_current_user,
)
from backend.database import execute_query
from backend.stripe_billing import add_user_seat, create_instance_subscription, create_stripe_customer

router = APIRouter(prefix="/instances")

# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class CreateInstanceBody(BaseModel):
    name: str
    slug: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("")
async def create_instance(body: CreateInstanceBody, user: AuthUser = Depends(get_current_user)):
    """Create a new instance. The caller becomes the owner."""
    slug = body.slug.lower().strip()

    # Validate slug: alphanumeric + hyphens, 3-50 chars
    if not re.match(r"^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$", slug):
        raise HTTPException(
            status_code=400,
            detail="Slug must be 3-50 characters, lowercase alphanumeric and hyphens only, "
                   "and must start and end with a letter or digit",
        )

    # Check slug uniqueness
    existing = execute_query(
        "SELECT id FROM instances WHERE slug = ?",
        [slug],
        instance_id=None,
    )
    if existing.get("rows"):
        raise HTTPException(status_code=409, detail="Slug already taken")

    # Create instance
    result = execute_query(
        "INSERT INTO instances (name, slug, tier, query_limit, billing_owner_id) VALUES (?, ?, 'free', 60, ?)",
        [body.name.strip(), slug, user.id],
        instance_id=None,
    )
    if "error" in result:
        raise HTTPException(status_code=500, detail=f"Failed to create instance: {result['error']}")

    instance_id = result["lastrowid"]

    # Create a person record for the owner in the people table
    display = user.display_name or user.email.split("@")[0]
    parts = display.split(" ", 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""
    person_result = execute_query(
        "INSERT INTO people (first_name, last_name, email, role_title, is_user, user_role, status, instance_id) "
        "VALUES (?, ?, ?, 'Owner', TRUE, 'owner', 'active', ?) RETURNING id",
        [first_name, last_name, user.email, instance_id],
        instance_id=instance_id,
    )
    person_id = person_result["rows"][0]["id"] if person_result.get("rows") else person_result.get("lastrowid")

    # Create owner membership
    membership_result = execute_query(
        "INSERT INTO instance_memberships (auth_user_id, instance_id, role, person_id) VALUES (?, ?, 'owner', ?)",
        [user.id, instance_id, person_id],
        instance_id=None,
    )
    if "error" in membership_result:
        raise HTTPException(status_code=500, detail=f"Failed to create membership: {membership_result['error']}")

    # Seed initial data for the new instance
    try:
        from initial_seed import seed_initial_data
        seed_initial_data(instance_id=instance_id)
    except Exception as e:
        # Non-fatal: instance is usable without seed data
        print(f"Warning: seed_initial_data failed for instance {instance_id}: {e}")

    # Set up Stripe billing: create customer (if needed) + subscription
    tier = "free"
    query_limit = 60
    client_secret = None
    try:
        from backend.stripe_billing import _get_stripe_customer_id
        if not _get_stripe_customer_id(user.id):
            create_stripe_customer(user.id, user.email, user.display_name or user.email)
        sub_result = create_instance_subscription(instance_id, user.id)
        if sub_result.get("subscription_id"):
            tier = "paid"
            query_limit = 250
            client_secret = sub_result.get("client_secret")
    except Exception as e:
        print(f"Warning: Stripe setup failed for instance {instance_id}: {e}")

    return JSONResponse(
        content={
            "id": instance_id,
            "name": body.name.strip(),
            "slug": slug,
            "tier": tier,
            "query_limit": query_limit,
            "client_secret": client_secret,
        },
        status_code=201,
    )


@router.get("")
async def list_instances(user: AuthUser = Depends(get_current_user)):
    """Return all instances the current user belongs to."""
    result = execute_query(
        "SELECT i.id, i.name, i.slug, i.tier, i.status, m.role "
        "FROM instance_memberships m "
        "JOIN instances i ON i.id = m.instance_id "
        "WHERE m.auth_user_id = ?",
        [user.id],
        instance_id=None,
    )
    return {"instances": result.get("rows", [])}


@router.post("/join")
async def join_instance(user: AuthUser = Depends(get_current_user)):
    """Join an instance via a pending invitation matching the user's email."""
    # Look up pending invitation
    inv_result = execute_query(
        "SELECT id, instance_id, role FROM instance_invitations "
        "WHERE email = ? AND status = 'pending'",
        [user.email],
        instance_id=None,
    )
    if not inv_result.get("rows"):
        raise HTTPException(status_code=404, detail="No pending invitation found")

    invitation = inv_result["rows"][0]
    inv_instance_id = invitation["instance_id"]
    inv_role = invitation["role"]

    # Check not already a member
    existing_membership = execute_query(
        "SELECT id FROM instance_memberships WHERE auth_user_id = ? AND instance_id = ?",
        [user.id, inv_instance_id],
        instance_id=None,
    )
    if existing_membership.get("rows"):
        # Already a member -- just mark the invitation as accepted
        execute_query(
            "UPDATE instance_invitations SET status = 'accepted' WHERE id = ?",
            [invitation["id"]],
            instance_id=None,
        )
        return {"message": "Already a member of this instance"}

    # Create a person record for the new member
    display = user.display_name or user.email.split("@")[0]
    parts = display.split(" ", 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""
    person_result = execute_query(
        "INSERT INTO people (first_name, last_name, email, role_title, is_user, user_role, status, instance_id) "
        "VALUES (?, ?, ?, ?, TRUE, ?, 'active', ?) RETURNING id",
        [first_name, last_name, user.email, inv_role.title(), inv_role, inv_instance_id],
        instance_id=inv_instance_id,
    )
    person_id = person_result["rows"][0]["id"] if person_result.get("rows") else person_result.get("lastrowid")

    # Create membership
    mem_result = execute_query(
        "INSERT INTO instance_memberships (auth_user_id, instance_id, role, person_id) VALUES (?, ?, ?, ?)",
        [user.id, inv_instance_id, inv_role, person_id],
        instance_id=None,
    )
    if "error" in mem_result:
        raise HTTPException(status_code=500, detail=f"Failed to join instance: {mem_result['error']}")

    # Mark invitation as accepted
    execute_query(
        "UPDATE instance_invitations SET status = 'accepted' WHERE id = ?",
        [invitation["id"]],
        instance_id=None,
    )

    # Add a user seat to the Stripe subscription (increments billing)
    try:
        seat_result = add_user_seat(inv_instance_id)
    except Exception as e:
        print(f"Warning: add_user_seat failed for instance {inv_instance_id}: {e}")
        seat_result = {}

    return {
        "message": "Joined instance successfully",
        "instance_id": inv_instance_id,
        "role": inv_role,
        "billing_note": "A €19.99/month seat has been added to the instance subscription." if seat_result.get("seats") else None,
    }


@router.post("/{instance_id}/select")
async def select_instance(instance_id: int, user: AuthUser = Depends(get_current_user)):
    """Set the active instance cookie for the current user."""
    # Verify membership
    result = execute_query(
        "SELECT role FROM instance_memberships WHERE auth_user_id = ? AND instance_id = ?",
        [user.id, instance_id],
        instance_id=None,
    )
    if not result.get("rows"):
        raise HTTPException(status_code=403, detail="Not a member of this instance")

    response = JSONResponse(content={"message": "Instance selected", "instance_id": instance_id})
    response.set_cookie(
        "instance_id",
        str(instance_id),
        httponly=False,  # frontend JS needs to read this
        samesite="lax",
        secure=False,
        path="/",
    )
    return response


@router.get("/{instance_id}/members")
async def list_members(instance_id: int, ctx: InstanceContext = Depends(get_current_instance)):
    """List all members of the instance. Only owner/admin can access."""
    if ctx.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owner or admin can view members")

    if ctx.instance_id != instance_id:
        raise HTTPException(status_code=403, detail="Instance mismatch")

    result = execute_query(
        "SELECT m.id, m.auth_user_id, m.role, m.person_id, m.created_at, "
        "u.email, u.display_name "
        "FROM instance_memberships m "
        "JOIN auth_users u ON u.id = m.auth_user_id "
        "WHERE m.instance_id = ?",
        [instance_id],
        instance_id=None,
    )

    members = []
    for row in result.get("rows", []):
        members.append({
            "id": row["id"],
            "auth_user_id": row["auth_user_id"],
            "email": row["email"],
            "display_name": row["display_name"],
            "role": row["role"],
            "person_id": row["person_id"],
            "created_at": str(row["created_at"]) if row.get("created_at") else None,
        })

    return {"members": members}
