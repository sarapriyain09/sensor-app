from __future__ import annotations

from dataclasses import dataclass
from typing import List

from sensor_simulator.models import Telemetry


MachineState = str


@dataclass(frozen=True)
class PlcThresholds:
    """Thresholds used by the simulated PLC to classify machine state."""

    temperature_warning_c: float = 80.0
    temperature_fault_c: float = 88.0
    vibration_warning_mm_s: float = 8.0
    vibration_fault_mm_s: float = 11.0


@dataclass(frozen=True)
class PlcResult:
    """Result of PLC evaluation for a telemetry sample."""

    state: MachineState
    alerts: List[str]


def evaluate_plc(telemetry: Telemetry, thresholds: PlcThresholds) -> PlcResult:
    """Evaluate one telemetry sample and return machine state + alerts.

    Rules (simple and deterministic):
    - If any FAULT condition occurs -> state is FAULT
    - Else if any WARNING condition occurs -> state is WARNING
    - Else -> state is RUNNING
    """

    alerts: List[str] = []

    is_fault = False
    is_warning = False

    if telemetry.temperature_c >= thresholds.temperature_fault_c:
        is_fault = True
        alerts.append("OVERHEAT_FAULT")
    elif telemetry.temperature_c >= thresholds.temperature_warning_c:
        is_warning = True
        alerts.append("OVERHEAT_WARNING")

    if telemetry.vibration_mm_s >= thresholds.vibration_fault_mm_s:
        is_fault = True
        alerts.append("VIBRATION_FAULT")
    elif telemetry.vibration_mm_s >= thresholds.vibration_warning_mm_s:
        is_warning = True
        alerts.append("VIBRATION_WARNING")

    if is_fault:
        return PlcResult(state="FAULT", alerts=alerts)
    if is_warning:
        return PlcResult(state="WARNING", alerts=alerts)
    return PlcResult(state="RUNNING", alerts=[])
