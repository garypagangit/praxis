# camlds: structured-record-loss controls

Existing-method feasibility experiment. Labels identify a source technique versus other annotated techniques, not verified benign activity.

Context events: 691,563; eligible targets: 6,524.

Clean-calibration thresholds are frozen across test conditions. Random conditions average three perturbation seeds; other conditions have one deterministic view.

## T1105

Status: COMPLETE. Primary screening: **FAIL**.

Support: `{"calibration": {"n": 68, "negative": 60, "positive": 8}, "development": {"n": 187, "negative": 181, "positive": 6}, "fit": {"n": 2060, "negative": 1846, "positive": 214}, "test": {"n": 4209, "negative": 4109, "positive": 100}}`

| Condition | Arm | Calibrated F1 | Recall | Other-label flag rate | F1 at0.5 |
|---|---|---:|---:|---:|---:|
| clean | semantic_event | 0.0000 | 0.0000 | 0.0005 | 0.0495 |
| clean | entity_context | 0.0141 | 0.0100 | 0.0100 | 0.0534 |
| clean | random_dropout | 0.0000 | 0.0000 | 0.0037 | 0.0498 |
| clean | type_dropout | 0.0147 | 0.0100 | 0.0085 | 0.0520 |
| clean | mixed_dropout | 0.0000 | 0.0000 | 0.0039 | 0.0527 |
| clean | observed_router | 0.0252 | 0.0200 | 0.0139 | 0.0529 |
| random_25 | semantic_event | 0.0051 | 0.0033 | 0.0064 | 0.0454 |
| random_25 | entity_context | 0.0137 | 0.0133 | 0.0208 | 0.0468 |
| random_25 | random_dropout | 0.0100 | 0.0067 | 0.0075 | 0.0495 |
| random_25 | type_dropout | 0.0191 | 0.0167 | 0.0170 | 0.0509 |
| random_25 | mixed_dropout | 0.0101 | 0.0067 | 0.0073 | 0.0515 |
| random_25 | observed_router | 0.0354 | 0.1000 | 0.1104 | 0.0486 |
| random_50 | semantic_event | 0.0052 | 0.0033 | 0.0061 | 0.0452 |
| random_50 | entity_context | 0.0334 | 0.0467 | 0.0423 | 0.0469 |
| random_50 | random_dropout | 0.0050 | 0.0033 | 0.0073 | 0.0497 |
| random_50 | type_dropout | 0.0379 | 0.0433 | 0.0298 | 0.0502 |
| random_50 | mixed_dropout | 0.0144 | 0.0100 | 0.0085 | 0.0491 |
| random_50 | observed_router | 0.0380 | 0.1500 | 0.1638 | 0.0489 |
| random_75 | semantic_event | 0.0000 | 0.0000 | 0.0019 | 0.0493 |
| random_75 | entity_context | 0.0235 | 0.0333 | 0.0445 | 0.0446 |
| random_75 | random_dropout | 0.0048 | 0.0033 | 0.0105 | 0.0463 |
| random_75 | type_dropout | 0.0279 | 0.0533 | 0.0673 | 0.0411 |
| random_75 | mixed_dropout | 0.0086 | 0.0067 | 0.0143 | 0.0467 |
| random_75 | observed_router | 0.0371 | 0.1600 | 0.1817 | 0.0430 |
| support_burst_60 | semantic_event | 0.0000 | 0.0000 | 0.0005 | 0.0495 |
| support_burst_60 | entity_context | 0.0429 | 0.4600 | 0.4865 | 0.0490 |
| support_burst_60 | random_dropout | 0.0105 | 0.0100 | 0.0219 | 0.0486 |
| support_burst_60 | type_dropout | 0.0451 | 0.4800 | 0.4824 | 0.0479 |
| support_burst_60 | mixed_dropout | 0.0078 | 0.0100 | 0.0377 | 0.0488 |
| support_burst_60 | observed_router | 0.0450 | 0.4900 | 0.4938 | 0.0495 |
| command_records_absent | semantic_event | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| command_records_absent | entity_context | 0.0000 | 0.0000 | 0.0000 | 0.0384 |
| command_records_absent | random_dropout | 0.0111 | 0.0100 | 0.0192 | 0.0503 |
| command_records_absent | type_dropout | 0.0000 | 0.0000 | 0.0027 | 0.0530 |
| command_records_absent | mixed_dropout | 0.0142 | 0.0100 | 0.0097 | 0.0532 |
| command_records_absent | observed_router | 0.0074 | 0.0100 | 0.0409 | 0.0521 |
| delay_30_deadline_0 | semantic_event | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| delay_30_deadline_0 | entity_context | 0.0000 | 0.0000 | 0.0002 | 0.0319 |
| delay_30_deadline_0 | random_dropout | 0.0082 | 0.0100 | 0.0350 | 0.0573 |
| delay_30_deadline_0 | type_dropout | 0.0143 | 0.0100 | 0.0095 | 0.0522 |
| delay_30_deadline_0 | mixed_dropout | 0.0096 | 0.0100 | 0.0260 | 0.0518 |
| delay_30_deadline_0 | observed_router | 0.0143 | 0.0300 | 0.0774 | 0.0498 |
| delay_30_deadline_30 | semantic_event | 0.0000 | 0.0000 | 0.0005 | 0.0495 |
| delay_30_deadline_30 | entity_context | 0.0141 | 0.0100 | 0.0100 | 0.0534 |
| delay_30_deadline_30 | random_dropout | 0.0000 | 0.0000 | 0.0037 | 0.0498 |
| delay_30_deadline_30 | type_dropout | 0.0147 | 0.0100 | 0.0085 | 0.0520 |
| delay_30_deadline_30 | mixed_dropout | 0.0000 | 0.0000 | 0.0039 | 0.0527 |
| delay_30_deadline_30 | observed_router | 0.0252 | 0.0200 | 0.0139 | 0.0529 |
| delay_120_deadline_0 | semantic_event | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| delay_120_deadline_0 | entity_context | 0.0000 | 0.0000 | 0.0000 | 0.0384 |
| delay_120_deadline_0 | random_dropout | 0.0111 | 0.0100 | 0.0192 | 0.0503 |
| delay_120_deadline_0 | type_dropout | 0.0000 | 0.0000 | 0.0027 | 0.0530 |
| delay_120_deadline_0 | mixed_dropout | 0.0142 | 0.0100 | 0.0097 | 0.0532 |
| delay_120_deadline_0 | observed_router | 0.0074 | 0.0100 | 0.0409 | 0.0521 |
| delay_120_deadline_30 | semantic_event | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| delay_120_deadline_30 | entity_context | 0.0000 | 0.0000 | 0.0000 | 0.0331 |
| delay_120_deadline_30 | random_dropout | 0.0106 | 0.0100 | 0.0214 | 0.0510 |
| delay_120_deadline_30 | type_dropout | 0.0000 | 0.0000 | 0.0034 | 0.0531 |
| delay_120_deadline_30 | mixed_dropout | 0.0117 | 0.0100 | 0.0170 | 0.0529 |
| delay_120_deadline_30 | observed_router | 0.0137 | 0.0200 | 0.0462 | 0.0515 |
| delay_120_deadline_120 | semantic_event | 0.0000 | 0.0000 | 0.0005 | 0.0495 |
| delay_120_deadline_120 | entity_context | 0.0141 | 0.0100 | 0.0100 | 0.0534 |
| delay_120_deadline_120 | random_dropout | 0.0000 | 0.0000 | 0.0037 | 0.0498 |
| delay_120_deadline_120 | type_dropout | 0.0147 | 0.0100 | 0.0085 | 0.0520 |
| delay_120_deadline_120 | mixed_dropout | 0.0000 | 0.0000 | 0.0039 | 0.0527 |
| delay_120_deadline_120 | observed_router | 0.0252 | 0.0200 | 0.0139 | 0.0529 |
| execve_absent | semantic_event | 0.0000 | 0.0000 | 0.0005 | 0.0478 |
| execve_absent | entity_context | 0.0000 | 0.0000 | 0.0034 | 0.0514 |
| execve_absent | random_dropout | 0.0078 | 0.0100 | 0.0377 | 0.0531 |
| execve_absent | type_dropout | 0.0147 | 0.0100 | 0.0085 | 0.0524 |
| execve_absent | mixed_dropout | 0.0096 | 0.0100 | 0.0263 | 0.0525 |
| execve_absent | observed_router | 0.0212 | 0.0300 | 0.0438 | 0.0504 |
| proctitle_absent | semantic_event | 0.0000 | 0.0000 | 0.0005 | 0.0075 |
| proctitle_absent | entity_context | 0.0000 | 0.0000 | 0.0010 | 0.0406 |
| proctitle_absent | random_dropout | 0.0000 | 0.0000 | 0.0010 | 0.0471 |
| proctitle_absent | type_dropout | 0.0000 | 0.0000 | 0.0029 | 0.0530 |
| proctitle_absent | mixed_dropout | 0.0000 | 0.0000 | 0.0027 | 0.0515 |
| proctitle_absent | observed_router | 0.0000 | 0.0000 | 0.0041 | 0.0518 |
| syscall_absent | semantic_event | 0.0000 | 0.0000 | 0.0005 | 0.0404 |
| syscall_absent | entity_context | 0.0000 | 0.0000 | 0.0005 | 0.0445 |
| syscall_absent | random_dropout | 0.0000 | 0.0000 | 0.0005 | 0.0502 |
| syscall_absent | type_dropout | 0.0000 | 0.0000 | 0.0000 | 0.0497 |
| syscall_absent | mixed_dropout | 0.0000 | 0.0000 | 0.0005 | 0.0510 |
| syscall_absent | observed_router | 0.0447 | 0.4300 | 0.4339 | 0.0483 |
| path_absent | semantic_event | 0.0370 | 0.0500 | 0.0402 | 0.0494 |
| path_absent | entity_context | 0.0577 | 0.1600 | 0.1068 | 0.0506 |
| path_absent | random_dropout | 0.0000 | 0.0000 | 0.0010 | 0.0485 |
| path_absent | type_dropout | 0.0341 | 0.0500 | 0.0458 | 0.0508 |
| path_absent | mixed_dropout | 0.0000 | 0.0000 | 0.0010 | 0.0499 |
| path_absent | observed_router | 0.0244 | 0.0200 | 0.0151 | 0.0496 |

