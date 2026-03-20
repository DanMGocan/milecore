"""Stripe billing integration for TrueCore.cloud per-user subscription model."""

from __future__ import annotations

import stripe

from backend.config import (
    APP_URL,
    STRIPE_SECRET_KEY,
    STRIPE_PRICE_USER_SEAT,
    STRIPE_PRICE_EMAIL_ADDON,
    STRIPE_PRICE_DAILY_REPORTS_ADDON,
    STRIPE_PRICE_INBOUND_EMAIL_ADDON,
    STRIPE_PRICE_QUERY_PACK,
)
from backend.database import execute_query

stripe.api_key = STRIPE_SECRET_KEY


def _stripe_configured() -> bool:
    return bool(STRIPE_SECRET_KEY and STRIPE_PRICE_USER_SEAT)


def _log_event(instance_id: int, event_type: str, details: str | None = None) -> None:
    execute_query(
        "INSERT INTO subscription_events (instance_id, event_type, details) VALUES (?, ?, ?)",
        [instance_id, event_type, details],
        instance_id=None,
    )


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------

def create_stripe_customer(auth_user_id: int, email: str, name: str) -> str | None:
    """Create a Stripe customer for an auth_user. Returns customer ID or None."""
    if not _stripe_configured():
        return None

    customer = stripe.Customer.create(email=email, name=name, metadata={"auth_user_id": str(auth_user_id)})
    execute_query(
        "UPDATE auth_users SET stripe_customer_id = ? WHERE id = ?",
        [customer.id, auth_user_id],
        instance_id=None,
    )
    return customer.id


def _get_stripe_customer_id(auth_user_id: int) -> str | None:
    result = execute_query(
        "SELECT stripe_customer_id FROM auth_users WHERE id = ?",
        [auth_user_id],
        instance_id=None,
    )
    if result.get("rows") and result["rows"][0].get("stripe_customer_id"):
        return result["rows"][0]["stripe_customer_id"]
    return None


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------

def create_instance_subscription(instance_id: int, auth_user_id: int) -> dict:
    """Create a Stripe subscription with 1 user seat for a new instance."""
    if not _stripe_configured():
        return {"skipped": True, "reason": "Stripe not configured"}

    customer_id = _get_stripe_customer_id(auth_user_id)
    if not customer_id:
        return {"error": "No Stripe customer for this user"}

    subscription = stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": STRIPE_PRICE_USER_SEAT, "quantity": 1}],
        metadata={"instance_id": str(instance_id), "auth_user_id": str(auth_user_id)},
        payment_behavior="default_incomplete",
        expand=["latest_invoice.payment_intent"],
    )

    execute_query(
        "UPDATE instances SET stripe_subscription_id = ?, billing_owner_id = ?, tier = 'paid', "
        "query_limit = 250, query_pool_reset_at = NOW() WHERE id = ?",
        [subscription.id, auth_user_id, instance_id],
        instance_id=None,
    )

    _log_event(instance_id, "subscription_created", f"Subscription {subscription.id} created with 1 seat")

    return {
        "subscription_id": subscription.id,
        "status": subscription.status,
        "client_secret": (
            subscription.latest_invoice.payment_intent.client_secret
            if subscription.latest_invoice and subscription.latest_invoice.payment_intent
            else None
        ),
    }


def _get_subscription_id(instance_id: int) -> str | None:
    result = execute_query(
        "SELECT stripe_subscription_id FROM instances WHERE id = ?",
        [instance_id],
        instance_id=None,
    )
    if result.get("rows") and result["rows"][0].get("stripe_subscription_id"):
        return result["rows"][0]["stripe_subscription_id"]
    return None


def _find_subscription_item(subscription_id: str, price_id: str) -> dict | None:
    """Find a specific line item in a subscription by price ID."""
    sub = stripe.Subscription.retrieve(subscription_id, expand=["items.data"])
    for item in sub["items"]["data"]:
        if item["price"]["id"] == price_id:
            return {"id": item["id"], "quantity": item.get("quantity", 1)}
    return None


# ---------------------------------------------------------------------------
# Seat management
# ---------------------------------------------------------------------------

