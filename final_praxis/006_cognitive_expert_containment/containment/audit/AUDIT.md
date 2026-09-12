# Final Praxis 006 containment audit

Artifact integrity: **PASS**.

| Condition / policy | Correct / 32 | Fallbacks / eligible |
|---|---:|---:|
| clean/none | 15 / 32 | 0 / 6961 |
| clean/permanent | 14 / 32 | 0 / 0 |
| clean/conditional | 15 / 32 | 0 / 6961 |
| clean/random | 15 / 32 | 3357 / 6955 |
| negate/none | 4 / 32 | 0 / 12873 |
| negate/permanent | 14 / 32 | 0 / 0 |
| negate/conditional | 14 / 32 | 6921 / 6921 |
| negate/random | 14 / 32 | 4688 / 9557 |
| permute/none | 9 / 32 | 0 / 9025 |
| permute/permanent | 14 / 32 | 0 / 0 |
| permute/conditional | 9 / 32 | 0 / 9025 |
| permute/random | 11 / 32 | 3689 / 7646 |

Scientific counters: `{"clean_permanent_harms": 1, "conditional_clean_losses": 0, "conditional_recovers_negation_damage": 12, "negation_damages_clean_correct": 13}`.

Threshold and random rate were independently reconstructed from all 192 calibration cells. All 384 confirmation cells are included. Paired intervals and all transitions are in audit.json.

Limits:

- Hardware identity, RAM, process device and actual expert FLOPs are not recorded in environment.json; join an independent launch receipt.
- Calibration content is recomputed exclusively from training cells. File content alone cannot prove it was frozen before confirmation; retain deployment and object timestamp receipts.
- Confidence intervals are descriptive paired question bootstrap intervals, with no multiple-comparison correction; synthetic-fault feasibility does not establish a novel method.
