"""Tests for backend/auth.py — JWT tokens and password hashing."""

import time

import jwt as pyjwt
import pytest
from fastapi import HTTPException

from backend.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


def test_hash_and_verify_password():
    hashed = hash_password("mysecret")
    assert verify_password("mysecret", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("mysecret")
    assert verify_password("wrongpassword", hashed) is False


def test_create_access_token_structure(mock_jwt_secret):
    token = create_access_token(user_id=1, email="test@example.com")
    payload = decode_token(token)
    assert payload["sub"] == 1
    assert payload["email"] == "test@example.com"
    assert "exp" in payload
    assert payload["type"] == "access"


def test_create_refresh_token_structure(mock_jwt_secret):
    token = create_refresh_token(user_id=1)
    payload = decode_token(token)
    assert payload["sub"] == 1
    assert "exp" in payload
    assert payload["type"] == "refresh"


def test_access_token_expiry(mock_jwt_secret):
    token = pyjwt.encode(
        {"sub": 1, "email": "test@example.com", "exp": int(time.time()) - 10, "type": "access"},
        "test-secret-key-for-testing-12345",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401


def test_decode_token_invalid(mock_jwt_secret):
    with pytest.raises(HTTPException) as exc_info:
        decode_token("garbage.token.string")
    assert exc_info.value.status_code == 401


def test_decode_token_valid_roundtrip(mock_jwt_secret):
    token = create_access_token(user_id=42, email="alice@example.com")
    payload = decode_token(token)
    assert payload["sub"] == 42
    assert payload["email"] == "alice@example.com"


def test_refresh_token_has_correct_type(mock_jwt_secret):
    token = create_refresh_token(user_id=1)
    payload = decode_token(token)
    assert payload["type"] == "refresh"
    assert payload["type"] != "access"