def add_user_seat(instance_id: int) -> dict:
    """Increment the user seat quantity on the instance subscription."""
    if not _stripe_configured():
        # Still update query_limit locally
        execute_query(
            "UPDATE instances SET query_limit = query_limit + 250 WHERE id = ?",
            [instance_id],
            instance_id=None,
        )
        return {"skipped": True}

    sub_id = _get_subscription_id(instance_id)
    if not sub_id:
        return {"error": "No subscription for this instance"}

    item = _find_subscription_item(sub_id, STRIPE_PRICE_USER_SEAT)
    if not item:
        return {"error": "User seat item not found on subscription"}

    new_qty = item["quantity"] + 1
    stripe.SubscriptionItem.modify(item["id"], quantity=new_qty)

    execute_query(
        "UPDATE instances SET query_limit = ? * 250 WHERE id = ?",
        [new_qty, instance_id],
        instance_id=None,
    )

    _log_event(instance_id, "user_added", f"Seats updated to {new_qty}")
    return {"seats": new_qty, "new_query_limit": new_qty * 250}


def remove_user_seat(instance_id: int) -> dict:
    """Decrement the user seat quantity on the instance subscription."""
    if not _stripe_configured():
        execute_query(
            "UPDATE instances SET query_limit = GREATEST(query_limit - 250, 250) WHERE id = ?",
            [instance_id],
            instance_id=None,
        )
        return {"skipped": True}

    sub_id = _get_subscription_id(instance_id)
    if not sub_id:
        return {"error": "No subscription for this instance"}

    item = _find_subscription_item(sub_id, STRIPE_PRICE_USER_SEAT)
    if not item:
        return {"error": "User seat item not found on subscription"}

    new_qty = max(1, item["quantity"] - 1)
    stripe.SubscriptionItem.modify(item["id"], quantity=new_qty)

    execute_query(
        "UPDATE instances SET query_limit = ? * 250 WHERE id = ?",
        [new_qty, instance_id],
        instance_id=None,
    )

    _log_event(instance_id, "user_removed", f"Seats updated to {new_qty}")
    return {"seats": new_qty, "new_query_limit": new_qty * 250}


# ---------------------------------------------------------------------------
# Addon management
# ---------------------------------------------------------------------------

def toggle_email_addon(instance_id: int, enable: bool) -> dict:
    """Add or remove the email addon line item on the subscription."""
    if not _stripe_configured():
        execute_query(
            "UPDATE instances SET email_addon = ? WHERE id = ?",
            [enable, instance_id],
            instance_id=None,
        )
        return {"skipped": True, "email_addon": enable}

    sub_id = _get_subscription_id(instance_id)
    if not sub_id:
        return {"error": "No subscription for this instance"}

    existing = _find_subscription_item(sub_id, STRIPE_PRICE_EMAIL_ADDON)

    if enable and not existing:
        stripe.SubscriptionItem.create(subscription=sub_id, price=STRIPE_PRICE_EMAIL_ADDON, quantity=1)
    elif not enable and existing:
        stripe.SubscriptionItem.delete(existing["id"])

    execute_query(
        "UPDATE instances SET email_addon = ? WHERE id = ?",
        [enable, instance_id],
        instance_id=None,
    )

    event_type = "addon_enabled" if enable else "addon_disabled"
    _log_event(instance_id, event_type, "Email addon")
    return {"email_addon": enable}


def toggle_inbound_email_addon(instance_id: int, enable: bool) -> dict:
    """Add or remove the inbound email addon line item on the subscription."""
    if not _stripe_configured():
        execute_query(
            "UPDATE instances SET inbound_email_addon = ? WHERE id = ?",
            [enable, instance_id],
            instance_id=None,
        )
        return {"skipped": True, "inbound_email_addon": enable}

    sub_id = _get_subscription_id(instance_id)
    if not sub_id:
        return {"error": "No subscription for this instance"}

    existing = _find_subscription_item(sub_id, STRIPE_PRICE_INBOUND_EMAIL_ADDON)

    if enable and not existing:
        stripe.SubscriptionItem.create(subscription=sub_id, price=STRIPE_PRICE_INBOUND_EMAIL_ADDON, quantity=1)
    elif not enable and existing:
        stripe.SubscriptionItem.delete(existing["id"])

    execute_query(
        "UPDATE instances SET inbound_email_addon = ? WHERE id = ?",
        [enable, instance_id],
        instance_id=None,
    )

    event_type = "addon_enabled" if enable else "addon_disabled"
    _log_event(instance_id, event_type, "Inbound email addon")
    return {"inbound_email_addon": enable}


