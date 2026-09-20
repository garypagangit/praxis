# Missing/delayed-log development comparisons

Datasets and target labels remain separate. Values are means across the fixed corruption seeds within each condition; ranges in JSON describe mask variability, not independent replication or confidence intervals.

Both decision rules are shown: fixed score > 0.5, and each model's separately frozen clean-calibration threshold. Completely unobserved targets remain in the denominator and receive no alarm.

## ait

Author rule annotations on audit fragments, unioned into events. Previously exposed development runs; other-label negatives are not independently adjudicated benign activity.

### escalate

Status: **COMPLETE**. Test support: 6,293 events, 44 positives, 6,249 other-label negatives.

Per-run support: harrison: 24 positive / 2806 negative; wilson: 20 positive / 3443 negative.

Preselected overview below; **all conditions, precision, recall, negative-label flag rates, coverage and paired per-run differences** appear in COMPARISONS.json.

| Condition | Decision | Generic F1 | Semantic F1 | Context F1 | Dropout F1 | Context − semantic | Dropout − context | Coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| clean | 0.5 | 0.6324 | 0.6833 | 0.7321 | 0.7130 | +0.0488 | -0.0191 | 1.0000 |
| clean | calibrated | 0.4757 | 0.5694 | 0.6833 | 0.6721 | +0.1139 | -0.0112 | 1.0000 |
| random_50 | 0.5 | 0.4740 | 0.4882 | 0.4818 | 0.4680 | -0.0064 | -0.0138 | 0.4992 |
| random_50 | calibrated | 0.3842 | 0.4268 | 0.4561 | 0.4517 | +0.0293 | -0.0044 | 0.4992 |
| support_burst_60 | 0.5 | 0.6324 | 0.6833 | 0.6165 | 0.5985 | -0.0668 | -0.0180 | 1.0000 |
| support_burst_60 | calibrated | 0.4757 | 0.5694 | 0.5734 | 0.5734 | +0.0040 | +0.0000 | 1.0000 |
| command_records_absent | 0.5 | 0.6324 | 0.6833 | 0.7321 | 0.7130 | +0.0488 | -0.0191 | 1.0000 |
| command_records_absent | calibrated | 0.4757 | 0.5694 | 0.6833 | 0.6721 | +0.1139 | -0.0112 | 1.0000 |

A positive F1 difference is descriptive, not an automatic win: check its recall/flag-rate tradeoff and each run. F1/recall comparisons for a run with no positive target labels are undefined, not evidence of successful detection.

## casino

Source process-technique annotations. Targets are annotation-onset proxies and negatives are other annotated techniques; not benign detection or independently verified action onset.

### T1068

Status: **COMPLETE**. Test support: 920 events, 14 positives, 906 other-label negatives.

Per-run support: aeriella: 0 positive / 3 negative; arthur: 0 positive / 45 negative; eclatant: 0 positive / 40 negative; etonnant: 1 positive / 104 negative; exaltant: 2 positive / 36 negative; exuberant: 3 positive / 75 negative; genereux: 1 positive / 79 negative; illusion: 0 positive / 18 negative; lumieres: 2 positive / 99 negative; magiqua: 0 positive / 8 negative; magique: 0 positive / 5 negative; papillon: 1 positive / 141 negative; radieusa: 0 positive / 12 negative; ravissant: 3 positive / 22 negative; seduisant: 0 positive / 4 negative; snoopy: 0 positive / 112 negative; vacances: 0 positive / 34 negative; vivifiant: 1 positive / 69 negative.

Preselected overview below; **all conditions, precision, recall, negative-label flag rates, coverage and paired per-run differences** appear in COMPARISONS.json.

| Condition | Decision | Generic F1 | Semantic F1 | Context F1 | Dropout F1 | Context − semantic | Dropout − context | Coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| clean | 0.5 | 0.2435 | 0.3889 | 0.3944 | 0.3836 | +0.0055 | -0.0108 | 1.0000 |
| clean | calibrated | 0.4286 | 0.6857 | 0.6667 | 0.6667 | -0.0190 | +0.0000 | 1.0000 |
| random_50 | 0.5 | 0.1247 | 0.1544 | 0.1809 | 0.2927 | +0.0264 | +0.1118 | 0.9547 |
| random_50 | calibrated | 0.3264 | 0.2393 | 0.3043 | 0.4955 | +0.0650 | +0.1913 | 0.9547 |
| support_burst_60 | 0.5 | 0.2435 | 0.3889 | 0.3881 | 0.4062 | -0.0008 | +0.0182 | 1.0000 |
| support_burst_60 | calibrated | 0.4286 | 0.6857 | 0.7273 | 0.7273 | +0.0416 | +0.0000 | 1.0000 |
| command_records_absent | 0.5 | 0.3111 | 0.2955 | 0.3291 | 0.2593 | +0.0337 | -0.0699 | 1.0000 |
| command_records_absent | calibrated | 0.4667 | 0.5000 | 0.6190 | 0.4000 | +0.1190 | -0.2190 | 1.0000 |

A positive F1 difference is descriptive, not an automatic win: check its recall/flag-rate tradeoff and each run. F1/recall comparisons for a run with no positive target labels are undefined, not evidence of successful detection.

### T1548

Status: **COMPLETE**. Test support: 920 events, 39 positives, 881 other-label negatives.