Primary gates: `{"clean_f1_delta_min": {"delta": 0.0, "limit": -0.02, "passed": true}, "command_records_absent_f1_delta_min": {"delta": 0.0030732860520094555, "limit": 0.05, "passed": false}, "command_records_absent_flag_rate_delta_max": {"delta": -0.00949136042832806, "limit": 0.005, "passed": true}, "command_records_absent_recall_delta_min": {"delta": 0.0, "limit": -0.02, "passed": true}, "random_50_mean_f1_delta_min": {"delta": 0.009383101181617986, "limit": -0.02, "passed": true}}`

## Interpretation limits

- AIT and Casino are already exposed development sources. No significance or population guarantee follows from passing descriptive gates.
- CAM-LDS, if qualified, uses a family-held-out interval-state proxy. It is not directly comparable to Casino annotation-onset targets or AIT rule labels.
- Router specialists use more parameters than one logistic regression; fit support counts unique underlying observed targets.
- Record-type removal is a synthetic log stress test, not a measured sensor outage. Waiting out injected delay restores clean evidence by construction.
- Invisible targets remain in denominators and get no alarm. The offline target roster is not a deployable detector trigger.
- Source labels, dependent events, small positive counts, recipe overlap and dataset shift limit generalization.
- No novel algorithm, complete APT detection, or improved real-world benign false-alarm rate is established.
