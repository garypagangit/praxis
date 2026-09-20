# AWS connection and GPU execution

## Current status: completed and stopped

The later [embedding scoring run](../embedding_baseline/results/gpu_scoring_20260920/REPORT.md) also completed on the existing host: CUDA frozen-embedding extraction plus exact CPU nearest-neighbor scoring, both datasets and three repeats. Independent verification passed; the scientific readiness gates did not. See its [separate AWS closeout](../embedding_baseline/results/gpu_scoring_20260920/AWS_CLOSEOUT.json). No weights were retrained in this follow-up.

The separate [native graph pilot](../native_graph/README.md) ran on the existing AWS `g5.xlarge` GPU host, completed both CADETS and THEIA with three seeds, and passed independent saved-evidence verification. The host is stopped. See the [experiment report](../native_graph/results/gpu_pilot_20260920/REPORT.md) and [AWS closeout receipt](../native_graph/results/gpu_pilot_20260920/AWS_CLOSEOUT.json).

The new GPU path passed CPU/CUDA agreement checks, repeated CUDA inference checks, and deterministic backward qualification before fitting. Actual versions, GPU identity, timings and peak GPU memory are recorded with the results. These measurements do not establish speedup over an equivalent CPU run. The detectors had poor recall, and the fixed checker provided no useful gain.

## Initial connection verification: historical record

The existing `praxis-build` AWS IAM Identity Center session was renewed by the user, and live AWS API calls verified the expected account and the designated existing EC2 host. Region: `us-east-1`. See [sanitized connection receipt](CONNECTION_20260919.json).

- Instance type: `g5.xlarge`.
- AWS inventory: one NVIDIA A10G, reporting 22,888 MiB of GPU memory.
- State at the initial connection check: **stopped**.
- At that initial check, no instance was started, provisioned, or modified and no model job was submitted. The later native graph execution is documented above.
- No live CUDA/driver/SSM-command test was performed during the initial connection check. Live GPU qualification was subsequently completed for the native graph pilot.
- Temporary tokens, account/host/bucket/role identifiers, and login device codes are excluded from the published receipt.

The connection uses the existing private settings; no permanent access key is needed. Authentication is temporary. To check or renew it later:

```powershell
aws sts get-caller-identity --profile praxis-build --region us-east-1
aws sso login --profile praxis-build --use-device-code --no-browser
```

Complete a newly requested sign-in in the AWS browser page when renewal is required. [AWS CLI sign-in documentation](https://docs.aws.amazon.com/cli/latest/reference/sso/login.html).

## Original CPU engine and subsequent GPU path

The original Unraveled E1-E4 engine remains **CPU-only**, under its original registration. Its E0 audit was primarily file parsing and took about nine seconds; its synthetic pipeline took about six seconds. Those historical measurements do not describe the new native graph GPU workload.

The separately registered native graph engine now selects the device explicitly, moves models and tensors consistently, enforces deterministic requirements, saves portable checkpoints, and synchronizes CUDA timings. Explicit CUDA requests fail if unavailable; they do not silently fall back to CPU. The original registration and results are preserved.

The native graph launcher uses account/instance checks, an immutable bundle, a bounded job, an independent automatic stop, and final stop verification. Its worker and runtime artifacts are separate from prior CTI workloads. See the [native graph execution instructions](../native_graph/README.md).

The next research task is normal-reference and calibration stability after the scoring follow-up. Any operative change requires a new registration and run directory. The GPU host remains stopped between authorized runs.
