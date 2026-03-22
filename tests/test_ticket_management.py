"""Tests for ticket management: replies, watchers, timeline, email attachments."""

import os
import json
import tempfile
from unittest.mock import patch, MagicMock, call

from backend.inbound_email import _process_reply


# --- Inbound reply processing ------------------------------------------------

@patch("backend.inbound_email.send_email")
@patch("backend.inbound_email.execute_query")
def test_process_reply_existing_ticket(mock_eq, mock_send):
    """Inbound reply to an existing ticket inserts into ticket_replies and ticket_timeline."""
    mock_eq.side_effect = [
        # 1. SELECT ticket
        {"rows": [{"id": 5, "title": "Broken printer", "email_thread_id": "<thread@test>"}]},
        # 2. Match sender to person
        {"rows": [{"id": 10, "site_id": 1}]},
        # 3. INSERT ticket_replies
        {"lastrowid": 1},
        # 4. INSERT ticket_timeline
        {"lastrowid": 2},
        # 5. SELECT watchers
        {"rows": []},
    ]

    result = _process_reply(
        instance_id=1,
        ticket_id=5,
        sender_email="user@test.com",
        sender_name="Test User",
        body_plain="This is my reply",
    )

    assert result["status"] == "reply_processed"
    assert result["ticket_id"] == 5

    # Verify ticket_replies INSERT was called with 'inbound' direction in the SQL
    replies_call = mock_eq.call_args_list[2]
    assert "ticket_replies" in replies_call[0][0]
    assert "'inbound'" in replies_call[0][0]


@patch("backend.inbound_email.send_email")
@patch("backend.inbound_email.execute_query")
def test_process_reply_nonexistent_ticket(mock_eq, mock_send):
    """Reply to a ticket that doesn't exist returns error."""
    mock_eq.return_value = {"rows": []}

    result = _process_reply(
        instance_id=1,
        ticket_id=999,
        sender_email="user@test.com",
        sender_name="Test User",
        body_plain="Reply to nothing",
    )

    assert result["status"] == "error"
    assert "not found" in result["error"]


@patch("backend.inbound_email.send_email")
@patch("backend.inbound_email.execute_query")
def test_process_reply_notifies_watchers(mock_eq, mock_send):
    """Inbound reply notifies watchers via email."""
    mock_eq.side_effect = [
        # 1. SELECT ticket
        {"rows": [{"id": 5, "title": "Issue", "email_thread_id": "<thread@test>"}]},
        # 2. Match sender to person
        {"rows": []},
        # 3. INSERT ticket_replies
        {"lastrowid": 1},
        # 4. INSERT ticket_timeline
        {"lastrowid": 2},
        # 5. SELECT watchers - two watchers
        {"rows": [{"email": "watcher1@test.com", "first_name": "W1"}, {"email": "watcher2@test.com", "first_name": "W2"}]},
    ]

    _process_reply(
        instance_id=1,
        ticket_id=5,
        sender_email="user@test.com",
        sender_name="Test User",
        body_plain="Here is my update",
    )

    # send_email should have been called for watcher notification
    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args
    assert call_kwargs[1]["to_email"] == "watcher1@test.com"
    assert call_kwargs[1]["cc_emails"] == ["watcher2@test.com"]


# --- Email sender attachments ------------------------------------------------

@patch("smtplib.SMTP")
def test_send_email_with_attachments(mock_smtp, mock_smtp_config):
    """send_email with attachments uses MIMEMultipart."""
    from backend.email_sender import send_email

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"fake image data")
        tmp_path = f.name

    try:
        result = send_email(
            to_email="test@test.com",
            subject="With attachment",
            body="See attached",
            attachments=[{"path": tmp_path, "filename": "test.png", "content_type": "image/png"}],
        )
        assert result.get("success") is True
        # Verify SMTP was used
        mock_smtp.return_value.__enter__.return_value.send_message.assert_called_once()
    finally:
        os.unlink(tmp_path)


@patch("smtplib.SMTP")
def test_send_email_without_attachments(mock_smtp, mock_smtp_config):
    """send_email without attachments still works (backward compat)."""
    from backend.email_sender import send_email

    result = send_email(
        to_email="test@test.com",
        subject="No attachment",
        body="Plain email",
    )
    assert result.get("success") is True


@patch("smtplib.SMTP")
def test_send_email_with_cc(mock_smtp, mock_smtp_config):
    """send_email sends to all recipients including CC."""
    from backend.email_sender import send_email

    result = send_email(
        to_email="main@test.com",
        subject="CC test",
        body="Testing CC",
        cc_emails=["cc1@test.com", "cc2@test.com"],
    )
    assert result.get("success") is True
    send_call = mock_smtp.return_value.__enter__.return_value.send_message
    send_call.assert_called_once()
    _, kwargs = send_call.call_args
    assert "cc1@test.com" in kwargs["to_addrs"]
    assert "cc2@test.com" in kwargs["to_addrs"]


@patch("smtplib.SMTP")
def test_send_email_threading_headers(mock_smtp, mock_smtp_config):
    """send_email includes threading headers when provided."""
    from backend.email_sender import send_email

    result = send_email(
        to_email="test@test.com",
        subject="Thread test",
        body="Threaded reply",
        in_reply_to="<original@test.com>",
        references="<original@test.com>",
        reply_to_address="slug+5@tickets.truecore.cloud",
    )
    assert result.get("success") is True


# --- Upload file validation ---------------------------------------------------

def test_upload_file_validates_type():
    """upload_file allows images only, rejects other types."""
    from backend.config import TICKET_ATTACHMENT_ALLOWED_TYPES
    assert "image/jpeg" in TICKET_ATTACHMENT_ALLOWED_TYPES
    assert "image/png" in TICKET_ATTACHMENT_ALLOWED_TYPES
    assert "image/gif" in TICKET_ATTACHMENT_ALLOWED_TYPES
    assert "image/svg+xml" in TICKET_ATTACHMENT_ALLOWED_TYPES
    # Videos and PDFs no longer allowed
    assert "video/mp4" not in TICKET_ATTACHMENT_ALLOWED_TYPES
    assert "application/pdf" not in TICKET_ATTACHMENT_ALLOWED_TYPES
    assert "application/zip" not in TICKET_ATTACHMENT_ALLOWED_TYPES


def test_upload_file_validates_size():
    """Default max size is 25 MB."""
    from backend.config import TICKET_ATTACHMENT_MAX_SIZE_MB
    assert TICKET_ATTACHMENT_MAX_SIZE_MB == 25


# --- Chat attachment path resolution -----------------------------------------

def test_get_chat_attachment_path_not_found():
    """get_chat_attachment_path returns None for unknown file_id."""
    from backend.routes.upload import get_chat_attachment_path
    result = get_chat_attachment_path("nonexistent-id", 999)
    assert result is None


def test_get_chat_attachment_path_found():
    """get_chat_attachment_path returns metadata for existing file."""
    from backend.routes.upload import get_chat_attachment_path, _META_DIR

    meta = {"s3_key": "chat/999/test-file-id.avif", "filename": "test.png", "content_type": "image/avif", "file_size_bytes": 100}
    meta_path = os.path.join(_META_DIR, "test-file-id.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f)

    try:
        result = get_chat_attachment_path("test-file-id", 999)
        assert result is not None
        assert result["filename"] == "test.png"
        assert result["s3_key"] == "chat/999/test-file-id.avif"
    finally:
        os.unlink(meta_path)
