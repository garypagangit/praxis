param(
    [Parameter(Mandatory = $true)]
    [string]$BucketName,
    [string]$Profile = "praxis-build",
    [string]$Prefix = "datasets/unraveled/network-flows",
    [string]$SourcePath = "C:\Users\garyp\OneDrive\Documents\codex\imports\unraveled\data\network-flows"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $SourcePath)) {
    throw "Source path not found: $SourcePath"
}

$destination = "s3://$BucketName/$Prefix"
Write-Host "Syncing $SourcePath -> $destination"

aws s3 sync $SourcePath $destination --profile $Profile --no-progress

Write-Host ""
Write-Host "Upload complete."
Write-Host "Destination: $destination"
