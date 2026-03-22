"""Shared test fixtures and helpers."""

import os

# Set test environment variables before any backend imports.
# These must be present before backend.config is imported (which happens
# transitively when any backend module is loaded).
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")

import pytest
from unittest.mock import patch

# JWT secret must be 32+ bytes to avoid InsecureKeyLengthWarning with HS256.
TEST_JWT_SECRET = "test-secret-key-for-testing-12345"


@pytest.fixture
def mock_jwt_secret():
    """Patch JWT_SECRET at the import site (backend.auth) to a known test value."""
    with patch("backend.auth.JWT_SECRET", TEST_JWT_SECRET):
        yield TEST_JWT_SECRET


@pytest.fixture
def mock_stripe_config():
    """Patch Stripe config values so _stripe_configured() returns True."""
    with patch("backend.stripe_billing.STRIPE_SECRET_KEY", "sk_test_xxx"), \
         patch("backend.stripe_billing.STRIPE_PRICE_USER_SEAT", "price_seat_xxx"), \
         patch("backend.stripe_billing.STRIPE_PRICE_EMAIL_ADDON", "price_email_xxx"), \
         patch("backend.stripe_billing.STRIPE_PRICE_DAILY_REPORTS_ADDON", "price_reports_xxx"), \
         patch("backend.stripe_billing.STRIPE_PRICE_QUERY_PACK", "price_pack_xxx"):
        yield


@pytest.fixture
def mock_smtp_config():
    """Patch BREVO SMTP config values to non-empty test values."""
    with patch("backend.email_sender.BREVO_SMTP_LOGIN", "test-login"), \
         patch("backend.email_sender.BREVO_SMTP_PASSWORD", "test-password"), \
         patch("backend.email_sender.BREVO_SENDER_EMAIL", "test@sender.com"), \
         patch("backend.email_sender.BREVO_SENDER_NAME", "Test Sender"), \
         patch("backend.email_sender.BREVO_SMTP_HOST", "smtp.test.com"), \
         patch("backend.email_sender.BREVO_SMTP_PORT", 587):
        yield


@pytest.fixture
def mock_ticket_attachments_dir(tmp_path):
    """Patch TICKET_ATTACHMENTS_DIR to a temp directory."""
    with patch("backend.config.TICKET_ATTACHMENTS_DIR", str(tmp_path / "ticket_attachments")):
        yield tmp_path / "ticket_attachments"


@pytest.fixture
def mock_chat_attachments_dir(tmp_path):
    """Patch CHAT_ATTACHMENTS_DIR to a temp directory."""
    with patch("backend.config.CHAT_ATTACHMENTS_DIR", str(tmp_path / "chat_attachments")):
        yield tmp_path / "chat_attachments"


@pytest.fixture
def mock_s3_client():
    """Patch the S3 client singleton in s3_storage."""
    from unittest.mock import MagicMock
    mock_client = MagicMock()
    with patch("backend.s3_storage._s3_client", mock_client):
        yield mock_client
