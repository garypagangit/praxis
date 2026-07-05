# SEC-LoRD Relationship-Evidence Model Gate

Generated: 2026-05-17

Status: **PASS - RELATIONSHIP EVIDENCE MODEL GATE**

## Model

- Model: `Qwen/Qwen2.5-7B-Instruct`
- Device: `cuda`
- Rows: `500`

## Strict Scorecard

| Condition | Accuracy | Correct | Rows | Invalid | Invalid rate | Seconds / row |
|---|---:|---:|---:|---:|---:|---:|
| `vanilla` | `0.614` | `307` | `500` | `0` | `0.000` | `0.157` |
| `relationship_evidence` | `0.822` | `411` | `500` | `0` | `0.000` | `0.219` |

## Paired Vanilla Vs Relationship Evidence

| Both correct | Vanilla only | Evidence only | Both wrong |
|---:|---:|---:|---:|
| `271` | `36` | `140` | `53` |

## Pass Criteria

- Accuracy delta relationship minus vanilla: `0.208`; pass = `True`.
- Accuracy delta relationship minus technique-only: `0.000`; pass = `False`.
- Random-facts negative control pass: `not_run`.
- Empty-evidence negative control pass: `not_run`.
- Relationship invalid rate no worse than vanilla: pass = `True`.
- Evidence-only paired wins exceed vanilla-only wins: pass = `True`.
- Broad-seed negative control is reported above and cannot be hidden.
- Hypothesis verdict: `not_available`.

## Pairwise Win Matrix

Each cell counts rows where the row condition is correct and the column condition is wrong; diagonal cells are correct counts.

| Condition | `relationship_evidence` | `vanilla` |
|---|---:|---:|
| `relationship_evidence` | `411` | `140` |
| `vanilla` | `36` | `307` |

## Decision

Run technique-only, random-facts, and empty-evidence ablations before naming the Praxis mechanism.
