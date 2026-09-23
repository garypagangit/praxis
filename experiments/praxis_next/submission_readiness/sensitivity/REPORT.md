# Capture and fitting-seed sensitivity of the measured warning tradeoff

**Status: completed retrospective audit.** All 36 paired contrasts were evaluated under all five capture omissions; all 12 experiment groups were evaluated under all three fitting-seed omissions. No model was refitted, no operating threshold changed, and no original evidence file was modified.

The calculations address how much the observed findings depend on a particular fragment or fit. Removing a capture changes the evaluation population while leaving predictions fixed. Removing a fitting seed averages the remaining two per-seed metrics. Neither creates an independent test campaign or measures a model retrained without that capture.

## Complete three-seed groups: omit each fitting seed

All changes are candidate minus baseline. Macro-F1 changes are score points (the raw score difference multiplied by 100); recall and false-alert-rate changes are percentage points. Ranges contain exactly the three specified omissions, not confidence intervals. The last column counts F1-up/exfil-warning-down among defined omission means.

| Comparison | Full mean Δ macro-F1 (×100) | Full mean Δ exfil warning pp | Two-seed mean Δ macro-F1 (×100) range | Two-seed mean Δ warning pp range | F1 up / warning down |
| --- | --- | --- | --- | --- | --- |
| PX081 clean B1 | 3.61 | -20.12 | 2.53 to 5.57 | -30.19 to -14.90 | 3/3 defined (0 undefined) |
| PX081 clean B2 | 3.70 | -20.26 | 2.64 to 5.63 | -30.39 to -15.18 | 3/3 defined (0 undefined) |
| PX081 clean B3 | 2.31 | -8.93 | 0.65 to 3.51 | -13.35 to -0.36 | 3/3 defined (0 undefined) |
| PX081 delayed unavailable B1 | 3.42 | -13.81 | 2.41 to 5.28 | -20.71 to -10.36 | 3/3 defined (0 undefined) |
| PX081 delayed unavailable B2 | 3.57 | -13.95 | 2.59 to 5.42 | -20.90 to -10.36 | 3/3 defined (0 undefined) |
| PX081 delayed unavailable B3 | 2.47 | -11.80 | 1.06 to 3.63 | -17.65 to -7.55 | 3/3 defined (0 undefined) |
| PX081 wrong host history B1 | 3.61 | -20.12 | 2.53 to 5.57 | -30.19 to -14.90 | 3/3 defined (0 undefined) |
| PX081 wrong host history B2 | 12.34 | -20.33 | 6.69 to 16.36 | -30.48 to -15.25 | 3/3 defined (0 undefined) |
| PX081 wrong host history B3 | -1.10 | -0.15 | -1.90 to -0.26 | -0.26 to -0.07 | 0/3 defined (0 undefined) |
| PX082 current mixed minus past | 6.32 | 32.02 | 5.73 to 7.26 | 31.97 to 32.06 | 0/3 defined (0 undefined) |
| PX082 current history mixed minus past | 3.83 | 17.85 | 3.15 to 4.25 | 10.98 to 22.13 | 0/3 defined (0 undefined) |
| PX082 chronological history minus current | 2.17 | -0.41 | 1.77 to 2.72 | -0.44 to -0.38 | 3/3 defined (0 undefined) |

9/12 groups have the specified mean sign disagreement on all data; 9/12 retain it under every fitting-seed omission. These are observed group counts, not independent replications or a statistical acceptance rate.

## Complete groups: omit each capture

Each entry is a range across all five omissions of a three-seed mean of point differences. Different omissions retain different numbers of rows; the complete per-seed tables preserve row and class supports. Both methods always retain the same rows for a given comparison.

