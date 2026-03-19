"""Tests for backend/stripe_billing.py — subscriptions, seats, addons, webhooks."""

from unittest.mock import patch, MagicMock

from backend.stripe_billing import (
    _stripe_configured,
    create_stripe_customer,
    create_instance_subscription,
    add_user_seat,
    remove_user_seat,
    toggle_email_addon,
    toggle_daily_reports_addon,
    handle_subscription_renewed,
    handle_payment_failed,
    handle_query_pack_paid,
    handle_subscription_cancelled,
    get_billing_status,
)


# --- Configuration -----------------------------------------------------------

def test_stripe_configured_true(mock_stripe_config):
    assert _stripe_configured() is True


@patch("backend.stripe_billing.STRIPE_SECRET_KEY", "")
@patch("backend.stripe_billing.STRIPE_PRICE_USER_SEAT", "")
def test_stripe_configured_false():
    assert _stripe_configured() is False


# --- Customer ----------------------------------------------------------------

@patch("backend.stripe_billing.execute_query")
@patch("stripe.Customer.create")
def test_create_stripe_customer(mock_stripe_create, mock_eq, mock_stripe_config):
    mock_stripe_create.return_value = MagicMock(id="cus_test123")
    mock_eq.return_value = {"rowcount": 1, "lastrowid": None}

    result = create_stripe_customer(auth_user_id=1, email="test@example.com", name="Test User")

    assert result == "cus_test123"
    mock_stripe_create.assert_called_once_with(
        email="test@example.com", name="Test User", metadata={"auth_user_id": "1"},
    )
    mock_eq.assert_called_once()


@patch("backend.stripe_billing.STRIPE_SECRET_KEY", "")
@patch("backend.stripe_billing.STRIPE_PRICE_USER_SEAT", "")
def test_create_customer_not_configured():
    result = create_stripe_customer(auth_user_id=1, email="test@example.com", name="Test")
    assert result is None


# --- Subscription creation ----------------------------------------------------

@patch("backend.stripe_billing.execute_query")
@patch("stripe.Subscription.create")
def test_create_instance_subscription(mock_sub_create, mock_eq, mock_stripe_config):
    mock_sub = MagicMock()
    mock_sub.id = "sub_new123"
    mock_sub.status = "incomplete"
    mock_sub.latest_invoice.payment_intent.client_secret = "pi_secret_xxx"
    mock_sub_create.return_value = mock_sub

    mock_eq.side_effect = [
        {"rows": [{"stripe_customer_id": "cus_test123"}]},  # _get_stripe_customer_id
        {"rowcount": 1, "lastrowid": None},                  # UPDATE instances
        {"rowcount": 1, "lastrowid": 1},                     # _log_event INSERT
    ]

    result = create_instance_subscription(instance_id=42, auth_user_id=1)

    assert result["subscription_id"] == "sub_new123"
    assert result["status"] == "incomplete"
    assert result["client_secret"] == "pi_secret_xxx"
    mock_sub_create.assert_called_once()


# --- Seat management ----------------------------------------------------------

@patch("backend.stripe_billing.execute_query")
@patch("stripe.SubscriptionItem.modify")
@patch("stripe.Subscription.retrieve")
def test_add_user_seat(mock_sub_retrieve, mock_item_modify, mock_eq, mock_stripe_config):
    mock_eq.side_effect = [
        {"rows": [{"stripe_subscription_id": "sub_test123"}]},  # _get_subscription_id
        {"rowcount": 1, "lastrowid": None},                     # UPDATE query_limit
        {"rowcount": 1, "lastrowid": 1},                        # _log_event INSERT
    ]
    mock_sub_retrieve.return_value = {
        "items": {"data": [
            {"id": "si_item1", "price": {"id": "price_seat_xxx"}, "quantity": 2},
        ]},
    }

    result = add_user_seat(instance_id=42)

    assert result == {"seats": 3, "new_query_limit": 750}
    mock_item_modify.assert_called_once_with("si_item1", quantity=3)


@patch("backend.stripe_billing.execute_query")
def test_add_user_seat_no_subscription(mock_eq, mock_stripe_config):
    mock_eq.return_value = {"rows": [{"stripe_subscription_id": None}]}

    result = add_user_seat(instance_id=42)

    assert result == {"error": "No subscription for this instance"}


@patch("backend.stripe_billing.STRIPE_SECRET_KEY", "")
@patch("backend.stripe_billing.STRIPE_PRICE_USER_SEAT", "")
@patch("backend.stripe_billing.execute_query")
def test_add_user_seat_stripe_not_configured(mock_eq):
    mock_eq.return_value = {"rowcount": 1, "lastrowid": None}

    result = add_user_seat(instance_id=42)

    assert result == {"skipped": True}
    mock_eq.assert_called_once()
    assert "query_limit + 250" in mock_eq.call_args[0][0]


