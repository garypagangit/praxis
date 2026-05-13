param(
    [string]$Region = "us-east-1",
    [string]$Profile = "praxis-build",
    [string]$BucketName = "praxis-garypagan-272615233626-us-east-1",
    [string]$RunPrefix = "experiments/provenance-window-factory/runs/full-e5cadets-20260511",
    [string]$LocalOut = "runs/full-e5cadets-window-factory-20260511"
)

$ErrorActionPreference = "Stop"

$aws = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
if (!(Test-Path -LiteralPath $aws)) {
    $aws = "aws"
}

$source = "s3://$BucketName/$RunPrefix/"
New-Item -ItemType Directory -Force -Path $LocalOut | Out-Null
& $aws s3 sync $source $LocalOut --profile $Profile --region $Region --no-progress

$cloudReport = Join-Path $LocalOut "report.md"
if (Test-Path -LiteralPath $cloudReport) {
    New-Item -ItemType Directory -Force -Path "reports/provenance_architecture" | Out-Null
    Copy-Item -LiteralPath $cloudReport -Destination "reports/provenance_architecture/FULL_CADETS_WINDOW_FACTORY_20260511.md" -Force
}

$features = Join-Path $LocalOut "window_features.csv"
if (!(Test-Path -LiteralPath $features)) {
    throw "Expected feature file not found: $features"
}

& ".\.venv\Scripts\python.exe" scripts\run_provenance_detector_zoo_gate.py `
    --features $features `
    --out-dir "runs/provenance-detector-zoo-gate-full-e5cadets-20260511" `
    --report "reports/provenance_architecture/PROVENANCE_DETECTOR_ZOO_GATE_FULL_E5CADETS_20260511.md"
