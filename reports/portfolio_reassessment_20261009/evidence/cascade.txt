# Final Praxis 002 final determination

Classification: **Negative**

| Frozen gate | Result |
|---|---|
| H1_cascade_reduction | PASS |
| H2_clean_utility | FAIL |
| H3_propagation_depth | PASS |
| H4_handoff_placement | PASS |
| measurable_ungated_cascade | PASS |
| independent_audit | PASS |

| Arm | CER | Clean success | Mean propagation depth |
|---|---:|---:|---:|
| A0 | 0.167 (10/60) | 0.850 (51/60) | 0.567 |
| A1 | 0.000 (0/60) | 0.850 (51/60) | 0.567 |
| A2 | 0.000 (0/60) | 0.850 (51/60) | 0.000 |
| A3 | 0.000 (0/60) | 0.850 (51/60) | 0.000 |

Paired 95% CI for A0 minus A3 CER: [0.08333333333333333, 0.26666666666666666].

Handoff-depth CI (A1 minus A2): [0.3666666666666667, 0.7833333333333333].

This result concerns controlled field corruption in frozen toy security workflows using one model. Final-action rejection is deterministic by construction. It does not establish general multi-agent safety, natural error incidence, real SOC performance or cross-model replication.
