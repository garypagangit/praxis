# casino missing/delayed-log development experiments

Fixed protocol; no new novelty claim. Event-time plus synthetic delays is not measured online latency.

Negative means absence of this source technique label in the eligible target roster; it does not mean independently verified benign activity.

Random conditions average three fixed perturbation seeds; other conditions are deterministic. Models and calibration thresholds stay fixed.

## Qualification

- Context events: 3,758,674; eligible prediction targets: 8,240.
- Input event SHA256: `17b5f4b3cc5465f3abfff6a94e0d850ba90246149e38365c3f47bdd5533f6b83`.
- Protocol SHA256: `8e3b38e68546cfb233806bb354a807f691401c41c1d1b5c6744d4def28e389ed`.
- Runtime: 27.39 seconds.

## T1068

Status: **COMPLETE**. Support: `{"calibration": {"n": 1494, "negative": 1471, "positive": 23}, "development": {"n": 1894, "negative": 1850, "positive": 44}, "fit": {"n": 3932, "negative": 3853, "positive": 79}, "test": {"n": 920, "negative": 906, "positive": 14}}`.

| Condition | Model | F1 at 0.5 | Recall at frozen calibration threshold | Other-label flag rate | Observed target coverage |
|---|---|---:|---:|---:|---:|
| clean | generic_event | 0.2435 | 0.4286 | 0.0088 | 1.0000 |
| clean | semantic_event | 0.3889 | 0.8571 | 0.0099 | 1.0000 |
| clean | entity_context | 0.3944 | 0.8571 | 0.0110 | 1.0000 |
| clean | context_dropout | 0.3836 | 0.8571 | 0.0110 | 1.0000 |
| random_25 | generic_event | 0.1687 | 0.3810 | 0.0099 | 0.9953 |
| random_25 | semantic_event | 0.2117 | 0.8095 | 0.0419 | 0.9953 |
| random_25 | entity_context | 0.2409 | 0.8571 | 0.0261 | 0.9953 |
| random_25 | context_dropout | 0.3396 | 0.7857 | 0.0129 | 0.9953 |
| random_50 | generic_event | 0.1247 | 0.4286 | 0.0188 | 0.9547 |
| random_50 | semantic_event | 0.1544 | 0.7381 | 0.0692 | 0.9547 |
| random_50 | entity_context | 0.1809 | 0.7857 | 0.0522 | 0.9547 |
| random_50 | context_dropout | 0.2927 | 0.7143 | 0.0180 | 0.9547 |
| random_75 | generic_event | 0.0874 | 0.3095 | 0.0140 | 0.7819 |
| random_75 | semantic_event | 0.1067 | 0.5952 | 0.0857 | 0.7819 |
| random_75 | entity_context | 0.1101 | 0.5238 | 0.0754 | 0.7819 |
| random_75 | context_dropout | 0.2223 | 0.5476 | 0.0258 | 0.7819 |
| support_burst_60 | generic_event | 0.2435 | 0.4286 | 0.0088 | 1.0000 |
| support_burst_60 | semantic_event | 0.3889 | 0.8571 | 0.0099 | 1.0000 |
| support_burst_60 | entity_context | 0.3881 | 0.8571 | 0.0077 | 1.0000 |
| support_burst_60 | context_dropout | 0.4062 | 0.8571 | 0.0077 | 1.0000 |
| command_records_absent | generic_event | 0.3111 | 0.5000 | 0.0099 | 1.0000 |
| command_records_absent | semantic_event | 0.2955 | 0.8571 | 0.0243 | 1.0000 |
| command_records_absent | entity_context | 0.3291 | 0.9286 | 0.0166 | 1.0000 |
| command_records_absent | context_dropout | 0.2593 | 0.9286 | 0.0419 | 1.0000 |
| delay_30_deadline_0 | generic_event | 0.3111 | 0.5000 | 0.0099 | 1.0000 |
| delay_30_deadline_0 | semantic_event | 0.2955 | 0.8571 | 0.0243 | 1.0000 |
| delay_30_deadline_0 | entity_context | 0.3291 | 0.9286 | 0.0166 | 1.0000 |
| delay_30_deadline_0 | context_dropout | 0.2593 | 0.9286 | 0.0386 | 1.0000 |
| delay_30_deadline_30 | generic_event | 0.2435 | 0.4286 | 0.0088 | 1.0000 |
| delay_30_deadline_30 | semantic_event | 0.3889 | 0.8571 | 0.0099 | 1.0000 |
| delay_30_deadline_30 | entity_context | 0.3944 | 0.8571 | 0.0110 | 1.0000 |
| delay_30_deadline_30 | context_dropout | 0.3836 | 0.8571 | 0.0110 | 1.0000 |
| delay_120_deadline_0 | generic_event | 0.3111 | 0.5000 | 0.0099 | 1.0000 |
| delay_120_deadline_0 | semantic_event | 0.2955 | 0.8571 | 0.0243 | 1.0000 |
| delay_120_deadline_0 | entity_context | 0.3291 | 0.9286 | 0.0166 | 1.0000 |
| delay_120_deadline_0 | context_dropout | 0.2593 | 0.9286 | 0.0419 | 1.0000 |
| delay_120_deadline_30 | generic_event | 0.3111 | 0.5000 | 0.0099 | 1.0000 |
| delay_120_deadline_30 | semantic_event | 0.2955 | 0.8571 | 0.0243 | 1.0000 |
| delay_120_deadline_30 | entity_context | 0.3291 | 0.9286 | 0.0166 | 1.0000 |
| delay_120_deadline_30 | context_dropout | 0.2617 | 0.9286 | 0.0419 | 1.0000 |
| delay_120_deadline_120 | generic_event | 0.2435 | 0.4286 | 0.0088 | 1.0000 |
| delay_120_deadline_120 | semantic_event | 0.3889 | 0.8571 | 0.0099 | 1.0000 |
| delay_120_deadline_120 | entity_context | 0.3944 | 0.8571 | 0.0110 | 1.0000 |
| delay_120_deadline_120 | context_dropout | 0.3836 | 0.8571 | 0.0110 | 1.0000 |

