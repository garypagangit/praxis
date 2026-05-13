# AWS Large Dataset Mirror Status - 2026-05-09

Bucket: `s3://praxis-garypagan-272615233626-us-east-1/`
Region: `us-east-1`

## Completed Before Large Mirror

NVD 2024-present has been downloaded and synced to S3 in windowed JSON files:

- Local prefix: `external/datasets/nvd/`
- S3 prefix: `s3://praxis-garypagan-272615233626-us-east-1/datasets/nvd/raw/`
- Date range: `2024-01-01` through `2026-05-08`
- Total CVEs fetched: `114699`
- Manifest: `nvd-cves-20240101-to-20260508-manifest.json`

## AWS Data Loader

Instance:

- Instance ID: `i-0bd262c42220bb4a2`
- Instance type: `t3.large`
- Region/AZ: `us-east-1a`
- IAM instance profile: `praxis-data-loader-profile`
- Security: no inbound SSH required; SSM online
- Storage: encrypted `4096 GiB` gp3 root volume
- Local staging root: `/opt/praxis-data`

Scripts:

- Local: `scripts/aws_large_dataset_mirror.sh`
- S3: `s3://praxis-garypagan-272615233626-us-east-1/registry/scripts/aws_large_dataset_mirror.sh`

## Mirror Plan

The AWS data-loader is running the full public Google Drive mirrors in this order:

1. DARPA TC Engagement 5 full public release
   - Local: `/opt/praxis-data/raw/darpa-tc/e5`
   - S3: `datasets/darpa-tc/raw/engagement-5/`
2. DARPA TC Engagement 3 full public release
   - Local: `/opt/praxis-data/raw/darpa-tc/e3`
   - S3: `datasets/darpa-tc/raw/engagement-3/`
3. OpTC full public release
   - Local: `/opt/praxis-data/raw/optc`
   - S3: `datasets/optc/raw/full-drive-mirror/`

## Current Status

The mirror is running in the background on EC2 under:

```text
/opt/praxis-data/scripts/aws_large_dataset_mirror.sh
```

Log:

```text
/opt/praxis-data/logs/large-dataset-mirror.log
```

Initial check showed:

- Process running
- DARPA TC E5 download active
- Local staged data: approximately `1.3 GiB` and growing

## Check Progress

Use SSM to inspect:

```powershell
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" ssm send-command `
  --instance-ids i-0bd262c42220bb4a2 `
  --document-name AWS-RunShellScript `
  --parameters '{"commands":["ps -p $(cat /opt/praxis-data/logs/large-dataset-mirror.pid) -o pid,etime,cmd || true","tail -80 /opt/praxis-data/logs/large-dataset-mirror.log | LC_ALL=C tr -cd ''\\11\\12\\15\\40-\\176'' || true","du -sh /opt/praxis-data/raw 2>/dev/null || true","df -h /opt/praxis-data"]}' `
  --region us-east-1 `
  --profile praxis-build
```

## Stop The Loader When Done

This instance and 4 TiB EBS volume are billable while running. Stop or terminate after the mirror is complete and verified:

```powershell
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" ec2 stop-instances `
  --instance-ids i-0bd262c42220bb4a2 `
  --region us-east-1 `
  --profile praxis-build
```

Terminate only after confirming all needed data is in S3:

```powershell
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" ec2 terminate-instances `
  --instance-ids i-0bd262c42220bb4a2 `
  --region us-east-1 `
  --profile praxis-build
```
