# Phase 8 — Storage + Dashboard + Alerts (AWS)

Goal: take the telemetry you already see in AWS IoT MQTT test client and build:

- AWS IoT Core (already done)
- Lambda ingestion
- Storage (Timestream preferred, DynamoDB supported)
- Amazon Managed Grafana dashboard
- Alerting logic (SNS on `FAULT`)

This repo includes CloudFormation templates for both storage paths.

---

## Architecture

Topic path:

`edge sensor-app` → local Mosquitto → `aws-iot-bridge` → **AWS IoT Core** (`factory/+/telemetry`) → **IoT Rule** → **Lambda** → **Timestream** → **Grafana**

---

## Deploy ingestion (CloudFormation)

Note: AWS IoT Rule names must match `^[a-zA-Z0-9_]+$` (letters, numbers, underscores only).

### Option A (recommended): Timestream

Template:
- `aws/phase8/cloudformation.yaml`

Deploy using AWS CLI (region must match your IoT endpoint, e.g. `us-east-1`):

```powershell
aws cloudformation deploy `
  --stack-name sensor-app-phase8 `
  --template-file aws/phase8/cloudformation.yaml `
  --capabilities CAPABILITY_NAMED_IAM
```

Or use the helper script:

```powershell
./scripts/phase8_deploy.ps1 -Region us-east-1
```

Default IoT Rule name:

- `sensor_app_telemetry_to_timestream`

### Option B: DynamoDB (when Timestream has issues)

Important: Amazon Managed Grafana does **not** query DynamoDB telemetry directly.
This option uses:

**DynamoDB + Streams → Metrics Lambda → CloudWatch Metrics → Managed Grafana (CloudWatch data source)**

Template:
- `aws/phase8/cloudformation-dynamodb.yaml`

Helper script (prompts for your existing ingestion Lambda ARN):

```powershell
./scripts/phase8_deploy_dynamodb.ps1 -Region us-east-1
```

If the DynamoDB table already exists (recommended when you previously created `factoryTelemetry`):

1) Ensure DynamoDB Streams are enabled on the table (example uses `NEW_IMAGE`):

```powershell
aws dynamodb update-table --region us-east-1 --table-name factoryTelemetry --stream-specification StreamEnabled=true,StreamViewType=NEW_IMAGE
```

2) Deploy using existing table mode:

```powershell
./scripts/phase8_deploy_dynamodb.ps1 -Region us-east-1 -UseExistingTable true -DynamoTableName factoryTelemetry
```

Default IoT Rule name:

- `sensor_app_telemetry_to_dynamodb`

After deploy, verify the IoT Rule exists and is enabled:

```powershell
aws iot get-topic-rule --region us-east-1 --rule-name sensor_app_telemetry_to_dynamodb
```

---

## Verify data is being stored

1) Publish data (your bridge already does this)
2) Query Timestream (example):

```powershell
$DB = "sensor_app"
$TABLE = "telemetry"
aws timestream-query query --query-string "SELECT time, measure_name, measure_value::double, machine_id FROM \"$DB\".\"$TABLE\" WHERE measure_name = 'temperature_c' ORDER BY time DESC LIMIT 10"
```

Notes:
- This template writes one record per field (measure) to keep ingestion simple.
- Dimensions are `factory_id` and `machine_id`.

If you are using **DynamoDB option**:
- Verify the DynamoDB table is receiving items.
- Then verify CloudWatch metrics are being emitted (namespace default: `SensorApp/Telemetry`).

---

## Managed Grafana (dashboard)

This phase assumes **Amazon Managed Grafana (AMG)**.

### 1) Create AMG workspace

Create an Amazon Managed Grafana workspace in the AWS console.

Notes (common gotchas):
- AMG typically uses IAM Identity Center for user access; make sure you can sign in.
- Keep the workspace in the same region as your Timestream DB.

### 2) Add Timestream data source

In the AMG workspace:

1) Go to **Connections → Data sources → Add data source**.
2) Choose **Amazon Timestream**.
3) Configure authentication (workspace IAM role / AWS-managed auth depending on your setup).
4) Save & Test.

### 3) Import the dashboard JSON

This repo includes a starter dashboard you can import:

- `aws/phase8/managed-grafana-dashboard.json`

Steps:
1) In Grafana: **Dashboards → New → Import**
2) Upload the JSON file.
3) Set the variable **DS_TIMESTREAM** to your Timestream data source UID.
4) Set **machine_id** (textbox) to the machine you want to view (e.g. `machine-001`).

Panels included:
- Temperature (line)
- Vibration (line)
- RPM (line)
- Pressure (line)
- Current State (stat)
- Recent FAULT Events (table)

### DynamoDB path: AMG dashboard via CloudWatch

If you deployed the **DynamoDB option**, the stack emits CloudWatch custom metrics (default namespace: `SensorApp/Telemetry`) with dimension:

- `MachineId = <machine_id>`

Import the CloudWatch dashboard JSON:

- `aws/phase8/managed-grafana-dashboard-cloudwatch.json`

Steps:
1) Add the **CloudWatch** data source in AMG.
2) Import the JSON.
3) Set `DS_CLOUDWATCH` to your CloudWatch datasource UID.
4) Set `machine_id`.

Metrics expected (depending on your ingestion schema):
- `temperature_c`
- `vibration_mm_s` (or `vibration`)
- `rpm`
- `pressure_bar` (or `pressure`)
- `fault` (count when `state == FAULT`)

Example Timestream query for temperature:

```sql
SELECT
  time,
  measure_value::double AS temperature_c,
  machine_id
FROM "sensor_app"."telemetry"
WHERE measure_name = 'temperature_c'
ORDER BY time ASC
```

If you have multiple machines, group/legend by `machine_id`.

---

## Alerts

The template creates an SNS topic `sensor-app-alerts` (enabled by default) and the Lambda publishes the full payload when:

- `state == FAULT`

To receive alerts:
- subscribe your email to the SNS topic in the AWS console

If you want to disable alerts:

```powershell
aws cloudformation deploy `
  --stack-name sensor-app-phase8 `
  --template-file aws/phase8/cloudformation.yaml `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides EnableSnsAlerts=false
```

### Phase 9 (recommended): CloudWatch alarms (DynamoDB metrics path)

If you deployed the **DynamoDB + Streams → CloudWatch metrics** option, you can create CloudWatch alarms
for `temperature_c`, `vibration_mm_s`, `pressure_bar`, and `fault`.

See:
- `docs/phase9-edge-cloud-monitoring.md`
- `aws/phase9/cloudwatch-alarms.yaml`

---

## Optional later

- Run Grafana in Kubernetes (edge) for local-only dashboards.
- Add anomaly detection (ML) on top of stored telemetry.
- Add a digital twin view (AWS IoT TwinMaker or a custom UI).
