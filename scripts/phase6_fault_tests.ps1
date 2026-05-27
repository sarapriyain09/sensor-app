param(
    [int]$SensorReplicas = 2
)

$ErrorActionPreference = 'Stop'

function Assert-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Write-Section {
    param([string]$Title)
    Write-Host "" 
    Write-Host "=== $Title ==="
}

function Wait-Rollout {
    param(
        [string]$Deployment,
        [int]$TimeoutSeconds = 180
    )
    kubectl rollout status "deployment/$Deployment" "--timeout=${TimeoutSeconds}s"
}

Assert-Command kubectl

Write-Section "Context"
$ctx = kubectl config current-context
Write-Host "kubectl context: $ctx"

Write-Section "Current pods"
kubectl get pods -o wide

Write-Section "Test A: Pod crash (sensor-app)"
$sensorPod = kubectl get pods -l app=sensor-app -o jsonpath='{.items[0].metadata.name}'
if (-not $sensorPod) {
    throw "No sensor-app pods found"
}
Write-Host "Deleting pod: $sensorPod"
kubectl delete pod $sensorPod
Wait-Rollout -Deployment sensor-app
kubectl get pods -l app=sensor-app -o wide

Write-Section "Test B: Broker failure (mosquitto)"
$brokerPod = kubectl get pods -l app=mosquitto -o jsonpath='{.items[0].metadata.name}'
if (-not $brokerPod) {
    throw "No mosquitto pods found"
}
Write-Host "Deleting pod: $brokerPod"
kubectl delete pod $brokerPod
Wait-Rollout -Deployment mosquitto
kubectl get pods -l app=mosquitto -o wide

Write-Section "Test C: Scale sensor-app"
Write-Host "Scaling sensor-app to $SensorReplicas replicas"
kubectl scale deployment/sensor-app "--replicas=$SensorReplicas"
Wait-Rollout -Deployment sensor-app
kubectl get pods -l app=sensor-app -o wide

Write-Section "Recent sensor-app logs"
kubectl logs -l app=sensor-app --tail=10

Write-Host "Done."
