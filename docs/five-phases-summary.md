# Phase 1 → Phase 10 Summary

Title: **Fault-Tolerant Kubernetes-Based Edge–Cloud Architecture for Industrial IoT Applications**

This file consolidates **Phases 1–10** into a thesis-ready summary, including an abstract, contributions, evaluation plan, conclusion, and future work.

---

## Abstract

This work designs and validates a fault-tolerant Kubernetes-based edge–cloud architecture for industrial IoT telemetry. The system supports continuous edge operation during intermittent connectivity while preserving security and observability. At the edge, telemetry is produced and transported via MQTT, buffered during outages, and visualized using a fully offline dashboard stack (MQTT → Telegraf → InfluxDB → Grafana). For cloud integration, the final design uses an HTTPS ingestion service on EKS that verifies RS256-signed JWTs and performs idempotent inserts into AWS RDS PostgreSQL using a per-event identifier to safely handle retries. The architecture is evaluated through controlled failure-injection experiments (network outages, broker restarts, pod restarts, rolling updates) and measured using recovery time, backlog growth/drain behavior, duplicate-rate suppression, and alert detection time. Results demonstrate that store-and-forward buffering plus idempotent writes enables reliable recovery after disruptions, while offline dashboards maintain operator visibility even without cloud connectivity.

---

## Condensed 5-Phase Plan (Aligned to This Repo)

This section maps a **5-phase** roadmap to the implemented repo phases (1–10). Phase titles are kept intentionally close to the proposed plan, but the content reflects what is actually implemented and validated here.

### Phase 1 — Python MQTT simulator + Mosquitto + Grafana dashboard

- Implemented: simulator + PLC evaluation + MQTT publishing to Mosquitto.
- Implemented: **fully offline** local observability stack (Mosquitto → Telegraf → InfluxDB → Grafana).
- Repo mapping: Phases 1–3 (simulator/PLC/MQTT) + Phase 8 (offline dashboard).

### Phase 2 — Edge node (Raspberry Pi target) + FastAPI backend + PostgreSQL

- Implemented: edge→cloud forwarding model with **store-and-forward buffering** and retries.
- Implemented: cloud **ingestion API** (FastAPI) that verifies **RS256 JWT** and performs **idempotent inserts** into PostgreSQL (RDS).
- Notes: the repo validates the design on Kubernetes (Minikube/EKS). Raspberry Pi is a deployment target (e.g., K3s) rather than a separate architecture.
- Repo mapping: Phase 10 (HTTPS + RS256 JWT + Postgres).

### Phase 3 — Docker Compose + multi-machine simulation + alerts

- Implemented: Docker image + Docker Compose for a repeatable local stack.
- Partially implemented: multi-machine behavior via `MACHINE_ID`/`FACTORY_ID` overrides; can be extended to multiple simulator services in Compose for true multi-machine load.
- Implemented: alert/state generation in the telemetry payload (RUNNING/WARNING/FAULT + alerts) and alerting pathways via dashboards/monitoring.
- Repo mapping: Phase 4 (Compose) + Phase 2 (PLC alerts in payload) + Phases 8–9 (dashboard + alerting/monitoring patterns).

### Phase 4 — Kubernetes/K3s + (optional) KubeEdge + edge–cloud sync

- Implemented: Kubernetes deployments for Mosquitto + sensor-app for self-healing and fault-injection experiments.
- Implemented: edge–cloud sync patterns via:
   - HTTPS batching with buffering (Phase 10), and
   - optional MQTT bridge-to-cloud patterns (Phase 7).
- Not implemented: KubeEdge-specific deployment (candidate future enhancement if you want edge device management and cloud-assisted orchestration).
- Repo mapping: Phase 5 (K8s edge) + Phase 6 (fault tolerance tests) + Phases 7/10 (edge→cloud paths).

### Phase 5 — AI anomaly detection + predictive maintenance + digital twin visualization

- Not implemented (future work): ML/anomaly detection on stored telemetry, predictive maintenance modeling, and digital twin UI.
- Recommended anchors:
   - run anomaly detection as a separate service consuming stored telemetry or a stream
   - visualize via Grafana overlays and/or a dedicated twin UI
- Repo mapping: Future Work.

---

## End-to-End Architecture (Edge → Cloud)

The complete pipeline implemented across the phases is:

