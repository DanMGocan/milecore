"""Inbound email-to-ticket processing for TrueCore.cloud.

Brevo Inbound Parsing POSTs parsed emails to our webhook. This module
extracts the target instance from the TO address, validates the sender,
uses Claude to extract structured fields, and creates a tickets record.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone

from backend.config import (
    INBOUND_EMAIL_DOMAIN,
    INBOUND_EMAIL_RATE_LIMIT_PER_SENDER,
    INBOUND_EMAIL_RATE_LIMIT_WINDOW_MINUTES,
)
from backend.database import execute_query
from backend.email_sender import send_email

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TO-address parsing
# ---------------------------------------------------------------------------

def _parse_instance_from_to(to_address: str) -> str | None:
    """Extract the instance slug from ``{slug}@tickets.truecore.cloud``."""
    if not to_address:
        return None
    # Handle "Name <email>" format
    match = re.search(r"<([^>]+)>", to_address)
    email = match.group(1) if match else to_address.strip()
    email = email.lower()
    domain = INBOUND_EMAIL_DOMAIN.lower()
    if email.endswith(f"@{domain}"):
        slug = email.rsplit("@", 1)[0]
        return slug if slug else None
    return None


# ---------------------------------------------------------------------------
# Addon / whitelist checks
# ---------------------------------------------------------------------------

def _check_addon_enabled(instance_id: int) -> bool:
    """Return True if inbound_email_addon is enabled for the instance."""
    result = execute_query(
        "SELECT inbound_email_addon FROM instances WHERE id = ?",
        [instance_id],
        instance_id=None,
    )
    if result.get("rows"):
        return bool(result["rows"][0]["inbound_email_addon"])
    return False


def _check_sender_whitelist(instance_id: int, sender_email: str) -> bool:
    """Check sender against whitelist. Empty whitelist = accept all."""
    result = execute_query(
        "SELECT pattern, pattern_type FROM inbound_email_senders WHERE instance_id = ?",
        [instance_id],
        instance_id=None,
    )
    rows = result.get("rows", [])
    if not rows:
        return True  # No whitelist entries = accept all

    sender_lower = sender_email.lower()
    sender_domain = sender_lower.rsplit("@", 1)[-1] if "@" in sender_lower else ""

    for row in rows:
        pattern = row["pattern"].lower()
        if row["pattern_type"] == "email" and sender_lower == pattern:
            return True
        if row["pattern_type"] == "domain" and sender_domain == pattern:
            return True

    return False


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def _check_rate_limit(sender_email: str) -> bool:
    """Return True if sender is within rate limit, False if exceeded."""
    window_start = datetime.now(timezone.utc) - timedelta(minutes=INBOUND_EMAIL_RATE_LIMIT_WINDOW_MINUTES)
    result = execute_query(
        "SELECT COUNT(*) as cnt FROM inbound_emails WHERE sender_email = %s AND received_at >= %s",
        [sender_email.lower(), window_start],
        instance_id=None,
    )
    count = result["rows"][0]["cnt"] if result.get("rows") else 0
    return count < INBOUND_EMAIL_RATE_LIMIT_PER_SENDER


# ---------------------------------------------------------------------------
# Claude field extraction
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """You are extracting structured fields from an inbound support email to create a ticket.
Return ONLY a JSON object with these fields:
- title: concise ticket title (max 100 chars)
- description: the problem description
- ticket_type: one of (incident, service_request, question, access_request)
- priority: one of (low, medium, high, critical)"""


def _extract_fields_with_claude(subject: str, body: str, instance_id: int) -> dict:
    """Use Claude to extract structured ticket fields from the email.

    Falls back to raw extraction on quota exhaustion or API error.
    """
    from backend.claude_client import _get_client, _increment_query_count, CLAUDE_MODEL

    # Try to consume a query
    limit_error = _increment_query_count(instance_id)
    if limit_error:
        logger.warning("Query limit reached for instance %d, using raw extraction", instance_id)
        return _raw_extract(subject, body)

    try:
        client = _get_client()
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": f"Subject: {subject}\n\nBody:\n{body}",
            }],
            system=_EXTRACTION_PROMPT,
        )

        text = response.content[0].text if response.content else ""
        # Parse JSON from response — handle markdown code fences
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            text = text.strip()

        fields = json.loads(text)
        return {
            "title": str(fields.get("title", subject))[:100],
            "description": str(fields.get("description", body)),
            "ticket_type": str(fields.get("ticket_type", "incident")),
            "priority": str(fields.get("priority", "medium")),
        }
    except Exception as e:
        logger.error("Claude extraction failed: %s", e)
        return _raw_extract(subject, body)


def _raw_extract(subject: str, body: str) -> dict:
    """Fallback extraction: use email fields directly."""
    return {
        "title": (subject or "Inbound email ticket")[:100],
        "description": body or subject or "",
        "ticket_type": "incident",
        "priority": "medium",
    }


# ---------------------------------------------------------------------------
# Person matching
# ---------------------------------------------------------------------------

def _match_sender_to_person(instance_id: int, sender_email: str) -> dict | None:
    """Try to find a people record matching the sender email.

    Returns ``{"id": ..., "site_id": ...}`` or ``None``.
    """
    result = execute_query(
        "SELECT id, site_id FROM people WHERE LOWER(email) = LOWER(?) LIMIT 1",
        [sender_email],
        instance_id=instance_id,
    )
    if result.get("rows"):
        return result["rows"][0]
    return None


# ---------------------------------------------------------------------------
# Ticket creation
# ---------------------------------------------------------------------------

def _create_ticket(instance_id: int, fields: dict, requester_id: int | None, site_id: int | None) -> int:
    """Insert a tickets record and return its id."""
    result = execute_query(
        "INSERT INTO tickets "
        "(instance_id, ticket_type, title, description, priority, source, requester_person_id, site_id) "
        "VALUES (?, ?, ?, ?, ?, 'email', ?, ?)",
        [
            instance_id,
            fields["ticket_type"],
            fields["title"],
            fields["description"],
            fields["priority"],
            requester_id,
            site_id,
        ],
        instance_id=instance_id,
    )
    return result.get("lastrowid")


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def _log_inbound_email(
    *,
    instance_id: int | None,
    sender_email: str,
    sender_name: str | None,
    subject: str | None,
    body_plain: str | None,
    from_domain: str,
    status: str,
    ticket_id: int | None = None,
    error_message: str | None = None,
    brevo_message_id: str | None = None,
) -> int | None:
    """Insert a row into inbound_emails for audit purposes."""
    result = execute_query(
        "INSERT INTO inbound_emails "
        "(instance_id, sender_email, sender_name, subject, body_plain, from_domain, "
        "status, ticket_id, error_message, brevo_message_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        [
            instance_id,
            sender_email,
            sender_name,
            subject,
            body_plain,
            from_domain,
            status,
            ticket_id,
            error_message,
            brevo_message_id,
        ],
        instance_id=None,
    )
    return result.get("lastrowid")


# ---------------------------------------------------------------------------
# Confirmation email
# ---------------------------------------------------------------------------

def _send_confirmation(sender_email: str, sender_name: str | None, ticket_id: int, subject: str) -> None:
    """Send a confirmation email back to the sender."""
    name = sender_name or "there"
    send_email(
        to_email=sender_email,
        subject=f"Re: {subject or 'Your ticket'}",
        body=(
            f"Hi {name},\n\n"
            f"Your ticket has been created (ticket #{ticket_id}).\n"
            f"Our team will review it and get back to you.\n\n"
            f"Thank you,\nTrueCore Support"
        ),
        to_name=sender_name or "",
    )


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def process_inbound_email(payload: dict) -> dict:
    """Process a Brevo inbound email webhook payload.

    Always returns a dict with at minimum ``{"status": "..."}`` so the
    webhook endpoint can return 200 regardless of outcome.
    """
    # Extract fields from Brevo payload
    sender_info = payload.get("Sender") or payload.get("sender") or {}
    sender_email = (
        sender_info.get("Address")
        or sender_info.get("address")
        or payload.get("From", "")
    ).strip().lower()
    sender_name = sender_info.get("Name") or sender_info.get("name") or ""
    subject = payload.get("Subject") or payload.get("subject") or ""
    body_plain = (
        payload.get("RawTextBody")
        or payload.get("TextBody")
        or payload.get("ExtractedMarkdownBody")
        or ""
    )
    brevo_message_id = payload.get("MessageId") or payload.get("message_id") or ""

    # Determine TO address
    to_list = payload.get("Recipients") or payload.get("recipients") or []
    to_address = ""
    if isinstance(to_list, list) and to_list:
        first = to_list[0]
        to_address = first.get("Address") or first.get("address") or str(first)
    elif isinstance(to_list, str):
        to_address = to_list

    from_domain = sender_email.rsplit("@", 1)[-1] if "@" in sender_email else "unknown"

    # 1. Parse instance slug from TO address
    slug = _parse_instance_from_to(to_address)
    if not slug:
        _log_inbound_email(
            instance_id=None,
            sender_email=sender_email,
            sender_name=sender_name,
            subject=subject,
            body_plain=body_plain,
            from_domain=from_domain,
            status="rejected_instance_not_found",
            error_message=f"Could not parse slug from TO: {to_address}",
            brevo_message_id=brevo_message_id,
        )
        return {"status": "rejected_instance_not_found"}

    # 2. Look up instance
    inst = execute_query(
        "SELECT id FROM instances WHERE slug = ?",
        [slug],
        instance_id=None,
    )
    if not inst.get("rows"):
        _log_inbound_email(
            instance_id=None,
            sender_email=sender_email,
            sender_name=sender_name,
            subject=subject,
            body_plain=body_plain,
            from_domain=from_domain,
            status="rejected_instance_not_found",
            error_message=f"No instance found for slug: {slug}",
            brevo_message_id=brevo_message_id,
        )
        return {"status": "rejected_instance_not_found"}

    instance_id = inst["rows"][0]["id"]

    # 3. Check addon enabled
    if not _check_addon_enabled(instance_id):
        _log_inbound_email(
            instance_id=instance_id,
            sender_email=sender_email,
            sender_name=sender_name,
            subject=subject,
            body_plain=body_plain,
            from_domain=from_domain,
            status="rejected_addon_disabled",
            brevo_message_id=brevo_message_id,
        )
        return {"status": "rejected_addon_disabled"}

    # 4. Rate limit
    if not _check_rate_limit(sender_email):
        _log_inbound_email(
            instance_id=instance_id,
            sender_email=sender_email,
            sender_name=sender_name,
            subject=subject,
            body_plain=body_plain,
            from_domain=from_domain,
            status="rejected_rate_limited",
            brevo_message_id=brevo_message_id,
        )
        return {"status": "rejected_rate_limited"}

    # 5. Check sender whitelist
    if not _check_sender_whitelist(instance_id, sender_email):
        _log_inbound_email(
            instance_id=instance_id,
            sender_email=sender_email,
            sender_name=sender_name,
            subject=subject,
            body_plain=body_plain,
            from_domain=from_domain,
            status="rejected_sender_not_whitelisted",
            brevo_message_id=brevo_message_id,
        )
        return {"status": "rejected_sender_not_whitelisted"}

    # 6. Extract fields with Claude
    try:
        fields = _extract_fields_with_claude(subject, body_plain, instance_id)
    except Exception as e:
        logger.error("Field extraction error: %s", e)
        fields = _raw_extract(subject, body_plain)

    # 7. Match sender to person
    person_match = _match_sender_to_person(instance_id, sender_email)
    requester_id = person_match["id"] if person_match else None
    site_id = person_match["site_id"] if person_match else None

    # 8. Create ticket
    try:
        ticket_id = _create_ticket(instance_id, fields, requester_id, site_id)
    except Exception as e:
        _log_inbound_email(
            instance_id=instance_id,
            sender_email=sender_email,
            sender_name=sender_name,
            subject=subject,
            body_plain=body_plain,
            from_domain=from_domain,
            status="error",
            error_message=str(e),
            brevo_message_id=brevo_message_id,
        )
        return {"status": "error", "error": str(e)}

    # 9. Log success
    _log_inbound_email(
        instance_id=instance_id,
        sender_email=sender_email,
        sender_name=sender_name,
        subject=subject,
        body_plain=body_plain,
        from_domain=from_domain,
        status="processed",
        ticket_id=ticket_id,
        brevo_message_id=brevo_message_id,
    )

    # 10. Send confirmation (best effort)
    try:
        _send_confirmation(sender_email, sender_name, ticket_id, subject)
    except Exception as e:
        logger.warning("Failed to send confirmation email: %s", e)

    return {"status": "processed", "ticket_id": ticket_id}
