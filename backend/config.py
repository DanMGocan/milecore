import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_API_KEY_SPARE = os.getenv("ANTHROPIC_API_KEY_SPARE")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://truecore:truecore@localhost:5432/truecore")
SCHEMA_PATH = os.getenv("SCHEMA_PATH", "schema_pg.sql")

# Legacy (kept for backward compatibility during migration)
DATABASE_PATH = os.getenv("DATABASE_PATH", "milecore.db")

# JWT Authentication
JWT_SECRET = os.getenv("JWT_SECRET", "")
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

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]

APP_URL = os.getenv("APP_URL", "http://localhost:8000")

# Stripe Billing
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_USER_SEAT = os.getenv("STRIPE_PRICE_USER_SEAT", "")
STRIPE_PRICE_EMAIL_ADDON = os.getenv("STRIPE_PRICE_EMAIL_ADDON", "")
STRIPE_PRICE_DAILY_REPORTS_ADDON = os.getenv("STRIPE_PRICE_DAILY_REPORTS_ADDON", "")
STRIPE_PRICE_QUERY_PACK = os.getenv("STRIPE_PRICE_QUERY_PACK", "")
