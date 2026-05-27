from __future__ import annotations

import json
import logging
import ssl
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MqttSettings:
    """MQTT connection and publishing settings."""

    host: str
    port: int
    topic_prefix: str
    qos: int = 0
    retain: bool = False
    client_id: str = "sensor-simulator"

    # Optional broker auth
    username: Optional[str] = None
    password: Optional[str] = None

    # Optional TLS
    tls_enabled: bool = False
    tls_ca_path: Optional[str] = None
    tls_insecure: bool = False


class MqttPublisher:
    """Small helper that connects to an MQTT broker and publishes JSON payloads."""

    def __init__(self, settings: MqttSettings) -> None:
        """Create a publisher with the given settings (not connected yet)."""

        self._settings = settings
        self._client = mqtt.Client(client_id=settings.client_id, clean_session=True)
        self._connected = False
        self._loop_started = False

        if settings.username:
            self._client.username_pw_set(settings.username, password=settings.password)

        if settings.tls_enabled:
            # If tls_ca_path is omitted, paho-mqtt uses system CA certificates.
            self._client.tls_set(
                ca_certs=settings.tls_ca_path,
                tls_version=ssl.PROTOCOL_TLS_CLIENT,
            )
            self._client.tls_insecure_set(bool(settings.tls_insecure))

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

        # Make reconnect behavior resilient during broker restarts.
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._client.max_queued_messages_set(10_000)

        self._next_connect_attempt_at = 0.0
        self._connect_backoff_seconds = 1.0
        self._last_connect_log_at = 0.0
        self._last_disconnect_log_at = 0.0

    def connect(self) -> None:
        """Connect to the broker and start the network loop in a background thread.

        Best-effort connect. If the broker is unavailable, this does not raise.
        Publishing will retry connections on the next loop iterations.
        """

        if not self._loop_started:
            self._client.loop_start()
            self._loop_started = True

        if self._connected:
            return

        now = time.monotonic()
        if now < self._next_connect_attempt_at:
            return

        # Avoid spamming connect logs when the broker is down or restarting.
        if now - self._last_connect_log_at > 5:
            logger.info("Connecting to MQTT broker %s:%s", self._settings.host, self._settings.port)
            self._last_connect_log_at = now

        try:
            # Use async connect so we don't block the caller; loop thread drives retries.
            self._client.connect_async(self._settings.host, self._settings.port, keepalive=60)
            # If the broker is down, back off subsequent connect attempts.
            self._next_connect_attempt_at = now + self._connect_backoff_seconds
            self._connect_backoff_seconds = min(30.0, self._connect_backoff_seconds * 2)
        except Exception as exc:
            logger.warning("MQTT connect failed (%s); will retry", exc)
            self._next_connect_attempt_at = now + self._connect_backoff_seconds
            self._connect_backoff_seconds = min(30.0, self._connect_backoff_seconds * 2)

    def close(self) -> None:
        """Stop loop and disconnect (best-effort)."""

        try:
            if self._loop_started:
                self._client.loop_stop()
        finally:
            try:
                self._client.disconnect()
            except Exception:
                logger.exception("Failed to disconnect MQTT client")

    def publish_json(self, topic: str, payload: Dict[str, Any]) -> None:
        """Publish a JSON message to a topic."""

        if not self._connected:
            self.connect()

        data = json.dumps(payload, ensure_ascii=False)
        result = self._client.publish(topic, payload=data, qos=self._settings.qos, retain=self._settings.retain)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.warning("MQTT publish failed rc=%s topic=%s", result.rc, topic)

    def publish_text(self, topic: str, payload: str) -> None:
        """Publish a text payload to a topic."""

        if not self._connected:
            self.connect()

        result = self._client.publish(topic, payload=payload, qos=self._settings.qos, retain=self._settings.retain)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.warning("MQTT publish failed rc=%s topic=%s", result.rc, topic)

    @property
    def topic_prefix(self) -> str:
        """Return the configured topic prefix."""

        return self._settings.topic_prefix

    def _on_connect(self, client: mqtt.Client, userdata: Optional[object], flags: Dict[str, Any], rc: int) -> None:
        """paho-mqtt callback invoked when the client connects."""

        self._connected = rc == 0
        if self._connected:
            logger.info("MQTT connected")
            self._connect_backoff_seconds = 1.0
            self._next_connect_attempt_at = 0.0
        else:
            logger.warning("MQTT connect failed rc=%s", rc)

    def _on_disconnect(self, client: mqtt.Client, userdata: Optional[object], rc: int) -> None:
        """paho-mqtt callback invoked when the client disconnects."""

        self._connected = False
        if rc == 0:
            logger.info("MQTT disconnected")
        else:
            now = time.monotonic()
            if now - self._last_disconnect_log_at > 5:
                logger.warning("MQTT disconnected unexpectedly rc=%s", rc)
                self._last_disconnect_log_at = now
            # Backoff future connect attempts to avoid a tight reconnect loop.
            self._next_connect_attempt_at = max(self._next_connect_attempt_at, now + self._connect_backoff_seconds)
            self._connect_backoff_seconds = min(30.0, self._connect_backoff_seconds * 2)