Per-run confusion counts, precision, recall, F1, ROC-AUC and average precision are in RESULTS.json. Correlated source events and three corruption seeds do not provide a population confidence interval.

## T1548

Status: **COMPLETE**. Support: `{"calibration": {"n": 1494, "negative": 1456, "positive": 38}, "development": {"n": 1894, "negative": 1846, "positive": 48}, "fit": {"n": 3932, "negative": 3844, "positive": 88}, "test": {"n": 920, "negative": 881, "positive": 39}}`.

| Condition | Model | F1 at 0.5 | Recall at frozen calibration threshold | Other-label flag rate | Observed target coverage |
|---|---|---:|---:|---:|---:|
| clean | generic_event | 0.5739 | 0.4615 | 0.0136 | 1.0000 |
| clean | semantic_event | 0.6286 | 0.6923 | 0.0136 | 1.0000 |
| clean | entity_context | 0.6471 | 0.7179 | 0.0125 | 1.0000 |
| clean | context_dropout | 0.6346 | 0.7179 | 0.0125 | 1.0000 |
| random_25 | generic_event | 0.2783 | 0.5385 | 0.0303 | 0.9953 |
| random_25 | semantic_event | 0.5176 | 0.6667 | 0.0216 | 0.9953 |
| random_25 | entity_context | 0.5504 | 0.6923 | 0.0189 | 0.9953 |
| random_25 | context_dropout | 0.6166 | 0.7094 | 0.0197 | 0.9953 |
| random_50 | generic_event | 0.1691 | 0.5641 | 0.0840 | 0.9547 |
| random_50 | semantic_event | 0.3470 | 0.5983 | 0.0212 | 0.9547 |
| random_50 | entity_context | 0.4118 | 0.5812 | 0.0166 | 0.9547 |
| random_50 | context_dropout | 0.5589 | 0.6581 | 0.0219 | 0.9547 |
| random_75 | generic_event | 0.1162 | 0.4103 | 0.1468 | 0.7819 |
| random_75 | semantic_event | 0.2138 | 0.3846 | 0.0132 | 0.7819 |
| random_75 | entity_context | 0.2607 | 0.3846 | 0.0132 | 0.7819 |
| random_75 | context_dropout | 0.4360 | 0.4615 | 0.0193 | 0.7819 |
| support_burst_60 | generic_event | 0.5739 | 0.4615 | 0.0136 | 1.0000 |
| support_burst_60 | semantic_event | 0.6286 | 0.6923 | 0.0136 | 1.0000 |
| support_burst_60 | entity_context | 0.6275 | 0.6923 | 0.0159 | 1.0000 |
| support_burst_60 | context_dropout | 0.6275 | 0.6923 | 0.0159 | 1.0000 |
| command_records_absent | generic_event | 0.1934 | 0.8205 | 0.0443 | 1.0000 |
| command_records_absent | semantic_event | 0.3139 | 0.8205 | 0.0386 | 1.0000 |
| command_records_absent | entity_context | 0.3271 | 0.8462 | 0.0386 | 1.0000 |
| command_records_absent | context_dropout | 0.6226 | 0.7179 | 0.0148 | 1.0000 |
| delay_30_deadline_0 | generic_event | 0.1934 | 0.8205 | 0.0443 | 1.0000 |
| delay_30_deadline_0 | semantic_event | 0.3139 | 0.8205 | 0.0386 | 1.0000 |
| delay_30_deadline_0 | entity_context | 0.3535 | 0.8462 | 0.0386 | 1.0000 |
| delay_30_deadline_0 | context_dropout | 0.6226 | 0.7436 | 0.0182 | 1.0000 |
| delay_30_deadline_30 | generic_event | 0.5739 | 0.4615 | 0.0136 | 1.0000 |
| delay_30_deadline_30 | semantic_event | 0.6286 | 0.6923 | 0.0136 | 1.0000 |
| delay_30_deadline_30 | entity_context | 0.6471 | 0.7179 | 0.0125 | 1.0000 |
| delay_30_deadline_30 | context_dropout | 0.6346 | 0.7179 | 0.0125 | 1.0000 |
| delay_120_deadline_0 | generic_event | 0.1934 | 0.8205 | 0.0443 | 1.0000 |
| delay_120_deadline_0 | semantic_event | 0.3139 | 0.8205 | 0.0386 | 1.0000 |
| delay_120_deadline_0 | entity_context | 0.3271 | 0.8462 | 0.0386 | 1.0000 |
| delay_120_deadline_0 | context_dropout | 0.6226 | 0.7179 | 0.0148 | 1.0000 |
| delay_120_deadline_30 | generic_event | 0.1934 | 0.8205 | 0.0443 | 1.0000 |
| delay_120_deadline_30 | semantic_event | 0.3139 | 0.8205 | 0.0386 | 1.0000 |
| delay_120_deadline_30 | entity_context | 0.3415 | 0.8462 | 0.0386 | 1.0000 |
| delay_120_deadline_30 | context_dropout | 0.6226 | 0.7179 | 0.0148 | 1.0000 |
| delay_120_deadline_120 | generic_event | 0.5739 | 0.4615 | 0.0136 | 1.0000 |
| delay_120_deadline_120 | semantic_event | 0.6286 | 0.6923 | 0.0136 | 1.0000 |
| delay_120_deadline_120 | entity_context | 0.6471 | 0.7179 | 0.0125 | 1.0000 |
| delay_120_deadline_120 | context_dropout | 0.6346 | 0.7179 | 0.0125 | 1.0000 |

