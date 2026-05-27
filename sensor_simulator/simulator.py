from __future__ import annotations

import json
import logging
import random
import time
from typing import Any, Dict, Iterator

from sensor_simulator.models import Telemetry, new_event_id, utc_now_iso
from sensor_simulator.plc import PlcThresholds, evaluate_plc

logger = logging.getLogger(__name__)


def generate_telemetry(factory_id: str, machine_id: str) -> Telemetry:
    """Generate one realistic-ish telemetry sample."""

    temperature_c = round(random.uniform(60, 90), 2)
    vibration_mm_s = round(random.uniform(0.5, 12.0), 2)
    rpm = int(random.uniform(900, 1800))
    pressure_bar = round(random.uniform(2.0, 10.0), 2)

    return Telemetry(
        event_id=new_event_id(),
        factory_id=factory_id,
        machine_id=machine_id,
        timestamp=utc_now_iso(),
        temperature_c=temperature_c,
        vibration_mm_s=vibration_mm_s,
        rpm=rpm,
        pressure_bar=pressure_bar,
    )


def telemetry_stream(factory_id: str, machine_id: str, interval_seconds: float) -> Iterator[Telemetry]:
    """Yield telemetry samples forever at a fixed interval."""

    while True:
        yield generate_telemetry(factory_id=factory_id, machine_id=machine_id)
        time.sleep(interval_seconds)


def build_edge_message(sample: Telemetry, thresholds: PlcThresholds) -> Dict[str, Any]:
    """Build the edge-processed JSON message (telemetry + PLC state)."""

    plc_result = evaluate_plc(sample, thresholds=thresholds)
    message: Dict[str, Any] = sample.to_dict()
    message["state"] = plc_result.state
    message["alerts"] = plc_result.alerts
    return message


def print_edge_message(message: Dict[str, Any]) -> None:
    """Print an edge message as a single-line JSON payload."""

    print(json.dumps(message, ensure_ascii=False))


def run_simulator(
    factory_id: str,
    machine_id: str,
    interval_seconds: float,
    thresholds: PlcThresholds,
) -> None:
    """Run the simulator loop, emitting edge-processed JSON to stdout."""

    logger.info("Starting simulator: %s/%s interval=%ss", factory_id, machine_id, interval_seconds)
    for sample in telemetry_stream(factory_id=factory_id, machine_id=machine_id, interval_seconds=interval_seconds):
        message = build_edge_message(sample, thresholds=thresholds)
        print_edge_message(message)
