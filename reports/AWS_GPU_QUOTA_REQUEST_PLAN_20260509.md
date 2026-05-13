# AWS GPU Quota Request Plan

Date: 2026-05-09

## Goal

Prepare the AWS account to run multiple Praxis experiments and model jobs simultaneously. This plan requests quota increases only; it does not launch instances or spend compute by itself.

Primary region:

- `us-east-1`, matching the current S3 bucket and data-loader infrastructure.

## Requested Quota Targets

| Quota | Target vCPUs | Why |
|---|---:|---|
| Running On-Demand G and VT instances | 256 | Main parallel GPU pool for G-family instances such as g5/g6-style experiment runners. |
| Running On-Demand P instances | 128 | Higher-end GPU family for full SAE, LLM, and larger model jobs if available. |
| Running On-Demand DL instances | 64 | Deep Learning accelerator family if available in the account/region. |
| Running On-Demand Trn instances | 64 | Trainium capacity for high-throughput training if we later use it. |
| Running On-Demand Inf instances | 64 | Inferentia capacity for large parallel inference/evaluation workloads. |

## Script

Use:

```powershell
.\scripts\request_aws_gpu_quotas.ps1 -Profile praxis-build -Regions us-east-1
```

That performs a dry run and writes a report under `reports/`.

After AWS SSO is refreshed and the dry run looks right, submit:

```powershell
.\scripts\request_aws_gpu_quotas.ps1 -Profile praxis-build -Regions us-east-1 -Submit
```

Optional multi-region capacity request:

```powershell
.\scripts\request_aws_gpu_quotas.ps1 `
  -Profile praxis-build `
  -Regions us-east-1,us-east-2,us-west-2 `
  -Submit
```

## Current Blocker

Resolved for submission on 2026-05-09. The local AWS profile `praxis-build` authenticated as:

```text
arn:aws:sts::272615233626:assumed-role/AWSReservedSSO_AdminAccess_c0cc500ab86f3e7b/paganpraxis
```

If the session expires again, refresh it with:

```powershell
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" sso login --profile praxis-build
```

## Submitted Requests

Submission report:

`reports/aws_gpu_quota_request_20260509-182729.json`

| Region | Quota | Current | Requested | Request ID | Status |
|---|---|---:|---:|---|---|
| us-east-1 | Running On-Demand G and VT instances | 8 | 256 | `81f41441d17a44f58642801dab328281xW7TdIzU` | PENDING |
| us-east-1 | Running On-Demand P instances | 0 | 128 | `07244f397e454e0090e21ca53016ae370ByQZroJ` | PENDING |
| us-east-1 | Running On-Demand DL instances | 0 | 64 | `89b198deadf54ebd9c01bff5c64b2cf7dmmnjhHM` | PENDING |
| us-east-1 | Running On-Demand Trn instances | 0 | 64 | `6ce1425c29a943c6846439108d46b479yjScUMfc` | PENDING |
| us-east-1 | Running On-Demand Inf instances | 0 | 64 | `fd1ae09bc6da46bcb4cb4f20c318d506dc5hcSOn` | PENDING |

Check status later with:

```powershell
& "C:\Program Files\Amazon\AWSCLIV2\aws.exe" service-quotas list-requested-service-quota-change-history-by-quota `
  --service-code ec2 `
  --quota-code L-DB2E81BA `
  --region us-east-1 `
  --profile praxis-build
```

Repeat with the quota codes from the table/report for P, DL, Trn, and Inf.

## Cost Note

Quota approvals do not spend money. Costs start when instances, EBS volumes, NAT gateways, or managed jobs run. Since the intent is maximum speed and parallelism, the next control should be operational visibility: tag every GPU job with experiment id, write outputs to S3, and keep a stop/terminate checklist for idle instances.
