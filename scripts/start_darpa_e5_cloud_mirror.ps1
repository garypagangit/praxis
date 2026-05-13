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
    "set -euo pipefail",
    "mkdir -p /mnt/praxis/logs /mnt/praxis/bin",
    "cat > /mnt/praxis/bin/darpa_e5_mirror_20260509.sh <<'EOF'",
    "#!/usr/bin/env bash",
    "set -euo pipefail",
    'export HOME="${HOME:-/root}"',
    'ROOT=/mnt/praxis/datasets/darpa-tc/e5/cadets',
    'LOG=/mnt/praxis/logs/darpa-e5-cadets-mirror-20260509.log',
    "BUCKET=$BucketName",
    'mkdir -p /mnt/praxis/logs "$ROOT"',
    'exec > >(tee -a "$LOG") 2>&1',
    'echo START $(date -u +%Y-%m-%dT%H:%M:%SZ)',
    "python3 -m pip install --user --upgrade gdown >/dev/null",
    'export PATH=$HOME/.local/bin:$PATH',
    "cd /mnt/praxis",
    'python3 -m gdown --folder https://drive.google.com/drive/folders/1YOaC0SMGjBnrT9952EwmKKngQkBYf4hY --output "$ROOT" --remaining-ok --continue',
    'find "$ROOT" -type f -printf ''%P	%s\n'' | sort > "$ROOT"/_manifest_files.tsv',
    'aws s3 sync "$ROOT" "s3://$BUCKET/datasets/darpa-tc/raw/engagement-5/cadets/" --no-progress',
    'echo DONE $(date -u +%Y-%m-%dT%H:%M:%SZ)',
    "EOF",
    "chmod +x /mnt/praxis/bin/darpa_e5_mirror_20260509.sh",
    "if tmux has-session -t darpa-e5-cadets-mirror 2>/dev/null; then echo 'darpa-e5-cadets-mirror already running'; tmux ls; exit 0; fi",
    "tmux new-session -d -s darpa-e5-cadets-mirror bash -lc /mnt/praxis/bin/darpa_e5_mirror_20260509.sh",
    "tmux ls"
)

$params = @{ commands = $commands } | ConvertTo-Json -Compress
$tmp = Join-Path $env:TEMP "ssm-start-darpa-e5-mirror.json"
Set-Content -LiteralPath $tmp -Value $params -Encoding ascii

$commandId = & $aws ssm send-command `
    --profile $Profile `
    --region $Region `
    --instance-ids $InstanceId `
    --document-name AWS-RunShellScript `
    --parameters "file://$tmp" `
    --query "Command.CommandId" `
    --output text

Start-Sleep -Seconds 3
& $aws ssm get-command-invocation `
    --profile $Profile `
    --region $Region `
    --command-id $commandId `
    --instance-id $InstanceId `
    --query "{Status:Status,Stdout:StandardOutputContent,Stderr:StandardErrorContent}" `
    --output json
