# OLMoE Router-Audit Smoke

Updated: 2026-06-23 11:25:08 UTC

Model: `allenai/OLMoE-1B-7B-0924`.

## Decision

Smoke decision: **PASS**.

| Metric | Value |
|---|---:|
| Prompt count | 60 |
| Router-captured prompts | 60 |
| Router capture rate | 1.0000 |
| Mean pairwise committee Jaccard | 0.3668 |
| Mean layer top-k mass | 0.2853 |
| Mean layer entropy | 3.6551 |

## Domain Committees

| Domain | Committee preview |
|---|---|
| `cyber` | `['L02:E030', 'L13:E002', 'L10:E004', 'L08:E022', 'L12:E059', 'L14:E060', 'L03:E039', 'L14:E036', 'L09:E008', 'L11:E056', 'L13:E011', 'L04:E055']` |
| `code` | `['L13:E002', 'L02:E030', 'L13:E006', 'L14:E006', 'L15:E030', 'L10:E004', 'L03:E039', 'L14:E036', 'L08:E022', 'L12:E059', 'L14:E060', 'L11:E013']` |
| `math` | `['L13:E002', 'L02:E030', 'L12:E043', 'L15:E034', 'L10:E004', 'L04:E017', 'L08:E022', 'L14:E060', 'L12:E059', 'L15:E017', 'L03:E039', 'L11:E056']` |
| `policy` | `['L02:E030', 'L13:E002', 'L10:E004', 'L08:E022', 'L12:E059', 'L14:E060', 'L03:E039', 'L11:E056', 'L09:E008', 'L15:E042', 'L03:E057', 'L00:E006']` |
| `writing` | `['L02:E030', 'L13:E002', 'L10:E004', 'L08:E022', 'L14:E060', 'L03:E039', 'L12:E059', 'L11:E056', 'L09:E008', 'L00:E006', 'L04:E014', 'L12:E023']` |

## Interpretation

This is a smoke test for router observability and a first estimate of domain-invariant committee overlap. It is not a final standing-committee replication because it uses a small fixed prompt set and no fine-tuning/domain-shift intervention.

## Claim Boundary

This is an AWS router-observability and standing-committee smoke test on OLMoE. It can justify a larger pre-registered router audit, but it is not a full standing-committee replication or fine-tuning-shift claim.