Per-run support: aeriella: 0 positive / 3 negative; arthur: 1 positive / 44 negative; eclatant: 1 positive / 39 negative; etonnant: 5 positive / 100 negative; exaltant: 2 positive / 36 negative; exuberant: 3 positive / 75 negative; genereux: 1 positive / 79 negative; illusion: 4 positive / 14 negative; lumieres: 3 positive / 98 negative; magiqua: 0 positive / 8 negative; magique: 1 positive / 4 negative; papillon: 3 positive / 139 negative; radieusa: 0 positive / 12 negative; ravissant: 0 positive / 25 negative; seduisant: 0 positive / 4 negative; snoopy: 0 positive / 112 negative; vacances: 7 positive / 27 negative; vivifiant: 8 positive / 62 negative.

Preselected overview below; **all conditions, precision, recall, negative-label flag rates, coverage and paired per-run differences** appear in COMPARISONS.json.

| Condition | Decision | Generic F1 | Semantic F1 | Context F1 | Dropout F1 | Context − semantic | Dropout − context | Coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| clean | 0.5 | 0.5739 | 0.6286 | 0.6471 | 0.6346 | +0.0185 | -0.0124 | 1.0000 |
| clean | calibrated | 0.5217 | 0.6923 | 0.7179 | 0.7179 | +0.0256 | +0.0000 | 1.0000 |
| random_50 | 0.5 | 0.1691 | 0.3470 | 0.4118 | 0.5589 | +0.0649 | +0.1471 | 0.9547 |
| random_50 | calibrated | 0.3257 | 0.5756 | 0.5932 | 0.6131 | +0.0176 | +0.0199 | 0.9547 |
| support_burst_60 | 0.5 | 0.5739 | 0.6286 | 0.6275 | 0.6275 | -0.0011 | +0.0000 | 1.0000 |
| support_burst_60 | calibrated | 0.5217 | 0.6923 | 0.6750 | 0.6750 | -0.0173 | +0.0000 | 1.0000 |
| command_records_absent | 0.5 | 0.1934 | 0.3139 | 0.3271 | 0.6226 | +0.0132 | +0.2955 | 1.0000 |
| command_records_absent | calibrated | 0.5818 | 0.6095 | 0.6226 | 0.7000 | +0.0131 | +0.0774 | 1.0000 |

A positive F1 difference is descriptive, not an automatic win: check its recall/flag-rate tradeoff and each run. F1/recall comparisons for a run with no positive target labels are undefined, not evidence of successful detection.

### T1105

Status: **COMPLETE**. Test support: 920 events, 17 positives, 903 other-label negatives.

Per-run support: aeriella: 0 positive / 3 negative; arthur: 0 positive / 45 negative; eclatant: 0 positive / 40 negative; etonnant: 2 positive / 103 negative; exaltant: 0 positive / 38 negative; exuberant: 1 positive / 77 negative; genereux: 1 positive / 79 negative; illusion: 0 positive / 18 negative; lumieres: 5 positive / 96 negative; magiqua: 0 positive / 8 negative; magique: 0 positive / 5 negative; papillon: 1 positive / 141 negative; radieusa: 0 positive / 12 negative; ravissant: 2 positive / 23 negative; seduisant: 0 positive / 4 negative; snoopy: 3 positive / 109 negative; vacances: 0 positive / 34 negative; vivifiant: 2 positive / 68 negative.

Preselected overview below; **all conditions, precision, recall, negative-label flag rates, coverage and paired per-run differences** appear in COMPARISONS.json.

| Condition | Decision | Generic F1 | Semantic F1 | Context F1 | Dropout F1 | Context − semantic | Dropout − context | Coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| clean | 0.5 | 0.1677 | 0.7368 | 0.5957 | 0.5833 | -0.1411 | -0.0124 | 1.0000 |
| clean | calibrated | 0.4242 | 0.7568 | 0.7000 | 0.6667 | -0.0568 | -0.0333 | 1.0000 |
| random_50 | 0.5 | 0.0937 | 0.2368 | 0.3274 | 0.3993 | +0.0906 | +0.0719 | 0.9547 |
| random_50 | calibrated | 0.1564 | 0.2564 | 0.3489 | 0.5173 | +0.0926 | +0.1684 | 0.9547 |
| support_burst_60 | 0.5 | 0.1677 | 0.7368 | 0.5769 | 0.5000 | -0.1599 | -0.0769 | 1.0000 |
| support_burst_60 | calibrated | 0.4242 | 0.7568 | 0.6250 | 0.5833 | -0.1318 | -0.0417 | 1.0000 |
| command_records_absent | 0.5 | 0.1290 | 0.2258 | 0.3607 | 0.1591 | +0.1348 | -0.2016 | 1.0000 |
| command_records_absent | calibrated | 0.5000 | 0.4138 | 0.4231 | 0.2203 | +0.0093 | -0.2027 | 1.0000 |

A positive F1 difference is descriptive, not an automatic win: check its recall/flag-rate tradeoff and each run. F1/recall comparisons for a run with no positive target labels are undefined, not evidence of successful detection.

## Interpretation limits

- The calibration budget is an empirical calibration-set operating point; it does not guarantee a population or deployment false-alarm rate. Other-label negatives have different meanings across datasets.
- Small positive counts, correlated events and shared recipes limit conclusions. Three removal seeds are not three independently trained models or attack campaigns.
- Random record loss often hides whole AIT singleton events. The evaluator's known target roster is not a deployed mechanism for detecting invisible events.
- A recent-support burst is a target-relative stress test; record-type removal is not a whole-sensor outage. Native arrival times are not measured.
- Recovery once waiting reaches the injected deterministic delay is guaranteed by construction. It is a buffering control with a latency cost, not a learned robustness success.
- No dataset/label pooling, winner selection, significance claim, larger-model recommendation or novelty claim is produced here.
- This helper summarizes supplied frozen aggregate results; it does not independently audit predictions or rerun models.