def toggle_daily_reports_addon(instance_id: int, enable: bool) -> dict:
    """Add or remove the daily reports addon line item on the subscription."""
    if not _stripe_configured():
        execute_query(
            "UPDATE instances SET daily_reports_addon = ? WHERE id = ?",
            [enable, instance_id],
            instance_id=None,
        )
        return {"skipped": True, "daily_reports_addon": enable}

    sub_id = _get_subscription_id(instance_id)
    if not sub_id:
        return {"error": "No subscription for this instance"}

    existing = _find_subscription_item(sub_id, STRIPE_PRICE_DAILY_REPORTS_ADDON)

    if enable and not existing:
        stripe.SubscriptionItem.create(subscription=sub_id, price=STRIPE_PRICE_DAILY_REPORTS_ADDON, quantity=1)
    elif not enable and existing:
        stripe.SubscriptionItem.delete(existing["id"])

    execute_query(
        "UPDATE instances SET daily_reports_addon = ? WHERE id = ?",
        [enable, instance_id],
        instance_id=None,
    )

    event_type = "addon_enabled" if enable else "addon_disabled"
    _log_event(instance_id, event_type, "Daily reports addon")
    return {"daily_reports_addon": enable}


# ---------------------------------------------------------------------------
# Query pack (one-time purchase)
# ---------------------------------------------------------------------------

def create_query_pack_checkout(instance_id: int, auth_user_id: int) -> dict:
    """Create a Stripe Checkout session for a 250-query pack purchase."""
    if not _stripe_configured():
        return {"error": "Stripe not configured"}

    customer_id = _get_stripe_customer_id(auth_user_id)
    if not customer_id:
        return {"error": "No Stripe customer for this user"}

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="payment",
        line_items=[{"price": STRIPE_PRICE_QUERY_PACK, "quantity": 1}],
        metadata={"instance_id": str(instance_id), "auth_user_id": str(auth_user_id), "type": "query_pack"},
        success_url=f"{APP_URL}/dashboard?purchase=success",
        cancel_url=f"{APP_URL}/dashboard?purchase=cancelled",
    )
    return {"checkout_url": session.url, "session_id": session.id}


# ---------------------------------------------------------------------------
# Customer portal
# ---------------------------------------------------------------------------

def create_customer_portal_session(auth_user_id: int) -> dict:
    """Create a Stripe Customer Portal session for managing payment methods."""
    if not _stripe_configured():
        return {"error": "Stripe not configured"}

    customer_id = _get_stripe_customer_id(auth_user_id)
    if not customer_id:
        return {"error": "No Stripe customer for this user"}

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{APP_URL}/dashboard",
    )
    return {"portal_url": session.url}


# ---------------------------------------------------------------------------
# Webhook handlers
# ---------------------------------------------------------------------------

def handle_subscription_renewed(subscription_id: str) -> None:
    """On subscription renewal: reset query pool and recalculate limit."""
    result = execute_query(
        "SELECT id FROM instances WHERE stripe_subscription_id = ?",
        [subscription_id],
        instance_id=None,
    )
    if not result.get("rows"):
        return

    instance_id = result["rows"][0]["id"]

    # Count active memberships
    member_count_result = execute_query(
        "SELECT COUNT(*) as cnt FROM instance_memberships WHERE instance_id = ?",
        [instance_id],
        instance_id=None,
    )
    active_users = member_count_result["rows"][0]["cnt"] if member_count_result.get("rows") else 1

    new_limit = active_users * 250

    execute_query(
        "UPDATE instances SET query_count = 0, query_limit = ?, query_pool_reset_at = NOW() WHERE id = ?",
        [new_limit, instance_id],
        instance_id=None,
    )

    _log_event(instance_id, "queries_reset", f"Pool reset: {new_limit} queries ({active_users} users)")


def handle_payment_failed(subscription_id: str) -> None:
    """On payment failure: mark instance status."""
    result = execute_query(
        "SELECT id FROM instances WHERE stripe_subscription_id = ?",
        [subscription_id],
        instance_id=None,
    )
    if not result.get("rows"):
        return

    instance_id = result["rows"][0]["id"]
    execute_query(
        "UPDATE instances SET status = 'payment_failed' WHERE id = ?",
        [instance_id],
        instance_id=None,
    )
    _log_event(instance_id, "payment_failed", f"Subscription {subscription_id}")


