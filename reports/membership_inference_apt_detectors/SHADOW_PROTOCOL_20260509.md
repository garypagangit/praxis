# Membership Inference Shadow Protocol

Generated: 2026-05-09

## Decision

Status: **WEAKENED - TEMPORAL SHIFT EXPLAINS MOST SIGNAL**.

## Aggregate Results

| Evaluation | ROC-AUC mean | AP mean | Interpretation |
|---|---:|---:|---|
| `shadow attack / same-distribution nonmembers` | `0.5599` | `0.5351` | Controls ordinary day-shift; strongest privacy test here. |
| `shadow attack / temporal nonmembers` | `0.7256` | `0.8310` | Includes temporal shift; useful but confounded. |
| `best direct score / same-distribution nonmembers` | `0.5562` | `0.5341` | No shadow training; useful sanity check. |
| `best direct score / temporal nonmembers` | `0.7142` | `0.8260` | Comparable to the earlier smoke setup. |

## Per-Seed Shadow Attack

| Seed | Same-dist ROC-AUC | Temporal ROC-AUC | Same member mean | Same nonmember mean |
|---:|---:|---:|---:|---:|
| `13` | `0.5572` | `0.7221` | `0.5158` | `0.4951` |
| `29` | `0.5673` | `0.7297` | `0.5161` | `0.4921` |
| `43` | `0.5551` | `0.7250` | `0.5130` | `0.4930` |

## Recommendation

Keep as a documented diagnostic; do not promote unless a same-distribution signal appears on a stronger detector family.
