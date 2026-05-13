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
    "tmux ls 2>/dev/null || true",
    "tail -n 80 /mnt/praxis/logs/darpa-e5-cadets-mirror-20260509.log 2>/dev/null | LC_ALL=C tr -cd '\11\12\15\40-\176' || true",
    "echo LOCAL_COUNTS",
    "find /mnt/praxis/datasets/darpa-tc/e5/cadets -type f 2>/dev/null | wc -l || true",
    "du -sh /mnt/praxis/datasets/darpa-tc/e5/cadets 2>/dev/null || true",
    "echo S3_COUNTS",
    "aws s3 ls s3://$BucketName/datasets/darpa-tc/raw/engagement-5/cadets/ --recursive --summarize --human-readable 2>/dev/null | tail -n 12 || true"
)

$params = @{ commands = $commands } | ConvertTo-Json -Compress
$tmp = Join-Path $env:TEMP "ssm-check-darpa-e5-mirror.json"
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
