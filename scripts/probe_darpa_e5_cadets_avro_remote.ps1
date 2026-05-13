param(
    [string]$InstanceId = "i-0bd262c42220bb4a2",
    [string]$Profile = "praxis-build",
    [string]$Region = "us-east-1",
    [int]$MaxRecords = 2000
)

$ErrorActionPreference = "Stop"

$aws = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
if (!(Test-Path $aws)) {
    $aws = "aws"
}

$remoteCommand = @"
set -euo pipefail
python3 -m pip install --user fastavro >/tmp/praxis-fastavro-install.log 2>&1 || { cat /tmp/praxis-fastavro-install.log; exit 1; }
python3 - <<'PY'
import gzip
import json
from collections import Counter
from pathlib import Path

from fastavro import reader

root = Path('/mnt/praxis/datasets/darpa-tc/e5/cadets')
first = sorted(root.glob('*.gz'))[0]
max_records = $MaxRecords
top_keys = Counter()
record_type_counts = Counter()
datum_type_counts = Counter()
datum_name_counts = Counter()
sample_records = []

with gzip.open(first, 'rb') as handle:
    avro_reader = reader(handle)
    schema_name = avro_reader.writer_schema.get('name')
    schema_namespace = avro_reader.writer_schema.get('namespace')
    for idx, record in enumerate(avro_reader):
        if idx >= max_records:
            break
        non_null = [key for key, value in record.items() if value is not None]
        for key in non_null:
            top_keys[key] += 1
        record_type_counts[str(record.get('type'))] += 1
        datum = record.get('datum') or {}
        datum_type_counts[str(datum.get('type'))] += 1
        for name in datum.get('names') or []:
            datum_name_counts[str(name)] += 1
        if len(sample_records) < 3:
            compact = {}
            for key in non_null[:3]:
                compact[key] = record[key]
            sample_records.append(compact)

summary = {
    'file': str(first),
    'schema_name': schema_name,
    'schema_namespace': schema_namespace,
    'records_sampled': min(max_records, sum(record_type_counts.values())),
    'top_keys': dict(top_keys.most_common(20)),
    'record_type_counts': dict(record_type_counts.most_common(20)),
    'datum_type_counts': dict(datum_type_counts.most_common(30)),
    'datum_name_counts': dict(datum_name_counts.most_common(30)),
    'sample_records': sample_records,
}
out = Path('/mnt/praxis/datasets/darpa-tc/e5/cadets_probe_summary.json')
out.write_text(json.dumps(summary, indent=2, default=str), encoding='utf-8')
print(json.dumps(summary, indent=2, default=str)[:12000])
PY
"@

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
    Start-Sleep -Seconds 10
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
