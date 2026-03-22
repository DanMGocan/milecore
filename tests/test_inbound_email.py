"""Tests for backend/inbound_email.py — inbound email-to-ticket processing."""

from unittest.mock import patch, MagicMock

from backend.inbound_email import (
    _parse_instance_from_to,
    _check_addon_enabled,
    _check_sender_whitelist,
    _check_rate_limit,
    _extract_fields_with_claude,
    _raw_extract,
    _match_sender_to_person,
    _create_ticket,
    process_inbound_email,
)


# --- TO address parsing ------------------------------------------------------

def test_parse_slug_from_to():
    result = _parse_instance_from_to("workday@tickets.truecore.cloud")
    assert result == {"slug": "workday", "ticket_id": None, "type": "ticket"}


def test_parse_slug_from_to_with_name():
    result = _parse_instance_from_to("Support <workday@tickets.truecore.cloud>")
    assert result == {"slug": "workday", "ticket_id": None, "type": "ticket"}


def test_parse_slug_case_insensitive():
    result = _parse_instance_from_to("WorkDay@Tickets.TrueCore.Cloud")
    assert result == {"slug": "workday", "ticket_id": None, "type": "ticket"}


def test_parse_slug_wrong_domain():
    assert _parse_instance_from_to("workday@other.com") is None


def test_parse_slug_empty():
    assert _parse_instance_from_to("") is None
    assert _parse_instance_from_to(None) is None


def test_parse_slug_no_local_part():
    assert _parse_instance_from_to("@tickets.truecore.cloud") is None


def test_parse_reply_address():
    result = _parse_instance_from_to("workday+42@tickets.truecore.cloud")
    assert result == {"slug": "workday", "ticket_id": 42, "type": "ticket"}


def test_parse_reply_address_with_name():
    result = _parse_instance_from_to("Support <workday+7@tickets.truecore.cloud>")
    assert result == {"slug": "workday", "ticket_id": 7, "type": "ticket"}


def test_parse_reply_address_invalid_ticket_id():
    result = _parse_instance_from_to("workday+abc@tickets.truecore.cloud")
    assert result == {"slug": "workday", "ticket_id": None, "type": "ticket"}


def test_parse_booking_address():
    result = _parse_instance_from_to("book-workday@tickets.truecore.cloud")
    assert result == {"slug": "workday", "ticket_id": None, "type": "booking"}


def test_parse_booking_address_with_name():
    result = _parse_instance_from_to("Bookings <book-acme@tickets.truecore.cloud>")
    assert result == {"slug": "acme", "ticket_id": None, "type": "booking"}


def test_parse_booking_address_case_insensitive():
    result = _parse_instance_from_to("Book-WorkDay@Tickets.TrueCore.Cloud")
    assert result == {"slug": "workday", "ticket_id": None, "type": "booking"}


def test_parse_booking_no_slug():
    assert _parse_instance_from_to("book-@tickets.truecore.cloud") is None


# --- Addon check --------------------------------------------------------------

@patch("backend.inbound_email.execute_query")
def test_addon_enabled_true(mock_eq):
    mock_eq.return_value = {"rows": [{"inbound_email_addon": True}]}
    assert _check_addon_enabled(1) is True


@patch("backend.inbound_email.execute_query")
def test_addon_enabled_false(mock_eq):
    mock_eq.return_value = {"rows": [{"inbound_email_addon": False}]}
    assert _check_addon_enabled(1) is False


@patch("backend.inbound_email.execute_query")
def test_addon_enabled_no_instance(mock_eq):
    mock_eq.return_value = {"rows": []}
    assert _check_addon_enabled(999) is False


# --- Sender whitelist ---------------------------------------------------------

@patch("backend.inbound_email.execute_query")
def test_whitelist_empty_accepts_all(mock_eq):
    mock_eq.return_value = {"rows": []}
    assert _check_sender_whitelist(1, "anyone@anywhere.com") is True


@patch("backend.inbound_email.execute_query")
def test_whitelist_domain_match(mock_eq):
    mock_eq.return_value = {"rows": [
        {"pattern": "workday.com", "pattern_type": "domain"},
    ]}
    assert _check_sender_whitelist(1, "jane@workday.com") is True


@patch("backend.inbound_email.execute_query")
def test_whitelist_domain_no_match(mock_eq):
    mock_eq.return_value = {"rows": [
        {"pattern": "workday.com", "pattern_type": "domain"},
    ]}
    assert _check_sender_whitelist(1, "jane@other.com") is False


@patch("backend.inbound_email.execute_query")
def test_whitelist_exact_email_match(mock_eq):
    mock_eq.return_value = {"rows": [
        {"pattern": "jane@vendor.com", "pattern_type": "email"},
    ]}
    assert _check_sender_whitelist(1, "jane@vendor.com") is True


