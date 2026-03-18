import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_API_KEY_SPARE = os.getenv("ANTHROPIC_API_KEY_SPARE")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
DATABASE_PATH = os.getenv("DATABASE_PATH", "milecore.db")
SCHEMA_PATH = os.getenv("SCHEMA_PATH", "schema.sql")

BREVO_SMTP_HOST = os.getenv("BREVO_SMTP_HOST", "smtp-relay.brevo.com")
BREVO_SMTP_PORT = int(os.getenv("BREVO_SMTP_PORT", "587"))
BREVO_SMTP_LOGIN = os.getenv("BREVO_SMTP_LOGIN", "")
BREVO_SMTP_PASSWORD = os.getenv("BREVO_SMTP_PASSWORD", "")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "")

DAILY_REPORT_HOUR = int(os.getenv("DAILY_REPORT_HOUR", "7"))
DAILY_REPORT_MINUTE = int(os.getenv("DAILY_REPORT_MINUTE", "0"))

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]

APP_URL = os.getenv("APP_URL", "http://localhost:8000")
