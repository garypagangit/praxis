param(
    [string]$InstanceId = "i-0bd262c42220bb4a2",
    [string]$Profile = "praxis-build",
    [string]$Region = "us-east-1",
    [string]$Bucket = "praxis-garypagan-272615233626-us-east-1"
)

$ErrorActionPreference = "Stop"

$aws = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
if (!(Test-Path $aws)) {
    $aws = "aws"
}

$remoteCommand = @'
set -euo pipefail
SRC=/mnt/praxis/datasets/darpa-tc/e5/cadets/
DST=s3://praxis-garypagan-272615233626-us-east-1/datasets/darpa-tc/raw/engagement-5/cadets/
LOG=/mnt/praxis/logs/darpa-e5-cadets-partial-sync-20260509.log
{
  date -u
  echo "Syncing partial Cadets mirror from $SRC to $DST"
  aws s3 sync "$SRC" "$DST" --only-show-errors
  echo "Partial sync complete"
  aws s3 ls "$DST" --recursive --summarize | tail -20
  date -u
} | tee "$LOG"
'@

$payload = @{
    commands = @($remoteCommand)
} | ConvertTo-Json -Compress

$tmp = New-TemporaryFile
try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($tmp, $payload, $utf8NoBom)
    & $aws ssm send-command `
        --instance-ids $InstanceId `
        --document-name AWS-RunShellScript `
        --parameters "file://$tmp" `
        --profile $Profile `
        --region $Region `
        --query "Command.CommandId" `
        --output text
}
finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}
