param(
  [string]$Name = "sensor-app-grafana",
  [int]$Port = 3000,
  [string]$Region = "us-east-1",
  [string]$AwsProfile = "default"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw "docker not found. Install Docker Desktop first."
}

$awsDir = Join-Path $env:USERPROFILE ".aws"
$credentials = Join-Path $awsDir "credentials"
$config = Join-Path $awsDir "config"

if (-not (Test-Path $credentials)) {
  throw "AWS credentials not found at $credentials. Run: aws configure"
}
if (-not (Test-Path $config)) {
  Write-Host "Warning: AWS config not found at $config (continuing)." -ForegroundColor Yellow
}

# Create a persistent volume for Grafana data (idempotent).
$null = docker volume create "$Name-data" 2>$null

# Remove existing container if present.
$existing = docker ps -a --filter "name=^/$Name$" --format "{{.ID}}"
if ($existing) {
  Write-Host "Removing existing container $Name..." -ForegroundColor Yellow
  docker rm -f $Name | Out-Null
}

Write-Host "Starting Grafana..." -ForegroundColor Cyan
Write-Host "  URL:   http://localhost:$Port"
Write-Host "  AWS:   profile=$AwsProfile region=$Region"
Write-Host "  Mount: $awsDir -> /aws (read-only)"

# NOTE:
# - We mount ~/.aws into /aws, and point AWS SDK env vars there.
# - Grafana CloudWatch datasource uses AWS SDK credential chain.
# - Never pass access keys directly on the command line.

docker run -d --name $Name -p "$Port:3000" `
  -v "$Name-data:/var/lib/grafana" `
  -v "${awsDir}:/aws:ro" `
  -e "AWS_REGION=$Region" `
  -e "AWS_DEFAULT_REGION=$Region" `
  -e "AWS_PROFILE=$AwsProfile" `
  -e "AWS_SDK_LOAD_CONFIG=1" `
  -e "AWS_SHARED_CREDENTIALS_FILE=/aws/credentials" `
  -e "AWS_CONFIG_FILE=/aws/config" `
  grafana/grafana

Write-Host "\nGrafana is starting. Default login is admin / admin (change the password after first login)." -ForegroundColor Green
