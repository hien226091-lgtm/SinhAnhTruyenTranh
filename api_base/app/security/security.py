"""Security helpers for hashing passwords and issuing JWT tokens."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from typing import Any, Dict


import jwt

from api_base.app.config import CONFIG


@dataclass(frozen=True)
class TokenPayload:
    """Decoded JWT payload data."""

    sub: str
    exp: datetime


def _hash_raw(password: str, salt: str) -> str:
    """Hash a password using PBKDF2 for storage/verification."""
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    )
    return dk.hex()


def hash_password(password: str) -> str:
    """Create a salted hash of a password for storage."""
    return _hash_raw(password, CONFIG.password_salt)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plain password against a stored hash."""
    if not hashed:
        return False
    expected = _hash_raw(password, CONFIG.password_salt)
    return hmac.compare_digest(expected, hashed)


def create_access_token(subject: str) -> str:
    """Create a JWT token for a subject identifier."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=CONFIG.jwt_exp_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, CONFIG.jwt_secret, algorithm=CONFIG.jwt_algorithm)


def decode_access_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token."""
    payload: Dict[str, Any] = jwt.decode(
        token,
        CONFIG.jwt_secret,
        algorithms=[CONFIG.jwt_algorithm],
    )
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    return TokenPayload(sub=str(payload.get("sub", "")), exp=exp)
