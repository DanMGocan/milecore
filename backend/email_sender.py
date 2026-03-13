import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from backend.config import (
    BREVO_SMTP_HOST,
    BREVO_SMTP_PORT,
    BREVO_SMTP_LOGIN,
    BREVO_SMTP_PASSWORD,
    BREVO_SENDER_EMAIL,
    BREVO_SENDER_NAME,
)


def send_email(to_email: str, subject: str, body: str, to_name: str = "") -> dict:
    """Send a plain-text email via Brevo SMTP."""
    if not BREVO_SMTP_LOGIN or not BREVO_SMTP_PASSWORD or not BREVO_SENDER_EMAIL:
        return {"error": "Email not configured — BREVO_SMTP_* environment variables are missing"}

    msg = MIMEText(body, "plain")
    msg["From"] = formataddr((BREVO_SENDER_NAME, BREVO_SENDER_EMAIL))
    msg["To"] = formataddr((to_name, to_email)) if to_name else to_email
    msg["Subject"] = subject

    try:
        with smtplib.SMTP(BREVO_SMTP_HOST, BREVO_SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(BREVO_SMTP_LOGIN, BREVO_SMTP_PASSWORD)
            server.send_message(msg)
        return {"success": True}
    except smtplib.SMTPException as e:
        return {"error": f"SMTP error: {e}"}
    except OSError as e:
        return {"error": f"Email failed: {e}"}
