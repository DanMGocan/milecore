"""Tests for backend/inbound_booking.py — inbound email-to-booking processing."""

from unittest.mock import patch, MagicMock

from backend.inbound_booking import (
    _check_bookings_addon,
    _extract_booking_fields,
    _resolve_resource,
    _check_availability,
    _find_alternatives,
    _create_booking,
    _check_and_send_av_notification,
    process_inbound_booking,
)


# --- Addon check --------------------------------------------------------------

@patch("backend.inbound_booking.execute_query")
def test_bookings_addon_enabled(mock_eq):
    mock_eq.return_value = {"rows": [{"bookings_addon": True}]}
    assert _check_bookings_addon(1) is True


@patch("backend.inbound_booking.execute_query")
def test_bookings_addon_disabled(mock_eq):
    mock_eq.return_value = {"rows": [{"bookings_addon": False}]}
    assert _check_bookings_addon(1) is False


@patch("backend.inbound_booking.execute_query")
def test_bookings_addon_no_instance(mock_eq):
    mock_eq.return_value = {"rows": []}
    assert _check_bookings_addon(999) is False


# --- Claude booking extraction ------------------------------------------------

@patch("backend.claude_client._increment_query_count", return_value=None)
@patch("backend.claude_client._get_client")
def test_extract_booking_fields_success(mock_client, mock_inc):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"resource_type": "room", "resource_name": "Conference Room A", "date": "2026-03-25", '
             '"start_time": "14:00", "end_time": "15:00", "site_name": null, '
             '"title": "Team standup", "notes": null}'
    )]
    mock_client.return_value.messages.create.return_value = mock_response

    result = _extract_booking_fields("Book a room", "I need Conference Room A tomorrow 2-3pm", 1)
    assert result is not None
    assert result["resource_type"] == "room"
    assert result["resource_name"] == "Conference Room A"
    assert result["date"] == "2026-03-25"
    assert result["start_time"] == "14:00"
    assert result["end_time"] == "15:00"
    assert result["title"] == "Team standup"


@patch("backend.claude_client._increment_query_count")
def test_extract_booking_fields_quota_exhausted(mock_inc):
    mock_inc.return_value = {"error": "Query limit reached"}
    result = _extract_booking_fields("Book a room", "I need a room", 1)
    assert result is None


@patch("backend.claude_client._increment_query_count", return_value=None)
@patch("backend.claude_client._get_client")
def test_extract_booking_fields_invalid_type(mock_client, mock_inc):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"resource_type": "spaceship", "resource_name": "Apollo", "date": "2026-03-25", '
             '"start_time": "14:00", "end_time": "15:00", "site_name": null, '
             '"title": "Launch", "notes": null}'
    )]
    mock_client.return_value.messages.create.return_value = mock_response

    result = _extract_booking_fields("Book a spaceship", "I need a spaceship", 1)
    assert result is None


@patch("backend.claude_client._increment_query_count", return_value=None)
@patch("backend.claude_client._get_client")
def test_extract_booking_fields_api_error(mock_client, mock_inc):
    mock_client.return_value.messages.create.side_effect = Exception("API Error")
    result = _extract_booking_fields("Book", "Room please", 1)
    assert result is None


# --- Resource resolution -------------------------------------------------------

@patch("backend.inbound_booking.execute_query")
def test_resolve_resource_found(mock_eq):
    mock_eq.return_value = {"rows": [{"id": 5, "name": "Conference Room A", "site_id": 1}]}
    result = _resolve_resource(1, "room", "Conference Room A")
    assert result is not None
    assert result["id"] == 5
    assert result["name"] == "Conference Room A"


@patch("backend.inbound_booking.execute_query")
def test_resolve_resource_not_found(mock_eq):
    mock_eq.return_value = {"rows": []}
    result = _resolve_resource(1, "room", "Nonexistent Room")
    assert result is None


@patch("backend.inbound_booking.execute_query")
def test_resolve_resource_with_site_filter(mock_eq):
    mock_eq.return_value = {"rows": [{"id": 3, "name": "Desk 12", "site_id": 2}]}
    result = _resolve_resource(1, "desk", "Desk 12", site_id=2)
    assert result is not None
    # Verify site_id was included in query params
    call_params = mock_eq.call_args[0][1]
    assert 2 in call_params


def test_resolve_resource_invalid_type():
    result = _resolve_resource(1, "spaceship", "Apollo")
    assert result is None


# --- Availability checking ----------------------------------------------------

@patch("backend.inbound_booking.execute_query")
def test_availability_free(mock_eq):
    mock_eq.return_value = {"rows": [{"cnt": 0}]}
    assert _check_availability(1, "room", 5, "2026-03-25T14:00:00", "2026-03-25T15:00:00") is True


@patch("backend.inbound_booking.execute_query")
def test_availability_booked(mock_eq):
    mock_eq.return_value = {"rows": [{"cnt": 1}]}
    assert _check_availability(1, "room", 5, "2026-03-25T14:00:00", "2026-03-25T15:00:00") is False


