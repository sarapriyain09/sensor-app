from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    # Local MQTT
    mqtt_host: str
    mqtt_port: int
    mqtt_topic_filter: str
    mqtt_qos: int
    mqtt_client_id: str

    # Cloud API
    cloud_api_url: str
    flush_batch_size: int
    flush_interval_seconds: float

    # Queue
    queue_db_path: str
    queue_max_messages: int

    # JWT (RS256)
    jwt_private_key_path: str
    jwt_issuer: str
    jwt_audience: str
    jwt_subject: str


def load_settings() -> Settings:
    mqtt_host = os.getenv("LOCAL_MQTT_HOST", "mosquitto")
    mqtt_port = int(os.getenv("LOCAL_MQTT_PORT", "1883"))
    mqtt_topic_filter = os.getenv("LOCAL_MQTT_TOPIC_FILTER", "factory/+/telemetry")
    mqtt_qos = int(os.getenv("LOCAL_MQTT_QOS", "1"))
    mqtt_client_id = os.getenv("LOCAL_MQTT_CLIENT_ID", "edge-forwarder")

    cloud_api_url = os.getenv("CLOUD_API_URL", "")
    if not cloud_api_url:
        raise RuntimeError("CLOUD_API_URL is required, e.g. https://example.com/ingest/batch")

    flush_batch_size = int(os.getenv("FLUSH_BATCH_SIZE", "200"))
    flush_interval_seconds = float(os.getenv("FLUSH_INTERVAL_SECONDS", "1.0"))

    queue_db_path = os.getenv("QUEUE_DB_PATH", "/var/lib/edge-forwarder/queue.db")
    queue_max_messages = int(os.getenv("QUEUE_MAX_MESSAGES", "100000"))

    jwt_private_key_path = os.getenv("JWT_PRIVATE_KEY_PATH", "/run/secrets/jwt/private.pem")
    jwt_issuer = os.getenv("JWT_ISSUER", "sensor-app-edge")
    jwt_audience = os.getenv("JWT_AUDIENCE", "sensor-app-ingestion")
    jwt_subject = os.getenv("JWT_SUBJECT", "edge-forwarder")

    return Settings(
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_topic_filter=mqtt_topic_filter,
        mqtt_qos=mqtt_qos,
        mqtt_client_id=mqtt_client_id,
        cloud_api_url=cloud_api_url,
        flush_batch_size=flush_batch_size,
        flush_interval_seconds=flush_interval_seconds,
        queue_db_path=queue_db_path,
        queue_max_messages=queue_max_messages,
        jwt_private_key_path=jwt_private_key_path,
        jwt_issuer=jwt_issuer,
        jwt_audience=jwt_audience,
        jwt_subject=jwt_subject,
    )
