# TTA Locked Final Replay

Generated: 2026-05-09

## Decision

Status: **PASSED LOCKED FINAL REPLAY**.

The locked replay used the previously validation-selected policy:

- Policy: `recon_guarded`
- TTA method: `bn_adapt`
- DE delta limit: `0.05`
- Selection source: `runs/tta-hybrid-gate-sweep-20260509/selected_hybrid_policies.csv`

No new broad threshold sweep was performed for this final replay.

## Artifacts

- Local run: `runs/tta-locked-final-20260509/`
- S3 run: `s3://praxis-garypagan-272615233626-us-east-1/experiments/tta-streaming-apt/runs/tta-locked-final-20260509/`
- Script: `scripts/run_tta_locked_final.py`

## Locked Test Summary

| Metric | Frozen -> Locked Hybrid |
|---|---:|
| Accuracy | `0.9243` |
| Macro F1 | `0.8658` |
| PR-AUC | `0.8738` |
| Recon F1 | `0.5050` |
| DE F1 | `0.9202` |
| Override rate | `0.0470` |
| Macro F1 delta vs frozen | `+0.0974` |
| Recon F1 delta vs frozen | `+0.4800` |
| DE F1 delta vs frozen | `+0.0045` |

## Confidence-Reject Baseline

A matched-rate frozen confidence rejection check does not explain the result.

| Baseline | Coverage | Reject rate | Kept Macro F1 | Kept Recon F1 | Kept DE F1 |
|---|---:|---:|---:|---:|---:|
| Frozen confidence reject | `0.9530` | `0.0470` | `0.7730` | `0.0000` | `0.9374` |

Interpretation: simply refusing the lowest-confidence frozen predictions at the same rate does not recover Reconnaissance. The TTA gate is doing something more specific than identifying uncertain rows.

## Praxis Candidate Status

This keeps TTA as the lead Praxis 06 candidate. Remaining write-up work is now mostly presentation and appendix-level:

1. Include split/leakage audit.
2. Include PR-AUC discussion.
3. Include the matched confidence-reject baseline above.
4. Decide whether to run DAPT2020/CIC-IDS2018 replication before drafting.
