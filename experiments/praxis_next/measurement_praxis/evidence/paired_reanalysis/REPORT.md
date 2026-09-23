# Retrospective paired reanalysis: stage scores and lost warnings

**Status:** all 36 comparisons completed; all 66 private probability archives match their original receipts. No new fits. The frozen analysis commit is `c0d884e`. This is a retrospective measurement analysis of previously examined results, not independent confirmation.

An incorrect attack-stage name can still alert an analyst. Predicting benign for a true attack removes that warning. The tables report these separately. Positive F1/recall deltas are favorable; positive missed-warning or false-alert counts are unfavorable.

## Complete seed-mean results

These are arithmetic point means across three fitting seeds. There is no confidence interval for a pooled seed mean. PX081 uses 208,094 rows (35 author movement events); PX082 uses the identical 104,051-row common anchor across all paired arms (18 movement events).

| Study | Contrast / condition | Macro-F1 | Δ F1 (pp) | Exfil warning recall (%) | Exfil → benign mean count | Benign false alerts mean | F1 up / warning down seeds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PX081 | clean / B1 | 0.7139 → 0.7500 | 3.61 | 87.95 → 67.83 | 414.67 → 1107.33 | 174.00 → 169.67 | 2 |
| PX081 | clean / B2 | 0.7181 → 0.7551 | 3.70 | 87.58 → 67.33 | 427.33 → 1124.67 | 101.33 → 107.33 | 2 |
| PX081 | clean / B3 | 0.7148 → 0.7379 | 2.31 | 85.18 → 76.25 | 510.00 → 817.33 | 111.33 → 122.33 | 2 |
| PX081 | delayed_unavailable / B1 | 0.7168 → 0.7509 | 3.42 | 81.54 → 67.73 | 635.33 → 1110.67 | 169.67 → 167.67 | 2 |
| PX081 | delayed_unavailable / B2 | 0.7187 → 0.7544 | 3.57 | 81.41 → 67.46 | 640.00 → 1120.00 | 143.33 → 144.33 | 2 |
| PX081 | delayed_unavailable / B3 | 0.7180 → 0.7427 | 2.47 | 81.00 → 69.20 | 654.00 → 1060.00 | 144.00 → 146.33 | 3 |
| PX081 | wrong_host_history / B1 | 0.7139 → 0.7500 | 3.61 | 87.95 → 67.83 | 414.67 → 1107.33 | 174.00 → 169.67 | 2 |
| PX081 | wrong_host_history / B2 | 0.5687 → 0.6921 | 12.34 | 87.46 → 67.13 | 431.67 → 1131.33 | 66.00 → 81.00 | 3 |
| PX081 | wrong_host_history / B3 | 0.6873 → 0.6763 | -1.10 | 77.52 → 77.37 | 773.67 → 779.00 | 73.00 → 87.00 | 1 |
| PX082 | current_mixed_minus_past | 0.7365 → 0.7997 | 6.32 | 67.27 → 99.28 | 563.67 → 12.33 | 24.00 → 88.67 | 0 |
| PX082 | current_history_mixed_minus_past | 0.7582 → 0.7964 | 3.83 | 66.86 → 84.71 | 570.67 → 263.33 | 14.33 → 47.67 | 0 |
| PX082 | chronological_history_minus_current | 0.7365 → 0.7582 | 2.17 | 67.27 → 66.86 | 563.67 → 570.67 | 24.00 → 14.33 | 3 |

For PX081 the candidate is harm and baseline is entropy. For PX082 mixed-minus-past, future-training exposure is deliberate protocol sensitivity, not deployment-valid improvement.

## Complete warning/recognition decomposition by stage

