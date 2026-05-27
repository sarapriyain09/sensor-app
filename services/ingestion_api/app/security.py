from __future__ import annotations

import hashlib
import os
from typing import Any, Dict

import jwt


def load_public_key(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def verify_bearer_token(*, token: str, public_key_pem: str, issuer: str, audience: str) -> Dict[str, Any]:
    return jwt.decode(
        token,
        public_key_pem,
        algorithms=["RS256"],
        issuer=issuer,
        audience=audience,
        leeway=60,
        options={"require": ["exp", "iss", "aud", "sub"], "verify_iat": False},
    )


def compute_event_id(payload: Dict[str, Any]) -> str:
    """Deterministic fallback event_id if sender didn't provide one."""

    machine_id = str(payload.get("machine_id") or "")
    timestamp = str(payload.get("timestamp") or "")
    base = f"{machine_id}|{timestamp}|{payload.get('temperature_c')}|{payload.get('vibration_mm_s')}|{payload.get('rpm')}|{payload.get('pressure_bar')}|{payload.get('state')}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()
