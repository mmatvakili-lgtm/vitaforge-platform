"""Verification codes / reset tokens are DERIVED from a random nonce with a server-side key, so the outbox only stores the nonce and the
token table only stores a SHA-256 of the value. Neither raw values nor anything that recovers them without the server secret is persisted.
Rotating DJANGO_SECRET_KEY therefore invalidates still-unsent messages (the user simply requests a new one)."""
from __future__ import annotations

import hashlib
import hmac
import secrets

VERIFY_TTL = 30 * 60
RESET_TTL = 30 * 60
MAX_VERIFY_ATTEMPTS = 5


def _key(secret: str) -> bytes:
    return hmac.new(secret.encode(), b"vitaforge/mail/v1", hashlib.sha256).digest()


def new_nonce() -> str:
    return secrets.token_hex(16)                                    # 128 bits


def derive_code(secret: str, uid: str, nonce: str) -> str:
    d = hmac.new(_key(secret), f"verify|{uid}|{nonce}".encode(), hashlib.sha256).digest()
    return f"{int.from_bytes(d[:8], 'big') % 10**6:06d}"           # 6 digits; guarded by attempt limit + expiry


def derive_reset_token(secret: str, nonce: str) -> str:
    d = hmac.new(_key(secret), f"reset|{nonce}".encode(), hashlib.sha256).hexdigest()
    return d                                                        # 256 bits


def digest(value: str) -> str:
    return hashlib.sha256((value or "").encode()).hexdigest()
