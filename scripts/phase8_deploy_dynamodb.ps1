param(
  [string]$StackName = "sensor-app-phase8-dynamodb",
  [string]$Region = "us-east-1",
  [string]$TopicFilter = "factory/+/telemetry",
  [string]$IotRuleName = "sensor_app_telemetry_to_dynamodb",
  [string]$IngestionLambdaArn = "",
  [string]$DynamoTableName = "factoryTelemetry",
  [string]$PartitionKeyName = "machine_id",
  [string]$SortKeyName = "timestamp",
  [string]$MetricsNamespace = "SensorApp/Telemetry",
  [ValidateSet("true","false")][string]$UseExistingTable = "false",
  [string]$ExistingDynamoTableStreamArn = ""
)

$ErrorActionPreference = "Stop"

$Template = "aws/phase8/cloudformation-dynamodb.yaml"
if (-not (Test-Path $Template)) {
  throw "Template not found: $Template"
}

if ([string]::IsNullOrWhiteSpace($IngestionLambdaArn)) {
  Write-Host "Enter your ingestion Lambda ARN (the one that writes to DynamoDB):" -ForegroundColor Yellow
  $IngestionLambdaArn = Read-Host "IngestionLambdaArn"
}

if ($UseExistingTable -eq "true" -and [string]::IsNullOrWhiteSpace($ExistingDynamoTableStreamArn)) {
  Write-Host "UseExistingTable=true. Resolving DynamoDB stream ARN for table '$DynamoTableName'..." -ForegroundColor Yellow
  $ExistingDynamoTableStreamArn = aws dynamodb describe-table --region $Region --table-name $DynamoTableName --query "Table.LatestStreamArn" --output text
  if ([string]::IsNullOrWhiteSpace($ExistingDynamoTableStreamArn) -or $ExistingDynamoTableStreamArn -eq "None") {
    throw "Could not resolve LatestStreamArn for table '$DynamoTableName'. Ensure DynamoDB Streams are enabled on the table, or pass -ExistingDynamoTableStreamArn explicitly."
  }
}

Write-Host "Deploying Phase 8 (DynamoDB) stack..." -ForegroundColor Cyan
Write-Host "  Stack:  $StackName"
Write-Host "  Region: $Region"
Write-Host "  Topic:  $TopicFilter"
Write-Host "  Rule:   $IotRuleName"
Write-Host "  Lambda: $IngestionLambdaArn"
Write-Host "  Table:  $DynamoTableName ($PartitionKeyName,$SortKeyName)"
Write-Host "  CW NS:  $MetricsNamespace"
Write-Host "  UseExistingTable: $UseExistingTable"
if ($UseExistingTable -eq "true") {
  Write-Host "  Table Stream ARN: $ExistingDynamoTableStreamArn"
}

aws cloudformation deploy `
  --region $Region `
  --stack-name $StackName `
  --template-file $Template `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides `
      TopicFilter=$TopicFilter `
      IotRuleName=$IotRuleName `
      IngestionLambdaArn=$IngestionLambdaArn `
      DynamoTableName=$DynamoTableName `
      PartitionKeyName=$PartitionKeyName `
      SortKeyName=$SortKeyName `
  MetricsNamespace=$MetricsNamespace `
  UseExistingTable=$UseExistingTable `
  ExistingDynamoTableStreamArn=$ExistingDynamoTableStreamArn

Write-Host "\nStack deployed. Outputs:" -ForegroundColor Green
aws cloudformation describe-stacks --region $Region --stack-name $StackName `
  --query "Stacks[0].Outputs" --output table

Write-Host "\nNext checks:" -ForegroundColor Yellow
Write-Host "  1) Verify IoT Rule:" 
Write-Host "     aws iot get-topic-rule --region $Region --rule-name $IotRuleName"
Write-Host "  2) Verify CloudWatch metrics are arriving (after a few messages):"
Write-Host "     aws cloudwatch list-metrics --region $Region --namespace $MetricsNamespace"
