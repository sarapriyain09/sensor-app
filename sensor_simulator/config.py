from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the sensor simulator."""

    factory_id: str = "factory"
    machine_id: str = "machine1"
    interval_seconds: float = 2.0

    temperature_warning_c: float = 80.0
    temperature_fault_c: float = 88.0
    vibration_warning_mm_s: float = 8.0
    vibration_fault_mm_s: float = 11.0

    mqtt_enabled: bool = False
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic_prefix: str = "factory"
    mqtt_qos: int = 0
    mqtt_retain: bool = False
    mqtt_client_id: str = "sensor-simulator"

    # Optional broker auth (prefer env vars over config files)
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None

    # Optional TLS (useful when pointing at a secured broker)
    mqtt_tls_enabled: bool = False
    mqtt_tls_ca_path: Optional[str] = None
    mqtt_tls_insecure: bool = False


def load_settings(config_path: str = "configs/settings.json") -> Settings:
    """Load settings from JSON config file and environment overrides.

    Environment variables (optional):
    - FACTORY_ID
    - MACHINE_ID
    - INTERVAL_SECONDS
    - TEMPERATURE_WARNING_C
    - TEMPERATURE_FAULT_C
    - VIBRATION_WARNING_MM_S
    - VIBRATION_FAULT_MM_S
    - MQTT_ENABLED
    - MQTT_HOST
    - MQTT_PORT
    - MQTT_TOPIC_PREFIX
    - MQTT_QOS
    - MQTT_RETAIN
    - MQTT_CLIENT_ID
    - MQTT_USERNAME
    - MQTT_PASSWORD
    - MQTT_TLS_ENABLED
    - MQTT_TLS_CA_PATH
    - MQTT_TLS_INSECURE
    """

    file_settings = _load_settings_file(config_path)

    factory_id = os.getenv("FACTORY_ID") or file_settings.factory_id
    machine_id = os.getenv("MACHINE_ID") or file_settings.machine_id

    interval_raw = os.getenv("INTERVAL_SECONDS")
    interval_seconds = file_settings.interval_seconds
    if interval_raw:
        try:
            interval_seconds = float(interval_raw)
        except ValueError:
            interval_seconds = file_settings.interval_seconds

    temperature_warning_c = _env_float("TEMPERATURE_WARNING_C") or file_settings.temperature_warning_c
    temperature_fault_c = _env_float("TEMPERATURE_FAULT_C") or file_settings.temperature_fault_c
    vibration_warning_mm_s = _env_float("VIBRATION_WARNING_MM_S") or file_settings.vibration_warning_mm_s
    vibration_fault_mm_s = _env_float("VIBRATION_FAULT_MM_S") or file_settings.vibration_fault_mm_s

    mqtt_enabled = _env_bool("MQTT_ENABLED") if _env_bool("MQTT_ENABLED") is not None else file_settings.mqtt_enabled
    mqtt_host = os.getenv("MQTT_HOST") or file_settings.mqtt_host
    mqtt_port = _env_int("MQTT_PORT") or file_settings.mqtt_port
    mqtt_topic_prefix = os.getenv("MQTT_TOPIC_PREFIX") or file_settings.mqtt_topic_prefix
    mqtt_qos = _env_int("MQTT_QOS") if _env_int("MQTT_QOS") is not None else file_settings.mqtt_qos
    mqtt_retain = _env_bool("MQTT_RETAIN") if _env_bool("MQTT_RETAIN") is not None else file_settings.mqtt_retain
    base_client_id = os.getenv("MQTT_CLIENT_ID") or file_settings.mqtt_client_id

    mqtt_username = os.getenv("MQTT_USERNAME") or file_settings.mqtt_username
    mqtt_password = os.getenv("MQTT_PASSWORD") or file_settings.mqtt_password

    mqtt_tls_enabled = (
        _env_bool("MQTT_TLS_ENABLED") if _env_bool("MQTT_TLS_ENABLED") is not None else file_settings.mqtt_tls_enabled
    )
    mqtt_tls_ca_path = os.getenv("MQTT_TLS_CA_PATH") or file_settings.mqtt_tls_ca_path
    mqtt_tls_insecure = (
        _env_bool("MQTT_TLS_INSECURE")
        if _env_bool("MQTT_TLS_INSECURE") is not None
        else file_settings.mqtt_tls_insecure
    )

    # When running multiple replicas in Kubernetes, client IDs must be unique.
    # Otherwise the broker will disconnect older sessions as "taken over".
    mqtt_client_id = base_client_id
    if os.getenv("MQTT_CLIENT_ID") is None and os.getenv("KUBERNETES_SERVICE_HOST"):
        suffix = os.getenv("POD_NAME") or socket.gethostname()
        if suffix:
            mqtt_client_id = f"{base_client_id}-{suffix}"

    return Settings(
        factory_id=factory_id,
        machine_id=machine_id,
        interval_seconds=interval_seconds,
        temperature_warning_c=temperature_warning_c,
        temperature_fault_c=temperature_fault_c,
        vibration_warning_mm_s=vibration_warning_mm_s,
        vibration_fault_mm_s=vibration_fault_mm_s,
        mqtt_enabled=mqtt_enabled,
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_topic_prefix=mqtt_topic_prefix,
        mqtt_qos=mqtt_qos,
        mqtt_retain=mqtt_retain,
        mqtt_client_id=mqtt_client_id,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        mqtt_tls_enabled=mqtt_tls_enabled,
        mqtt_tls_ca_path=mqtt_tls_ca_path,
        mqtt_tls_insecure=mqtt_tls_insecure,
    )


def _env_float(name: str) -> Optional[float]:
    """Parse an optional float environment variable."""

    raw = os.getenv(name)
    if raw is None or raw == "":
        return None

    try:
        return float(raw)
    except ValueError:
        return None


def _env_int(name: str) -> Optional[int]:
    """Parse an optional int environment variable."""

    raw = os.getenv(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _env_bool(name: str) -> Optional[bool]:
    """Parse an optional boolean environment variable.

    Accepts: 1/0, true/false, yes/no, on/off (case-insensitive).
    """

    raw = os.getenv(name)
    if raw is None or raw == "":
        return None

    value = raw.strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    return None


def _load_settings_file(config_path: str) -> Settings:
    """Load settings from JSON file if it exists; otherwise return defaults."""

    if not os.path.exists(config_path):
        return Settings()

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return Settings(
        factory_id=str(data.get("factory_id", Settings.factory_id)),
        machine_id=str(data.get("machine_id", Settings.machine_id)),
        interval_seconds=float(data.get("interval_seconds", Settings.interval_seconds)),
        temperature_warning_c=float(data.get("temperature_warning_c", Settings.temperature_warning_c)),
        temperature_fault_c=float(data.get("temperature_fault_c", Settings.temperature_fault_c)),
        vibration_warning_mm_s=float(data.get("vibration_warning_mm_s", Settings.vibration_warning_mm_s)),
        vibration_fault_mm_s=float(data.get("vibration_fault_mm_s", Settings.vibration_fault_mm_s)),
        mqtt_enabled=bool(data.get("mqtt_enabled", Settings.mqtt_enabled)),
        mqtt_host=str(data.get("mqtt_host", Settings.mqtt_host)),
        mqtt_port=int(data.get("mqtt_port", Settings.mqtt_port)),
        mqtt_topic_prefix=str(data.get("mqtt_topic_prefix", Settings.mqtt_topic_prefix)),
        mqtt_qos=int(data.get("mqtt_qos", Settings.mqtt_qos)),
        mqtt_retain=bool(data.get("mqtt_retain", Settings.mqtt_retain)),
        mqtt_client_id=str(data.get("mqtt_client_id", Settings.mqtt_client_id)),
        mqtt_username=(str(data["mqtt_username"]) if data.get("mqtt_username") not in (None, "") else None),
        mqtt_password=(str(data["mqtt_password"]) if data.get("mqtt_password") not in (None, "") else None),
        mqtt_tls_enabled=bool(data.get("mqtt_tls_enabled", Settings.mqtt_tls_enabled)),
        mqtt_tls_ca_path=(str(data["mqtt_tls_ca_path"]) if data.get("mqtt_tls_ca_path") not in (None, "") else None),
        mqtt_tls_insecure=bool(data.get("mqtt_tls_insecure", Settings.mqtt_tls_insecure)),
    )