| Comparison | Δ macro-F1 (×100) range | Δ exfil warning pp range | Δ movement exact recall pp range | Δ benign false-alert rate pp range | F1 up / warning down |
| --- | --- | --- | --- | --- | --- |
| PX081 clean B1 | 2.56 to 5.48 | -58.26 to -8.37 | -0.00 to 0.00 | -0.00 to -0.00 | 5/5 defined (0 undefined) |
| PX081 clean B2 | 2.90 to 5.86 | -58.48 to -8.54 | -2.30 to -1.39 | 0.00 to 0.00 | 5/5 defined (0 undefined) |
| PX081 clean B3 | 1.52 to 3.67 | -25.71 to -2.80 | 3.45 to 4.17 | 0.00 to 0.01 | 5/5 defined (0 undefined) |
| PX081 delayed unavailable B1 | 2.35 to 5.34 | -39.98 to -5.62 | 0.00 to 0.00 | -0.00 to -0.00 | 5/5 defined (0 undefined) |
| PX081 delayed unavailable B2 | 2.50 to 5.84 | -40.34 to -5.79 | -2.30 to -1.39 | -0.00 to 0.00 | 5/5 defined (0 undefined) |
| PX081 delayed unavailable B3 | 1.89 to 3.77 | -34.15 to -4.72 | -1.39 to 1.96 | 0.00 to 0.00 | 5/5 defined (0 undefined) |
| PX081 wrong host history B1 | 2.56 to 5.48 | -58.26 to -8.37 | -0.00 to 0.00 | -0.00 to -0.00 | 5/5 defined (0 undefined) |
| PX081 wrong host history B2 | 11.77 to 13.87 | -58.59 to -8.62 | 0.00 to 1.39 | 0.01 to 0.01 | 5/5 defined (0 undefined) |
| PX081 wrong host history B3 | -1.38 to -0.93 | -0.25 to -0.04 | 2.78 to 4.60 | 0.01 to 0.01 | 0/5 defined (0 undefined) |
| PX082 current mixed minus past | 3.64 to 19.43 | 14.86 to 92.66 | 18.52 to 55.56 | 0.06 to 0.08 | 0/5 defined (0 undefined) |
| PX082 current history mixed minus past | 1.65 to 13.32 | 11.66 to 51.20 | 18.52 to 38.89 | 0.03 to 0.04 | 0/5 defined (0 undefined) |
| PX082 chronological history minus current | 1.38 to 2.70 | -0.84 to -0.15 | 0.00 to 11.11 | -0.01 to -0.01 | 5/5 defined (0 undefined) |

9/12 groups retain the specified mean sign disagreement under every capture omission. This finite perturbation result does not justify independent-campaign generalization.

## Clean budget-three sensitivity in detail

This comparison was highlighted before the audit because its original mean combines markedly different fitting-seed outcomes. The table retains every omission; it does not select a preferred result.

| Omitted unit | Δ macro-F1 (×100) | Δ exfil warning pp | Mean extra exfil → benign | Mean extra benign alerts |
| --- | --- | --- | --- | --- |
| None (three-seed mean) | 2.31 | -8.93 | 307.33 | 11.00 |
| Fit seed 8101 | 0.65 | -0.36 | 12.50 | 14.00 |
| Fit seed 8102 | 3.51 | -13.35 | 459.50 | 3.00 |
| Fit seed 8103 | 2.78 | -13.07 | 450.00 | 16.00 |
| Capture 6 (three-seed mean) | 1.57 | -25.71 | 305.67 | 7.00 |
| Capture 7 (three-seed mean) | 3.67 | -8.95 | 307.33 | 8.67 |
| Capture 8 (three-seed mean) | 2.26 | -9.12 | 293.00 | 7.67 |
| Capture 9 (three-seed mean) | 2.16 | -7.74 | 246.33 | 9.67 |
| Capture 10 (three-seed mean) | 1.52 | -2.80 | 77.00 | 11.00 |

Positive missed-warning counts mean fewer attack warnings. Positive benign false-alert counts mean more benign records labeled attack. Count changes across capture omissions refer to different retained populations and should be read with their rate changes and support counts.

The clean budget-three mean retains higher F1/lower warning recall under all five capture omissions and all three fitting-seed omissions. At individual-seed level, 10/15 capture-omission pairs have that direction: five for seed 8101, zero for seed 8102 and five for seed 8103. The direction of the seed mean is stable under the specified omissions, while its magnitude is strongly seed-sensitive.

## Temporal-score direction under every capture omission