@patch("backend.inbound_booking.execute_query")
def test_availability_query_params(mock_eq):
    """Verify the overlap detection query uses correct parameters."""
    mock_eq.return_value = {"rows": [{"cnt": 0}]}
    _check_availability(1, "desk", 3, "2026-03-25T09:00:00", "2026-03-25T17:00:00")
    call_params = mock_eq.call_args[0][1]
    assert 1 in call_params  # instance_id
    assert "desk" in call_params  # resource_type
    assert 3 in call_params  # resource_id


# --- Alternative finding -------------------------------------------------------

@patch("backend.inbound_booking.execute_query")
def test_find_alternatives_returns_results(mock_eq):
    mock_eq.return_value = {"rows": [
        {"id": 6, "name": "Conference Room B", "location": "2nd Floor"},
        {"id": 7, "name": "Conference Room C", "location": "3rd Floor"},
    ]}
    results = _find_alternatives(1, "room", 1, "2026-03-25T14:00:00", "2026-03-25T15:00:00")
    assert len(results) == 2
    assert results[0]["name"] == "Conference Room B"


@patch("backend.inbound_booking.execute_query")
def test_find_alternatives_none_available(mock_eq):
    mock_eq.return_value = {"rows": []}
    results = _find_alternatives(1, "room", 1, "2026-03-25T14:00:00", "2026-03-25T15:00:00")
    assert results == []


def test_find_alternatives_invalid_type():
    results = _find_alternatives(1, "spaceship", 1, "2026-03-25T14:00:00", "2026-03-25T15:00:00")
    assert results == []


# --- Booking creation ---------------------------------------------------------

@patch("backend.inbound_booking.execute_query")
def test_create_booking_success(mock_eq):
    mock_eq.return_value = {"lastrowid": 42}
    result = _create_booking(
        instance_id=1, resource_type="room", resource_id=5,
        site_id=1, person_id=10,
        start_time="2026-03-25T14:00:00", end_time="2026-03-25T15:00:00",
        title="Team meeting", notes="Bring snacks",
    )
    assert result == 42
    call_sql = mock_eq.call_args[0][0]
    assert "INSERT INTO bookings" in call_sql
    assert "'email'" in call_sql  # source = 'email' is hardcoded in SQL


# --- AV notification -----------------------------------------------------------

@patch("backend.inbound_booking.send_email")
@patch("backend.inbound_booking.execute_query")
def test_av_notification_sent_for_av_room(mock_eq, mock_send):
    mock_eq.side_effect = [
        {"rows": [{"name": "AV Room", "capacity": 10, "has_av": True}]},  # room lookup
        {"rows": [{"value": "avteam@company.com"}]},  # app_settings lookup
    ]
    _check_and_send_av_notification(1, "room", 5, 42, "John", "2026-03-25T14:00", "2026-03-25T15:00")
    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args[1]
    assert call_kwargs["to_email"] == "avteam@company.com"
    assert "AV Room" in call_kwargs["subject"]


@patch("backend.inbound_booking.send_email")
@patch("backend.inbound_booking.execute_query")
def test_av_notification_sent_for_large_room(mock_eq, mock_send):
    mock_eq.side_effect = [
        {"rows": [{"name": "Auditorium", "capacity": 50, "has_av": False}]},
        {"rows": [{"value": "avteam@company.com"}]},
    ]
    _check_and_send_av_notification(1, "room", 5, 42, "John", "2026-03-25T14:00", "2026-03-25T15:00")
    mock_send.assert_called_once()


@patch("backend.inbound_booking.send_email")
@patch("backend.inbound_booking.execute_query")
def test_no_av_notification_for_small_room(mock_eq, mock_send):
    mock_eq.return_value = {"rows": [{"name": "Huddle", "capacity": 4, "has_av": False}]}
    _check_and_send_av_notification(1, "room", 5, 42, "John", "2026-03-25T14:00", "2026-03-25T15:00")
    mock_send.assert_not_called()


@patch("backend.inbound_booking.send_email")
def test_no_av_notification_for_desk(mock_send):
    _check_and_send_av_notification(1, "desk", 3, 42, "John", "2026-03-25T09:00", "2026-03-25T17:00")
    mock_send.assert_not_called()


@patch("backend.inbound_booking.send_email")
@patch("backend.inbound_booking.execute_query")
def test_no_av_notification_when_not_configured(mock_eq, mock_send):
    mock_eq.side_effect = [
        {"rows": [{"name": "AV Room", "capacity": 10, "has_av": True}]},
        {"rows": []},  # no av_support_email in app_settings
    ]
    _check_and_send_av_notification(1, "room", 5, 42, "John", "2026-03-25T14:00", "2026-03-25T15:00")
    mock_send.assert_not_called()


# --- Full orchestration --------------------------------------------------------

