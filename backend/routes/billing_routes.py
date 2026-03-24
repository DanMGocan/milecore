"""Billing API endpoints: subscription management, addons, query packs, BYOK key management, Stripe webhook."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.auth import AuthUser, InstanceContext, get_current_instance, get_current_user
from backend.config import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
from backend.database import execute_query
from backend.key_vault import decrypt_api_key, encrypt_api_key, mask_api_key
from backend.llm_client import SUPPORTED_MODELS, clear_config_cache, validate_key
from backend.stripe_billing import (
    cancel_instance_subscription,
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
    update_query_tier,
)

router = APIRouter(prefix="/billing")

stripe.api_key = STRIPE_SECRET_KEY


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class ToggleAddonBody(BaseModel):
    addon: str
    enable: bool


class EmailSignatureBody(BaseModel):
    signature: str


class SetApiKeyBody(BaseModel):
    api_key: str


class LLMConfigBody(BaseModel):
    provider: str
    model: Optional[str] = None


class QueryTierBody(BaseModel):
    tier: int


class DeploymentModeBody(BaseModel):
    mode: str  # 'saas' or 'byok'


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
# Deployment mode
# ---------------------------------------------------------------------------

@router.post("/deployment-mode")
async def set_deployment_mode(body: DeploymentModeBody, ctx: InstanceContext = Depends(get_current_instance)):
    """Switch the instance between SaaS and BYOK mode (owner only).

    Cancels the existing Stripe subscription, resets counters, and cleans up
    credentials when leaving BYOK mode.  The user sets up new billing
    separately via /api/billing/setup after switching.
    """
    if ctx.role != "owner":
        raise HTTPException(status_code=403, detail="Only the instance owner can change the deployment mode")
    if body.mode not in ("saas", "byok"):
        raise HTTPException(status_code=400, detail="Mode must be 'saas' or 'byok'")

    # Check current mode to avoid no-op
    cur = execute_query(
        "SELECT deployment_mode FROM instances WHERE id = ?",
        [ctx.instance_id],
        instance_id=None,
    )
    current_mode = cur["rows"][0]["deployment_mode"] if cur.get("rows") else "saas"
    if current_mode == body.mode:
        return {"deployment_mode": body.mode, "changed": False}

    # Cancel existing Stripe subscription regardless of direction
    cancel_instance_subscription(ctx.instance_id)

    if body.mode == "byok":
        # SaaS → BYOK
        execute_query(
            "UPDATE instances SET deployment_mode = 'byok', "
            "query_limit = NULL, query_tier = NULL, "
            "query_count = 0, query_pool_reset_at = NOW(), "
            "tier = 'free' "
            "WHERE id = ?",
            [ctx.instance_id],
            instance_id=None,
        )
    else:
        # BYOK → SaaS: clear credentials and reset LLM config
        execute_query(
            "UPDATE instances SET deployment_mode = 'saas', "
            "query_tier = 1, query_limit = 250, "
            "query_count = 0, query_pool_reset_at = NOW(), "
            "tier = 'free', "
            "llm_api_key_encrypted = NULL, llm_api_key_iv = NULL, "
            "llm_key_last_validated = NULL, "
            "llm_provider = 'anthropic', llm_model = NULL "
            "WHERE id = ?",
            [ctx.instance_id],
            instance_id=None,
        )
        # Audit log for key revocation
        execute_query(
            "INSERT INTO api_key_audit_log (instance_id, action, performed_by, details) "
            "VALUES (?, 'revoked', ?, 'Automatic revocation on switch to SaaS mode')",
            [ctx.instance_id, ctx.auth_user_id],
            instance_id=None,
        )

    clear_config_cache(ctx.instance_id)
    return {"deployment_mode": body.mode, "changed": True}


# ---------------------------------------------------------------------------
# Query tier management (SaaS)
# ---------------------------------------------------------------------------

@router.post("/update-query-tier")
async def update_tier(body: QueryTierBody, ctx: InstanceContext = Depends(get_current_instance)):
    """Update the SaaS query tier (1-40 x 250 queries)."""
    if ctx.role != "owner":
        raise HTTPException(status_code=403, detail="Only the instance owner can change the query tier")
    if body.tier < 1 or body.tier > 40:
        raise HTTPException(status_code=400, detail="Query tier must be between 1 and 40")

    result = update_query_tier(ctx.instance_id, body.tier)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# BYOK API key management
# ---------------------------------------------------------------------------

@router.post("/set-api-key")
async def set_api_key(body: SetApiKeyBody, ctx: InstanceContext = Depends(get_current_instance)):
    """Set or update the instance's BYOK LLM API key (owner only)."""
    if ctx.role != "owner":
        raise HTTPException(status_code=403, detail="Only the instance owner can manage the API key")

    # Encrypt and store
    ciphertext, iv = encrypt_api_key(body.api_key)
    execute_query(
        "UPDATE instances SET llm_api_key_encrypted = ?, llm_api_key_iv = ?, "
        "llm_key_last_validated = NULL WHERE id = ?",
        [ciphertext, iv, ctx.instance_id],
        instance_id=None,
    )

    # Audit log
    execute_query(
        "INSERT INTO api_key_audit_log (instance_id, action, performed_by, details) VALUES (?, ?, ?, ?)",
        [ctx.instance_id, "set", ctx.auth_user_id, f"Key set (masked: {mask_api_key(body.api_key)})"],
        instance_id=None,
    )

    clear_config_cache(ctx.instance_id)
    return {"message": "API key saved", "masked_key": mask_api_key(body.api_key)}


