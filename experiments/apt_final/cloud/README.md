# AWS connection and GPU preparation

## Verified connection

The existing `praxis-build` AWS IAM Identity Center session was renewed by the user, and live AWS API calls verified the expected account and the designated existing EC2 host. Region: `us-east-1`. See [sanitized connection receipt](CONNECTION_20260919.json).

- Instance type: `g5.xlarge`.
- AWS inventory: one NVIDIA A10G, reporting 22,888 MiB of GPU memory.
- Observed state: **stopped**.
- No instance was started, provisioned, or modified; no model job was submitted.
- No live CUDA/driver/SSM-command test was performed. SSM inventory returned no entry for the stopped host at this check; guest manageability remains to be reverified after a bounded start.
- Temporary tokens, account/host/bucket/role identifiers, and login device codes are excluded from the published receipt.

The connection uses the existing private settings; no permanent access key is needed. Authentication is temporary. To check or renew it later:

```powershell
aws sts get-caller-identity --profile praxis-build --region us-east-1
aws sso login --profile praxis-build --use-device-code --no-browser
```

Complete a newly requested sign-in in the AWS browser page when renewal is required. [AWS CLI sign-in documentation](https://docs.aws.amazon.com/cli/latest/reference/sso/login.html).

## What GPU use still requires

The currently registered APT engine is **CPU-only**. AWS connectivity alone does not move its models or tensors onto the GPU. E0 is primarily file parsing, and its initial run took about nine seconds; the synthetic pipeline took about six seconds. Those measurements do not establish GPU speedup.

Before real GPU jobs, create a new development revision that selects the device explicitly, moves all required tensors and models consistently, preserves deterministic requirements, loads portable checkpoints, and synchronizes CUDA for accurate timings. Record driver/CUDA/package versions, memory, repeatability, CPU/GPU agreement with justified tolerances, and a representative workload timing comparison. Preserve the existing registration and results.

Reuse the existing reviewed controller pattern for account/instance checks, a bounded job, a separate automatic stop timer, and final stop verification. The CTI-specific worker script is not an APT launcher and must not be submitted unchanged. Prepare a separate immutable APT bundle and qualify its launcher before starting the host. This document is a preparation record, not a completed launcher or GPU benchmark.

Data normalization and evidence review can proceed locally while the host remains stopped. GPU training will become useful only after the relevant data and GPU implementation gates pass.