@patch("backend.stripe_billing.execute_query")
@patch("stripe.SubscriptionItem.modify")
@patch("stripe.Subscription.retrieve")
def test_remove_user_seat_minimum_one(mock_sub_retrieve, mock_item_modify, mock_eq, mock_stripe_config):
    mock_eq.side_effect = [
        {"rows": [{"stripe_subscription_id": "sub_test123"}]},  # _get_subscription_id
        {"rowcount": 1, "lastrowid": None},                     # UPDATE query_limit
        {"rowcount": 1, "lastrowid": 1},                        # _log_event INSERT
    ]
    mock_sub_retrieve.return_value = {
        "items": {"data": [
            {"id": "si_item1", "price": {"id": "price_seat_xxx"}, "quantity": 1},
        ]},
    }

    result = remove_user_seat(instance_id=42)

    assert result == {"seats": 1, "new_query_limit": 250}
    mock_item_modify.assert_called_once_with("si_item1", quantity=1)


@patch("backend.stripe_billing.STRIPE_SECRET_KEY", "")
@patch("backend.stripe_billing.STRIPE_PRICE_USER_SEAT", "")
@patch("backend.stripe_billing.execute_query")
def test_remove_user_seat_stripe_not_configured(mock_eq):
    mock_eq.return_value = {"rowcount": 1, "lastrowid": None}

    result = remove_user_seat(instance_id=42)

    assert result == {"skipped": True}
    mock_eq.assert_called_once()
    assert "GREATEST" in mock_eq.call_args[0][0]


# --- Addon management ---------------------------------------------------------

@patch("backend.stripe_billing.execute_query")
@patch("stripe.SubscriptionItem.create")
@patch("stripe.Subscription.retrieve")
def test_toggle_email_addon_enable(mock_sub_retrieve, mock_item_create, mock_eq, mock_stripe_config):
    mock_eq.side_effect = [
        {"rows": [{"stripe_subscription_id": "sub_test123"}]},  # _get_subscription_id
        {"rowcount": 1, "lastrowid": None},                     # UPDATE email_addon
        {"rowcount": 1, "lastrowid": 1},                        # _log_event INSERT
    ]
    mock_sub_retrieve.return_value = {"items": {"data": []}}

    result = toggle_email_addon(instance_id=42, enable=True)

    assert result == {"email_addon": True}
    mock_item_create.assert_called_once_with(
        subscription="sub_test123", price="price_email_xxx", quantity=1,
    )


@patch("backend.stripe_billing.execute_query")
@patch("stripe.SubscriptionItem.delete")
@patch("stripe.Subscription.retrieve")
def test_toggle_email_addon_disable(mock_sub_retrieve, mock_item_delete, mock_eq, mock_stripe_config):
    mock_eq.side_effect = [
        {"rows": [{"stripe_subscription_id": "sub_test123"}]},  # _get_subscription_id
        {"rowcount": 1, "lastrowid": None},                     # UPDATE email_addon
        {"rowcount": 1, "lastrowid": 1},                        # _log_event INSERT
    ]
    mock_sub_retrieve.return_value = {
        "items": {"data": [
            {"id": "si_email1", "price": {"id": "price_email_xxx"}, "quantity": 1},
        ]},
    }

    result = toggle_email_addon(instance_id=42, enable=False)

    assert result == {"email_addon": False}
    mock_item_delete.assert_called_once_with("si_email1")


@patch("backend.stripe_billing.execute_query")
@patch("stripe.SubscriptionItem.create")
@patch("stripe.Subscription.retrieve")
def test_toggle_daily_reports_addon_enable(mock_sub_retrieve, mock_item_create, mock_eq, mock_stripe_config):
    mock_eq.side_effect = [
        {"rows": [{"stripe_subscription_id": "sub_test123"}]},  # _get_subscription_id
        {"rowcount": 1, "lastrowid": None},                     # UPDATE daily_reports_addon
        {"rowcount": 1, "lastrowid": 1},                        # _log_event INSERT
    ]
    mock_sub_retrieve.return_value = {"items": {"data": []}}

    result = toggle_daily_reports_addon(instance_id=42, enable=True)

    assert result == {"daily_reports_addon": True}
    mock_item_create.assert_called_once_with(
        subscription="sub_test123", price="price_reports_xxx", quantity=1,
    )


