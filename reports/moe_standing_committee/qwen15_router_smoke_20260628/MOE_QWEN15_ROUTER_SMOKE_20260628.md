# Qwen1.5-MoE Router-Audit Smoke

Updated: 2026-06-28 19:13:06 UTC

Model: `Qwen/Qwen1.5-MoE-A2.7B`.

## Provenance

- AWS instance: `i-07178e293e8df2a60` (`g5.xlarge`, us-east-1).
- Successful SSM command: `eb6acd24-a0ae-41bb-adf0-15892507fc0a`.
- Initial placement failure before offload patch: `73ca066d-6001-4a40-b628-40371274c9c2`.
- S3 prefix: `s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/moe_qwen15_router_smoke_20260628/`.
- Local raw log: `moe-qwen15-router-smoke-20260628.log`.

## Decision

Smoke decision: **PASS**.

| Metric | Value |
|---|---:|
| Prompt count | 5 |
| Router-captured prompts | 5 |
| Router capture rate | 1.0000 |
| Mean pairwise committee Jaccard | 0.2195 |
| Mean layer top-k mass | 0.3396 |
| Mean layer entropy | 3.2480 |

## Load configuration

- 8-bit loading requested: `True`
- CUDA available: `True`
- Hook names observed: `['model.layers.0.mlp.gate', 'model.layers.1.mlp.gate', 'model.layers.10.mlp.gate', 'model.layers.11.mlp.gate', 'model.layers.12.mlp.gate', 'model.layers.13.mlp.gate', 'model.layers.14.mlp.gate', 'model.layers.15.mlp.gate', 'model.layers.16.mlp.gate', 'model.layers.17.mlp.gate', 'model.layers.18.mlp.gate', 'model.layers.19.mlp.gate', 'model.layers.2.mlp.gate', 'model.layers.20.mlp.gate', 'model.layers.21.mlp.gate', 'model.layers.22.mlp.gate', 'model.layers.23.mlp.gate', 'model.layers.3.mlp.gate', 'model.layers.4.mlp.gate', 'model.layers.5.mlp.gate']`

## Domain committees

| Domain | Committee preview |
|---|---|
| `cyber` | `['L17:E045', 'L16:E040', 'L13:E016', 'L06:E037', 'L05:E022', 'L19:E037', 'L18:E056', 'L23:E036', 'L05:E004', 'L23:E016', 'L21:E024', 'L02:E000']` |
| `code` | `['L13:E016', 'L06:E037', 'L16:E040', 'L17:E045', 'L10:E018', 'L22:E035', 'L19:E010', 'L09:E028', 'L23:E015', 'L02:E000', 'L20:E058', 'L05:E022']` |
| `math` | `['L16:E040', 'L13:E016', 'L17:E045', 'L06:E037', 'L20:E058', 'L05:E022', 'L15:E046', 'L05:E005', 'L02:E000', 'L17:E003', 'L15:E047', 'L18:E052']` |
| `policy` | `['L16:E040', 'L13:E016', 'L17:E045', 'L06:E037', 'L05:E022', 'L02:E000', 'L19:E037', 'L04:E016', 'L20:E058', 'L07:E000', 'L21:E037', 'L11:E036']` |
| `writing` | `['L13:E016', 'L06:E037', 'L16:E040', 'L17:E045', 'L11:E051', 'L20:E058', 'L05:E022', 'L13:E049', 'L06:E058', 'L18:E001', 'L02:E000', 'L07:E022']` |

## Interpretation

This is the first non-OLMoE router-observability smoke. A PASS supports moving to a frozen full audit on the same architecture. A FAIL or BLOCKED result should be treated as tooling/resource evidence, not as evidence against standing committees.

## Claim boundary

This is a small non-OLMoE router-observability smoke on Qwen1.5-MoE. It does not prove cross-architecture standing-committee validity until the frozen full audit runs.
