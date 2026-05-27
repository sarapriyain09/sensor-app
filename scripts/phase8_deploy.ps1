param(
  [string]$StackName = "sensor-app-phase8",
  [string]$Region = "us-east-1",
  [string]$TopicFilter = "factory/+/telemetry",
  [string]$TimestreamDatabaseName = "sensor_app",
  [string]$TimestreamTableName = "telemetry",
  [string]$IotRuleName = "sensor_app_telemetry_to_timestream",
  [ValidateSet("true","false")][string]$EnableSnsAlerts = "true"
)

$ErrorActionPreference = "Stop"

$Template = "aws/phase8/cloudformation.yaml"
if (-not (Test-Path $Template)) {
  throw "Template not found: $Template"
}

Write-Host "Deploying Phase 8 stack..." -ForegroundColor Cyan
Write-Host "  Stack:  $StackName"
Write-Host "  Region: $Region"
Write-Host "  Topic:  $TopicFilter"
Write-Host "  TS DB:  $TimestreamDatabaseName"
Write-Host "  TS Tbl: $TimestreamTableName"
Write-Host "  Rule:   $IotRuleName"
Write-Host "  SNS:    $EnableSnsAlerts"

aws cloudformation deploy `
  --region $Region `
  --stack-name $StackName `
  --template-file $Template `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides `
      TopicFilter=$TopicFilter `
      TimestreamDatabaseName=$TimestreamDatabaseName `
      TimestreamTableName=$TimestreamTableName `
      IotRuleName=$IotRuleName `
      EnableSnsAlerts=$EnableSnsAlerts

Write-Host "\nStack deployed. Outputs:" -ForegroundColor Green
aws cloudformation describe-stacks --region $Region --stack-name $StackName `
  --query "Stacks[0].Outputs" --output table

Write-Host "\nNext checks:" -ForegroundColor Yellow
Write-Host "  1) Verify IoT Rule:" 
Write-Host "     aws iot get-topic-rule --region $Region --rule-name $IotRuleName"
Write-Host "  2) Query Timestream (example):"
Write-Host "     aws timestream-query query --region $Region --query-string \"SELECT time, measure_name, measure_value::varchar, machine_id FROM \\\"$TimestreamDatabaseName\\\".\\\"$TimestreamTableName\\\" ORDER BY time DESC LIMIT 10\""
