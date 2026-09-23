## Retrospective paired analysis of stage recognition and warnings

We reanalyzed unchanged probabilities after observing selected warning-recall differences. The complete plan was frozen at commit `c0d884e` before this reanalysis, but it is not an original preregistration or independent confirmation. All 27 entropy-versus-harm PX081 pairs and all nine common-anchor PX082 pairs were retained. No new models, thresholds or calibration were fitted. Warning recall means any nonbenign prediction among the true events of one attack stage; it distinguishes an incorrect attack name from an absent warning.

One 2,000-draw paired capture-bootstrap plan (seed 20260923) was reused across all seeds and comparisons on each cohort. The plans share capture multiplicities and preserve whole fragments and unequal fragment sizes. Intervals are descriptive, conditional on this single campaign; absent-stage rate draws are marked undefined and excluded transparently. Seed means are point summaries, never pooled-row confidence intervals.

### Complete mean effects

| Study / contrast | Δ macro-F1 pp | Δ exfil warning pp | Δ exfil → benign mean | F1 up / warning down seeds |
| --- | --- | --- | --- | --- |
| PX081 clean B1 | 3.61 | -20.12 | 692.67 | 2 |
| PX081 clean B2 | 3.70 | -20.26 | 697.33 | 2 |
| PX081 clean B3 | 2.31 | -8.93 | 307.33 | 2 |
| PX081 delayed_unavailable B1 | 3.42 | -13.81 | 475.33 | 2 |
| PX081 delayed_unavailable B2 | 3.57 | -13.95 | 480.00 | 2 |
| PX081 delayed_unavailable B3 | 2.47 | -11.80 | 406.00 | 3 |
| PX081 wrong_host_history B1 | 3.61 | -20.12 | 692.67 | 2 |
| PX081 wrong_host_history B2 | 12.34 | -20.33 | 699.67 | 3 |
| PX081 wrong_host_history B3 | -1.10 | -0.15 | 5.33 | 1 |
| PX082 current_mixed_minus_past | 6.32 | 32.02 | -551.33 | 0 |
| PX082 current_history_mixed_minus_past | 3.83 | 17.85 | -307.33 | 0 |
| PX082 chronological_history_minus_current | 2.17 | -0.41 | 7.00 | 3 |

### Exact per-seed intervals and counts for manuscript tables

PX081: 19/27 pairs increase macro-F1 and reduce exfiltration warning recall at the point estimate; 17/27 warning-difference intervals are entirely below zero; 17/27 simultaneously have a macro-F1 interval above zero and warning interval below zero. These are correlated descriptive comparisons, not counts of independent confirmations.

PX082: 3/9 pairs increase macro-F1 and reduce exfiltration warning recall at the point estimate; 1/9 warning-difference intervals are entirely below zero; 1/9 simultaneously have a macro-F1 interval above zero and warning interval below zero. These are correlated descriptive comparisons, not counts of independent confirmations.

| Comparison | Seed | Δ macro-F1 pp [95%] | Δ exfil warning pp [95%] | Exfil → benign | All exact exfil errors | Other attack label |
| --- | --- | --- | --- | --- | --- | --- |
| PX081 clean B3 harm−entropy | 8101 | 5.65 [0.78, 10.41] | -26.06 [-92.42, -0.88] | 222 → 1119 | 1122 → 1130 | 900 → 11 |
| PX081 clean B3 harm−entropy | 8102 | -0.08 [-0.32, 0.07] | -0.09 [-0.52, 0.00] | 203 → 206 | 1128 → 1129 | 925 → 923 |
| PX081 clean B3 harm−entropy | 8103 | 1.38 [0.17, 3.47] | -0.64 [-3.06, -0.15] | 1105 → 1127 | 1128 → 1130 | 23 → 3 |
| PX082 current_mixed_minus_past | 20260923 | 7.52 [1.96, 26.31] | 32.11 [4.05, 98.38] | 565 → 12 | 565 → 22 | 0 → 10 |
| PX082 current_history_mixed_minus_past | 20260923 | 3.32 [1.20, 17.24] | 12.66 [1.92, 70.30] | 572 → 354 | 576 → 356 | 4 → 2 |
| PX082 chronological_history_minus_current | 20260923 | 2.98 [0.42, 6.41] | -0.41 [-2.62, 0.00] | 565 → 572 | 565 → 576 | 0 → 4 |
| PX082 current_mixed_minus_past | 20260924 | 6.99 [1.65, 24.36] | 32.00 [3.97, 98.38] | 563 → 12 | 563 → 25 | 0 → 13 |
| PX082 current_history_mixed_minus_past | 20260924 | 2.97 [0.62, 15.49] | 9.29 [1.17, 64.31] | 569 → 409 | 575 → 411 | 6 → 2 |
| PX082 chronological_history_minus_current | 20260924 | 1.08 [-2.11, 4.20] | -0.35 [-2.09, 0.00] | 563 → 569 | 563 → 575 | 0 → 6 |
| PX082 current_mixed_minus_past | 20260925 | 4.46 [0.12, 20.62] | 31.94 [3.97, 98.17] | 563 → 13 | 564 → 19 | 1 → 6 |
| PX082 current_history_mixed_minus_past | 20260925 | 5.18 [-0.75, 25.69] | 31.59 [3.76, 98.38] | 571 → 27 | 585 → 29 | 14 → 2 |
| PX082 chronological_history_minus_current | 20260925 | 2.45 [0.43, 3.07] | -0.46 [-2.88, -0.09] | 563 → 571 | 564 → 585 | 1 → 14 |

### Interpretation

The defensible contribution is an applied measurement result: aggregate stage scores and attack-warning retention can recommend different choices on the same events. An F1 gain alone therefore does not establish that analysts retain more warnings. This does not make warning recall a novel metric or prove which operating point is best in a real organization. Report the stage decomposition together with benign false alerts and the intended operational objective.

Chronological history comparisons assess context under past-only training; time-mixed comparisons intentionally expose future events and measure evaluation-protocol sensitivity. The author movement annotations are Remote System Discovery progress, and full-flow features cannot establish early exfiltration warning. The same previously exposed campaign underlies both cohorts. Dataset breadth and a genuinely fresh execution remain necessary before claiming generalization.

Complete results, every stage and count interval, supports, shared draws and receipts are in [REPORT.md](REPORT.md), [PAIRED_METRICS.csv](PAIRED_METRICS.csv), [PAIRED_RESULTS.json](PAIRED_RESULTS.json) and [AUDIT.json](AUDIT.json).