@patch("backend.stripe_billing.execute_query")
@patch("stripe.SubscriptionItem.delete")
@patch("stripe.Subscription.retrieve")
def test_toggle_daily_reports_addon_disable(mock_sub_retrieve, mock_item_delete, mock_eq, mock_stripe_config):
    mock_eq.side_effect = [
        {"rows": [{"stripe_subscription_id": "sub_test123"}]},  # _get_subscription_id
        {"rowcount": 1, "lastrowid": None},                     # UPDATE daily_reports_addon
        {"rowcount": 1, "lastrowid": 1},                        # _log_event INSERT
    ]
    mock_sub_retrieve.return_value = {
        "items": {"data": [
            {"id": "si_reports1", "price": {"id": "price_reports_xxx"}, "quantity": 1},
        ]},
    }

    result = toggle_daily_reports_addon(instance_id=42, enable=False)

    assert result == {"daily_reports_addon": False}
    mock_item_delete.assert_called_once_with("si_reports1")


# --- Webhook handlers ---------------------------------------------------------

@patch("backend.stripe_billing.execute_query")
def test_handle_subscription_renewed(mock_eq):
    mock_eq.side_effect = [
        {"rows": [{"id": 42}]},              # SELECT instance
        {"rows": [{"cnt": 3}]},              # COUNT members
        {"rowcount": 1, "lastrowid": None},  # UPDATE query pool
        {"rowcount": 1, "lastrowid": 1},     # _log_event INSERT
    ]

    handle_subscription_renewed("sub_test123")

    # Verify UPDATE sets query_limit = 3 * 250 = 750
    update_call = mock_eq.call_args_list[2]
    assert update_call[0][1] == [750, 42]


@patch("backend.stripe_billing.execute_query")
def test_handle_subscription_renewed_instance_not_found(mock_eq):
    mock_eq.return_value = {"rows": []}

    handle_subscription_renewed("sub_nonexistent")

    assert mock_eq.call_count == 1  # Only the SELECT, then early return


@patch("backend.stripe_billing.execute_query")
def test_handle_payment_failed(mock_eq):
    mock_eq.side_effect = [
        {"rows": [{"id": 42}]},              # SELECT instance
        {"rowcount": 1, "lastrowid": None},  # UPDATE status
        {"rowcount": 1, "lastrowid": 1},     # _log_event INSERT
    ]

    handle_payment_failed("sub_test123")

    update_call = mock_eq.call_args_list[1]
    assert "payment_failed" in update_call[0][0]


@patch("backend.stripe_billing.execute_query")
def test_handle_payment_failed_instance_not_found(mock_eq):
    mock_eq.return_value = {"rows": []}

    handle_payment_failed("sub_nonexistent")

    assert mock_eq.call_count == 1


@patch("backend.stripe_billing.execute_query")
def test_handle_query_pack_paid(mock_eq):
    mock_eq.side_effect = [
        {"rowcount": 1, "lastrowid": None},  # UPDATE query_limit
        {"rowcount": 1, "lastrowid": 1},     # INSERT purchase record
        {"rowcount": 1, "lastrowid": 2},     # _log_event INSERT
    ]

    handle_query_pack_paid(instance_id=42, auth_user_id=1, payment_intent_id="pi_test123")

    assert mock_eq.call_count == 3
    assert "query_limit + 250" in mock_eq.call_args_list[0][0][0]
    assert "query_pack_purchases" in mock_eq.call_args_list[1][0][0]


@patch("backend.stripe_billing.execute_query")
def test_handle_subscription_cancelled(mock_eq):
    mock_eq.side_effect = [
        {"rows": [{"id": 42}]},              # SELECT instance
        {"rowcount": 1, "lastrowid": None},  # UPDATE status
        {"rowcount": 1, "lastrowid": 1},     # _log_event INSERT
    ]

    handle_subscription_cancelled("sub_test123")

    update_call = mock_eq.call_args_list[1]
    assert "cancelled" in update_call[0][0]


@patch("backend.stripe_billing.execute_query")
def test_handle_subscription_cancelled_instance_not_found(mock_eq):
    mock_eq.return_value = {"rows": []}

    handle_subscription_cancelled("sub_nonexistent")

    assert mock_eq.call_count == 1


# --- Billing status -----------------------------------------------------------

@patch("backend.stripe_billing.execute_query")
def test_get_billing_status(mock_eq):
    mock_eq.side_effect = [
        {"rows": [{
            "stripe_subscription_id": "sub_test",
            "billing_owner_id": 1,
            "query_count": 50,
            "query_limit": 750,
            "email_addon": True,
            "daily_reports_addon": False,
            "query_pool_reset_at": "2024-01-01",
            "email_signature": "-- Sent via TrueCore",
            "tier": "paid",
        }]},
        {"rows": [{"cnt": 3}]},       # COUNT members
        {"rows": [{"total": 250}]},    # SUM query packs
        {"rows": []},                  # subscription events
    ]

    result = get_billing_status(instance_id=42)

    assert result["queries_remaining"] == 700   # 750 - 50
    assert result["base_queries"] == 750        # 3 * 250
    assert result["seat_count"] == 3
    assert result["email_addon"] is True
    assert result["daily_reports_addon"] is False
    assert result["purchased_queries"] == 250
    assert result["tier"] == "paid"
