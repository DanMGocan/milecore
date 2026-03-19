"""Tests for backend/email_sender.py — SMTP mocking."""

import smtplib
from unittest.mock import patch

from backend.email_sender import send_email


@patch("backend.email_sender.BREVO_SMTP_LOGIN", "")
@patch("backend.email_sender.BREVO_SMTP_PASSWORD", "")
@patch("backend.email_sender.BREVO_SENDER_EMAIL", "")
def test_not_configured():
    result = send_email(to_email="test@example.com", subject="Test", body="Hello")
    assert "error" in result
    assert "not configured" in result["error"]


@patch("smtplib.SMTP")
def test_send_success(mock_smtp_cls, mock_smtp_config):
    mock_server = mock_smtp_cls.return_value.__enter__.return_value

    result = send_email(to_email="test@example.com", subject="Test", body="Hello")

    assert result == {"success": True}
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once()
    mock_server.send_message.assert_called_once()


@patch("smtplib.SMTP")
def test_smtp_error(mock_smtp_cls, mock_smtp_config):
    mock_server = mock_smtp_cls.return_value.__enter__.return_value
    mock_server.send_message.side_effect = smtplib.SMTPException("Connection refused")

    result = send_email(to_email="test@example.com", subject="Test", body="Hello")

    assert "error" in result
    assert "SMTP error" in result["error"]
