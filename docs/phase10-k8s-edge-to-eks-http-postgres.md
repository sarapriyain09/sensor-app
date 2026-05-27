# Phase 10 — K8s Edge → EKS Cloud via HTTPS + JWT (RS256) + RDS PostgreSQL

Goal: implement a **fault-tolerant edge→cloud** telemetry pipeline:

- Edge cluster publishes MQTT
- Edge forwarder buffers locally and sends batches to cloud over **HTTPS**
- Cloud ingestion API verifies **RS256 JWT** and writes idempotently to **RDS PostgreSQL**

---

## Components

**Edge (local Kubernetes)**
- `mosquitto`
- `sensor-app`
- `edge-forwarder` (MQTT subscriber → SQLite queue (PVC) → HTTPS POST)

**Cloud (AWS)**
- EKS: `ingestion-api` Deployment + Service (HTTP LoadBalancer for quick-start; Ingress/TLS later)
- RDS PostgreSQL

---

## JWT keys (RS256)

Generate a keypair locally (do NOT commit keys):

```powershell
mkdir .\secrets 2>$null
$openssl = "C:\\Program Files\\Git\\usr\\bin\\openssl.exe"  # Git for Windows bundle
& $openssl genrsa -out .\secrets\jwt-private.pem 2048
& $openssl rsa -in .\secrets\jwt-private.pem -pubout -out .\secrets\jwt-public.pem
```

Edge forwarder uses `jwt-private.pem`.
Ingestion API uses `jwt-public.pem`.

---

## Database schema

Apply schema to Postgres (example):

- `services/ingestion_api/sql/schema.sql`

You can run it via `psql` against RDS:

```powershell
psql "$env:DATABASE_URL" -f services/ingestion_api/sql/schema.sql
```

Quick-start (no RDS yet): run PostgreSQL inside the cloud cluster (dev/demo)

Notes:
- This dev Postgres uses `emptyDir` (no PVC). Data will be lost if the pod is recreated.

1) Create a Postgres password secret (choose your own password):

```powershell
kubectl create secret generic postgres-dev --from-literal=password="CHANGE_ME"
```

2) Deploy Postgres:

```powershell
kubectl apply -f kubernetes/cloud/postgres-dev.yaml
```

3) Create the ingestion DB URL secret (points at the in-cluster `postgres` service):

```powershell
$pw = kubectl get secret postgres-dev -o jsonpath="{.data.password}" | %{ [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($_)) }
kubectl delete secret ingestion-api-db 2>$null
kubectl create secret generic ingestion-api-db \
  --from-literal=database_url="postgresql://sensorapp:$pw@postgres:5432/sensorapp"
```

4) Apply schema using a one-shot Job:

```powershell
kubectl delete configmap ingestion-api-schema 2>$null
kubectl create configmap ingestion-api-schema --from-file=schema.sql=services/ingestion_api/sql/schema.sql
kubectl apply -f kubernetes/cloud/ingestion-api-schema-job.yaml
```

---

## Cloud (EKS) deployment

1) Create a Secret with DB URL (RDS):

```powershell
kubectl create secret generic ingestion-api-db \
  --from-literal=database_url="postgresql://USER:PASSWORD@HOST:5432/DBNAME"
```

2) Create a Secret with the JWT public key:

```powershell
kubectl create secret generic ingestion-api-jwt \
  --from-file=public.pem=.\secrets\jwt-public.pem
```

3) Deploy the ingestion API:

- `kubernetes/cloud/ingestion-api.yaml`

If you do not have TLS/Ingress ready yet, expose it via a public HTTP LoadBalancer:

```powershell
kubectl apply -f kubernetes/cloud/ingestion-api-loadbalancer.yaml
kubectl get svc ingestion-api-lb
```

Notes:
- For a quick demo without TLS, use the LoadBalancer service above and set edge-forwarder `CLOUD_API_URL` to `http://<LB_DNS>/ingest/batch`.

---

## Edge (local K8s) deployment

1) Create Secret with JWT private key:

```powershell
kubectl create secret generic edge-forwarder-jwt \
  --from-file=private.pem=.\secrets\jwt-private.pem
```

2) Deploy edge-forwarder:

- `kubernetes/edge-forwarder-deployment.yaml`

Notes:
- Update `CLOUD_API_URL` to `https://<YOUR_INGEST_HOST>/ingest/batch`

---

## Fault-tolerance experiments (MSc evaluation)

1) **Network outage**: block edge egress to cloud
- Observe edge-forwarder queue depth grows
- Restore connectivity
- Observe queue drains and cloud inserts catch up

2) **Pod failure**
- delete ingestion-api pods → Deployment recreates
- verify no data loss (idempotent inserts)

3) **Rolling update**
- update ingestion-api image tag
- verify service stays available and queue remains bounded

Metrics to record:
- queue size over time
- time to recover after outage
- duplicate rate (ON CONFLICT) during retries
