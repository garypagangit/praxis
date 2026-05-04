param(
    [string]$OutputDir = "data\cic-ids-2018"
)

$ErrorActionPreference = "Stop"
aws s3 cp --no-sign-request --region ca-central-1 "s3://cse-cic-ids2018/Processed Traffic Data for ML Algorithms/" $OutputDir --recursive
python scripts\praxis04_write_manifest.py --data-dir $OutputDir

