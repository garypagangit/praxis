# SEC-LoRD Relationship-Evidence Model Gate

Generated: 2026-05-17

Status: **PASS - RELATIONSHIP EVIDENCE MODEL GATE**

## Model

- Model: `meta-llama/Llama-3.1-8B-Instruct`
- Device: `cuda`
- Rows: `106`

## Strict Scorecard

| Condition | Accuracy | Correct | Rows | Invalid | Invalid rate | Seconds / row |
|---|---:|---:|---:|---:|---:|---:|
| `vanilla` | `0.642` | `68` | `106` | `0` | `0.000` | `0.153` |
| `relationship_evidence` | `0.915` | `97` | `106` | `0` | `0.000` | `0.218` |
| `broad_seed` | `0.642` | `68` | `106` | `1` | `0.009` | `0.189` |

## Paired Vanilla Vs Relationship Evidence

| Both correct | Vanilla only | Evidence only | Both wrong |
|---:|---:|---:|---:|
| `64` | `4` | `33` | `5` |

## Pass Criteria

- Accuracy delta relationship minus vanilla: `0.274`; pass = `True`.
- Relationship invalid rate no worse than vanilla: pass = `True`.
- Evidence-only paired wins exceed vanilla-only wins: pass = `True`.
- Broad-seed negative control is reported above and cannot be hidden.

## Decision

Design the separate SEC-LoRD extraction experiment; keep this CTI-MCQ result scoped as retrieval-conditioned task compliance.