Sensors → MQTT Broker → Edge Processing → Local Edge Storage (SQLite / InfluxDB) → Edge Dashboard (Offline) → HTTPS + RS256 JWT → Cloud API (EKS) → AWS RDS PostgreSQL

```mermaid
flowchart TD
   A[Sensors] --> B[MQTT Broker]
   B --> C[Edge Processing]
   C --> D[Local Edge Storage<br/>(SQLite / InfluxDB)]
   D --> E[Edge Dashboard<br/>(Offline)]
   E --> F[HTTPS + RS256 JWT]
   F --> G[Cloud API<br/>(EKS)]
   G --> H[AWS RDS PostgreSQL]
```

### Implementation Mapping (Repo → Runtime)

| Layer | Component | Repo location (examples) | Runs on |
|---|---|---|---|
| Sensors | Telemetry generation | `sensor_simulator/` | Edge (local) |
| Edge processing | PLC logic (state/alerts) | `sensor_simulator/plc.py` | Edge (local) |
| MQTT | Publish + broker | `mqtt/publisher.py`, `docker/mosquitto/`, `kubernetes/mosquitto-*.yaml` | Edge (local) |
| Local edge storage | Offline dashboard TSDB | `docker/local-dashboard/` (Telegraf→InfluxDB→Grafana) | Edge (local, offline) |
| Local edge storage | Store-and-forward queue | `aws_iot/offline_queue.py` (SQLite queue) | Edge (local K8s) |
| Edge dashboard | Grafana offline dashboards | `docker/local-dashboard/grafana/` | Edge (local, offline) |
| Security | RS256 JWT sign/verify | `services/edge_forwarder/app/jwt_utils.py`, `services/ingestion_api/app/security.py` | Edge + Cloud |
| Cloud API | HTTPS ingestion API | `services/ingestion_api/` | Cloud (EKS) |
| Cloud storage | Postgres schema + idempotent inserts | `services/ingestion_api/sql/schema.sql` | Cloud (RDS PostgreSQL) |

---

## Phase 1 — Sensor Simulation

Condensed plan mapping: **Phase 1 (Python MQTT simulator + Mosquitto + Grafana dashboard)**

### Objective

Generate continuous industrial-like telemetry samples for repeatable experiments.

### Architecture

- Python sensor simulator
- JSON telemetry output (stdout) as the base payload for downstream phases

### Implementation Highlights

- Realistic-ish telemetry ranges (temperature, vibration, RPM, pressure)
- Deterministic payload structure suitable for MQTT/cloud ingestion

### Validation / Evidence

- Continuous telemetry generation verified locally

---

## Phase 2 — Simulated PLC Logic

Condensed plan mapping: **Phase 1 (Python MQTT simulator + Mosquitto + Grafana dashboard)**

### Objective

Model PLC-style evaluation to derive operational state and alerts from raw telemetry.

### Architecture

- PLC evaluator processes each telemetry sample
- Thresholds and evaluation behavior are configurable

### Implementation Highlights

- `state`: RUNNING / WARNING / FAULT
- `alerts`: e.g., overheat and vibration faults
- Thresholds configured via settings

### Validation / Evidence

- PLC state transitions observed as telemetry crosses thresholds

---

## Phase 3 — MQTT Publish (Local)

Condensed plan mapping: **Phase 1 (Python MQTT simulator + Mosquitto + Grafana dashboard)**

### Objective

Publish telemetry to an edge-local broker to simulate industrial messaging and enable real-time consumers.

### Architecture

- Simulator publishes via MQTT to Mosquitto
- Topic strategy supports both full-payload and metric-specific consumption

### Implementation Highlights

- Full JSON topic: `factory/machine1/telemetry`
- Per-metric topics (temperature, vibration, rpm, pressure, state)
- Uses `paho-mqtt`

### Validation / Evidence

- Live publishes verified against local broker topics

---

## Phase 4 — Containerization (Docker + Docker Compose)

Condensed plan mapping: **Phase 3 (Docker Compose + multi-machine simulation + alerts)**

### Objective

Package and run the edge stack consistently across environments.

### Architecture

- Docker image for the simulator
- Docker Compose stack for Mosquitto + simulator (MQTT publishing)

### Implementation Highlights

- One-command local startup for repeatable demos
- Clear separation of broker config and app runtime config

### Validation / Evidence

- Compose stack runs and produces MQTT telemetry continuously

---

