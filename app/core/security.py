from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any, Dict


def _decode_base64url(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def decode_access_token(token: str, secret_key: str, algorithm: str = "HS256") -> Dict[str, Any]:
    if algorithm != "HS256":
        raise ValueError(f"Unsupported token algorithm: {algorithm}")

    header_b64, payload_b64, signature_b64 = token.split(".")
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_signature = hmac.new(
        secret_key.encode(),
        signing_input,
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(_decode_base64url(signature_b64), expected_signature):
        raise ValueError("Invalid token signature")

    header = json.loads(_decode_base64url(header_b64))
    if header.get("alg") != algorithm:
        raise ValueError("Invalid token algorithm")

    return json.loads(_decode_base64url(payload_b64))
