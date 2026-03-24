"""AES-256-GCM encryption/decryption for BYOK API keys."""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.config import KEY_ENCRYPTION_KEY

_IV_BYTES = 12


def _get_aes_key() -> bytes:
    """Derive the 32-byte AES key from the KEY_ENCRYPTION_KEY env var."""
    if not KEY_ENCRYPTION_KEY:
        raise RuntimeError(
            "KEY_ENCRYPTION_KEY is not configured. "
            "Set it in .env to enable BYOK API key storage."
        )
    raw = base64.b64decode(KEY_ENCRYPTION_KEY)
    if len(raw) != 32:
        raise RuntimeError(
            f"KEY_ENCRYPTION_KEY must decode to exactly 32 bytes, got {len(raw)}"
        )
    return raw


def encrypt_api_key(plaintext: str) -> tuple[bytes, bytes]:
    """Encrypt an API key string. Returns (ciphertext, iv)."""
    key = _get_aes_key()
    iv = os.urandom(_IV_BYTES)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
    return ciphertext, iv


def decrypt_api_key(ciphertext: bytes, iv: bytes) -> str:
    """Decrypt an API key. Returns the plaintext string."""
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(iv, ciphertext, None)
    return plaintext.decode("utf-8")


def mask_api_key(key: str) -> str:
    """Return a masked version of an API key showing only the last 4 chars."""
    if len(key) <= 4:
        return "****"
    return "****..." + key[-4:]
