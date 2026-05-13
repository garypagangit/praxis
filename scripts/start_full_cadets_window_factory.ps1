param(
    [string]$InstanceId = "i-0bd262c42220bb4a2",
    [string]$Region = "us-east-1",
    [string]$Profile = "praxis-build",
    [string]$BucketName = "praxis-garypagan-272615233626-us-east-1",
    [int]$EventsPerWindow = 50000
)

$ErrorActionPreference = "Stop"

$aws = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
if (!(Test-Path -LiteralPath $aws)) {
    $aws = "aws"
}

$jobPrefix = "experiments/provenance-window-factory/jobs/full-e5cadets-20260511"
$runPrefix = "experiments/provenance-window-factory/runs/full-e5cadets-20260511"
$scriptLocal = "cloud_jobs/provenance_full_window_20260511/process_cadets_windows_cloud.py"
$labelA = "external/PIDSMaker/Ground_Truth/orthrus/E5-CADETS/node_Nginx_Drakon_APT.csv"
$labelB = "external/PIDSMaker/Ground_Truth/orthrus/E5-CADETS/node_Nginx_Drakon_APT_17.csv"

& $aws s3 cp $scriptLocal "s3://$BucketName/$jobPrefix/process_cadets_windows_cloud.py" --profile $Profile --region $Region --no-progress
& $aws s3 cp $labelA "s3://$BucketName/$jobPrefix/node_Nginx_Drakon_APT.csv" --profile $Profile --region $Region --no-progress
& $aws s3 cp $labelB "s3://$BucketName/$jobPrefix/node_Nginx_Drakon_APT_17.csv" --profile $Profile --region $Region --no-progress

$commands = @(
    "set -euo pipefail",
    "JOB=/mnt/praxis/jobs/full-e5cadets-window-factory-20260511",
    "OUT=/mnt/praxis/runs/full-e5cadets-window-factory-20260511",
    "RAW=/mnt/praxis/datasets/darpa-tc/e5/cadets",
    "LOG=/mnt/praxis/logs/full-e5cadets-window-factory-20260511.log",
    "mkdir -p `$JOB `$OUT /mnt/praxis/logs",
    "aws s3 cp s3://$BucketName/$jobPrefix/process_cadets_windows_cloud.py `$JOB/process_cadets_windows_cloud.py --no-progress",
    "aws s3 cp s3://$BucketName/$jobPrefix/node_Nginx_Drakon_APT.csv `$JOB/node_Nginx_Drakon_APT.csv --no-progress",
    "aws s3 cp s3://$BucketName/$jobPrefix/node_Nginx_Drakon_APT_17.csv `$JOB/node_Nginx_Drakon_APT_17.csv --no-progress",
    "python3 -m pip install --user --upgrade fastavro >/tmp/full-e5cadets-pip.log 2>&1 || cat /tmp/full-e5cadets-pip.log",
    "cat > `$JOB/run.sh <<'EOF'",
    "#!/usr/bin/env bash",
    "set -euo pipefail",
    'export HOME="${HOME:-/root}"',
    "export PATH=`$HOME/.local/bin:`$PATH",
    "JOB=/mnt/praxis/jobs/full-e5cadets-window-factory-20260511",
    "OUT=/mnt/praxis/runs/full-e5cadets-window-factory-20260511",
    "RAW=/mnt/praxis/datasets/darpa-tc/e5/cadets",
    "LOG=/mnt/praxis/logs/full-e5cadets-window-factory-20260511.log",
    "exec > >(tee -a `$LOG) 2>&1",
    "echo START `$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "python3 `$JOB/process_cadets_windows_cloud.py --input-dir `$RAW --out-dir `$OUT --events-per-window $EventsPerWindow --node-labels `$JOB/node_Nginx_Drakon_APT.csv `$JOB/node_Nginx_Drakon_APT_17.csv",
    "aws s3 sync `$OUT s3://$BucketName/$runPrefix/ --no-progress",
    "echo DONE `$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "EOF",
    "chmod +x `$JOB/run.sh",
    "if tmux has-session -t full-e5cadets-window-factory 2>/dev/null; then echo already-running; tmux ls; exit 0; fi",
    "tmux new-session -d -s full-e5cadets-window-factory bash -lc `$JOB/run.sh",
    "tmux ls"
)

$params = @{ commands = $commands } | ConvertTo-Json -Compress
$tmp = Join-Path $env:TEMP "ssm-start-full-e5cadets-window-factory.json"
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