| Contrast | Stage | Support | Exact recall (%) | Warning recall (%) | Attack → benign | Wrong attack stage |
| --- | --- | --- | --- | --- | --- | --- |
| PX081 clean / B1 | OtherAttackStage | 12424 | 96.80 → 96.80 | 99.68 → 99.68 | 40.33 → 39.67 | 357.00 → 357.33 |
| PX081 clean / B1 | LateralMovement | 35 | 81.90 → 81.90 | 81.90 → 81.90 | 6.33 → 6.33 | 0.00 → 0.00 |
| PX081 clean / B1 | DataExfiltration | 3442 | 67.52 → 67.52 | 87.95 → 67.83 | 414.67 → 1107.33 | 703.33 → 10.67 |
| PX081 clean / B2 | OtherAttackStage | 12424 | 97.02 → 96.99 | 99.50 → 99.51 | 61.67 → 60.33 | 308.00 → 314.00 |
| PX081 clean / B2 | LateralMovement | 35 | 63.81 → 61.90 | 63.81 → 61.90 | 12.67 → 13.33 | 0.00 → 0.00 |
| PX081 clean / B2 | DataExfiltration | 3442 | 67.29 → 67.25 | 87.58 → 67.33 | 427.33 → 1124.67 | 698.67 → 2.67 |
| PX081 clean / B3 | OtherAttackStage | 12424 | 97.03 → 97.00 | 99.51 → 99.51 | 60.33 → 60.67 | 309.00 → 311.67 |
| PX081 clean / B3 | LateralMovement | 35 | 65.71 → 69.52 | 65.71 → 69.52 | 12.00 → 10.67 | 0.00 → 0.00 |
| PX081 clean / B3 | DataExfiltration | 3442 | 67.29 → 67.18 | 85.18 → 76.25 | 510.00 → 817.33 | 616.00 → 312.33 |
| PX081 delayed_unavailable / B1 | OtherAttackStage | 12424 | 96.78 → 96.79 | 99.67 → 99.68 | 40.67 → 39.67 | 359.00 → 358.67 |
| PX081 delayed_unavailable / B1 | LateralMovement | 35 | 80.95 → 80.95 | 80.95 → 80.95 | 6.67 → 6.67 | 0.00 → 0.00 |
| PX081 delayed_unavailable / B1 | DataExfiltration | 3442 | 67.52 → 67.52 | 81.54 → 67.73 | 635.33 → 1110.67 | 482.67 → 7.33 |
| PX081 delayed_unavailable / B2 | OtherAttackStage | 12424 | 96.88 → 96.87 | 99.62 → 99.62 | 47.33 → 46.67 | 340.00 → 342.33 |
| PX081 delayed_unavailable / B2 | LateralMovement | 35 | 76.19 → 74.29 | 76.19 → 74.29 | 8.33 → 9.00 | 0.00 → 0.00 |
| PX081 delayed_unavailable / B2 | DataExfiltration | 3442 | 67.44 → 67.42 | 81.41 → 67.46 | 640.00 → 1120.00 | 480.67 → 1.33 |
| PX081 delayed_unavailable / B3 | OtherAttackStage | 12424 | 96.88 → 96.87 | 99.62 → 99.62 | 47.67 → 47.00 | 339.67 → 342.00 |
| PX081 delayed_unavailable / B3 | LateralMovement | 35 | 75.24 → 75.24 | 75.24 → 75.24 | 8.67 → 8.67 | 0.00 → 0.00 |
| PX081 delayed_unavailable / B3 | DataExfiltration | 3442 | 67.43 → 67.43 | 81.00 → 69.20 | 654.00 → 1060.00 | 467.00 → 61.00 |
| PX081 wrong_host_history / B1 | OtherAttackStage | 12424 | 96.80 → 96.80 | 99.68 → 99.68 | 40.33 → 39.67 | 357.00 → 357.33 |
| PX081 wrong_host_history / B1 | LateralMovement | 35 | 81.90 → 81.90 | 81.90 → 81.90 | 6.33 → 6.33 | 0.00 → 0.00 |
| PX081 wrong_host_history / B1 | DataExfiltration | 3442 | 67.52 → 67.52 | 87.95 → 67.83 | 414.67 → 1107.33 | 703.33 → 10.67 |
| PX081 wrong_host_history / B2 | OtherAttackStage | 12424 | 37.92 → 72.48 | 39.99 → 74.57 | 7456.00 → 3159.67 | 257.33 → 260.00 |
| PX081 wrong_host_history / B2 | LateralMovement | 35 | 40.00 → 40.95 | 40.00 → 40.95 | 21.00 → 20.67 | 0.00 → 0.00 |
| PX081 wrong_host_history / B2 | DataExfiltration | 3442 | 67.20 → 67.08 | 87.46 → 67.13 | 431.67 → 1131.33 | 697.33 → 1.67 |
| PX081 wrong_host_history / B3 | OtherAttackStage | 12424 | 79.00 → 75.19 | 81.11 → 77.31 | 2347.33 → 2819.33 | 262.00 → 263.67 |
| PX081 wrong_host_history / B3 | LateralMovement | 35 | 40.00 → 43.81 | 40.00 → 43.81 | 21.00 → 19.67 | 0.00 → 0.00 |
| PX081 wrong_host_history / B3 | DataExfiltration | 3442 | 67.22 → 67.01 | 77.52 → 77.37 | 773.67 → 779.00 | 354.67 → 356.67 |
| PX082 current_mixed_minus_past | OtherAttackStage | 6213 | 96.79 → 97.98 | 99.70 → 99.86 | 18.67 → 8.67 | 180.67 → 116.67 |
| PX082 current_mixed_minus_past | LateralMovement | 18 | 25.93 → 61.11 | 25.93 → 61.11 | 13.33 → 7.00 | 0.00 → 0.00 |
| PX082 current_mixed_minus_past | DataExfiltration | 1722 | 67.25 → 98.72 | 67.27 → 99.28 | 563.67 → 12.33 | 0.33 → 9.67 |
| PX082 current_history_mixed_minus_past | OtherAttackStage | 6213 | 97.26 → 99.73 | 99.13 → 99.93 | 54.33 → 4.33 | 115.67 → 12.67 |
| PX082 current_history_mixed_minus_past | LateralMovement | 18 | 29.63 → 57.41 | 29.63 → 57.41 | 12.67 → 7.67 | 0.00 → 0.00 |
| PX082 current_history_mixed_minus_past | DataExfiltration | 1722 | 66.40 → 84.59 | 66.86 → 84.71 | 570.67 → 263.33 | 8.00 → 2.00 |
| PX082 chronological_history_minus_current | OtherAttackStage | 6213 | 96.79 → 97.26 | 99.70 → 99.13 | 18.67 → 54.33 | 180.67 → 115.67 |
| PX082 chronological_history_minus_current | LateralMovement | 18 | 25.93 → 29.63 | 25.93 → 29.63 | 13.33 → 12.67 | 0.00 → 0.00 |
| PX082 chronological_history_minus_current | DataExfiltration | 1722 | 67.25 → 66.40 | 67.27 → 66.86 | 563.67 → 570.67 | 0.33 → 8.00 |

