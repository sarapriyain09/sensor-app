# Phase 6 — Fault Tolerance Tests (Minikube)

This phase demonstrates Kubernetes self-healing and service resilience using controlled failures.

## Preconditions

- Minikube running: `minikube status`
- Context set: `kubectl config current-context` → `minikube`
- Workloads deployed: `kubectl get deploy,pods,svc`

## Useful watch commands

- Pods: `kubectl get pods -w`
- Sensor logs: `kubectl logs -l app=sensor-app -f`
- Mosquitto logs: `kubectl logs -l app=mosquitto -f`

## Test A — Pod crash (self-healing)

Goal: prove Deployments recreate pods.

1) List sensor pods:

```bash
kubectl get pods -l app=sensor-app
```

2) Delete one sensor pod:

```bash
kubectl delete pod <sensor-pod-name>
```

3) Observe Kubernetes recreates it:

```bash
kubectl get pods -l app=sensor-app -w
```

Evidence to capture:
- the deleted pod name
- the new pod name
- timestamps from `kubectl describe pod <new-pod>` Events

## Test B — Broker failure (MQTT resilience)

Goal: prove the system keeps running, and MQTT resumes after broker recovery.

1) Watch sensor logs in one terminal:

```bash
kubectl logs -l app=sensor-app -f
```

2) Delete the broker pod:

```bash
kubectl delete pod -l app=mosquitto
```

3) Wait for broker to become Ready again:

```bash
kubectl rollout status deployment/mosquitto --timeout=180s
```

Expected behavior:
- `sensor-app` pods remain Running.
- You may see temporary MQTT warnings during downtime.
- After Mosquitto is back, publishing continues.

## Test C — Scale + recovery

Goal: show scaling behavior and that replicas come up cleanly.

```bash
kubectl scale deployment/sensor-app --replicas=5
kubectl rollout status deployment/sensor-app --timeout=180s
kubectl get pods -l app=sensor-app
```

Scale back down:

```bash
kubectl scale deployment/sensor-app --replicas=2
```

## Optional Test D — Node disruption (Minikube)

Minikube is a single-node cluster, so “node failure” is limited, but you can still demonstrate restart recovery:

```bash
minikube stop
minikube start
kubectl get pods
```

## Cleanup

```bash
kubectl delete -f kubernetes/
```
