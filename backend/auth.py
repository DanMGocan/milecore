"""Authentication utilities: JWT tokens, password hashing, FastAPI dependencies."""

from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Any

import bcrypt
import jwt
from fastapi import Request, HTTPException

from backend.config import JWT_SECRET, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_REFRESH_TOKEN_EXPIRE_DAYS
from backend.database import execute_query


@dataclass
class AuthUser:
    id: int
    email: str
    display_name: str


@dataclass
class InstanceContext:
    auth_user_id: int
    instance_id: int
    role: str           # 'owner' | 'admin' | 'user'
    person_id: int | None
    email: str
    display_name: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user_id: int, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": int(time.time()) + JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    payload = {
        "sub": user_id,
        "exp": int(time.time()) + JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "type": "refresh",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises HTTPException on failure."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"verify_sub": False})
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(request: Request) -> AuthUser:
    """FastAPI dependency: extract user from access_token cookie."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    return AuthUser(id=payload["sub"], email=payload["email"], display_name="")


async def get_current_instance(request: Request) -> InstanceContext:
    """FastAPI dependency: extract user + instance from cookies. Validates membership."""
    user = await get_current_user(request)

    instance_id_str = request.cookies.get("instance_id")
    if not instance_id_str:
        raise HTTPException(status_code=400, detail="No instance selected")

    try:
        instance_id = int(instance_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid instance_id")

    # Verify membership
    result = execute_query(
        "SELECT role, person_id FROM instance_memberships WHERE auth_user_id = ? AND instance_id = ?",
        [user.id, instance_id],
        instance_id=None,  # global table, no RLS
    )
    if not result.get("rows"):
        raise HTTPException(status_code=403, detail="Not a member of this instance")

    membership = result["rows"][0]

    # Get display_name
    user_result = execute_query(
        "SELECT display_name FROM auth_users WHERE id = ?",
        [user.id],
        instance_id=None,
    )
    display_name = user_result["rows"][0]["display_name"] if user_result.get("rows") else ""

    return InstanceContext(
        auth_user_id=user.id,
        instance_id=instance_id,
        role=membership["role"],
        person_id=membership["person_id"],
        email=user.email,
        display_name=display_name,
    )
