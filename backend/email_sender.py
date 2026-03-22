import os
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from email import encoders

from backend.config import (
    BREVO_SMTP_HOST,
    BREVO_SMTP_PORT,
    BREVO_SMTP_LOGIN,
    BREVO_SMTP_PASSWORD,
    BREVO_SENDER_EMAIL,
    BREVO_SENDER_NAME,
)


def send_email(
    to_email: str,
    subject: str,
    body: str,
    to_name: str = "",
    reply_to_address: str = "",
    message_id: str = "",
    in_reply_to: str = "",
    references: str = "",
    cc_emails: list[str] | None = None,
    attachments: list[dict] | None = None,
) -> dict:
    """Send an email via Brevo SMTP.

    When *attachments* is provided, the message is sent as MIME multipart
    with the body as a text part and each attachment as a binary part.
    Each attachment dict: {"path": str, "filename": str, "content_type": str}.

    Threading headers (message_id, in_reply_to, references) enable email
    clients to group messages into conversation threads.
    """
    if not BREVO_SMTP_LOGIN or not BREVO_SMTP_PASSWORD or not BREVO_SENDER_EMAIL:
        return {"error": "Email not configured — BREVO_SMTP_* environment variables are missing"}

    if attachments:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, "plain"))
        for att in attachments:
            if not os.path.isfile(att["path"]):
                continue
            maintype, _, subtype = att["content_type"].partition("/")
            part = MIMEBase(maintype, subtype or "octet-stream")
            with open(att["path"], "rb") as f:
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment", filename=att["filename"])
            msg.attach(part)
    else:
        msg = MIMEText(body, "plain")

    msg["From"] = formataddr((BREVO_SENDER_NAME, BREVO_SENDER_EMAIL))
    msg["To"] = formataddr((to_name, to_email)) if to_name else to_email
    msg["Subject"] = subject

    if cc_emails:
        msg["Cc"] = ", ".join(cc_emails)
    if reply_to_address:
        msg["Reply-To"] = reply_to_address
    if message_id:
        msg["Message-ID"] = message_id
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references

    all_recipients = [to_email] + (cc_emails or [])

    try:
        with smtplib.SMTP(BREVO_SMTP_HOST, BREVO_SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(BREVO_SMTP_LOGIN, BREVO_SMTP_PASSWORD)
            server.send_message(msg, to_addrs=all_recipients)
        return {"success": True}
    except smtplib.SMTPException as e:
        return {"error": f"SMTP error: {e}"}
    except OSError as e:
        return {"error": f"Email failed: {e}"}
