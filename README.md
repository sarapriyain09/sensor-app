# Sensor App

Industrial IoT sensor simulation and edge-to-cloud telemetry pipeline.

## Overview

This repository provides a modular sensor telemetry system that can run locally, at the edge, and in Kubernetes-based edge-cloud deployments.

Core capabilities:
- Sensor simulation with PLC-style state evaluation (`RUNNING`, `WARNING`, `FAULT`)
- MQTT publishing to local broker (Mosquitto)
- Offline observability stack (Telegraf + InfluxDB + Grafana)
- Optional AWS IoT bridge with store-and-forward buffering
- Cloud ingestion path with FastAPI, JWT verification, and PostgreSQL (see docs)

## High-Level Flow

Sensors -> Simulator -> MQTT Broker -> Local Dashboard / Edge Forwarders -> Cloud Ingestion

## Repository Structure

- `app.py`: main simulator entrypoint
- `sensor_simulator/`: telemetry generation and PLC threshold logic
- `mqtt/`: MQTT publisher implementation
- `docker-compose.yml`: local stack (Mosquitto, InfluxDB, Telegraf, Grafana, sensor-app)
- `kubernetes/`: Kubernetes manifests for edge components
- `services/`: ingestion and forwarding services
- `aws_iot/`: AWS IoT bridge and offline queue components
- `docs/`: phase-by-phase implementation and architecture notes

## Quick Start (Local Docker Stack)

Prerequisites:
- Docker Desktop
- Git

1. Clone the repository:

```powershell
git clone https://github.com/sarapriyain09/sensor-app
cd sensor-app
```

2. Start the local stack:

```powershell
docker compose up --build -d
```

3. Check logs (optional):

```powershell
docker compose logs -f sensor-app
```

4. Open Grafana:
- URL: http://localhost:3000
- Default username: `admin`
- Default password: `admin`

5. Stop the stack:

```powershell
docker compose down
```

## Run Simulator Without Docker

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Run:

```powershell
python app.py
```

## Key Documentation

- `docs/five-phases-summary.md`
- `docs/local-dashboard-grafana.md`
- `docs/phase7-aws-iot-core.md`
- `docs/phase10-k8s-edge-to-eks-http-postgres.md`

## Notes

- This repo is designed for incremental deployment from local simulation to resilient edge-cloud architecture.
- Security-sensitive files (AWS certificates/keys) should never be committed.
