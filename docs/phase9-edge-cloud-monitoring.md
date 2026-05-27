# Phase 9 — Edge–Cloud Deployment + Monitoring + Alerts (AWS)

Goal: demonstrate an **edge → cloud** Industrial IoT pipeline with measurable reliability and operations readiness:

- Edge deployment (Kubernetes)
- Secure forwarding to **AWS IoT Core**
- Storage + metrics in AWS
- Dashboards + alerts

---

## Target architecture

**Edge (Kubernetes / laptop / site)**

- `sensor-app` publishes telemetry to local broker (Mosquitto)
- `aws-iot-bridge` subscribes to `factory/+/telemetry` and republishes to AWS IoT Core over TLS
- Bridge is store-and-forward (buffers when AWS is unreachable; flushes on reconnect)

**Cloud (AWS)**

- AWS IoT Core receives MQTT messages
- IoT Rule invokes your ingestion Lambda
- Storage option:
  - DynamoDB (recommended for this phase when you want CloudWatch alarms)
- Metrics:
  - DynamoDB Streams → metrics Lambda → CloudWatch custom metrics
- Dashboards:
  - Amazon Managed Grafana (CloudWatch datasource)
- Alerts:
  - CloudWatch alarms → SNS email

---

## Prerequisites

- Phase 7 bridge configured and working (you can see messages in AWS IoT test client)
- Phase 8 DynamoDB + CloudWatch metrics stack deployed
  - see: `docs/phase8-dashboard.md`

Expected metrics shape (from Phase 8 default stack):

- Namespace: `SensorApp/Telemetry`
- Dimension: `MachineId=<machine_id>`

---

## Managed Grafana workspace (AMG)

This phase uses **Amazon Managed Grafana** (AMG) with a **CloudWatch** data source.

If you used the Phase 8 DynamoDB path (recommended for alarms), import the CloudWatch dashboard JSON:

- `aws/phase8/managed-grafana-dashboard-cloudwatch.json`

### 1) Get workspace URL (AWS CLI)

If you already created an AMG workspace (example name: `iiot-edge-cloud-grafana`), fetch its ID/status/URL:

```powershell
$region = 'us-east-1'
$name = 'iiot-edge-cloud-grafana'

$ws = aws --no-cli-pager grafana list-workspaces --region $region `
  --query "workspaces[?name=='$name'] | [0]" --output json | ConvertFrom-Json

$ws.id
$ws.status
$ws.endpoint
```

Wait until the status is `ACTIVE`:

```powershell
aws --no-cli-pager grafana describe-workspace --region $region --workspace-id $ws.id `
  --query "workspace.status" --output text
```

Open the workspace:

- `https://<endpoint>` (the `endpoint` value above)

### 2) Grant user access (AWS console)

AMG typically uses **IAM Identity Center** (AWS SSO). In the workspace, add at least one user/group
as an **Admin** so you can log in and manage data sources + dashboards.

If you see a banner like **“Security Assertion Markup Language (SAML) — Pending user input”** and you
cannot log in yet, the workspace was created with **SAML** as the auth provider and SAML setup is not
finished.

You have two options:

1) **Finish SAML configuration** (use your external IdP like Okta / Microsoft Entra ID / ADFS)
   - In AWS console (AMG workspace): upload your IdP metadata XML and configure the required assertion
     attributes/role mapping.
   - Helpful CLI introspection:

```powershell
aws --no-cli-pager grafana describe-workspace-authentication --region $region --workspace-id $ws.id
```

2) **Switch to IAM Identity Center (AWS SSO)** (simplest for most demos)
   - Ensure IAM Identity Center is enabled in your AWS account.
     - If the CLI fails with: `ValidationException: SSO is not enabled in any region.`
       go to AWS Console → **IAM Identity Center** → **Enable** (choose your Identity Center home region).
     - Quick verification (should return a non-empty `Instances` list):

```powershell
aws --no-cli-pager sso-admin list-instances --region us-east-1 --output json
```
   - Then update workspace authentication providers:

```powershell
aws --no-cli-pager grafana update-workspace-authentication --region $region --workspace-id $ws.id `
  --authentication-providers AWS_SSO
