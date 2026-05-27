from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import uuid
from typing import Any, Dict


@dataclass(frozen=True)
class Telemetry:
    """Single telemetry sample emitted by one machine."""

    event_id: str
    factory_id: str
    machine_id: str
    timestamp: str
    temperature_c: float
    vibration_mm_s: float
    rpm: int
    pressure_bar: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert telemetry to a JSON-serializable dictionary."""

        return asdict(self)


def utc_now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""

    return datetime.now(timezone.utc).isoformat()


def new_event_id() -> str:
    return str(uuid.uuid4())