## Phase 5 — Kubernetes (Minikube)

Condensed plan mapping: **Phase 4 (Kubernetes/K3s + edge–cloud sync)**

### Objective

Deploy the edge pipeline to Kubernetes to enable self-healing, scaling demonstrations, and fault-injection experiments.

### Architecture

- Mosquitto as Deployment + Service
- Sensor simulator as Deployment (multiple replicas)

### Implementation Highlights

- Sensor Deployment configured with 2 replicas for scaling/self-healing demonstrations
- Manifests for broker config and service discovery

### Validation / Evidence

- Workloads deploy cleanly and produce telemetry within the cluster

---

## Phase 6 — Fault Tolerance (Edge)

Condensed plan mapping: **Phase 4 (Kubernetes/K3s + edge–cloud sync)**

### Objective

Establish fault-tolerant behavior at the edge under common industrial conditions:

- Intermittent connectivity and broker restarts
- Bursty data generation
- Process/pod restarts and transient failures

### Architecture

- Sensor simulator / edge telemetry source
- Mosquitto MQTT broker
- Consumers/forwarders using reconnect/backoff patterns
- Buffering strategies (store-and-forward where applicable)

### Implementation Highlights

- Robust MQTT connection handling (reconnect delay, keepalive)
- QoS usage where appropriate
- Repeatable fault tests for outages and restarts

### Validation / Evidence

- Fault-injection tests show recovery behavior and continued ingestion after disruptions
- System remains stable during restarts (no crash loops)

---

## Phase 7 — AWS IoT Core Integration (Cloud Path)

Condensed plan mapping: **Phase 4 (Kubernetes/K3s + edge–cloud sync)**

### Objective

Create a cloud ingestion path for persistence and analysis using AWS managed services.

### Architecture

- AWS IoT Core topic ingestion
- Lambda processing
- DynamoDB persistence

### Implementation Highlights

- IoT policy and routing rules
- Lambda validation/transform
- DynamoDB writes and cloud-side storage structure

### Validation / Evidence

- End-to-end flow confirmed from edge topic publish to cloud persistence

---

## Phase 8 — Dashboards (Fully Offline Local Observability)

Condensed plan mapping: **Phase 1 (Python MQTT simulator + Mosquitto + Grafana dashboard)**

### Objective

Provide full local visibility even without internet/cloud access.

### Architecture (Offline)

- MQTT (Mosquitto) → Telegraf → InfluxDB (InfluxQL) → Grafana OSS
- Entire stack runs locally using Docker Compose

### Implementation Highlights

- Telegraf MQTT consumer maps telemetry fields into Influx
- Grafana provisioning (datasource + dashboards)

### Key Issue Resolved

- Grafana panels showing “No data” were resolved by ensuring InfluxQL targets are executed as raw queries (Grafana 13 behavior requires explicit raw query mode for string queries).

### Validation / Evidence

- Dashboards refresh live from MQTT-derived measurements and remain usable offline

---

## Phase 9 — Edge/Cloud Monitoring & Alerts

Condensed plan mapping: **Phase 3 (Docker Compose + multi-machine simulation + alerts)**

### Objective

Add monitoring/alerting aligned to fault tolerance KPIs:

- Detect failures quickly
- Quantify backlog and recovery
- Track error rates and reliability indicators

### Architecture

- DynamoDB Streams → metrics Lambda → CloudWatch metrics
- CloudWatch alarms and dashboards (AMG optional)

### Implementation Highlights

- Alarm templates for ingestion failure signals and backlog-like indicators
- Monitoring write-up for evaluation and operations

### Validation / Evidence

- Monitoring outputs support measurable thesis evaluation (detection time, error spikes, recovery confirmation)

---

## Phase 10 — Final Thesis Architecture (K8s Edge → EKS Cloud via HTTPS + RS256 JWT + RDS PostgreSQL)

Condensed plan mapping: **Phase 2 (Edge node + FastAPI backend + PostgreSQL)** and **Phase 4 (Kubernetes/K3s + edge–cloud sync)**

### Objective

Implement the final secure and production-shaped pipeline:

- Secure edge→cloud telemetry forwarding over HTTPS
- Strong authentication using RS256 JWT
- Durable persistence in PostgreSQL (RDS)
- Idempotent writes to tolerate retries safely

### Architecture

**Edge (local Kubernetes):**

