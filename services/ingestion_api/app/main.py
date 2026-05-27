from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from psycopg2.extras import Json

from app.db import Db
from app.security import compute_event_id, load_public_key, verify_bearer_token
from app.settings import Settings, load_settings


class TelemetryEvent(BaseModel):
    event_id: Optional[str] = None
    factory_id: str
    machine_id: str
    timestamp: str
    temperature_c: float
    vibration_mm_s: float
    rpm: int
    pressure_bar: float
    state: str


class IngestBatchRequest(BaseModel):
    events: List[TelemetryEvent] = Field(default_factory=list)


class IngestBatchResponse(BaseModel):
    received: int
    inserted: int
    duplicates: int


def build_app() -> FastAPI:
    settings = load_settings()
    public_key = load_public_key(settings.jwt_public_key_path)
    db = Db(settings.database_url)

    app = FastAPI(title="sensor-app ingestion API", version="0.1")

    @app.on_event("shutdown")
    def _shutdown() -> None:
        db.close()

    def _auth(authorization: str = Header(default="")) -> Dict[str, Any]:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Bearer token")
        token = authorization.removeprefix("Bearer ").strip()
        try:
            return verify_bearer_token(
                token=token,
                public_key_pem=public_key,
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
            )
        except Exception as exc:
            raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"ok": "true"}

    @app.post("/ingest/batch", response_model=IngestBatchResponse)
    def ingest_batch(req: IngestBatchRequest, _claims: Dict[str, Any] = Depends(_auth)) -> IngestBatchResponse:
        if len(req.events) > settings.max_batch_size:
            raise HTTPException(status_code=413, detail=f"Too many events; max={settings.max_batch_size}")

        rows: List[Dict[str, Any]] = []
        for e in req.events:
            payload = e.model_dump()
            eid = payload.get("event_id") or compute_event_id(payload)
            payload["event_id"] = eid
            rows.append(payload)

        inserted = 0
        duplicates = 0

        if not rows:
            return IngestBatchResponse(received=0, inserted=0, duplicates=0)

        with db.conn() as conn:
            with conn.cursor() as cur:
                for r in rows:
                    cur.execute(
                        """
                        INSERT INTO telemetry_events(
                          event_id, factory_id, machine_id, ts,
                          temperature_c, vibration_mm_s, rpm, pressure_bar, state, raw
                        ) VALUES (
                          %(event_id)s, %(factory_id)s, %(machine_id)s, %(timestamp)s,
                          %(temperature_c)s, %(vibration_mm_s)s, %(rpm)s, %(pressure_bar)s, %(state)s, %(raw)s
                        )
                        ON CONFLICT (event_id) DO NOTHING
                        """,
                        {
                            **r,
                            "raw": Json(r),
                        },
                    )
                    if cur.rowcount == 1:
                        inserted += 1
                    else:
                        duplicates += 1
            conn.commit()

        return IngestBatchResponse(received=len(rows), inserted=inserted, duplicates=duplicates)

    return app


app = build_app()
