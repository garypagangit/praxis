# PX-054 Refusal Geometry Across Recurrent Depth

Purpose: run the first safe activation-capture gate for Huginn recurrent-depth refusal geometry.

This job is characterization only. It compares benign refusal-style statements, benign-helpful statements, and benign safety-themed controls across recurrent depths. It does not alter the model, remove refusal vectors, optimize jailbreak prompts, or generate unsafe content.

## Upload

```powershell
aws s3 sync cloud_jobs\px054_refusal_geometry_20260705 s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/px054_refusal_geometry_20260705/code --profile praxis-build --region us-east-1
```

## Default Run

Environment defaults:

- `JOB=px054-refusal-geometry-huginn-20260705`
- `DEPTHS=4,8,16,32`
- `MAX_INPUT_TOKENS=96`
- `MAX_DIMS=512`

The job writes `summary.json`, reduced vectors, row CSV, report markdown, and logs to S3 under:

```text
s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/px054_refusal_geometry_20260705/output/
```