@patch("backend.inbound_email.execute_query")
def test_whitelist_exact_email_no_match(mock_eq):
    mock_eq.return_value = {"rows": [
        {"pattern": "jane@vendor.com", "pattern_type": "email"},
    ]}
    assert _check_sender_whitelist(1, "bob@vendor.com") is False


# --- Rate limiting ------------------------------------------------------------

@patch("backend.inbound_email.execute_query")
def test_rate_limit_within(mock_eq):
    mock_eq.return_value = {"rows": [{"cnt": 5}]}
    assert _check_rate_limit("user@example.com") is True


@patch("backend.inbound_email.execute_query")
def test_rate_limit_exceeded(mock_eq):
    mock_eq.return_value = {"rows": [{"cnt": 20}]}
    assert _check_rate_limit("user@example.com") is False


# --- Raw extraction -----------------------------------------------------------

def test_raw_extract():
    result = _raw_extract("Printer broken", "The printer on floor 3 is jammed")
    assert result["title"] == "Printer broken"
    assert result["description"] == "The printer on floor 3 is jammed"
    assert result["ticket_type"] == "incident"
    assert result["priority"] == "medium"


def test_raw_extract_empty():
    result = _raw_extract("", "")
    assert result["title"] == "Inbound email ticket"
    assert result["ticket_type"] == "incident"


# --- Claude extraction --------------------------------------------------------

@patch("backend.claude_client._increment_query_count", return_value=None)
@patch("backend.claude_client._get_client")
def test_claude_extraction_success(mock_client, mock_inc):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"title": "Printer jam", "description": "Paper stuck", "ticket_type": "hardware", "priority": "low", "keywords": "printer,paper jam,tray"}'
    )]
    mock_client.return_value.messages.create.return_value = mock_response

    result = _extract_fields_with_claude("Printer issue", "Paper stuck in tray", 1)
    assert result["title"] == "Printer jam"
    assert result["ticket_type"] == "hardware"
    assert result["priority"] == "low"
    assert result["keywords"] == "printer,paper jam,tray"


