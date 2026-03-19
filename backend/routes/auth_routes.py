"""Authentication endpoints: signup, login, logout, refresh, Google OAuth."""

from __future__ import annotations

import re
import urllib.parse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from backend.auth import (
    AuthUser,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.config import (
    APP_URL,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
)
from backend.database import execute_query
from backend.stripe_billing import create_stripe_customer

router = APIRouter(prefix="/auth")

# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------

_COOKIE_DEFAULTS = {
    "httponly": True,
    "samesite": "lax",
    "secure": False,  # localhost dev
    "path": "/",
}


def _set_auth_cookies(response: JSONResponse, user_id: int, email: str) -> None:
    """Create access + refresh tokens and attach them as cookies."""
    access = create_access_token(user_id, email)
    refresh = create_refresh_token(user_id)
    response.set_cookie("access_token", access, **_COOKIE_DEFAULTS)
    response.set_cookie("refresh_token", refresh, **_COOKIE_DEFAULTS)


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class SignupBody(BaseModel):
    email: str
    password: str
    display_name: str


class LoginBody(BaseModel):
    email: str
    password: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/signup")
async def signup(body: SignupBody):
    """Register a new user."""
    # Validate email format
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", body.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    # Validate password length
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    email = body.email.lower().strip()

    # Check if email already registered
    existing = execute_query(
        "SELECT id FROM auth_users WHERE email = ?",
        [email],
        instance_id=None,
    )
    if existing.get("rows"):
        raise HTTPException(status_code=409, detail="Email already registered")

    # Hash password and insert
    hashed = hash_password(body.password)
    result = execute_query(
        "INSERT INTO auth_users (email, password_hash, display_name, email_verified) VALUES (?, ?, ?, false)",
        [email, hashed, body.display_name.strip()],
        instance_id=None,
    )
    if "error" in result:
        raise HTTPException(status_code=500, detail=f"Registration failed: {result['error']}")

    user_id = result["lastrowid"]

    # Create Stripe customer on signup
    try:
        create_stripe_customer(user_id, email, body.display_name.strip())
    except Exception as e:
        print(f"Warning: Stripe customer creation failed for user {user_id}: {e}")

    response = JSONResponse(
        content={
            "id": user_id,
            "email": email,
            "display_name": body.display_name.strip(),
        },
        status_code=201,
    )
    _set_auth_cookies(response, user_id, email)
    return response


@router.post("/login")
async def login(body: LoginBody):
    """Authenticate with email + password."""
    email = body.email.lower().strip()

    result = execute_query(
        "SELECT id, email, password_hash, display_name FROM auth_users WHERE email = ?",
        [email],
        instance_id=None,
    )
    if not result.get("rows"):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = result["rows"][0]

    if not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="This account uses Google sign-in")

    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    response = JSONResponse(
        content={
            "id": user["id"],
            "email": user["email"],
            "display_name": user["display_name"],
        }
    )
    _set_auth_cookies(response, user["id"], user["email"])
    return response


@router.post("/logout")
async def logout():
    """Clear all auth cookies."""
    response = JSONResponse(content={"message": "Logged out"})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    response.delete_cookie("instance_id", path="/")
    return response


@router.post("/refresh")
async def refresh(request: Request):
    """Issue a new access token from a valid refresh token."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")

    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload["sub"]

    # Look up user to get current email
    result = execute_query(
        "SELECT email FROM auth_users WHERE id = ?",
        [user_id],
        instance_id=None,
    )
    if not result.get("rows"):
        raise HTTPException(status_code=401, detail="User not found")

    email = result["rows"][0]["email"]
    new_access = create_access_token(user_id, email)

    response = JSONResponse(content={"message": "Token refreshed"})
    response.set_cookie("access_token", new_access, **_COOKIE_DEFAULTS)
    return response


@router.get("/me")
async def me(user: AuthUser = Depends(get_current_user)):
    """Return current user info and their instances."""
    # Fetch full user record
    user_result = execute_query(
        "SELECT id, email, display_name, email_verified, created_at FROM auth_users WHERE id = ?",
        [user.id],
        instance_id=None,
    )
    if not user_result.get("rows"):
        raise HTTPException(status_code=404, detail="User not found")

    user_row = user_result["rows"][0]

    # Fetch instances the user belongs to
    instances_result = execute_query(
        "SELECT i.id, i.name, i.slug, i.tier, m.role "
        "FROM instance_memberships m "
        "JOIN instances i ON i.id = m.instance_id "
        "WHERE m.auth_user_id = ?",
        [user.id],
        instance_id=None,
    )
    instances = instances_result.get("rows", [])

    return {
        "id": user_row["id"],
        "email": user_row["email"],
        "display_name": user_row["display_name"],
        "email_verified": user_row["email_verified"],
        "created_at": str(user_row["created_at"]) if user_row.get("created_at") else None,
        "instances": instances,
    }


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/google")
async def google_login():
    """Redirect to Google OAuth authorization page."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_callback(code: str | None = None, error: str | None = None):
    """Handle Google OAuth callback."""
    if error:
        return RedirectResponse(url=f"{APP_URL}/login?error={error}")

    if not code:
        return RedirectResponse(url=f"{APP_URL}/login?error=no_code")

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": GOOGLE_REDIRECT_URI,
            },
        )

    if token_resp.status_code != 200:
        return RedirectResponse(url=f"{APP_URL}/login?error=token_exchange_failed")

    tokens = token_resp.json()
    google_access_token = tokens.get("access_token")
    if not google_access_token:
        return RedirectResponse(url=f"{APP_URL}/login?error=no_access_token")

    # Get user profile
    async with httpx.AsyncClient() as client:
        profile_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_access_token}"},
        )

    if profile_resp.status_code != 200:
        return RedirectResponse(url=f"{APP_URL}/login?error=profile_fetch_failed")

    profile = profile_resp.json()
    google_email = profile.get("email", "").lower().strip()
    google_name = profile.get("name", google_email.split("@")[0])
    google_id = profile.get("id", "")

    if not google_email:
        return RedirectResponse(url=f"{APP_URL}/login?error=no_email")

    # Check if user exists
    existing = execute_query(
        "SELECT id, email, display_name FROM auth_users WHERE email = ?",
        [google_email],
        instance_id=None,
    )

    if existing.get("rows"):
        # Existing user -- link Google ID if not already set
        user = existing["rows"][0]
        user_id = user["id"]
        execute_query(
            "UPDATE auth_users SET google_id = ?, email_verified = true WHERE id = ? AND google_id IS NULL",
            [google_id, user_id],
            instance_id=None,
        )
    else:
        # New user via Google
        result = execute_query(
            "INSERT INTO auth_users (email, display_name, google_id, email_verified) VALUES (?, ?, ?, true)",
            [google_email, google_name, google_id],
            instance_id=None,
        )
        if "error" in result:
            return RedirectResponse(url=f"{APP_URL}/login?error=registration_failed")
        user_id = result["lastrowid"]

        # Create Stripe customer on Google signup
        try:
            create_stripe_customer(user_id, google_email, google_name)
        except Exception as e:
            print(f"Warning: Stripe customer creation failed for user {user_id}: {e}")

    # Set JWT cookies and redirect to frontend
    response = RedirectResponse(url=f"{APP_URL}/")
    access = create_access_token(user_id, google_email)
    refresh = create_refresh_token(user_id)
    response.set_cookie("access_token", access, **_COOKIE_DEFAULTS)
    response.set_cookie("refresh_token", refresh, **_COOKIE_DEFAULTS)
    return response
