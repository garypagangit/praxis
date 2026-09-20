# ait: structured-record-loss controls

Existing-method feasibility experiment. Labels identify a source technique versus other annotated techniques, not verified benign activity.

Context events: 22,890; eligible targets: 22,890.

Clean-calibration thresholds are frozen across test conditions. Random conditions average three perturbation seeds; other conditions have one deterministic view.

## escalate

Status: COMPLETE. Primary screening: **FAIL**.

Support: `{"calibration": {"n": 2833, "negative": 2819, "positive": 14}, "development": {"n": 3395, "negative": 3376, "positive": 19}, "fit": {"n": 10369, "negative": 10303, "positive": 66}, "test": {"n": 6293, "negative": 6249, "positive": 44}}`

| Condition | Arm | Calibrated F1 | Recall | Other-label flag rate | F1 at0.5 |
|---|---|---:|---:|---:|---:|
| clean | semantic_event | 0.5694 | 0.9318 | 0.0094 | 0.6833 |
| clean | entity_context | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| clean | random_dropout | 0.6721 | 0.9318 | 0.0059 | 0.7130 |
| clean | type_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| clean | mixed_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7130 |
| clean | observed_router | 0.6833 | 0.9318 | 0.0056 | 0.7193 |
| random_25 | semantic_event | 0.5156 | 0.6894 | 0.0069 | 0.6109 |
| random_25 | entity_context | 0.5888 | 0.6894 | 0.0046 | 0.6231 |
| random_25 | random_dropout | 0.5833 | 0.6894 | 0.0047 | 0.6043 |
| random_25 | type_dropout | 0.5888 | 0.6894 | 0.0046 | 0.6231 |
| random_25 | mixed_dropout | 0.5853 | 0.6894 | 0.0047 | 0.6105 |
| random_25 | observed_router | 0.5853 | 0.6894 | 0.0047 | 0.6105 |
| random_50 | semantic_event | 0.4268 | 0.4545 | 0.0048 | 0.4882 |
| random_50 | entity_context | 0.4561 | 0.4621 | 0.0039 | 0.4818 |
| random_50 | random_dropout | 0.4517 | 0.4621 | 0.0041 | 0.4680 |
| random_50 | type_dropout | 0.4561 | 0.4621 | 0.0039 | 0.4818 |
| random_50 | mixed_dropout | 0.4513 | 0.4621 | 0.0041 | 0.4756 |
| random_50 | observed_router | 0.4476 | 0.4545 | 0.0041 | 0.4699 |
| random_75 | semantic_event | 0.3290 | 0.2652 | 0.0024 | 0.3549 |
| random_75 | entity_context | 0.3382 | 0.2803 | 0.0026 | 0.3432 |
| random_75 | random_dropout | 0.3384 | 0.2803 | 0.0026 | 0.3364 |
| random_75 | type_dropout | 0.3382 | 0.2803 | 0.0026 | 0.3432 |
| random_75 | mixed_dropout | 0.3353 | 0.2803 | 0.0027 | 0.3502 |
| random_75 | observed_router | 0.3285 | 0.2727 | 0.0027 | 0.3414 |
| support_burst_60 | semantic_event | 0.5694 | 0.9318 | 0.0094 | 0.6833 |
| support_burst_60 | entity_context | 0.5734 | 0.9318 | 0.0093 | 0.6165 |
| support_burst_60 | random_dropout | 0.5734 | 0.9318 | 0.0093 | 0.5985 |
| support_burst_60 | type_dropout | 0.5734 | 0.9318 | 0.0093 | 0.6165 |
| support_burst_60 | mixed_dropout | 0.5734 | 0.9318 | 0.0093 | 0.5985 |
| support_burst_60 | observed_router | 0.5734 | 0.9318 | 0.0093 | 0.6029 |
| command_records_absent | semantic_event | 0.5694 | 0.9318 | 0.0094 | 0.6833 |
| command_records_absent | entity_context | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| command_records_absent | random_dropout | 0.6721 | 0.9318 | 0.0059 | 0.7130 |
| command_records_absent | type_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| command_records_absent | mixed_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7130 |
| command_records_absent | observed_router | 0.6833 | 0.9318 | 0.0056 | 0.7193 |
| delay_30_deadline_0 | semantic_event | 0.5694 | 0.9318 | 0.0094 | 0.6833 |
| delay_30_deadline_0 | entity_context | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| delay_30_deadline_0 | random_dropout | 0.6721 | 0.9318 | 0.0059 | 0.7130 |
| delay_30_deadline_0 | type_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| delay_30_deadline_0 | mixed_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7130 |
| delay_30_deadline_0 | observed_router | 0.6833 | 0.9318 | 0.0056 | 0.7193 |
| delay_30_deadline_30 | semantic_event | 0.5694 | 0.9318 | 0.0094 | 0.6833 |
| delay_30_deadline_30 | entity_context | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| delay_30_deadline_30 | random_dropout | 0.6721 | 0.9318 | 0.0059 | 0.7130 |
| delay_30_deadline_30 | type_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| delay_30_deadline_30 | mixed_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7130 |
| delay_30_deadline_30 | observed_router | 0.6833 | 0.9318 | 0.0056 | 0.7193 |
| delay_120_deadline_0 | semantic_event | 0.5694 | 0.9318 | 0.0094 | 0.6833 |
| delay_120_deadline_0 | entity_context | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| delay_120_deadline_0 | random_dropout | 0.6721 | 0.9318 | 0.0059 | 0.7130 |
| delay_120_deadline_0 | type_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| delay_120_deadline_0 | mixed_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7130 |
| delay_120_deadline_0 | observed_router | 0.6833 | 0.9318 | 0.0056 | 0.7193 |
| delay_120_deadline_30 | semantic_event | 0.5694 | 0.9318 | 0.0094 | 0.6833 |
| delay_120_deadline_30 | entity_context | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| delay_120_deadline_30 | random_dropout | 0.6721 | 0.9318 | 0.0059 | 0.7130 |
| delay_120_deadline_30 | type_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| delay_120_deadline_30 | mixed_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7130 |
| delay_120_deadline_30 | observed_router | 0.6833 | 0.9318 | 0.0056 | 0.7193 |
| delay_120_deadline_120 | semantic_event | 0.5694 | 0.9318 | 0.0094 | 0.6833 |
| delay_120_deadline_120 | entity_context | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| delay_120_deadline_120 | random_dropout | 0.6721 | 0.9318 | 0.0059 | 0.7130 |
| delay_120_deadline_120 | type_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| delay_120_deadline_120 | mixed_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7130 |
| delay_120_deadline_120 | observed_router | 0.6833 | 0.9318 | 0.0056 | 0.7193 |
| execve_absent | semantic_event | 0.5694 | 0.9318 | 0.0094 | 0.6833 |
| execve_absent | entity_context | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| execve_absent | random_dropout | 0.6721 | 0.9318 | 0.0059 | 0.7130 |
| execve_absent | type_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| execve_absent | mixed_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7130 |
| execve_absent | observed_router | 0.6833 | 0.9318 | 0.0056 | 0.7193 |
| proctitle_absent | semantic_event | 0.5694 | 0.9318 | 0.0094 | 0.6833 |
| proctitle_absent | entity_context | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| proctitle_absent | random_dropout | 0.6721 | 0.9318 | 0.0059 | 0.7130 |
| proctitle_absent | type_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| proctitle_absent | mixed_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7130 |
| proctitle_absent | observed_router | 0.6833 | 0.9318 | 0.0056 | 0.7193 |
| syscall_absent | semantic_event | 0.5694 | 0.9318 | 0.0094 | 0.6833 |
| syscall_absent | entity_context | 0.6942 | 0.9545 | 0.0056 | 0.7321 |
| syscall_absent | random_dropout | 0.6829 | 0.9545 | 0.0059 | 0.7130 |
| syscall_absent | type_dropout | 0.6942 | 0.9545 | 0.0056 | 0.7321 |
| syscall_absent | mixed_dropout | 0.6885 | 0.9545 | 0.0058 | 0.7130 |
| syscall_absent | observed_router | 0.6885 | 0.9545 | 0.0058 | 0.7193 |
| path_absent | semantic_event | 0.5694 | 0.9318 | 0.0094 | 0.6833 |
| path_absent | entity_context | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| path_absent | random_dropout | 0.6721 | 0.9318 | 0.0059 | 0.7130 |
| path_absent | type_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7321 |
| path_absent | mixed_dropout | 0.6833 | 0.9318 | 0.0056 | 0.7130 |
| path_absent | observed_router | 0.6833 | 0.9318 | 0.0056 | 0.7193 |

