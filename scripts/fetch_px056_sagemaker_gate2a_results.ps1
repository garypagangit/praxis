param(
  [Parameter(Mandatory = $true)]
  [string]$JobName,
  [string]$Profile = "praxis-build",
  [string]$Region = "us-east-1",
  [string]$Bucket = "praxis-garypagan-272615233626-us-east-1"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Remote = "s3://$Bucket/experiments/model-registry-hallucination/gate2a-live-pilot-20260721/results/$JobName/"
$Local = Join-Path $Root "reports\model_registry_hallucination\gate2a_live_pilot_20260721\$JobName"

New-Item -ItemType Directory -Path $Local -Force | Out-Null
aws s3 sync $Remote $Local --profile $Profile --region $Region --no-progress
if ($LASTEXITCODE -ne 0) {
  throw "aws s3 sync failed with exit code $LASTEXITCODE"
}

$SummaryPath = Join-Path $Local "summary.json"
$ReportPath = Join-Path $Local "PX056_GATE2A_LIVE_MODEL_OUTPUT_PILOT.md"
if (-not (Test-Path $SummaryPath)) {
  throw "Missing summary.json at $SummaryPath"
}
if (-not (Test-Path $ReportPath)) {
  throw "Missing report at $ReportPath"
}

[pscustomobject]@{
  job_name = $JobName
  s3_uri = $Remote
  local_dir = $Local
  summary = $SummaryPath
  report = $ReportPath
} | ConvertTo-Json -Depth 4
