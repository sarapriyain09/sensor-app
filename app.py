import logging
import json

from sensor_simulator.config import load_settings
from sensor_simulator.logging_setup import setup_logging
from sensor_simulator.plc import PlcThresholds
from sensor_simulator.simulator import build_edge_message, telemetry_stream

from mqtt.publisher import MqttPublisher, MqttSettings


def main() -> None:
    """Container entrypoint for the sensor simulator."""

    setup_logging(level=logging.INFO)
    settings = load_settings()
    thresholds = PlcThresholds(
        temperature_warning_c=settings.temperature_warning_c,
        temperature_fault_c=settings.temperature_fault_c,
        vibration_warning_mm_s=settings.vibration_warning_mm_s,
        vibration_fault_mm_s=settings.vibration_fault_mm_s,
    )

    mqtt_publisher = None
    if settings.mqtt_enabled:
        mqtt_settings = MqttSettings(
            host=settings.mqtt_host,
            port=settings.mqtt_port,
            topic_prefix=settings.mqtt_topic_prefix,
            qos=settings.mqtt_qos,
            retain=settings.mqtt_retain,
            client_id=settings.mqtt_client_id,
            username=settings.mqtt_username,
            password=settings.mqtt_password,
            tls_enabled=settings.mqtt_tls_enabled,
            tls_ca_path=settings.mqtt_tls_ca_path,
            tls_insecure=settings.mqtt_tls_insecure,
        )
        mqtt_publisher = MqttPublisher(mqtt_settings)
        mqtt_publisher.connect()

    try:
        for sample in telemetry_stream(
            factory_id=settings.factory_id,
            machine_id=settings.machine_id,
            interval_seconds=settings.interval_seconds,
        ):
            edge_message = build_edge_message(sample, thresholds=thresholds)
            print(json.dumps(edge_message, ensure_ascii=False))

            if mqtt_publisher is not None:
                prefix = mqtt_publisher.topic_prefix
                base = f"{prefix}/{settings.machine_id}"

                mqtt_publisher.publish_json(f"{base}/telemetry", edge_message)
                mqtt_publisher.publish_text(f"{base}/temperature", str(edge_message["temperature_c"]))
                mqtt_publisher.publish_text(f"{base}/vibration", str(edge_message["vibration_mm_s"]))
                mqtt_publisher.publish_text(f"{base}/rpm", str(edge_message["rpm"]))
                mqtt_publisher.publish_text(f"{base}/pressure", str(edge_message["pressure_bar"]))
                mqtt_publisher.publish_text(f"{base}/state", str(edge_message["state"]))
    finally:
        if mqtt_publisher is not None:
            mqtt_publisher.close()


if __name__ == "__main__":
    main()