Primary gates: `{"clean_f1_delta_min": {"delta": 0.011202185792349773, "limit": -0.02, "passed": true}, "command_records_absent_f1_delta_min": {"delta": 0.011202185792349773, "limit": 0.05, "passed": false}, "command_records_absent_flag_rate_delta_max": {"delta": -0.0003200512081933107, "limit": 0.005, "passed": true}, "command_records_absent_recall_delta_min": {"delta": 0.0, "limit": -0.02, "passed": true}, "random_50_mean_f1_delta_min": {"delta": -0.0003772166512289732, "limit": -0.02, "passed": true}}`

## Interpretation limits

- AIT and Casino are already exposed development sources. No significance or population guarantee follows from passing descriptive gates.
- CAM-LDS, if qualified, uses a family-held-out interval-state proxy. It is not directly comparable to Casino annotation-onset targets or AIT rule labels.
- Router specialists use more parameters than one logistic regression; fit support counts unique underlying observed targets.
- Record-type removal is a synthetic log stress test, not a measured sensor outage. Waiting out injected delay restores clean evidence by construction.
- Invisible targets remain in denominators and get no alarm. The offline target roster is not a deployable detector trigger.
- Source labels, dependent events, small positive counts, recipe overlap and dataset shift limit generalization.
- No novel algorithm, complete APT detection, or improved real-world benign false-alarm rate is established.