@router.post("/validate-key")
async def validate_api_key(ctx: InstanceContext = Depends(get_current_instance)):
    """Test the stored BYOK API key with a minimal API call."""
    if ctx.role != "owner":
        raise HTTPException(status_code=403, detail="Only the instance owner can validate the API key")

    # Fetch encrypted key and provider/model
    result = execute_query(
        "SELECT llm_api_key_encrypted, llm_api_key_iv, llm_provider, llm_model "
        "FROM instances WHERE id = ?",
        [ctx.instance_id],
        instance_id=None,
    )
    if not result.get("rows"):
        raise HTTPException(status_code=404, detail="Instance not found")

    row = result["rows"][0]
    if not row.get("llm_api_key_encrypted") or not row.get("llm_api_key_iv"):
        raise HTTPException(status_code=400, detail="No API key is configured")

    api_key = decrypt_api_key(bytes(row["llm_api_key_encrypted"]), bytes(row["llm_api_key_iv"]))
    provider = row.get("llm_provider") or "anthropic"
    model = row.get("llm_model")

    validation = validate_key(provider, api_key, model)

    # Update validation timestamp
    action = "validated" if validation["valid"] else "validation_failed"
    if validation["valid"]:
        execute_query(
            "UPDATE instances SET llm_key_last_validated = NOW() WHERE id = ?",
            [ctx.instance_id],
            instance_id=None,
        )

    execute_query(
        "INSERT INTO api_key_audit_log (instance_id, action, performed_by, details) VALUES (?, ?, ?, ?)",
        [ctx.instance_id, action, ctx.auth_user_id, validation.get("error", "Key valid")],
        instance_id=None,
    )

    return validation


@router.delete("/api-key")
async def revoke_api_key(ctx: InstanceContext = Depends(get_current_instance)):
    """Revoke/delete the stored BYOK API key."""
    if ctx.role != "owner":
        raise HTTPException(status_code=403, detail="Only the instance owner can revoke the API key")

    execute_query(
        "UPDATE instances SET llm_api_key_encrypted = NULL, llm_api_key_iv = NULL, "
        "llm_key_last_validated = NULL WHERE id = ?",
        [ctx.instance_id],
        instance_id=None,
    )

    execute_query(
        "INSERT INTO api_key_audit_log (instance_id, action, performed_by) VALUES (?, ?, ?)",
        [ctx.instance_id, "revoked", ctx.auth_user_id],
        instance_id=None,
    )

    clear_config_cache(ctx.instance_id)
    return {"message": "API key revoked"}


# ---------------------------------------------------------------------------
# LLM configuration
# ---------------------------------------------------------------------------

@router.get("/llm-config")
async def get_llm_config(ctx: InstanceContext = Depends(get_current_instance)):
    """Get the instance's LLM provider, model, and key status (masked)."""
    result = execute_query(
        "SELECT deployment_mode, llm_provider, llm_model, llm_api_key_encrypted, "
        "llm_api_key_iv, llm_key_last_validated "
        "FROM instances WHERE id = ?",
        [ctx.instance_id],
        instance_id=None,
    )
    if not result.get("rows"):
        raise HTTPException(status_code=404, detail="Instance not found")

    row = result["rows"][0]
    config = {
        "deployment_mode": row.get("deployment_mode") or "saas",
        "provider": row.get("llm_provider") or "anthropic",
        "model": row.get("llm_model"),
        "has_api_key": bool(row.get("llm_api_key_encrypted")),
        "llm_key_last_validated": str(row["llm_key_last_validated"]) if row.get("llm_key_last_validated") else None,
    }

    # Show masked key only to owner
    if ctx.role == "owner" and row.get("llm_api_key_encrypted") and row.get("llm_api_key_iv"):
        try:
            key = decrypt_api_key(bytes(row["llm_api_key_encrypted"]), bytes(row["llm_api_key_iv"]))
            config["masked_key"] = mask_api_key(key)
        except Exception:
            config["masked_key"] = "****"

    return config


@router.post("/llm-config")
async def update_llm_config(body: LLMConfigBody, ctx: InstanceContext = Depends(get_current_instance)):
    """Update the instance's LLM provider and model selection (owner only)."""
    if ctx.role != "owner":
        raise HTTPException(status_code=403, detail="Only the instance owner can change LLM configuration")

    if body.provider not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {body.provider}")

    # Validate model if specified
    if body.model:
        valid_ids = [m["id"] for m in SUPPORTED_MODELS[body.provider]]
        if body.model not in valid_ids:
            raise HTTPException(status_code=400, detail=f"Unknown model: {body.model} for provider {body.provider}")

    execute_query(
        "UPDATE instances SET llm_provider = ?, llm_model = ? WHERE id = ?",
        [body.provider, body.model, ctx.instance_id],
        instance_id=None,
    )

    clear_config_cache(ctx.instance_id)
    return {"provider": body.provider, "model": body.model}


@router.get("/available-models")
async def available_models():
    """List all supported LLM providers and models."""
    return SUPPORTED_MODELS


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
