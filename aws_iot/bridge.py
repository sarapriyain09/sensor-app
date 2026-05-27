from __future__ import annotations

import json
import logging
import os
import ssl
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt

from aws_iot.offline_queue import SqliteMessageQueue

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BridgeSettings:
    """Settings for bridging local MQTT -> AWS IoT Core."""

    enabled: bool

    # Local MQTT broker (edge)
    local_host: str
    local_port: int
    local_topic_filter: str

    # AWS IoT Core
    aws_endpoint: str
    aws_port: int
    aws_client_id: str
    aws_topic_prefix: str

    # TLS credentials for AWS IoT Core
    ca_path: str
    cert_path: str
    key_path: str

    # Publishing behavior
    qos: int = 0
    retain: bool = False

    # Offline tolerance (store-and-forward)
    queue_db_path: str = "/var/lib/aws-iot-bridge/queue.db"
    queue_max_messages: int = 100_000
    flush_interval_seconds: float = 1.0
    flush_batch_size: int = 200


def load_bridge_settings() -> BridgeSettings:
    """Load bridge settings from environment variables.

    Secrets are provided as mounted files (paths), not as inline env values.

    Required env vars (when enabled):
    - AWS_IOT_ENDPOINT
    - AWS_IOT_CLIENT_ID
    - AWS_IOT_CA_PATH
    - AWS_IOT_CERT_PATH
    - AWS_IOT_KEY_PATH

    Local broker env vars:
    - LOCAL_MQTT_HOST (default: mosquitto)
    - LOCAL_MQTT_PORT (default: 1883)
    - LOCAL_MQTT_TOPIC_FILTER (default: factory/+/telemetry)

    Optional:
    - AWS_IOT_ENABLED (default: 0)
    - AWS_IOT_PORT (default: 8883)
    - AWS_IOT_TOPIC_PREFIX (default: factory)
    - AWS_IOT_QOS (default: 0)
    - AWS_IOT_RETAIN (default: 0)

    Offline tolerance:
    - AWS_IOT_QUEUE_DB_PATH (default: /var/lib/aws-iot-bridge/queue.db)
    - AWS_IOT_QUEUE_MAX_MESSAGES (default: 100000)
    - AWS_IOT_FLUSH_INTERVAL_SECONDS (default: 1.0)
    - AWS_IOT_FLUSH_BATCH_SIZE (default: 200)
    """

    enabled = _env_bool("AWS_IOT_ENABLED") or False

    local_host = os.getenv("LOCAL_MQTT_HOST", "mosquitto")
    local_port = int(os.getenv("LOCAL_MQTT_PORT", "1883"))
    local_topic_filter = os.getenv("LOCAL_MQTT_TOPIC_FILTER", "factory/+/telemetry")

    aws_endpoint = os.getenv("AWS_IOT_ENDPOINT", "")
    aws_port = int(os.getenv("AWS_IOT_PORT", "8883"))
    aws_client_id = os.getenv("AWS_IOT_CLIENT_ID", "sensor-app-bridge")
    aws_topic_prefix = os.getenv("AWS_IOT_TOPIC_PREFIX", "factory")

    ca_path = os.getenv("AWS_IOT_CA_PATH", "/run/secrets/aws/ca.pem")
    cert_path = os.getenv("AWS_IOT_CERT_PATH", "/run/secrets/aws/cert.pem")
    key_path = os.getenv("AWS_IOT_KEY_PATH", "/run/secrets/aws/private.key")

    qos = int(os.getenv("AWS_IOT_QOS", "0"))
    retain = _env_bool("AWS_IOT_RETAIN") or False

    queue_db_path = os.getenv("AWS_IOT_QUEUE_DB_PATH", "/var/lib/aws-iot-bridge/queue.db")
    queue_max_messages = int(os.getenv("AWS_IOT_QUEUE_MAX_MESSAGES", "100000"))
    flush_interval_seconds = float(os.getenv("AWS_IOT_FLUSH_INTERVAL_SECONDS", "1.0"))
    flush_batch_size = int(os.getenv("AWS_IOT_FLUSH_BATCH_SIZE", "200"))

    return BridgeSettings(
        enabled=enabled,
        local_host=local_host,
        local_port=local_port,
        local_topic_filter=local_topic_filter,
        aws_endpoint=aws_endpoint,
        aws_port=aws_port,
        aws_client_id=aws_client_id,
        aws_topic_prefix=aws_topic_prefix,
        ca_path=ca_path,
        cert_path=cert_path,
        key_path=key_path,
        qos=qos,
        retain=retain,
        queue_db_path=queue_db_path,
        queue_max_messages=queue_max_messages,
        flush_interval_seconds=flush_interval_seconds,
        flush_batch_size=flush_batch_size,
    )