```

### 3) CloudWatch data source + import dashboard

1) In the AMG workspace: add/confirm the **CloudWatch** data source
  - In Grafana: **Connections → Data sources → Add data source**
  - Choose: **CloudWatch**
  - Region: `us-east-1`
  - Auth: use the **workspace IAM role** / AWS-managed auth (default for AMG)
  - Click **Save & test**

If the CloudWatch data source page shows **504 Gateway Time-out**, check whether the workspace is
attached to a VPC without NAT/VPC endpoints. For quick-start demos, the simplest fix is to remove
the workspace VPC configuration:

```powershell
aws --no-cli-pager grafana update-workspace --region us-east-1 --workspace-id $ws.id --remove-vpc-configuration
```

2) Import the dashboard JSON:
  - In Grafana: **Dashboards → New → Import**
  - Upload: `aws/phase8/managed-grafana-dashboard-cloudwatch.json`
  - When prompted, select your CloudWatch data source for `DS_CLOUDWATCH`

3) Set the dashboard variables:
  - `machine_id` → `machine1` (must match the CloudWatch dimension `MachineId`)

Expected metrics:
- Namespace: `SensorApp/Telemetry`
- Dimension: `MachineId=<machine_id>`

Metrics currently emitted by the default Phase 8 stack:
- `temperature_c`
- `pressure_bar`
- `vibration_mm_s`
- `rpm`
- `fault`

If the dashboard imports but panels show **No data**, ensure the CloudWatch query **period** is a valid
value (CloudWatch uses seconds; `60` is a safe default for 1-minute metrics).

---

## Deploy CloudWatch alarms (Phase 9)

This repo includes a CloudFormation template that creates:
- an SNS topic
- CloudWatch alarms for one machine (`MachineId` dimension)
- optional email/SMS subscription

Template:
- `aws/phase9/cloudwatch-alarms.yaml`

Example deploy:

```powershell
aws cloudformation deploy `
  --stack-name sensor-app-phase9-alarms `
  --template-file aws/phase9/cloudwatch-alarms.yaml `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides `
      MetricsNamespace=SensorApp/Telemetry `
      MachineId=machine1 `
      AlarmEmail=you@example.com
```

Use an existing SNS topic (recommended if you want to manage subscriptions yourself):

```powershell
aws cloudformation deploy `
  --stack-name sensor-app-phase9-alarms `
  --template-file aws/phase9/cloudwatch-alarms.yaml `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides `
      MetricsNamespace=SensorApp/Telemetry `
      MachineId=machine1 `
      ExistingAlarmTopicArn=arn:aws:sns:us-east-1:123456789012:mytopic
```

Notes:
- When `ExistingAlarmTopicArn` is set, this stack does not create an SNS topic and does not manage subscriptions.
- Create/confirm the email (or SMS) subscription directly on that topic.

SMS deploy (recommended if email keeps auto-unsubscribing):

```powershell
aws cloudformation deploy `
  --stack-name sensor-app-phase9-alarms `
  --template-file aws/phase9/cloudwatch-alarms.yaml `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides `
      MetricsNamespace=SensorApp/Telemetry `
      MachineId=machine1 `
      AlarmSmsNumber=+14155552671
```

Notes:
- Email subscriptions require confirmation.
- If you do not want an email subscription, omit `AlarmEmail`.
- SMS subscriptions must be E.164 formatted (leading `+` and country code).
- If you do not want an SMS subscription, omit `AlarmSmsNumber`.

Verify the subscription is active (not `PendingConfirmation` / `Deleted`):

```powershell
$topicArn = aws --no-cli-pager cloudformation describe-stacks `
  --region us-east-1 `
  --stack-name sensor-app-phase9-alarms `
  --query "Stacks[0].Outputs[?OutputKey=='AlarmTopicArn'].OutputValue" `
  --output text

aws --no-cli-pager sns list-subscriptions-by-topic `
  --region us-east-1 `
  --topic-arn $topicArn `
  --query "Subscriptions[].{Endpoint:Endpoint,Arn:SubscriptionArn}" `
  --output table
```

If the list output is confusing (sometimes it can still show `Deleted` entries), verify the specific subscription ARN directly:

```powershell
aws --no-cli-pager sns get-subscription-attributes `
  --region us-east-1 `
  --subscription-arn <subscription-arn>
```

Look for `PendingConfirmation: false`.

Send a test notification:

```powershell
aws --no-cli-pager sns publish `
  --region us-east-1 `
  --topic-arn $topicArn `
  --subject "Sensor App SNS Test" `
  --message "Test publish from sensor-app-phase9-alarms"
```

Troubleshooting:
- If an email endpoint shows `Deleted`, re-run the deploy with a fresh alias (e.g., Gmail `+alias`) and/or re-deploy the stack with `AlarmEmail=<that alias>` to recreate the subscription.

---

## What to demonstrate (MSc evaluation)

### 1) Edge→cloud reliability

- Stop internet / block AWS egress temporarily
- Keep `sensor-app` publishing locally
- Restore connectivity
- Show the bridge flushes queued messages

Metrics to report:
- message loss rate during outage window
- time to flush after reconnect

### 2) Monitoring + alerts

- Induce a FAULT condition in the simulator (overheat or vibration)
- Confirm:
  - CloudWatch `fault` metric increments
  - CloudWatch Alarm transitions to ALARM
  - SNS notification is sent

Demo helper (forces an OK → ALARM notification in one command):

```powershell
./scripts/phase9_demo_trigger_alarm.ps1 -Region us-east-1 -AlarmName sensor-app-machine1-fault
```

### 3) Dashboards

- In AMG, import the CloudWatch dashboard:
  - `aws/phase8/managed-grafana-dashboard-cloudwatch.json`

---

## Suggested alarm thresholds

Use thresholds aligned with your PLC logic:
- temperature: 88°C (fault)
- vibration: 11 mm/s (fault)
- pressure: depends on your simulator range
