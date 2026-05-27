# Phase 7 — AWS IoT Core Integration (MQTT)

This phase sends edge telemetry from the local broker (Mosquitto) to AWS IoT Core.

**Important:** No AWS “login details” are required in code.
AWS IoT devices typically authenticate with an **X.509 certificate + private key**.
Those files must be kept secret and injected into Kubernetes as a Secret.

## What we built

- `sensor-app` publishes telemetry to the local broker topic: `factory/<machine>/telemetry`
- `aws-iot-bridge` subscribes to that local topic and republishes to AWS IoT Core:
  - `factory/<machine>/telemetry`

Bridge code: `aws_iot/bridge.py`

Kubernetes runs it as a module (so package imports work):
- `python -m aws_iot.bridge`

## AWS Console steps (you do these)

1) Create an IoT Thing (e.g., `machine1-thing`).
2) Create/download a device certificate and private key.
3) Attach an IoT policy allowing publish/connect (least privilege).
4) Note your AWS IoT endpoint (looks like `xxxxxxxxxxxx-ats.iot.<region>.amazonaws.com`).

For your setup:
- Endpoint: `axmuxp0nzbtg9-ats.iot.us-east-1.amazonaws.com`

You will end up with files like:
- `cert.pem` (certificate)
- `private.key` (private key)
- `AmazonRootCA1.pem` (CA)

## Create a Kubernetes Secret (do NOT commit keys)

From your machine (same where `kubectl` works):

```bash
kubectl create secret generic aws-iot-creds \
  --from-file=ca.pem=AmazonRootCA1.pem \
  --from-file=cert.pem=cert.pem \
  --from-file=private.key=private.key
```

## Configure the bridge

The bridge reads env vars (see `aws_iot/bridge.py`). Minimum:

- `AWS_IOT_ENABLED=1`
- `AWS_IOT_ENDPOINT=<your-endpoint>`

Optional defaults:
- `LOCAL_MQTT_HOST=mosquitto`
- `LOCAL_MQTT_TOPIC_FILTER=factory/+/telemetry`

## Deploy on Minikube

1) Ensure Mosquitto and sensor-app are running (Phase 5 manifests).
2) Apply the bridge manifest (added in `kubernetes/aws-iot-bridge-deployment.yaml`).

Then check logs:

```bash
kubectl logs -l app=aws-iot-bridge -f
```

## Validation / Evidence

- AWS IoT Core **MQTT test client** subscription to `factory/+/telemetry` shows live JSON telemetry forwarded from the edge.

## Notes

- The bridge is **offline-tolerant**: it enqueues outgoing AWS messages to an on-disk SQLite queue and flushes when AWS connectivity returns.
- For **at-least-once** delivery, set `AWS_IOT_QOS=1` (the Kubernetes manifest does this).
- Queue settings (optional):
  - `AWS_IOT_QUEUE_DB_PATH` (default: `/var/lib/aws-iot-bridge/queue.db`)
  - `AWS_IOT_QUEUE_MAX_MESSAGES` (default: `100000`)
  - `AWS_IOT_FLUSH_INTERVAL_SECONDS` (default: `1.0`)
  - `AWS_IOT_FLUSH_BATCH_SIZE` (default: `200`)
- Kubernetes persistence note: the provided manifest uses `emptyDir`, which survives network outages but not pod reschedules/restarts. For full durability on edge hardware, mount a persistent volume (e.g., `hostPath` on a single-node edge cluster or a PVC).

## Least-privilege IoT policy (template)

Attach a policy like this to your device certificate.

A ready-to-paste version for your account/client is in:
- `docs/aws-iot-policy-machine.json`

Replace `<ACCOUNT_ID>` with your AWS account id.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "iot:Connect",
      "Resource": "arn:aws:iot:us-east-1:<ACCOUNT_ID>:client/machine"
    },
    {
      "Effect": "Allow",
      "Action": "iot:Publish",
      "Resource": [
        "arn:aws:iot:us-east-1:<ACCOUNT_ID>:topic/factory/*/telemetry"
      ]
    }
  ]
}
```

If you change `AWS_IOT_CLIENT_ID` or `AWS_IOT_TOPIC_PREFIX`, update the policy to match.