class AwsIotBridge:
    """Bridge that subscribes to local MQTT and republishes to AWS IoT Core."""

    def __init__(self, settings: BridgeSettings) -> None:
        """Create the bridge from settings."""

        self._settings = settings
        self._local = mqtt.Client(client_id=f"local-{settings.aws_client_id}", clean_session=True)
        self._aws = mqtt.Client(client_id=settings.aws_client_id, clean_session=True)

        self._local.on_connect = self._on_local_connect
        self._local.on_message = self._on_local_message
        self._local.on_disconnect = self._on_local_disconnect

        self._aws.on_connect = self._on_aws_connect
        self._aws.on_disconnect = self._on_aws_disconnect

        self._aws_connected = False

        self._queue = SqliteMessageQueue(
            settings.queue_db_path,
            max_messages=settings.queue_max_messages,
        )
        self._stop_event = threading.Event()
        self._flush_event = threading.Event()
        self._flush_thread = threading.Thread(target=self._flush_loop, name="aws-iot-flush", daemon=True)

        # Make reconnect behavior resilient during broker restarts.
        self._local.reconnect_delay_set(min_delay=1, max_delay=30)
        self._aws.reconnect_delay_set(min_delay=1, max_delay=30)

    def run(self) -> None:
        """Run the bridge forever."""

        if not self._settings.enabled:
            logger.info("AWS IoT bridge disabled (AWS_IOT_ENABLED=0)")
            return

        self._validate_required_settings()
        self._configure_aws_tls()

        logger.info(
            "Connecting local MQTT %s:%s, filter=%s",
            self._settings.local_host,
            self._settings.local_port,
            self._settings.local_topic_filter,
        )
        self._local.connect(self._settings.local_host, self._settings.local_port, keepalive=60)
        self._local.loop_start()

        logger.info("Connecting AWS IoT %s:%s", self._settings.aws_endpoint, self._settings.aws_port)
        self._aws.connect(self._settings.aws_endpoint, self._settings.aws_port, keepalive=60)
        self._aws.loop_start()

        self._flush_thread.start()

        try:
            while True:
                time.sleep(1)
        finally:
            self._stop_event.set()
            self._flush_event.set()
            try:
                if self._flush_thread.is_alive():
                    self._flush_thread.join(timeout=15)
            except Exception:
                logger.exception("Failed to join flush thread")
            self._local.loop_stop()
            self._aws.loop_stop()
            try:
                self._local.disconnect()
            except Exception:
                logger.exception("Failed to disconnect local client")
            try:
                self._aws.disconnect()
            except Exception:
                logger.exception("Failed to disconnect AWS client")

            try:
                self._queue.close()
            except Exception:
                logger.exception("Failed to close offline queue")

    def _validate_required_settings(self) -> None:
        """Validate required AWS IoT settings when bridge is enabled."""

        missing = []
        if not self._settings.aws_endpoint:
            missing.append("AWS_IOT_ENDPOINT")
        for name, path in {
            "AWS_IOT_CA_PATH": self._settings.ca_path,
            "AWS_IOT_CERT_PATH": self._settings.cert_path,
            "AWS_IOT_KEY_PATH": self._settings.key_path,
        }.items():
            if not path or not os.path.exists(path):
                missing.append(f"{name} (file not found: {path})")

        if missing:
            raise RuntimeError("Missing AWS IoT settings: " + ", ".join(missing))

    def _configure_aws_tls(self) -> None:
        """Configure TLS for AWS IoT Core MQTT connection."""

        context = ssl.create_default_context()
        context.load_verify_locations(cafile=self._settings.ca_path)
        context.load_cert_chain(certfile=self._settings.cert_path, keyfile=self._settings.key_path)

        self._aws.tls_set_context(context)
        self._aws.tls_insecure_set(False)

    def _on_local_connect(self, client: mqtt.Client, userdata: Optional[object], flags: Dict[str, Any], rc: int) -> None:
        """Callback: local broker connect."""

        if rc != 0:
            logger.warning("Local MQTT connect failed rc=%s", rc)
            return

        logger.info("Local MQTT connected")
        client.subscribe(self._settings.local_topic_filter, qos=self._settings.qos)

    def _on_local_disconnect(self, client: mqtt.Client, userdata: Optional[object], rc: int) -> None:
        """Callback: local broker disconnect."""

        if rc == 0:
            logger.info("Local MQTT disconnected")
        else:
            logger.warning("Local MQTT disconnected unexpectedly rc=%s", rc)

    def _on_aws_connect(self, client: mqtt.Client, userdata: Optional[object], flags: Dict[str, Any], rc: int) -> None:
        """Callback: AWS IoT connect."""

        self._aws_connected = rc == 0
        if self._aws_connected:
            logger.info("AWS IoT connected")
            self._flush_event.set()
        else:
            logger.warning("AWS IoT connect failed rc=%s", rc)

    def _on_aws_disconnect(self, client: mqtt.Client, userdata: Optional[object], rc: int) -> None:
        """Callback: AWS IoT disconnect."""

        self._aws_connected = False
        if rc == 0:
            logger.info("AWS IoT disconnected")
        else:
            logger.warning("AWS IoT disconnected unexpectedly rc=%s", rc)

    def _on_local_message(self, client: mqtt.Client, userdata: Optional[object], msg: mqtt.MQTTMessage) -> None:
        """Callback: message from local broker; republish to AWS IoT."""

        # Example incoming: factory/machine1/telemetry
        in_topic = msg.topic
        payload_bytes = msg.payload or b""

        try:
            payload_obj = json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            payload_obj = {"raw": payload_bytes.decode("utf-8", errors="replace")}

        machine_id = _machine_id_from_topic(in_topic)
        out_topic = f"{self._settings.aws_topic_prefix}/{machine_id}/telemetry"

        payload_json = json.dumps(payload_obj, ensure_ascii=False)
        # Always enqueue first for offline tolerance.
        self._queue.enqueue(out_topic, payload_json)
        self._flush_event.set()

    def _flush_loop(self) -> None:
        """Background worker: drain queued messages to AWS when connected."""

        # Small backoff in case publish fails repeatedly.
        backoff_seconds = 0.25
        while not self._stop_event.is_set():
            # Wait either for periodic tick or an explicit signal.
            self._flush_event.wait(timeout=max(0.1, self._settings.flush_interval_seconds))
            self._flush_event.clear()

            if not self._aws_connected:
                continue

            try:
                published_any = self._flush_once()
                if published_any:
                    backoff_seconds = 0.25
                else:
                    # Nothing to do; avoid busy loop.
                    time.sleep(self._settings.flush_interval_seconds)
            except Exception:
                logger.exception("Flush loop error; will retry")
                time.sleep(min(30.0, backoff_seconds))
                backoff_seconds = min(30.0, backoff_seconds * 2)

    def _flush_once(self) -> bool:
        batch = self._queue.peek_batch(self._settings.flush_batch_size)
        if not batch:
            return False

        published_ids = []
        for item in batch:
            if not self._aws_connected:
                break

            info = self._aws.publish(
                item.topic,
                item.payload,
                qos=self._settings.qos,
                retain=self._settings.retain,
            )

            # For QoS 1/2 this waits for PUBACK/PUBCOMP; for QoS 0 it returns quickly.
            try:
                info.wait_for_publish(timeout=10)
            except Exception:
                # Do not delete; retry later.
                break

            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                # Do not delete; retry later.
                break

            published_ids.append(item.id)

        if published_ids:
            self._queue.delete_ids(published_ids)
        # If we didn't fully drain, schedule another immediate run.
        if len(published_ids) == len(batch):
            self._flush_event.set()
        return True


def _machine_id_from_topic(topic: str) -> str:
    """Extract machine id from topic: factory/<machine>/..."""

    parts = topic.split("/")
    if len(parts) >= 2:
        return parts[1]
    return "unknown"


def _env_bool(name: str) -> Optional[bool]:
    """Parse an optional boolean environment variable."""

    raw = os.getenv(name)
    if raw is None or raw == "":
        return None

    value = raw.strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    return None


def main() -> None:
    """Entrypoint."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    settings = load_bridge_settings()
    AwsIotBridge(settings).run()


if __name__ == "__main__":
    main()
