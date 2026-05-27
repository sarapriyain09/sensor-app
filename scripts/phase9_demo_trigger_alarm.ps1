param(
    [string]$Region = "us-east-1",
    [string]$AlarmName = "sensor-app-machine1-fault",
    [switch]$SkipReset
)

$ErrorActionPreference = "Stop"
$env:AWS_PAGER = ""

if (-not $SkipReset) {
    aws --no-cli-pager cloudwatch set-alarm-state `
        --region $Region `
        --alarm-name $AlarmName `
        --state-value OK `
        --state-reason "Demo: reset to OK"
}

aws --no-cli-pager cloudwatch set-alarm-state `
    --region $Region `
    --alarm-name $AlarmName `
    --state-value ALARM `
    --state-reason "Demo: force ALARM notification"

aws --no-cli-pager cloudwatch describe-alarms `
    --region $Region `
    --alarm-names $AlarmName `
    --query "MetricAlarms[0].{AlarmName:AlarmName,State:StateValue,Updated:StateUpdatedTimestamp,AlarmActions:AlarmActions}" `
    --output json