def handle_query_pack_paid(instance_id: int, auth_user_id: int, payment_intent_id: str) -> None:
    """On query pack purchase: add 250 to limit and record purchase."""
    execute_query(
        "UPDATE instances SET query_limit = query_limit + 250 WHERE id = ?",
        [instance_id],
        instance_id=None,
    )

    execute_query(
        "INSERT INTO query_pack_purchases (instance_id, purchased_by_auth_user_id, queries_added, stripe_payment_intent_id) "
        "VALUES (?, ?, 250, ?)",
        [instance_id, auth_user_id, payment_intent_id],
        instance_id=None,
    )

    _log_event(instance_id, "pack_purchased", "250 queries added")


def handle_subscription_cancelled(subscription_id: str) -> None:
    """On cancellation: mark instance status."""
    result = execute_query(
        "SELECT id FROM instances WHERE stripe_subscription_id = ?",
        [subscription_id],
        instance_id=None,
    )
    if not result.get("rows"):
        return

    instance_id = result["rows"][0]["id"]
    execute_query(
        "UPDATE instances SET status = 'cancelled' WHERE id = ?",
        [instance_id],
        instance_id=None,
    )
    _log_event(instance_id, "subscription_cancelled", f"Subscription {subscription_id}")


# ---------------------------------------------------------------------------
# Billing status
# ---------------------------------------------------------------------------

def get_billing_status(instance_id: int) -> dict:
    """Return billing info for an instance."""
    inst = execute_query(
        "SELECT i.stripe_subscription_id, i.billing_owner_id, i.query_count, i.query_limit, "
        "i.email_addon, i.inbound_email_addon, i.daily_reports_addon, i.query_pool_reset_at, i.email_signature, i.tier "
        "FROM instances i WHERE i.id = ?",
        [instance_id],
        instance_id=None,
    )
    if not inst.get("rows"):
        return {"error": "Instance not found"}

    row = inst["rows"][0]

    # Count active members
    member_result = execute_query(
        "SELECT COUNT(*) as cnt FROM instance_memberships WHERE instance_id = ?",
        [instance_id],
        instance_id=None,
    )
    seat_count = member_result["rows"][0]["cnt"] if member_result.get("rows") else 0

    # Count purchased packs
    packs_result = execute_query(
        "SELECT COALESCE(SUM(queries_added), 0) as total FROM query_pack_purchases WHERE instance_id = ?",
        [instance_id],
        instance_id=None,
    )
    purchased_queries = packs_result["rows"][0]["total"] if packs_result.get("rows") else 0

    # Recent events
    events_result = execute_query(
        "SELECT event_type, details, created_at FROM subscription_events "
        "WHERE instance_id = ? ORDER BY created_at DESC LIMIT 20",
        [instance_id],
        instance_id=None,
    )

    status = {
        "tier": row["tier"],
        "seat_count": seat_count,
        "base_queries": seat_count * 250,
        "purchased_queries": purchased_queries,
        "query_count": row["query_count"],
        "query_limit": row["query_limit"],
        "queries_remaining": max(0, row["query_limit"] - row["query_count"]),
        "email_addon": bool(row["email_addon"]),
        "inbound_email_addon": bool(row.get("inbound_email_addon", False)),
        "daily_reports_addon": bool(row["daily_reports_addon"]),
        "email_signature": row["email_signature"] or "",
        "query_pool_reset_at": str(row["query_pool_reset_at"]) if row["query_pool_reset_at"] else None,
        "has_subscription": bool(row["stripe_subscription_id"]),
        "events": [
            {"event_type": e["event_type"], "details": e["details"], "created_at": str(e["created_at"])}
            for e in events_result.get("rows", [])
        ],
    }

    # If Stripe is configured, fetch subscription details
    if _stripe_configured() and row["stripe_subscription_id"]:
        try:
            sub = stripe.Subscription.retrieve(row["stripe_subscription_id"])
            status["subscription_status"] = sub.status
            status["current_period_end"] = sub.current_period_end
        except Exception:
            status["subscription_status"] = "unknown"

    return status