| Contrast | Fitting seed | Positive Δ macro-F1 omissions | Δ macro-F1 (×100) range | Nonpositive omitted captures |
| --- | --- | --- | --- | --- |
| current_mixed_minus_past | 20260923 | 5/5 | 4.80 to 21.78 | None |
| current_mixed_minus_past | 20260924 | 5/5 | 4.29 to 20.56 | None |
| current_mixed_minus_past | 20260925 | 5/5 | 1.83 to 15.95 | None |
| current_history_mixed_minus_past | 20260923 | 5/5 | 1.64 to 10.82 | None |
| current_history_mixed_minus_past | 20260924 | 5/5 | 1.02 to 8.34 | None |
| current_history_mixed_minus_past | 20260925 | 5/5 | 2.30 to 20.81 | None |
| chronological_history_minus_current | 20260923 | 5/5 | 1.78 to 3.89 | None |
| chronological_history_minus_current | 20260924 | 4/5 | -0.13 to 2.52 | 9 |
| chronological_history_minus_current | 20260925 | 5/5 | 1.67 to 2.57 | None |

Both mixed-minus-past feature views retain a positive F1 difference in all 15 seed/capture-omission pairs. The chronological history-minus-current contrast is positive in 14/15: omitting capture 9 for seed 20260924 gives −0.13 macro-F1 score points. Every three-seed mean remains positive in that history contrast. These are fixed-prediction sensitivity results, not a new temporal test.

Unsupported-metric capture omissions: 0; omission IDs: []. All declared evaluation classes remain supported in each of these leave-one-capture-out populations. This does not contradict the earlier bootstrap’s unsupported draws: sampling captures with replacement can omit several distinct captures at once.

## Repeated aggregate comparisons

The original PX081 count is 19/27 paired seed comparisons with higher F1 and lower exfiltration warning recall. The ordered per-capture confusion signatures form 24 aggregate-equivalent classes; 17 of those classes have that direction. There are 3 classes with more than one registered comparison.

**Aggregate equivalence is not independence or proof of identical row-level predictions.** The signatures preserve ordered baseline/candidate matrices, capture order and class meanings. They establish equivalence only for these sufficient-statistic calculations. Different rows can be mislabeled yet yield the same confusion matrix. All signature classes still share a single campaign, many events and fitted components.

| Signature prefix | Registered comparisons | F1 up / warning down | Members |
| --- | --- | --- | --- |
| e2300f301195 | 2 | True | PX081|harm_minus_entropy|clean|1|8101; PX081|harm_minus_entropy|wrong_host_history|1|8101 |
| e2e3d7fcdde8 | 2 | True | PX081|harm_minus_entropy|clean|1|8102; PX081|harm_minus_entropy|wrong_host_history|1|8102 |
| 13931c5d3a40 | 2 | False | PX081|harm_minus_entropy|clean|1|8103; PX081|harm_minus_entropy|wrong_host_history|1|8103 |

Every equivalence class, including singletons and contrary directions, is saved in [AGGREGATE_EQUIVALENCE.json](AGGREGATE_EQUIVALENCE.json).

## Complete omission tables

- [All 180 paired capture omissions](CAPTURE_OMISSIONS.json) and [flat CSV](CAPTURE_OMISSIONS.csv), including supports and undefined values.
- [All 36 fitting-seed omissions](SEED_OMISSIONS.json) and [flat CSV](SEED_OMISSIONS.csv).
- [All 60 capture-omission seed means](CAPTURE_OMISSION_MEANS.json), [12 compact group summaries](SUMMARY.json), and [full-data reference points](FULL_POINTS.json).
- [Plan](ANALYSIS_PLAN.md), [input hashes](INPUTS.json), [freeze](FREEZE.json) and [arithmetic audit](AUDIT.json).

## Reproducibility and interpretation

Plan and executable code were committed at `e9de91d` before the omission calculations. The run completed 3816 scalar checks, including comparison with a separately implemented public confusion verifier. Five synthetic tests cover missing-stage metrics, capture weighting, seed averaging, directional flags and confusion-equivalent predictions. The run used public counts only and performed zero model fits.

Fixed-four-class macro-F1 is undefined when any true class is absent; stage recalls are undefined when that stage is absent. Null omission values remain explicit and are not converted to zero. Counts remain defined. Finite minimum/maximum omission ranges are descriptive and do not replace the original paired bootstrap intervals.

The source has only one previously examined campaign. Capture removal is not independent holdout validation, and a fitting seed is not an attack execution. The movement target is author Remote System Discovery progress; full-flow outcomes do not prove early exfiltration prediction or successful movement. This audit improves the precision of the empirical claim and its stated limitations; it cannot establish publication novelty or external generalization.
