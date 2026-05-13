param(
    [string]$InstanceId = "i-0bd262c42220bb4a2",
    [string]$Region = "us-east-1",
    [string]$Profile = "praxis-build",
    [string]$BucketName = "praxis-garypagan-272615233626-us-east-1"
)

$ErrorActionPreference = "Stop"

$aws = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
if (!(Test-Path -LiteralPath $aws)) {
    $aws = "aws"
}

$commands = @(
    "set -e",
    "echo PROCESS",
    "ps -eo pid,ppid,etime,%cpu,%mem,rss,cmd | awk '/python3 .*process_cadets_windows_cloud.py/ && !/awk/ {print}' || true",
    'pid=$(pgrep -f "python3 .*process_cadets_windows_cloud.py" | head -n 1 || true); echo PID=$pid',
    "echo OPEN_CADETS_FILE",
    'if [ -n "$pid" ]; then for fd in /proc/$pid/fd/*; do readlink "$fd" 2>/dev/null; done | grep -E "cadets|full-e5cadets|logs" | tail -n 10 || true; fi',
    "echo TMUX",
    "tmux ls 2>/dev/null || true",
    "echo LOG_TAIL",
    "tail -n 80 /mnt/praxis/logs/full-e5cadets-window-factory-20260511.log 2>/dev/null | LC_ALL=C tr -cd '\11\12\15\40-\176' || true",
    "echo LOCAL_OUTPUT",
    "ls -lh /mnt/praxis/runs/full-e5cadets-window-factory-20260511 2>/dev/null || true",
    "cat /mnt/praxis/runs/full-e5cadets-window-factory-20260511/manifest.json 2>/dev/null || true",
    "echo S3_OUTPUT",
    "aws s3 ls s3://$BucketName/experiments/provenance-window-factory/runs/full-e5cadets-20260511/ --recursive --summarize --human-readable 2>/dev/null | tail -n 20 || true"
)

$params = @{ commands = $commands } | ConvertTo-Json -Compress
$tmp = Join-Path $env:TEMP "ssm-check-full-e5cadets-window-factory.json"
Set-Content -LiteralPath $tmp -Value $params -Encoding ascii

$commandId = & $aws ssm send-command `
    --profile $Profile `
    --region $Region `
    --instance-ids $InstanceId `
    --document-name AWS-RunShellScript `
    --parameters "file://$tmp" `
    --query "Command.CommandId" `
    --output text

Start-Sleep -Seconds 5
& $aws ssm get-command-invocation `
    --profile $Profile `
    --region $Region `
    --command-id $commandId `
    --instance-id $InstanceId `
    --query "{Status:Status,Stdout:StandardOutputContent,Stderr:StandardErrorContent}" `
    --output json
