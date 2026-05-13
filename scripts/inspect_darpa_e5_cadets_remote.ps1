param(
    [string]$InstanceId = "i-0bd262c42220bb4a2",
    [string]$Profile = "praxis-build",
    [string]$Region = "us-east-1"
)

$ErrorActionPreference = "Stop"

$aws = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
if (!(Test-Path $aws)) {
    $aws = "aws"
}

$remoteCommand = @'
set -euo pipefail
ROOT=/mnt/praxis/datasets/darpa-tc/e5/cadets
echo "CADets local files:"
find "$ROOT" -maxdepth 1 -type f | sort | head -5
FIRST=$(find "$ROOT" -maxdepth 1 -type f -name '*.gz' | sort | head -1)
echo "FIRST=$FIRST"
echo "file:"
file "$FIRST"
echo "gzip test:"
gzip -t "$FIRST" && echo "gzip_ok"
echo "decompressed first 1024 bytes, hex/ascii:"
gzip -cd "$FIRST" | head -c 1024 | od -An -tx1c | head -60
echo "printable strings:"
gzip -cd "$FIRST" | strings | head -40
'@

$payload = @{
    commands = @($remoteCommand)
} | ConvertTo-Json -Compress

$tmp = New-TemporaryFile
try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($tmp, $payload, $utf8NoBom)
    $commandId = & $aws ssm send-command `
        --instance-ids $InstanceId `
        --document-name AWS-RunShellScript `
        --parameters "file://$tmp" `
        --profile $Profile `
        --region $Region `
        --query "Command.CommandId" `
        --output text
    Write-Host "CommandId=$commandId"
    Start-Sleep -Seconds 4
    & $aws ssm get-command-invocation `
        --command-id $commandId `
        --instance-id $InstanceId `
        --profile $Profile `
        --region $Region `
        --query "{Status:Status,Stdout:StandardOutputContent,Stderr:StandardErrorContent}" `
        --output json
}
finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}