## Per-seed paired macro-F1 and exfiltration-warning differences

Brackets are descriptive 95% paired capture-percentile intervals. They resample the same five fragments from one campaign. They do not quantify independent-campaign generalization or constitute confirmatory tests. All rate/count/stage intervals are in PAIRED_METRICS.csv.

| Contrast | Seed | Δ macro-F1 pp [interval] | Δ exfil warning pp [interval] | Δ exfil → benign | F1 valid draws | Exfil valid draws |
| --- | --- | --- | --- | --- | --- | --- |
| PX081 clean / B1 | 8101 | 5.37 [1.24, 9.48] | -29.81 [-95.57, -3.41] | 1026 | 1981 | 2000 |
| PX081 clean / B1 | 8102 | 5.77 [1.18, 9.95] | -30.56 [-96.21, -3.64] | 1052 | 1981 | 2000 |
| PX081 clean / B1 | 8103 | -0.31 [-0.54, 0.06] | 0.00 [0.00, 0.00] | 0 | 1981 | 2000 |
| PX081 clean / B2 | 8101 | 5.83 [1.30, 9.74] | -30.36 [-95.87, -3.68] | 1045 | 1981 | 2000 |
| PX081 clean / B2 | 8102 | 5.44 [1.17, 10.04] | -30.42 [-95.96, -3.64] | 1047 | 1981 | 2000 |
| PX081 clean / B2 | 8103 | -0.17 [-0.46, 0.25] | 0.00 [-0.08, 0.52] | 0 | 1981 | 2000 |
| PX081 clean / B3 | 8101 | 5.65 [0.78, 10.41] | -26.06 [-92.42, -0.88] | 897 | 1981 | 2000 |
| PX081 clean / B3 | 8102 | -0.08 [-0.32, 0.07] | -0.09 [-0.52, 0.00] | 3 | 1981 | 2000 |
| PX081 clean / B3 | 8103 | 1.38 [0.17, 3.47] | -0.64 [-3.06, -0.15] | 22 | 1981 | 2000 |
| PX081 delayed_unavailable / B1 | 8101 | 5.13 [1.12, 9.53] | -20.71 [-66.79, -2.38] | 713 | 1981 | 2000 |
| PX081 delayed_unavailable / B1 | 8102 | 5.43 [1.09, 10.00] | -20.71 [-66.24, -2.38] | 713 | 1981 | 2000 |
| PX081 delayed_unavailable / B1 | 8103 | -0.32 [-0.68, 0.19] | 0.00 [0.00, 0.00] | 0 | 1981 | 2000 |
| PX081 delayed_unavailable / B2 | 8101 | 5.33 [1.04, 9.36] | -21.12 [-66.96, -2.51] | 727 | 1981 | 2000 |
| PX081 delayed_unavailable / B2 | 8102 | 5.52 [1.01, 10.72] | -20.69 [-66.24, -2.36] | 712 | 1981 | 2000 |
| PX081 delayed_unavailable / B2 | 8103 | -0.15 [-0.39, 0.50] | -0.03 [-0.27, 0.00] | 1 | 1981 | 2000 |
| PX081 delayed_unavailable / B3 | 8101 | 5.28 [1.01, 9.04] | -20.28 [-66.67, -2.06] | 698 | 1981 | 2000 |
| PX081 delayed_unavailable / B3 | 8102 | 1.97 [0.29, 3.69] | -15.02 [-48.06, -1.68] | 517 | 1981 | 2000 |
| PX081 delayed_unavailable / B3 | 8103 | 0.15 [-0.40, 1.50] | -0.09 [-0.96, 0.16] | 3 | 1981 | 2000 |
| PX081 wrong_host_history / B1 | 8101 | 5.37 [1.24, 9.48] | -29.81 [-95.57, -3.41] | 1026 | 1981 | 2000 |
| PX081 wrong_host_history / B1 | 8102 | 5.77 [1.18, 9.95] | -30.56 [-96.21, -3.64] | 1052 | 1981 | 2000 |
| PX081 wrong_host_history / B1 | 8103 | -0.31 [-0.54, 0.06] | 0.00 [0.00, 0.00] | 0 | 1981 | 2000 |
| PX081 wrong_host_history / B2 | 8101 | 4.30 [1.41, 8.57] | -30.48 [-95.96, -3.81] | 1049 | 1981 | 2000 |
| PX081 wrong_host_history / B2 | 8102 | 9.08 [4.03, 13.03] | -30.48 [-96.00, -3.70] | 1049 | 1981 | 2000 |
| PX081 wrong_host_history / B2 | 8103 | 23.65 [21.71, 24.32] | -0.03 [-0.08, 0.26] | 1 | 1981 | 2000 |
| PX081 wrong_host_history / B3 | 8101 | -1.02 [-3.04, 0.01] | -0.32 [-1.31, 0.34] | 11 | 1981 | 2000 |
| PX081 wrong_host_history / B3 | 8102 | -2.78 [-4.01, -1.41] | 0.06 [-0.81, 1.95] | -2 | 1981 | 2000 |
| PX081 wrong_host_history / B3 | 8103 | 0.50 [0.36, 0.83] | -0.20 [-0.96, -0.06] | 7 | 1981 | 2000 |
| PX082 current_mixed_minus_past | 20260923 | 7.52 [1.96, 26.31] | 32.11 [4.05, 98.38] | -553 | 1981 | 2000 |
| PX082 current_history_mixed_minus_past | 20260923 | 3.32 [1.20, 17.24] | 12.66 [1.92, 70.30] | -218 | 1981 | 2000 |
| PX082 chronological_history_minus_current | 20260923 | 2.98 [0.42, 6.41] | -0.41 [-2.62, 0.00] | 7 | 1981 | 2000 |
| PX082 current_mixed_minus_past | 20260924 | 6.99 [1.65, 24.36] | 32.00 [3.97, 98.38] | -551 | 1981 | 2000 |
| PX082 current_history_mixed_minus_past | 20260924 | 2.97 [0.62, 15.49] | 9.29 [1.17, 64.31] | -160 | 1981 | 2000 |
| PX082 chronological_history_minus_current | 20260924 | 1.08 [-2.11, 4.20] | -0.35 [-2.09, 0.00] | 6 | 1981 | 2000 |
| PX082 current_mixed_minus_past | 20260925 | 4.46 [0.12, 20.62] | 31.94 [3.97, 98.17] | -550 | 1981 | 2000 |
| PX082 current_history_mixed_minus_past | 20260925 | 5.18 [-0.75, 25.69] | 31.59 [3.76, 98.38] | -544 | 1981 | 2000 |
| PX082 chronological_history_minus_current | 20260925 | 2.45 [0.43, 3.07] | -0.46 [-2.88, -0.09] | 8 | 1981 | 2000 |

