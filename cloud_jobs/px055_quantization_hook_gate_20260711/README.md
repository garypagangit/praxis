# PX-055 Quantization Hook Feasibility Gate

Purpose: run the Gate 0 hook feasibility smoke for PX-055 on a CUDA GPU instance.

This job is characterization only. It captures hidden states on safe refusal-style statements, benign-helpful statements, and benign safety-themed controls under FP16, bitsandbytes int8, and bitsandbytes NF4 inference. It does not alter model weights, remove refusal vectors, optimize jailbreak prompts, publish harmful prompt inventories, or generate unsafe content.

## Upload

```powershell
aws s3 sync cloud_jobs\px055_quantization_hook_gate_20260711 s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/px055_quantization_hook_gate_20260711/code --profile praxis-build --region us-east-1
aws s3 cp scripts\run_px055_quantization_hook_gate.py s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/px055_quantization_hook_gate_20260711/code/run_px055_quantization_hook_gate.py --profile praxis-build --region us-east-1
```

## Default Run

Environment defaults:

- `JOB=px055-quantization-hook-gate-20260711`
- `MODEL_ID=Qwen/Qwen2.5-7B-Instruct`
- `CONDITIONS=fp16,int8,nf4`
- `MAX_INPUT_TOKENS=96`
- `MAX_DIMS=512`
- `LAYER_INDEX=-1`

The job writes `summary.json`, reduced vectors, row CSV, report markdown, and logs to S3 under:

```text
s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/px055_quantization_hook_gate_20260711/output/
```
