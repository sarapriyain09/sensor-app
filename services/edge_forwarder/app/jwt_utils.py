from __future__ import annotations

import time
from typing import Any, Dict

import jwt


def load_private_key(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def make_token(*, private_key_pem: str, issuer: str, audience: str, subject: str, ttl_seconds: int = 300) -> str:
    now = int(time.time())
    payload: Dict[str, Any] = {
        "iss": issuer,
        "aud": audience,
        "sub": subject,
        "iat": now,
        "exp": now + int(ttl_seconds),
    }
    return jwt.encode(payload, private_key_pem, algorithm="RS256")