## Complete directional counts

| Study | Stage | Pairs | F1 up / warning down | F1 down / warning up | Warning interval below 0 | F1 interval above 0 + warning below 0 |
| --- | --- | --- | --- | --- | --- | --- |
| PX081 | OtherAttackStage | 27 | 7 | 2 | 3 | 1 |
| PX081 | LateralMovement | 27 | 2 | 3 | 0 | 0 |
| PX081 | DataExfiltration | 27 | 19 | 1 | 17 | 17 |
| PX082 | OtherAttackStage | 9 | 3 | 0 | 0 | 0 |
| PX082 | LateralMovement | 9 | 0 | 0 | 0 | 0 |
| PX082 | DataExfiltration | 9 | 3 | 0 | 1 | 1 |

Counts of interval directions are descriptive; the pairs share rows and models and are not independent replications.

## Uncertainty, verification and practical limits

One row-bound bootstrap plan per cohort is shared across every comparison and fitting seed. The two cohorts use identical capture multiplicities (2,000 draws, seed 20260923). Stage rates/F1 are undefined in draws lacking their true stage; fixed-four-class macro-F1 needs every true class. Every interval reports valid/undefined draws. Count intervals remain defined at zero stage support. Original PX082 intervals are unchanged; these new intervals use a different declared support convention and shared resampling plan.

