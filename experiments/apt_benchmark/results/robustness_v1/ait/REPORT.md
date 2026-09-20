# ait missing/delayed-log development experiments

Fixed protocol; no new novelty claim. Event-time plus synthetic delays is not measured online latency.

Negative means absence of this source technique label in the eligible target roster; it does not mean independently verified benign activity.

Random conditions average three fixed perturbation seeds; other conditions are deterministic. Models and calibration thresholds stay fixed.

## Qualification

- Context events: 22,890; eligible prediction targets: 22,890.
- Input event SHA256: `f3f5b10fd34ea368e3edb44ea530a656bfdc5d9a9e53b644588442e949be4660`.
- Protocol SHA256: `0d8b6d0fe354172fae4dae5433fb827f81380cbeb990f4bc966664ad724a1f14`.
- Runtime: 49.23 seconds.

## escalate

Status: **COMPLETE**. Support: `{"calibration": {"n": 2833, "negative": 2819, "positive": 14}, "development": {"n": 3395, "negative": 3376, "positive": 19}, "fit": {"n": 10369, "negative": 10303, "positive": 66}, "test": {"n": 6293, "negative": 6249, "positive": 44}}`.

| Condition | Model | F1 at 0.5 | Recall at frozen calibration threshold | Other-label flag rate | Observed target coverage |
|---|---|---:|---:|---:|---:|
| clean | generic_event | 0.6324 | 1.0000 | 0.0155 | 1.0000 |
| clean | semantic_event | 0.6833 | 0.9318 | 0.0094 | 1.0000 |
| clean | entity_context | 0.7321 | 0.9318 | 0.0056 | 1.0000 |
| clean | context_dropout | 0.7130 | 0.9318 | 0.0059 | 1.0000 |
| random_25 | generic_event | 0.5813 | 0.7500 | 0.0110 | 0.7489 |
| random_25 | semantic_event | 0.6109 | 0.6894 | 0.0069 | 0.7489 |
| random_25 | entity_context | 0.6231 | 0.6894 | 0.0046 | 0.7489 |
| random_25 | context_dropout | 0.6043 | 0.6894 | 0.0047 | 0.7489 |
| random_50 | generic_event | 0.4740 | 0.5000 | 0.0078 | 0.4992 |
| random_50 | semantic_event | 0.4882 | 0.4545 | 0.0048 | 0.4992 |
| random_50 | entity_context | 0.4818 | 0.4621 | 0.0039 | 0.4992 |
| random_50 | context_dropout | 0.4680 | 0.4621 | 0.0041 | 0.4992 |
| random_75 | generic_event | 0.3719 | 0.2955 | 0.0037 | 0.2508 |
| random_75 | semantic_event | 0.3549 | 0.2652 | 0.0024 | 0.2508 |
| random_75 | entity_context | 0.3432 | 0.2803 | 0.0026 | 0.2508 |
| random_75 | context_dropout | 0.3364 | 0.2803 | 0.0026 | 0.2508 |
| support_burst_60 | generic_event | 0.6324 | 1.0000 | 0.0155 | 1.0000 |
| support_burst_60 | semantic_event | 0.6833 | 0.9318 | 0.0094 | 1.0000 |
| support_burst_60 | entity_context | 0.6165 | 0.9318 | 0.0093 | 1.0000 |
| support_burst_60 | context_dropout | 0.5985 | 0.9318 | 0.0093 | 1.0000 |
| command_records_absent | generic_event | 0.6324 | 1.0000 | 0.0155 | 1.0000 |
| command_records_absent | semantic_event | 0.6833 | 0.9318 | 0.0094 | 1.0000 |
| command_records_absent | entity_context | 0.7321 | 0.9318 | 0.0056 | 1.0000 |
| command_records_absent | context_dropout | 0.7130 | 0.9318 | 0.0059 | 1.0000 |
| delay_30_deadline_0 | generic_event | 0.6324 | 1.0000 | 0.0155 | 1.0000 |
| delay_30_deadline_0 | semantic_event | 0.6833 | 0.9318 | 0.0094 | 1.0000 |
| delay_30_deadline_0 | entity_context | 0.7321 | 0.9318 | 0.0056 | 1.0000 |
| delay_30_deadline_0 | context_dropout | 0.7130 | 0.9318 | 0.0059 | 1.0000 |
| delay_30_deadline_30 | generic_event | 0.6324 | 1.0000 | 0.0155 | 1.0000 |
| delay_30_deadline_30 | semantic_event | 0.6833 | 0.9318 | 0.0094 | 1.0000 |
| delay_30_deadline_30 | entity_context | 0.7321 | 0.9318 | 0.0056 | 1.0000 |
| delay_30_deadline_30 | context_dropout | 0.7130 | 0.9318 | 0.0059 | 1.0000 |
| delay_120_deadline_0 | generic_event | 0.6324 | 1.0000 | 0.0155 | 1.0000 |
| delay_120_deadline_0 | semantic_event | 0.6833 | 0.9318 | 0.0094 | 1.0000 |
| delay_120_deadline_0 | entity_context | 0.7321 | 0.9318 | 0.0056 | 1.0000 |
| delay_120_deadline_0 | context_dropout | 0.7130 | 0.9318 | 0.0059 | 1.0000 |
| delay_120_deadline_30 | generic_event | 0.6324 | 1.0000 | 0.0155 | 1.0000 |
| delay_120_deadline_30 | semantic_event | 0.6833 | 0.9318 | 0.0094 | 1.0000 |
| delay_120_deadline_30 | entity_context | 0.7321 | 0.9318 | 0.0056 | 1.0000 |
| delay_120_deadline_30 | context_dropout | 0.7130 | 0.9318 | 0.0059 | 1.0000 |
| delay_120_deadline_120 | generic_event | 0.6324 | 1.0000 | 0.0155 | 1.0000 |
| delay_120_deadline_120 | semantic_event | 0.6833 | 0.9318 | 0.0094 | 1.0000 |
| delay_120_deadline_120 | entity_context | 0.7321 | 0.9318 | 0.0056 | 1.0000 |
| delay_120_deadline_120 | context_dropout | 0.7130 | 0.9318 | 0.0059 | 1.0000 |

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
