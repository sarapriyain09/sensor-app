from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    # Database
    database_url: str

    # JWT verification (RS256)
    jwt_public_key_path: str
    jwt_issuer: str
    jwt_audience: str

    # API behavior
    max_batch_size: int = 500


def load_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required (e.g. postgresql://user:pass@host:5432/db)")

    jwt_public_key_path = os.getenv("JWT_PUBLIC_KEY_PATH", "/run/secrets/jwt/public.pem")
    jwt_issuer = os.getenv("JWT_ISSUER", "sensor-app-edge")
    jwt_audience = os.getenv("JWT_AUDIENCE", "sensor-app-ingestion")

    max_batch_size = int(os.getenv("MAX_BATCH_SIZE", "500"))

    return Settings(
        database_url=database_url,
        jwt_public_key_path=jwt_public_key_path,
        jwt_issuer=jwt_issuer,
        jwt_audience=jwt_audience,
        max_batch_size=max_batch_size,
    )