The source is a previously exposed single UNRAVELED campaign. Five captures are fragments of that campaign, not five independent attacks. The author movement label is Remote System Discovery progress on one host pair. Completed flows do not demonstrate early prediction, confirmed movement, or confirmed data theft. PX081 collection costs/availability are simulated; PX082 future-training arms intentionally violate chronological deployment. These findings establish a concrete measurement disagreement on this benchmark, not a generally superior detector or novel universal metric.

Independent vectorized confusion arithmetic checked 720 point/interval quantities; a separate publication audit checked 756 mean/direction quantities. This verifies arithmetic and saved-source identity, not human label correctness. All 20 relevant synthetic/helper tests passed before freeze.

## Artifacts

- [Analysis plan](ANALYSIS_PLAN.md), [freeze](FREEZE.json), [input provenance](INPUTS.json), [arithmetic audit](AUDIT.json).
- [All paired metrics](PAIRED_RESULTS.json), [flat paired metrics and CIs](PAIRED_METRICS.csv).
- [Three-seed means](MEANS.json), [flat means](MEANS.csv), [direction counts](DIRECTION_COUNTS.json).
- [Capture sufficient statistics](CAPTURE_CONFUSIONS.json), [shared capture draws](CAPTURE_DRAWS.json).
- [Figure](METRIC_DISAGREEMENT.png), [vector figure](METRIC_DISAGREEMENT.pdf).
