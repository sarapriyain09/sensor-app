from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional

import paho.mqtt.client as mqtt
import requests

from aws_iot.offline_queue import SqliteMessageQueue
from app.jwt_utils import load_private_key, make_token
from app.settings import Settings, load_settings

logger = logging.getLogger(__name__)


class EdgeForwarder:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._queue = SqliteMessageQueue(settings.queue_db_path, max_messages=settings.queue_max_messages)

        self._private_key = load_private_key(settings.jwt_private_key_path)

        self._client = mqtt.Client(client_id=settings.mqtt_client_id, clean_session=True)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

        self._stop = threading.Event()
        self._flush_thread = threading.Thread(target=self._flush_loop, name="flush", daemon=True)

    def run(self) -> None:
        logger.info(
            "Starting edge-forwarder local=%s:%s filter=%s -> %s",
            self._settings.mqtt_host,
            self._settings.mqtt_port,
            self._settings.mqtt_topic_filter,
            self._settings.cloud_api_url,
        )
        self._client.connect(self._settings.mqtt_host, self._settings.mqtt_port, keepalive=60)
        self._client.loop_start()
        self._flush_thread.start()

        try:
            while True:
                time.sleep(1)
        finally:
            self._stop.set()
            self._client.loop_stop()
            try:
                self._client.disconnect()
            except Exception:
                logger.exception("disconnect failed")
            self._queue.close()

    def _on_connect(self, client: mqtt.Client, userdata: Optional[object], flags: Dict[str, Any], rc: int) -> None:
        if rc != 0:
            logger.warning("MQTT connect failed rc=%s", rc)
            return
        logger.info("MQTT connected")
        client.subscribe(self._settings.mqtt_topic_filter, qos=self._settings.mqtt_qos)

    def _on_disconnect(self, client: mqtt.Client, userdata: Optional[object], rc: int) -> None:
        if rc == 0:
            logger.info("MQTT disconnected")
        else:
            logger.warning("MQTT disconnected unexpectedly rc=%s", rc)

    def _on_message(self, client: mqtt.Client, userdata: Optional[object], msg: mqtt.MQTTMessage) -> None:
        try:
            payload = msg.payload.decode("utf-8", errors="replace")
            # Minimal validation: must be valid JSON.
            json.loads(payload)
            self._queue.enqueue(topic=str(msg.topic), payload=payload)
        except Exception:
            logger.exception("Failed to enqueue message")

    def _flush_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._flush_once()
            except Exception:
                logger.exception("Flush loop error")
            time.sleep(self._settings.flush_interval_seconds)

    def _flush_once(self) -> None:
        batch = self._queue.peek_batch(self._settings.flush_batch_size)
        if not batch:
            return

        events: List[Dict[str, Any]] = []
        ids: List[int] = []
        for m in batch:
            ids.append(m.id)
            events.append(json.loads(m.payload))

        token = make_token(
            private_key_pem=self._private_key,
            issuer=self._settings.jwt_issuer,
            audience=self._settings.jwt_audience,
            subject=self._settings.jwt_subject,
        )

        resp = requests.post(
            self._settings.cloud_api_url,
            json={"events": events},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )

        if resp.status_code >= 200 and resp.status_code < 300:
            self._queue.delete_ids(ids)
            return

        # Keep messages in queue; caller retries.
        logger.warning("Cloud ingest failed status=%s body=%s", resp.status_code, resp.text[:500])


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    EdgeForwarder(settings).run()


if __name__ == "__main__":
    main()