@patch("backend.claude_client._increment_query_count", return_value=None)
@patch("backend.claude_client._get_client")
def test_extraction_keywords_missing_defaults_empty(mock_client, mock_inc):
    """If Claude omits keywords, default to empty string."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"title": "Test", "description": "Desc", "ticket_type": "incident", "priority": "medium"}'
    )]
    mock_client.return_value.messages.create.return_value = mock_response

    result = _extract_fields_with_claude("Test", "Desc", 1)
    assert result["keywords"] == ""


def test_raw_extract_has_empty_keywords():
    """Fallback raw extraction sets keywords to empty string."""
    result = _raw_extract("Subject", "Body text")
    assert result["keywords"] == ""


@patch("backend.claude_client._increment_query_count")
def test_claude_extraction_quota_exhausted(mock_inc):
    mock_inc.return_value = {"error": "Query limit reached"}
    result = _extract_fields_with_claude("Test subject", "Test body", 1)
    assert result["title"] == "Test subject"
    assert result["ticket_type"] == "incident"


@patch("backend.claude_client._increment_query_count", return_value=None)
@patch("backend.claude_client._get_client")
def test_claude_extraction_api_error_falls_back(mock_client, mock_inc):
    mock_client.return_value.messages.create.side_effect = Exception("API Error")
    result = _extract_fields_with_claude("Subject", "Body text", 1)
    assert result["title"] == "Subject"
    assert result["ticket_type"] == "incident"


# --- Person matching ----------------------------------------------------------

@patch("backend.inbound_email.execute_query")
def test_match_sender_found(mock_eq):
    mock_eq.return_value = {"rows": [{"id": 42}]}
    assert _match_sender_to_person(1, "jane@company.com") == {"id": 42}


@patch("backend.inbound_email.execute_query")
def test_match_sender_not_found(mock_eq):
    mock_eq.return_value = {"rows": []}
    assert _match_sender_to_person(1, "unknown@company.com") is None


# --- Ticket creation ----------------------------------------------------------

@patch("backend.inbound_email.execute_query")
def test_create_ticket(mock_eq):
    mock_eq.return_value = {"lastrowid": 99}
    fields = {"ticket_type": "hardware", "title": "Broken", "description": "Jammed", "priority": "low", "keywords": "printer,paper jam"}
    result = _create_ticket(1, fields, requester_id=42, site_id=None)
    assert result == 99
    # First call is the INSERT INTO tickets, second is the timeline entry
    insert_sql = mock_eq.call_args_list[0][0][0]
    insert_params = mock_eq.call_args_list[0][0][1]
    assert "INSERT INTO tickets" in insert_sql
    assert "keywords" in insert_sql
    assert "printer,paper jam" in insert_params
    assert "ticket_timeline" in mock_eq.call_args_list[1][0][0]


# --- Full orchestration -------------------------------------------------------

@patch("backend.inbound_email._send_confirmation")
@patch("backend.inbound_email._log_inbound_email")
@patch("backend.inbound_email._create_ticket", return_value=101)
@patch("backend.inbound_email._match_sender_to_person", return_value={"id": 42, "site_id": 5})
@patch("backend.inbound_email._extract_fields_with_claude")
@patch("backend.inbound_email._check_sender_whitelist", return_value=True)
@patch("backend.inbound_email._check_rate_limit", return_value=True)
@patch("backend.inbound_email._check_addon_enabled", return_value=True)
@patch("backend.inbound_email.execute_query")
def test_process_full_success(
    mock_eq, mock_addon, mock_rate, mock_whitelist,
    mock_extract, mock_match, mock_create, mock_log, mock_confirm,
):
    # First call: instance lookup; second call: email_thread_id lookup
    mock_eq.side_effect = [
        {"rows": [{"id": 1}]},
        {"rows": [{"email_thread_id": "<thread@test>"}]},
    ]
    mock_extract.return_value = {
        "title": "Test Issue", "description": "Test description",
        "ticket_type": "incident", "priority": "medium",
    }

    payload = {
        "Sender": {"Address": "user@workday.com", "Name": "Test User"},
        "Subject": "Help needed",
        "RawTextBody": "My app is broken",
        "Recipients": [{"Address": "workday@tickets.truecore.cloud"}],
        "MessageId": "msg-123",
    }

    result = process_inbound_email(payload)
    assert result["status"] == "processed"
    assert result["ticket_id"] == 101
    mock_confirm.assert_called_once()
    # Verify confirmation includes threading params
    confirm_kwargs = mock_confirm.call_args
    assert confirm_kwargs[1].get("instance_slug") == "workday"
    assert confirm_kwargs[1].get("email_thread_id") == "<thread@test>"


@patch("backend.inbound_email._log_inbound_email")
@patch("backend.inbound_email.execute_query")
def test_process_instance_not_found(mock_eq, mock_log):
    payload = {
        "Sender": {"Address": "user@example.com"},
        "Subject": "Help",
        "RawTextBody": "Body",
        "Recipients": [{"Address": "nonexistent@tickets.truecore.cloud"}],
    }
    mock_eq.return_value = {"rows": []}

    result = process_inbound_email(payload)
    assert result["status"] == "rejected_instance_not_found"


@patch("backend.inbound_email._log_inbound_email")
def test_process_bad_to_address(mock_log):
    payload = {
        "Sender": {"Address": "user@example.com"},
        "Subject": "Help",
        "RawTextBody": "Body",
        "Recipients": [{"Address": "user@otherdomain.com"}],
    }

    result = process_inbound_email(payload)
    assert result["status"] == "rejected_instance_not_found"


@patch("backend.inbound_email._log_inbound_email")
@patch("backend.inbound_email._check_addon_enabled", return_value=False)
@patch("backend.inbound_email.execute_query")
def test_process_addon_disabled(mock_eq, mock_addon, mock_log):
    mock_eq.return_value = {"rows": [{"id": 1}]}
    payload = {
        "Sender": {"Address": "user@example.com"},
        "Subject": "Help",
        "RawTextBody": "Body",
        "Recipients": [{"Address": "testslug@tickets.truecore.cloud"}],
    }

    result = process_inbound_email(payload)
    assert result["status"] == "rejected_addon_disabled"


@patch("backend.inbound_email._log_inbound_email")
@patch("backend.inbound_email._check_sender_whitelist", return_value=False)
@patch("backend.inbound_email._check_rate_limit", return_value=True)
@patch("backend.inbound_email._check_addon_enabled", return_value=True)
@patch("backend.inbound_email.execute_query")
def test_process_sender_not_whitelisted(mock_eq, mock_addon, mock_rate, mock_whitelist, mock_log):
    mock_eq.return_value = {"rows": [{"id": 1}]}
    payload = {
        "Sender": {"Address": "blocked@evil.com"},
        "Subject": "Spam",
        "RawTextBody": "Body",
        "Recipients": [{"Address": "testslug@tickets.truecore.cloud"}],
    }

    result = process_inbound_email(payload)
    assert result["status"] == "rejected_sender_not_whitelisted"


@patch("backend.inbound_email._log_inbound_email")
@patch("backend.inbound_email._check_rate_limit", return_value=False)
@patch("backend.inbound_email._check_addon_enabled", return_value=True)
@patch("backend.inbound_email.execute_query")
def test_process_rate_limited(mock_eq, mock_addon, mock_rate, mock_log):
    mock_eq.return_value = {"rows": [{"id": 1}]}
    payload = {
        "Sender": {"Address": "spammer@example.com"},
        "Subject": "Spam",
        "RawTextBody": "Body",
        "Recipients": [{"Address": "testslug@tickets.truecore.cloud"}],
    }

    result = process_inbound_email(payload)
    assert result["status"] == "rejected_rate_limited"