- MQTT publish at edge
- Edge forwarder:
  - Subscribes to MQTT
  - Buffers to a local SQLite queue (PVC)
  - Flushes batches to cloud endpoint over HTTPS

**Cloud (AWS):**

- EKS ingestion API:
  - Validates Bearer token (RS256 JWT)
  - Inserts into RDS PostgreSQL
  - Idempotency via unique event identifiers (event_id)

### Implementation Highlights

- Store-and-forward buffering ensures no data loss during outages
- Idempotent inserts: repeated deliveries do not create duplicates
- K8s hardening patterns applied (non-root, drop capabilities, seccomp RuntimeDefault)

### Validation / Evidence

- Suitable for the final evaluation experiments: outage buffering + recovery, retries, duplicates suppression, rolling updates

---

## Main Contributions

- A phased implementation roadmap from edge fault tolerance to secure cloud ingestion with measurable validation outputs.
- A fully offline edge observability stack supporting live dashboards without internet.
- A secure edge→cloud ingestion pipeline using HTTPS + RS256 JWT verification and PostgreSQL persistence.
- Idempotency-by-design using per-event identifiers to safely handle retries.
- Monitoring and alerting approach aligned to reliability KPIs and failure recovery.

---

## Evaluation Plan (Experiments)

Use these experiments to produce thesis results/graphs:

1. **Network outage (Edge→Cloud blocked)**
   - Measures: queue growth rate, max queue depth, time-to-drain after restore, recovery time.

2. **Broker restart (Mosquitto restart)**
   - Measures: reconnect time, message loss rate (given QoS), dashboard continuity.

3. **Ingestion pod failure (EKS)**
   - Measures: downtime window, retries observed, duplicates suppressed by idempotency.

4. **Rolling update (EKS ingestion)**
   - Measures: availability during rollout, backlog stability, recovery to steady-state.

5. **Security enforcement (JWT invalid/expired)**
   - Measures: rejection behavior (HTTP 401), queue retention until valid replay succeeds.

Recommended metrics to log/plot:

- Queue depth over time
- Recovery time after disruption
- End-to-end latency (p50/p95)
- Inserted vs duplicates during replay
- Alarm detection time and MTTR proxy

---

## Conclusion

This thesis delivered and validated a fault-tolerant, secure, and observable industrial IoT telemetry architecture spanning edge and cloud Kubernetes. The phased implementation demonstrated that reliability is achieved by combining resilient edge messaging (reconnect/backoff), store-and-forward buffering during connectivity loss, and idempotent cloud persistence that safely tolerates retries. A fully offline dashboard stack ensured that operators retain real-time visibility even when cloud connectivity is unavailable. For cloud integration, HTTPS ingestion secured with RS256 JWT and PostgreSQL storage provided a production-aligned data path suitable for industrial environments. Overall, controlled failure-injection scenarios (network outage, restarts, rolling updates) showed consistent recovery behavior, controlled backlog drain after outages, and duplicate suppression via event-level deduplication, confirming the architecture’s suitability for fault-tolerant IIoT deployments.

---

## Future Work

- **Stronger device identity:** Replace shared JWT keys with per-device identities (SPIFFE/SPIRE or AWS IoT X.509), plus rotation and revocation.
- **End-to-end encryption posture:** Enforce mTLS edge→cloud, formalize TLS policy, and add continuous compliance checks.
- **Message semantics & ordering:** Add sequence numbers and ordering guarantees per machine/topic; adopt transactional outbox patterns where needed.
- **Backpressure & rate control:** Adaptive batching, jittered exponential backoff, and cloud throttling signals to keep queues bounded.
- **Observability depth:** Add OpenTelemetry tracing and SLOs (availability, ingest latency, backlog drain time) with automated reporting.
- **Low-code edge orchestration (optional):** Evaluate Node-RED-style flow tooling for operator-editable MQTT routing/transforms; excluded from the baseline implementation to keep the runtime stack simpler and more testable.
- **Higher durability at edge:** Evaluate alternatives to SQLite for node failure scenarios (local Postgres, embedded replication, or lightweight brokers).
- **Data lifecycle & governance:** Retention policies, anonymization where required, schema evolution and compatibility testing.
- **Broader evaluation:** Long-duration tests with realistic industrial patterns and comparisons to alternate designs (direct IoT Core publish, Kafka at edge, MQTT bridge-to-cloud).
