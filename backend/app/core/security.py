from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from datetime import datetime, timedelta
from hmac import compare_digest
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.models.users import User

bearer_scheme = HTTPBearer(auto_error=False)


def normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if not normalized:
        raise ValueError("Username must not be empty")
    if " " in normalized:
        raise ValueError("Username must not contain spaces")
    return normalized


def normalize_phone_number(phone: str) -> str:
    cleaned = re.sub(r"\D+", "", phone.strip())
    if not cleaned or len(cleaned) < 10 or len(cleaned) > 15:
        raise ValueError("Phone number must contain 10 to 15 digits")
    return cleaned


def hash_password(password: str, iterations: int = 100_000) -> str:
    if not password:
        raise ValueError("Password must not be empty")
    salt = os.urandom(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt.hex()}${derived_key.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, rounds, salt_hex, stored_key = password_hash.split("$")
    except ValueError as exc:
        raise ValueError("Invalid password hash format") from exc

    if algorithm != "pbkdf2_sha256":
        raise ValueError("Unsupported password hash algorithm")

    salt = bytes.fromhex(salt_hex)
    expected_key = bytes.fromhex(stored_key)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        int(rounds),
    )
    return compare_digest(expected_key, derived_key)


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(encoded: str) -> bytes:
    padding = "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(encoded + padding)


def create_access_token(
    subject: str,
    secret_key: str,
    expires_delta: timedelta,
    algorithm: str = "HS256",
) -> str:
    if algorithm != "HS256":
        raise ValueError("Unsupported token algorithm")

    now = int(time.time())
    payload = {
        "sub": subject,
        "iat": now,
        "exp": int(now + expires_delta.total_seconds()),
        "type": "access",
    }
    header = {"alg": algorithm, "typ": "JWT"}
    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str, secret_key: str, algorithm: str = "HS256") -> Dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise ValueError("Invalid token format") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()

    if not compare_digest(_base64url_decode(signature_b64), expected_signature):
        raise ValueError("Invalid token signature")

    header = json.loads(_base64url_decode(header_b64))
    if header.get("alg") != algorithm:
        raise ValueError("Invalid token algorithm")

    payload = json.loads(_base64url_decode(payload_b64))
    if not isinstance(payload, dict):
        raise ValueError("Invalid token payload")

    exp = payload.get("exp")
    if exp is None or not isinstance(exp, (int, float)):
        raise ValueError("Invalid token expiration")

    if int(time.time()) >= int(exp):
        raise ValueError("Token has expired")

    return payload


async def get_bearer_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> str:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


async def get_current_user(
    request: Request,
    token: str = Depends(get_bearer_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    if getattr(request.state, "user", None) is not None:
        return request.state.user

    payload = decode_access_token(token, settings.SECRET_KEY, settings.ALGORITHM)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return user