Per-run confusion counts, precision, recall, F1, ROC-AUC and average precision are in RESULTS.json. Correlated source events and three corruption seeds do not provide a population confidence interval.

## T1105

Status: **COMPLETE**. Support: `{"calibration": {"n": 1494, "negative": 1407, "positive": 87}, "development": {"n": 1894, "negative": 1859, "positive": 35}, "fit": {"n": 3932, "negative": 3807, "positive": 125}, "test": {"n": 920, "negative": 903, "positive": 17}}`.

| Condition | Model | F1 at 0.5 | Recall at frozen calibration threshold | Other-label flag rate | Observed target coverage |
|---|---|---:|---:|---:|---:|
| clean | generic_event | 0.1677 | 0.4118 | 0.0100 | 1.0000 |
| clean | semantic_event | 0.7368 | 0.8235 | 0.0066 | 1.0000 |
| clean | entity_context | 0.5957 | 0.8235 | 0.0100 | 1.0000 |
| clean | context_dropout | 0.5833 | 0.8235 | 0.0122 | 1.0000 |
| random_25 | generic_event | 0.1129 | 0.4314 | 0.0310 | 0.9953 |
| random_25 | semantic_event | 0.3996 | 0.8627 | 0.0395 | 0.9953 |
| random_25 | entity_context | 0.5271 | 0.8039 | 0.0207 | 0.9953 |
| random_25 | context_dropout | 0.5471 | 0.8039 | 0.0137 | 0.9953 |
| random_50 | generic_event | 0.0937 | 0.3333 | 0.0546 | 0.9547 |
| random_50 | semantic_event | 0.2368 | 0.8627 | 0.0915 | 0.9547 |
| random_50 | entity_context | 0.3274 | 0.8039 | 0.0532 | 0.9547 |
| random_50 | context_dropout | 0.3993 | 0.7843 | 0.0240 | 0.9547 |
| random_75 | generic_event | 0.0795 | 0.2353 | 0.0642 | 0.7819 |
| random_75 | semantic_event | 0.1361 | 0.7255 | 0.1399 | 0.7819 |
| random_75 | entity_context | 0.1946 | 0.6863 | 0.0963 | 0.7819 |
| random_75 | context_dropout | 0.2179 | 0.6275 | 0.0410 | 0.7819 |
| support_burst_60 | generic_event | 0.1677 | 0.4118 | 0.0100 | 1.0000 |
| support_burst_60 | semantic_event | 0.7368 | 0.8235 | 0.0066 | 1.0000 |
| support_burst_60 | entity_context | 0.5769 | 0.8824 | 0.0177 | 1.0000 |
| support_burst_60 | context_dropout | 0.5000 | 0.8235 | 0.0188 | 1.0000 |
| command_records_absent | generic_event | 0.1290 | 0.3529 | 0.0011 | 1.0000 |
| command_records_absent | semantic_event | 0.2258 | 0.7059 | 0.0321 | 1.0000 |
| command_records_absent | entity_context | 0.3607 | 0.6471 | 0.0266 | 1.0000 |
| command_records_absent | context_dropout | 0.1591 | 0.7647 | 0.0975 | 1.0000 |
| delay_30_deadline_0 | generic_event | 0.1290 | 0.3529 | 0.0011 | 1.0000 |
| delay_30_deadline_0 | semantic_event | 0.2258 | 0.7059 | 0.0321 | 1.0000 |
| delay_30_deadline_0 | entity_context | 0.3729 | 0.6471 | 0.0255 | 1.0000 |
| delay_30_deadline_0 | context_dropout | 0.1761 | 0.7647 | 0.0853 | 1.0000 |
| delay_30_deadline_30 | generic_event | 0.1677 | 0.4118 | 0.0100 | 1.0000 |
| delay_30_deadline_30 | semantic_event | 0.7368 | 0.8235 | 0.0066 | 1.0000 |
| delay_30_deadline_30 | entity_context | 0.5957 | 0.8235 | 0.0100 | 1.0000 |
| delay_30_deadline_30 | context_dropout | 0.5833 | 0.8235 | 0.0122 | 1.0000 |
| delay_120_deadline_0 | generic_event | 0.1290 | 0.3529 | 0.0011 | 1.0000 |
| delay_120_deadline_0 | semantic_event | 0.2258 | 0.7059 | 0.0321 | 1.0000 |
| delay_120_deadline_0 | entity_context | 0.3607 | 0.6471 | 0.0266 | 1.0000 |
| delay_120_deadline_0 | context_dropout | 0.1591 | 0.7647 | 0.0975 | 1.0000 |
| delay_120_deadline_30 | generic_event | 0.1290 | 0.3529 | 0.0011 | 1.0000 |
| delay_120_deadline_30 | semantic_event | 0.2258 | 0.7059 | 0.0321 | 1.0000 |
| delay_120_deadline_30 | entity_context | 0.3607 | 0.6471 | 0.0266 | 1.0000 |
| delay_120_deadline_30 | context_dropout | 0.1609 | 0.7647 | 0.0963 | 1.0000 |
| delay_120_deadline_120 | generic_event | 0.1677 | 0.4118 | 0.0100 | 1.0000 |
| delay_120_deadline_120 | semantic_event | 0.7368 | 0.8235 | 0.0066 | 1.0000 |
| delay_120_deadline_120 | entity_context | 0.5957 | 0.8235 | 0.0100 | 1.0000 |
| delay_120_deadline_120 | context_dropout | 0.5833 | 0.8235 | 0.0122 | 1.0000 |

Per-run confusion counts, precision, recall, F1, ROC-AUC and average precision are in RESULTS.json. Correlated source events and three corruption seeds do not provide a population confidence interval.

## Limits

- AIT uses already-exposed development runs and author-rule labels. Grouped audit events are a new denominator; do not compare directly with the old line-level F1.
- CasinoLimit uses annotated process-technique onset targets and other annotated techniques as negatives. It does not measure benign false positives or unseen campaign generalization.
- Record-type deletion is not a physical sensor outage; the recent-history burst is a target-relative stress test.
- No-observation targets are retained and forced to no alarm. This offline target roster does not implement a deployed trigger for invisible events.
- Source timestamps stand in for native fragment availability. Later source events are excluded even when a decision waits.
- Waiting at least the injected deterministic delay restores the clean view by construction; that recovery is a buffering control, not a learned-method success.
- Fit/calibration/test are separated by run. Shared recipes, process-label inheritance and potential repeat players remain dependencies.
- A clean-calibration 1% other-label budget can fail under corruption and run shift. Actual observed rates are reported; no guarantee is claimed.
