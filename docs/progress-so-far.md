# Progress So Far (as of 2026-05-19)

Project: **Fault-Tolerant Kubernetes-Based Edge Cloud Architecture for Industrial IoT Applications**

This document summarizes what has been implemented in this repo so far (Phases 1–7), how to run it, and what’s next.

---

## Current Architecture Implemented

**Sensor Simulator (Python) + Simulated PLC logic**
→ publishes to **local MQTT broker (Mosquitto)**
→ (optional) **AWS IoT Core bridge** forwards telemetry from local broker to AWS IoT Core.

Output message format is **JSON** and includes:
- telemetry: `temperature_c`, `vibration_mm_s`, `rpm`, `pressure_bar`
- PLC evaluation: `state` (`RUNNING`/`WARNING`/`FAULT`) and `alerts` (list)

---

## Repo Layout

- `sensor_simulator/` — Phase 1+2 simulator + PLC state
- `mqtt/` — Phase 3 MQTT publisher utilities
- `aws_iot/` — Phase 7 local→AWS IoT Core bridge
- `configs/settings.json` — runtime config (including MQTT + thresholds)
- `Dockerfile` — container build
- `docker-compose.yml` + `docker/mosquitto/mosquitto.conf` — Phase 4 compose
- `kubernetes/` — Phase 5 manifests + Phase 7 bridge deployment
- `docs/` — phase notes and policies
- `scripts/` — Phase 6 automation

Note: `docker.py` was renamed to `docker_sanity.py` to avoid shadowing the real Docker CLI on Windows.

---

## Phase-by-Phase Status

### Phase 1 — Sensor simulation (Done)
- Simulator generates continuous telemetry (realistic-ish random ranges).
- JSON output is emitted to stdout.

Key files:
- `sensor_simulator/simulator.py`
- `sensor_simulator/models.py`
- `app.py`

### Phase 2 — Simulated PLC logic (Done)
- PLC evaluates each sample and sets:
  - `state`: `RUNNING` / `WARNING` / `FAULT`
  - `alerts`: e.g. `OVERHEAT_WARNING`, `VIBRATION_FAULT`
- Thresholds are configurable in `configs/settings.json`.

Key files:
- `sensor_simulator/plc.py`
- `sensor_simulator/config.py`

### Phase 3 — MQTT publish (Done)
- When enabled, the simulator publishes to the local broker using `paho-mqtt`.
- Topics published:
  - `factory/machine1/telemetry` (full JSON)
  - plus per-metric topics: `temperature`, `vibration`, `rpm`, `pressure`, `state`

Key files:
- `mqtt/publisher.py`
- `configs/settings.json` (MQTT settings)

### Phase 4 — Docker + Docker Compose (Done)
- Docker image builds and runs the simulator.
- Compose stack runs Mosquitto + sensor simulator together.

Key files:
- `Dockerfile`
- `docker-compose.yml`
- `docker/mosquitto/mosquitto.conf`

### Phase 5 — Kubernetes (Minikube) (Done)
- Mosquitto deployed as Deployment + Service.
- Sensor simulator deployed as Deployment with **2 replicas** (for self-healing/scaling demos).

Key files:
- `kubernetes/mosquitto-configmap.yaml`
- `kubernetes/mosquitto-deployment.yaml`
- `kubernetes/mosquitto-service.yaml`
- `kubernetes/sensor-app-deployment.yaml`

### Phase 6 — Fault tolerance tests (Done)
- Test guide + PowerShell automation script.
- Verified scenarios:
  - delete sensor pod(s) → Deployment recreates
  - delete mosquitto pod → sensor pods stay running and reconnect

Key files:
- `docs/phase6-fault-tolerance.md`
- `scripts/phase6_fault_tests.ps1`

### Phase 7 — AWS IoT Core (Scaffolded + ready to configure)
- Added an **AWS IoT bridge** service that:
  - subscribes to local broker topic `factory/+/telemetry`
  - republishes to AWS IoT Core over TLS using X.509 certs
- Bridge is **offline-tolerant**: it buffers outgoing messages on disk and flushes when AWS connectivity returns.
- AWS endpoint set to: `axmuxp0nzbtg9-ats.iot.us-east-1.amazonaws.com`
- Using Option A: AWS IoT Client ID is the Thing name `machine`.

Key files:
- `aws_iot/bridge.py`
- `kubernetes/aws-iot-bridge-deployment.yaml`
- `docs/phase7-aws-iot-core.md`
- `docs/aws-iot-policy-machine.json`

Required action (you do this in AWS Console):
- create/attach IoT policy + certificate to Thing
- create Kubernetes secret `aws-iot-creds` from:
  - `AmazonRootCA1.pem` as `ca.pem`
  - `cert.pem`
  - `private.key`

---

## How to Run

### Run locally with Docker (no MQTT)
```powershell
docker build -t sensor-app .
docker run --rm sensor-app
```

### Run with Compose (Mosquitto + simulator publishing)
```powershell
docker compose up --build
# in another terminal
docker compose logs -f sensor-app
# stop
docker compose down
```

### Run on Minikube (Kubernetes)
```powershell
kubectl config current-context
kubectl apply -f kubernetes/

kubectl get pods -o wide
kubectl logs -l app=sensor-app -f
```

### Run Phase 6 fault tests
```powershell
powershell -ExecutionPolicy Bypass -File scripts/phase6_fault_tests.ps1 -SensorReplicas 5
```

### Enable AWS IoT bridge (after you create the secret)
```powershell
kubectl apply -f kubernetes/aws-iot-bridge-deployment.yaml
kubectl logs -l app=aws-iot-bridge -f
```

---

## Known Notes / Gotchas

- Windows/Minikube: Having a file named `docker.py` in the repo can interfere with Minikube calling the Docker CLI; it has been renamed to `docker_sanity.py`.
- Kubernetes: On a fresh code change, rebuild + reload image into Minikube:
  - `docker build -t sensor-app:dev .`
  - `minikube image load sensor-app:dev`
  - `kubectl rollout restart deployment/sensor-app`

---

## Next Steps (Tomorrow)

Recommended next work items:
1) **Phase 7 completion:** create AWS IoT certificate/policy in AWS Console, create `aws-iot-creds` secret, deploy `aws-iot-bridge`, verify messages arrive in AWS IoT test client.
2) **Phase 8:** add storage + dashboard stack (e.g., PostgreSQL/TimescaleDB + Grafana, or AWS Timestream) and visualize:
   - temperature graph
   - vibration trend
   - machine `state` and `alerts`
  - guide: `docs/phase8-dashboard.md`
  - local Grafana option: `docs/local-dashboard-grafana.md`
  - fully-offline local dashboard: `docs/local-dashboard-offline.md`
3) **Phase 9:** add monitoring + alerts for the AWS CloudWatch metrics path:
  - guide: `docs/phase9-edge-cloud-monitoring.md`
  - CloudWatch alarms template: `aws/phase9/cloudwatch-alarms.yaml`
3) Optional hardening: add a persistent queue/retry for bridge to avoid drops during AWS downtime.
