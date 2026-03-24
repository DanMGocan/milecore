import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_API_KEY_SPARE = os.getenv("ANTHROPIC_API_KEY_SPARE")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://truecore:truecore@localhost:5432/truecore")
SCHEMA_PATH = os.getenv("SCHEMA_PATH", "schema_pg.sql")

# JWT Authentication
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")

BREVO_SMTP_HOST = os.getenv("BREVO_SMTP_HOST", "smtp-relay.brevo.com")
BREVO_SMTP_PORT = int(os.getenv("BREVO_SMTP_PORT", "587"))
BREVO_SMTP_LOGIN = os.getenv("BREVO_SMTP_LOGIN", "")
BREVO_SMTP_PASSWORD = os.getenv("BREVO_SMTP_PASSWORD", "")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "")

DAILY_REPORT_HOUR = int(os.getenv("DAILY_REPORT_HOUR", "7"))
DAILY_REPORT_MINUTE = int(os.getenv("DAILY_REPORT_MINUTE", "0"))
MAINTENANCE_CHECK_INTERVAL_SECONDS = int(os.getenv("MAINTENANCE_CHECK_INTERVAL_SECONDS", "300"))

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]

APP_URL = os.getenv("APP_URL", "http://localhost:8000")

# Stripe Billing
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_USER_SEAT = os.getenv("STRIPE_PRICE_USER_SEAT", "")
STRIPE_PRICE_QUERY_TIER = os.getenv("STRIPE_PRICE_QUERY_TIER", "")
STRIPE_PRICE_BYOK_USER_SEAT = os.getenv("STRIPE_PRICE_BYOK_USER_SEAT", "")
STRIPE_PRICE_EMAIL_ADDON = os.getenv("STRIPE_PRICE_EMAIL_ADDON", "")
STRIPE_PRICE_DAILY_REPORTS_ADDON = os.getenv("STRIPE_PRICE_DAILY_REPORTS_ADDON", "")
STRIPE_PRICE_QUERY_PACK = os.getenv("STRIPE_PRICE_QUERY_PACK", "")
STRIPE_PRICE_INBOUND_EMAIL_ADDON = os.getenv("STRIPE_PRICE_INBOUND_EMAIL_ADDON", "")
STRIPE_PRICE_BOOKINGS_ADDON = os.getenv("STRIPE_PRICE_BOOKINGS_ADDON", "")

# BYOK API key encryption
KEY_ENCRYPTION_KEY = os.getenv("KEY_ENCRYPTION_KEY", "")

# Chat rate limiting (requests per minute per instance)
CHAT_RATE_LIMIT_PER_MINUTE = int(os.getenv("CHAT_RATE_LIMIT_PER_MINUTE", "100"))

# Inbound Email
BREVO_INBOUND_WEBHOOK_SECRET = os.getenv("BREVO_INBOUND_WEBHOOK_SECRET", "")
INBOUND_EMAIL_RATE_LIMIT_PER_SENDER = int(os.getenv("INBOUND_EMAIL_RATE_LIMIT_PER_SENDER", "20"))
INBOUND_EMAIL_RATE_LIMIT_WINDOW_MINUTES = int(os.getenv("INBOUND_EMAIL_RATE_LIMIT_WINDOW_MINUTES", "60"))
INBOUND_EMAIL_DOMAIN = os.getenv("INBOUND_EMAIL_DOMAIN", "tickets.truecore.cloud")
INBOUND_BOOKING_EMAIL_PREFIX = os.getenv("INBOUND_BOOKING_EMAIL_PREFIX", "book-")

# Token-based query metering
QUERY_TOKEN_THRESHOLD = int(os.getenv("QUERY_TOKEN_THRESHOLD", "80000"))

# Token optimization: conversation history and result caps
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))
MAX_TOOL_RESULT_CHARS = int(os.getenv("MAX_TOOL_RESULT_CHARS", "32000"))

# Email rate limiting (outbound via chat tool)
EMAIL_RATE_LIMIT_PER_HOUR = int(os.getenv("EMAIL_RATE_LIMIT_PER_HOUR", "20"))

# S3-compatible Object Storage
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
S3_BUCKET = os.getenv("S3_BUCKET", "truecore-attachments")
S3_REGION = os.getenv("S3_REGION", "nbg1")

# Attachments (images only — stored in S3)
TICKET_ATTACHMENTS_DIR = os.getenv("TICKET_ATTACHMENTS_DIR", "ticket_attachments")
CHAT_ATTACHMENTS_DIR = os.getenv("CHAT_ATTACHMENTS_DIR", "chat_attachments")
TICKET_ATTACHMENT_MAX_SIZE_MB = int(os.getenv("TICKET_ATTACHMENT_MAX_SIZE_MB", "25"))
TICKET_ATTACHMENT_ALLOWED_TYPES = os.getenv(
    "TICKET_ATTACHMENT_ALLOWED_TYPES",
    "image/jpeg,image/png,image/gif,image/webp,image/avif,image/bmp,image/tiff,image/svg+xml",
).split(",")

# Platform admin
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "gocandan@gmail.com")