@patch("backend.inbound_booking._check_and_send_av_notification")
@patch("backend.inbound_booking._send_booking_confirmation")
@patch("backend.inbound_booking._create_booking", return_value=42)
@patch("backend.inbound_booking._check_availability", return_value=True)
@patch("backend.inbound_booking._resolve_resource", return_value={"id": 5, "name": "Room A", "site_id": 1})
@patch("backend.inbound_booking._match_sender_to_person", return_value={"id": 10, "site_id": 1})
@patch("backend.inbound_booking._extract_booking_fields")
@patch("backend.inbound_booking._check_sender_whitelist", return_value=True)
@patch("backend.inbound_booking._check_rate_limit", return_value=True)
@patch("backend.inbound_booking._check_bookings_addon", return_value=True)
@patch("backend.inbound_booking._log_inbound_email")
def test_process_booking_success(
    mock_log, mock_addon, mock_rate, mock_whitelist,
    mock_extract, mock_match, mock_resolve, mock_avail,
    mock_create, mock_confirm, mock_av,
):
    mock_extract.return_value = {
        "resource_type": "room", "resource_name": "Room A",
        "date": "2026-03-25", "start_time": "14:00", "end_time": "15:00",
        "site_name": None, "title": "Meeting", "notes": None,
    }

    result = process_inbound_booking(
        instance_id=1, slug="workday",
        sender_email="user@company.com", sender_name="Test User",
        subject="Book a room", body_plain="I need Room A tomorrow 2-3pm",
        from_domain="company.com", brevo_message_id="msg-123",
    )
    assert result["status"] == "booking_confirmed"
    assert result["booking_id"] == 42
    mock_confirm.assert_called_once()
    mock_av.assert_called_once()


@patch("backend.inbound_booking._send_unavailable_with_alternatives")
@patch("backend.inbound_booking._find_alternatives", return_value=[{"id": 6, "name": "Room B", "location": "2nd Floor"}])
@patch("backend.inbound_booking._check_availability", return_value=False)
@patch("backend.inbound_booking._resolve_resource", return_value={"id": 5, "name": "Room A", "site_id": 1})
@patch("backend.inbound_booking._match_sender_to_person", return_value={"id": 10, "site_id": 1})
@patch("backend.inbound_booking._extract_booking_fields")
@patch("backend.inbound_booking._check_sender_whitelist", return_value=True)
@patch("backend.inbound_booking._check_rate_limit", return_value=True)
@patch("backend.inbound_booking._check_bookings_addon", return_value=True)
@patch("backend.inbound_booking._log_inbound_email")
def test_process_booking_unavailable_with_alternatives(
    mock_log, mock_addon, mock_rate, mock_whitelist,
    mock_extract, mock_match, mock_resolve, mock_avail,
    mock_alts, mock_send_alts,
):
    mock_extract.return_value = {
        "resource_type": "room", "resource_name": "Room A",
        "date": "2026-03-25", "start_time": "14:00", "end_time": "15:00",
        "site_name": None, "title": "Meeting", "notes": None,
    }

    result = process_inbound_booking(
        instance_id=1, slug="workday",
        sender_email="user@company.com", sender_name="Test User",
        subject="Book a room", body_plain="I need Room A tomorrow 2-3pm",
        from_domain="company.com", brevo_message_id="msg-123",
    )
    assert result["status"] == "booking_unavailable"
    mock_send_alts.assert_called_once()


@patch("backend.inbound_booking._log_inbound_email")
@patch("backend.inbound_booking._check_bookings_addon", return_value=False)
def test_process_booking_addon_disabled(mock_addon, mock_log):
    result = process_inbound_booking(
        instance_id=1, slug="workday",
        sender_email="user@company.com", sender_name="Test User",
        subject="Book a room", body_plain="I need a room",
        from_domain="company.com", brevo_message_id="msg-123",
    )
    assert result["status"] == "rejected_addon_disabled"


@patch("backend.inbound_booking.send_email")
@patch("backend.inbound_booking._match_sender_to_person", return_value=None)
@patch("backend.inbound_booking._extract_booking_fields")
@patch("backend.inbound_booking._check_sender_whitelist", return_value=True)
@patch("backend.inbound_booking._check_rate_limit", return_value=True)
@patch("backend.inbound_booking._check_bookings_addon", return_value=True)
@patch("backend.inbound_booking._log_inbound_email")
def test_process_booking_sender_not_found(
    mock_log, mock_addon, mock_rate, mock_whitelist,
    mock_extract, mock_match, mock_send,
):
    mock_extract.return_value = {
        "resource_type": "room", "resource_name": "Room A",
        "date": "2026-03-25", "start_time": "14:00", "end_time": "15:00",
        "site_name": None, "title": "Meeting", "notes": None,
    }

    result = process_inbound_booking(
        instance_id=1, slug="workday",
        sender_email="unknown@company.com", sender_name="Unknown",
        subject="Book a room", body_plain="I need a room",
        from_domain="company.com", brevo_message_id="msg-123",
    )
    assert result["status"] == "error"
    assert result["error"] == "sender_not_found"
