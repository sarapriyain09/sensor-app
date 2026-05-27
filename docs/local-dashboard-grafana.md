# Local Dashboard (Grafana OSS) — CloudWatch Metrics

This is the simplest “local dashboard” path when your data is in AWS (IoT → Lambda → DynamoDB) and you already emit **CloudWatch custom metrics** (recommended).

Architecture:

AWS IoT Core → Lambda → DynamoDB → (DynamoDB Streams → Metrics Lambda) → CloudWatch Metrics → **Local Grafana**

---

## Prerequisites

- Docker Desktop running
- AWS CLI configured on your machine (Windows):

```powershell
aws configure
```

This creates:
- `$env:USERPROFILE\.aws\credentials`
- `$env:USERPROFILE\.aws\config`

Avoid committing any credentials to git.

---

## Start Grafana locally

Use the helper script:

```powershell
./scripts/local_grafana_start.ps1 -Region us-east-1
```

Then open:

- http://localhost:3000

Default login:
- user: `admin`
- pass: `admin` (change after first login)

---

## Add CloudWatch data source

In Grafana:

- Connections → Data sources → Add data source → **CloudWatch**

Notes:
- Because Grafana is running in Docker, it needs AWS credentials inside the container.
- The helper script mounts your local `~/.aws` files into the container and sets the AWS env vars.

---

## Import the dashboard

Import this dashboard JSON:

- `aws/phase8/managed-grafana-dashboard-cloudwatch.json`

During import / after import:

- Set variable `DS_CLOUDWATCH` to your CloudWatch datasource UID
- Set `machine_id` (textbox) e.g. `machine-001`

If metrics don’t show up yet:

```powershell
aws cloudwatch list-metrics --region us-east-1 --namespace SensorApp/Telemetry
```

---

## Expected metrics

Namespace:
- `SensorApp/Telemetry`

Dimension:
- `MachineId = <machine_id>`

Metric names (depends on your ingestion schema):
- `temperature_c`
- `vibration_mm_s` (or `vibration`)
- `rpm`
- `pressure_bar` (or `pressure`)
- `fault` (Count)
