"""Billing API endpoints: subscription management, addons, query packs, Stripe webhook."""

from __future__ import annotations

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.auth import AuthUser, InstanceContext, get_current_instance, get_current_user
from backend.config import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
from backend.stripe_billing import (
    create_customer_portal_session,
    create_query_pack_checkout,
    create_stripe_customer,
    get_billing_status,
    handle_payment_failed,
    handle_query_pack_paid,
    handle_subscription_cancelled,
    handle_subscription_renewed,
    toggle_daily_reports_addon,
    toggle_email_addon,
    toggle_inbound_email_addon,
    toggle_bookings_addon,
)
from backend.database import execute_query

router = APIRouter(prefix="/billing")

stripe.api_key = STRIPE_SECRET_KEY


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class ToggleAddonBody(BaseModel):
    addon: str  # 'email' or 'daily_reports'
    enable: bool


class EmailSignatureBody(BaseModel):
    signature: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status")
async def billing_status(ctx: InstanceContext = Depends(get_current_instance)):
    """Return subscription status, seat count, addons, query pool info."""
    status = get_billing_status(ctx.instance_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status


@router.post("/setup")
async def billing_setup(ctx: InstanceContext = Depends(get_current_instance)):
    """Create Stripe customer + subscription for the instance owner."""
    if ctx.role != "owner":
        raise HTTPException(status_code=403, detail="Only the instance owner can set up billing")

    from backend.stripe_billing import create_instance_subscription, _get_stripe_customer_id

    # Ensure customer exists
    customer_id = _get_stripe_customer_id(ctx.auth_user_id)
    if not customer_id:
        customer_id = create_stripe_customer(ctx.auth_user_id, ctx.email, ctx.display_name)

    if not customer_id:
        raise HTTPException(status_code=400, detail="Could not create Stripe customer. Is Stripe configured?")

    # Check if subscription already exists
    inst = execute_query(
        "SELECT stripe_subscription_id FROM instances WHERE id = ?",
        [ctx.instance_id],
        instance_id=None,
    )
    if inst.get("rows") and inst["rows"][0].get("stripe_subscription_id"):
        return {"message": "Subscription already exists", "subscription_id": inst["rows"][0]["stripe_subscription_id"]}

    result = create_instance_subscription(ctx.instance_id, ctx.auth_user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/portal")
async def billing_portal(ctx: InstanceContext = Depends(get_current_instance)):
    """Generate a Stripe Customer Portal URL for managing payment methods."""
    if ctx.role != "owner":
        raise HTTPException(status_code=403, detail="Only the instance owner can access the billing portal")

    result = create_customer_portal_session(ctx.auth_user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/buy-queries")
async def buy_queries(ctx: InstanceContext = Depends(get_current_instance)):
    """Create a Stripe Checkout session for a 250-query pack."""
    if ctx.role != "owner":
        raise HTTPException(status_code=403, detail="Only the instance owner can purchase query packs")

    result = create_query_pack_checkout(ctx.instance_id, ctx.auth_user_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/toggle-addon")
async def toggle_addon(body: ToggleAddonBody, ctx: InstanceContext = Depends(get_current_instance)):
    """Enable or disable an addon (email or daily_reports)."""
    if ctx.role != "owner":
        raise HTTPException(status_code=403, detail="Only the instance owner can manage addons")

    if body.addon == "email":
        result = toggle_email_addon(ctx.instance_id, body.enable)
    elif body.addon == "daily_reports":
        result = toggle_daily_reports_addon(ctx.instance_id, body.enable)
    elif body.addon == "inbound_email":
        result = toggle_inbound_email_addon(ctx.instance_id, body.enable)
    elif body.addon == "bookings":
        result = toggle_bookings_addon(ctx.instance_id, body.enable)
    else:
        raise HTTPException(status_code=400, detail="Unknown addon. Use 'email', 'daily_reports', 'inbound_email', or 'bookings'.")

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/email-signature")
async def update_email_signature(body: EmailSignatureBody, ctx: InstanceContext = Depends(get_current_instance)):
    """Update the email signature for the instance."""
    if ctx.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owner or admin can update email signature")

    execute_query(
        "UPDATE instances SET email_signature = ? WHERE id = ?",
        [body.signature.strip(), ctx.instance_id],
        instance_id=None,
    )
    return {"message": "Email signature updated"}


# ---------------------------------------------------------------------------
# Stripe Webhook (no auth — verified by Stripe signature)
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=400, detail="Webhook secret not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "invoice.paid":
        subscription_id = data.get("subscription")
        if subscription_id:
            handle_subscription_renewed(subscription_id)

    elif event_type == "invoice.payment_failed":
        subscription_id = data.get("subscription")
        if subscription_id:
            handle_payment_failed(subscription_id)

    elif event_type == "checkout.session.completed":
        metadata = data.get("metadata", {})
        if metadata.get("type") == "query_pack":
            instance_id = int(metadata["instance_id"])
            auth_user_id = int(metadata["auth_user_id"])
            payment_intent_id = data.get("payment_intent", "")
            handle_query_pack_paid(instance_id, auth_user_id, payment_intent_id)

    elif event_type == "customer.subscription.deleted":
        subscription_id = data.get("id")
        if subscription_id:
            handle_subscription_cancelled(subscription_id)

    return JSONResponse(content={"received": True})
