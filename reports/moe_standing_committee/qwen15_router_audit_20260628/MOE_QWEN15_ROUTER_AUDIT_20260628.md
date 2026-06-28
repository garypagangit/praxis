# Qwen1.5-MoE Standing-Committee Router Audit

Updated: 2026-06-28 19:45:47 UTC

Model: `Qwen/Qwen1.5-MoE-A2.7B`.

## Provenance

- AWS instance: `i-07178e293e8df2a60` (`g5.xlarge`, us-east-1).
- Successful SSM command: `6793f01d-3424-4cd6-a27d-70ea5c60e276`.
- S3 prefix: `s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/moe_qwen15_router_audit_20260628/`.
- Local raw log: `moe-qwen15-router-audit-20260628.log`.

## Decision

Audit decision: **PASS**.

| Metric | Value |
|---|---:|
| Prompt count | 480 |
| Router-captured prompts | 480 |
| Router capture rate | 1.0000 |
| Primary committee size | 32 |
| Primary mean pairwise Jaccard | 0.5826 |
| Primary bootstrap CI low | 0.5552 |
| Primary bootstrap CI high | 0.6281 |
| Mean layer top-k mass | 0.3097 |
| Mean layer entropy | 3.3266 |

## Committee-size sensitivity

| Committee size | Mean Jaccard | Min Jaccard | CI low | CI high |
|---:|---:|---:|---:|---:|
| 16 | 0.5354 | 0.4545 | 0.4653 | 0.5582 |
| 32 | 0.5826 | 0.4884 | 0.5552 | 0.6281 |
| 64 | 0.5652 | 0.4713 | 0.5200 | 0.5772 |

## Gate checks

| Check | Passed |
|---|---:|
| `router_capture_rate` | `True` |
| `primary_jaccard_mean` | `True` |
| `primary_jaccard_ci_low` | `True` |
| `all_committee_size_means` | `True` |

## Domain committees

| Domain | Primary committee preview |
|---|---|
| `cyber` | `['L16:E040', 'L17:E045', 'L13:E016', 'L06:E037', 'L20:E058', 'L05:E022', 'L02:E000', 'L05:E004', 'L11:E036', 'L07:E056', 'L21:E055', 'L18:E001']` |
| `code` | `['L16:E040', 'L13:E016', 'L17:E045', 'L06:E037', 'L20:E058', 'L05:E022', 'L02:E000', 'L11:E036', 'L07:E056', 'L17:E026', 'L10:E018', 'L14:E023']` |
| `math` | `['L16:E040', 'L13:E016', 'L17:E045', 'L06:E037', 'L20:E058', 'L05:E022', 'L02:E000', 'L11:E036', 'L07:E056', 'L19:E045', 'L05:E005', 'L18:E001']` |
| `policy` | `['L16:E040', 'L13:E016', 'L17:E045', 'L06:E037', 'L20:E058', 'L05:E022', 'L02:E000', 'L11:E036', 'L18:E001', 'L07:E056', 'L19:E004', 'L12:E048']` |
| `writing` | `['L16:E040', 'L13:E016', 'L17:E045', 'L06:E037', 'L20:E058', 'L05:E022', 'L13:E049', 'L02:E000', 'L06:E058', 'L11:E036', 'L18:E001', 'L05:E026']` |

## Interpretation

This is the frozen non-OLMoE cross-architecture gate for PX-005. It uses the same prompt domains, style perturbations, committee sizes, and pass thresholds as the OLMoE audit while adapting only the model-loading path for Qwen1.5-MoE.

## Claim Boundary

This gate can support a bounded cross-architecture standing-committee claim only if it passes under the frozen OLMoE protocol. It still does not test fine-tuning shift or causal expert intervention.
