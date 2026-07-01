# SEC-LoRD Relationship-Evidence Model Gate

Generated: 2026-05-17

Status: **STOP - RELATIONSHIP EVIDENCE ABLATION GATE FAILED**

## Model

- Model: `Qwen/Qwen2.5-7B-Instruct`
- Device: `cuda`
- Rows: `106`

## Strict Scorecard

| Condition | Accuracy | Correct | Rows | Invalid | Invalid rate | Seconds / row |
|---|---:|---:|---:|---:|---:|---:|
| `vanilla` | `0.623` | `66` | `106` | `0` | `0.000` | `0.169` |
| `relationship_evidence` | `0.906` | `96` | `106` | `0` | `0.000` | `0.215` |
| `technique_only_evidence` | `0.726` | `77` | `106` | `0` | `0.000` | `0.168` |
| `random_facts` | `0.462` | `49` | `106` | `6` | `0.057` | `0.233` |
| `empty_evidence` | `0.594` | `63` | `106` | `6` | `0.057` | `0.122` |
| `broad_seed` | `0.660` | `70` | `106` | `1` | `0.009` | `0.234` |

## Paired Vanilla Vs Relationship Evidence

| Both correct | Vanilla only | Evidence only | Both wrong |
|---:|---:|---:|---:|
| `61` | `5` | `35` | `5` |

## Pass Criteria

- Accuracy delta relationship minus vanilla: `0.283`; pass = `True`.
- Accuracy delta relationship minus technique-only: `0.179`; pass = `True`.
- Random-facts negative control pass: `True`.
- Empty-evidence negative control pass: `True`.
- Relationship invalid rate no worse than vanilla: pass = `True`.
- Evidence-only paired wins exceed vanilla-only wins: pass = `True`.
- Broad-seed negative control is reported above and cannot be hidden.
- Hypothesis verdict: `unclear`.

## Pairwise Win Matrix

Each cell counts rows where the row condition is correct and the column condition is wrong; diagonal cells are correct counts.

| Condition | `broad_seed` | `empty_evidence` | `random_facts` | `relationship_evidence` | `technique_only_evidence` | `vanilla` |
|---|---:|---:|---:|---:|---:|---:|
| `broad_seed` | `70` | `14` | `27` | `6` | `10` | `12` |
| `empty_evidence` | `7` | `63` | `16` | `4` | `4` | `3` |
| `random_facts` | `6` | `2` | `49` | `4` | `3` | `2` |
| `relationship_evidence` | `32` | `37` | `51` | `96` | `24` | `35` |
| `technique_only_evidence` | `17` | `18` | `31` | `5` | `77` | `17` |
| `vanilla` | `8` | `6` | `19` | `5` | `6` | `66` |

## Decision

Do not promote the mechanism claim; inspect AB gates and reframe around the winning condition.
