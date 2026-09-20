# casino: structured-record-loss controls

Existing-method feasibility experiment. Labels identify a source technique versus other annotated techniques, not verified benign activity.

Context events: 3,758,674; eligible targets: 8,240.

Clean-calibration thresholds are frozen across test conditions. Random conditions average three perturbation seeds; other conditions have one deterministic view.

## T1068

Status: COMPLETE. Primary screening: **FAIL**.

Support: `{"calibration": {"n": 1494, "negative": 1471, "positive": 23}, "development": {"n": 1894, "negative": 1850, "positive": 44}, "fit": {"n": 3932, "negative": 3853, "positive": 79}, "test": {"n": 920, "negative": 906, "positive": 14}}`

| Condition | Arm | Calibrated F1 | Recall | Other-label flag rate | F1 at0.5 |
|---|---|---:|---:|---:|---:|
| clean | semantic_event | 0.6857 | 0.8571 | 0.0099 | 0.3889 |
| clean | entity_context | 0.6667 | 0.8571 | 0.0110 | 0.3944 |
| clean | random_dropout | 0.6667 | 0.8571 | 0.0110 | 0.3836 |
| clean | type_dropout | 0.6316 | 0.8571 | 0.0132 | 0.3636 |
| clean | mixed_dropout | 0.6316 | 0.8571 | 0.0132 | 0.3733 |
| clean | observed_router | 0.6154 | 0.8571 | 0.0143 | 0.3415 |
| random_25 | semantic_event | 0.3591 | 0.8095 | 0.0419 | 0.2117 |
| random_25 | entity_context | 0.4846 | 0.8571 | 0.0261 | 0.2409 |
| random_25 | random_dropout | 0.6022 | 0.7857 | 0.0129 | 0.3396 |
| random_25 | type_dropout | 0.4395 | 0.8095 | 0.0291 | 0.2118 |
| random_25 | mixed_dropout | 0.6077 | 0.7857 | 0.0125 | 0.3033 |
| random_25 | observed_router | 0.5588 | 0.8095 | 0.0169 | 0.2777 |
| random_50 | semantic_event | 0.2393 | 0.7381 | 0.0692 | 0.1544 |
| random_50 | entity_context | 0.3043 | 0.7857 | 0.0522 | 0.1809 |
| random_50 | random_dropout | 0.4955 | 0.7143 | 0.0180 | 0.2927 |
| random_50 | type_dropout | 0.2921 | 0.8095 | 0.0581 | 0.1556 |
| random_50 | mixed_dropout | 0.5261 | 0.7381 | 0.0169 | 0.2571 |
| random_50 | observed_router | 0.4578 | 0.7619 | 0.0247 | 0.2346 |
| random_75 | semantic_event | 0.1663 | 0.5952 | 0.0857 | 0.1067 |
| random_75 | entity_context | 0.1624 | 0.5238 | 0.0754 | 0.1101 |
| random_75 | random_dropout | 0.3424 | 0.5476 | 0.0258 | 0.2223 |
| random_75 | type_dropout | 0.1689 | 0.5714 | 0.0798 | 0.1137 |
| random_75 | mixed_dropout | 0.3209 | 0.5000 | 0.0250 | 0.2134 |
| random_75 | observed_router | 0.2068 | 0.5000 | 0.0508 | 0.2042 |
| support_burst_60 | semantic_event | 0.6857 | 0.8571 | 0.0099 | 0.3889 |
| support_burst_60 | entity_context | 0.7273 | 0.8571 | 0.0077 | 0.3881 |
| support_burst_60 | random_dropout | 0.7273 | 0.8571 | 0.0077 | 0.4062 |
| support_burst_60 | type_dropout | 0.6875 | 0.7857 | 0.0077 | 0.3714 |
| support_burst_60 | mixed_dropout | 0.7273 | 0.8571 | 0.0077 | 0.3939 |
| support_burst_60 | observed_router | 0.7742 | 0.8571 | 0.0055 | 0.4127 |
| command_records_absent | semantic_event | 0.5000 | 0.8571 | 0.0243 | 0.2955 |
| command_records_absent | entity_context | 0.6190 | 0.9286 | 0.0166 | 0.3291 |
| command_records_absent | random_dropout | 0.4000 | 0.9286 | 0.0419 | 0.2593 |
| command_records_absent | type_dropout | 0.4127 | 0.9286 | 0.0397 | 0.2364 |
| command_records_absent | mixed_dropout | 0.4194 | 0.9286 | 0.0386 | 0.2500 |
| command_records_absent | observed_router | 0.3562 | 0.9286 | 0.0508 | 0.2167 |
| delay_30_deadline_0 | semantic_event | 0.5000 | 0.8571 | 0.0243 | 0.2955 |
| delay_30_deadline_0 | entity_context | 0.6190 | 0.9286 | 0.0166 | 0.3291 |
| delay_30_deadline_0 | random_dropout | 0.4194 | 0.9286 | 0.0386 | 0.2593 |
| delay_30_deadline_0 | type_dropout | 0.4194 | 0.9286 | 0.0386 | 0.2545 |
| delay_30_deadline_0 | mixed_dropout | 0.4407 | 0.9286 | 0.0353 | 0.2524 |
| delay_30_deadline_0 | observed_router | 0.3562 | 0.9286 | 0.0508 | 0.2167 |
| delay_30_deadline_30 | semantic_event | 0.6857 | 0.8571 | 0.0099 | 0.3889 |
| delay_30_deadline_30 | entity_context | 0.6667 | 0.8571 | 0.0110 | 0.3944 |
| delay_30_deadline_30 | random_dropout | 0.6667 | 0.8571 | 0.0110 | 0.3836 |
| delay_30_deadline_30 | type_dropout | 0.6316 | 0.8571 | 0.0132 | 0.3636 |
| delay_30_deadline_30 | mixed_dropout | 0.6316 | 0.8571 | 0.0132 | 0.3733 |
| delay_30_deadline_30 | observed_router | 0.6154 | 0.8571 | 0.0143 | 0.3415 |
| delay_120_deadline_0 | semantic_event | 0.5000 | 0.8571 | 0.0243 | 0.2955 |
| delay_120_deadline_0 | entity_context | 0.6190 | 0.9286 | 0.0166 | 0.3291 |
| delay_120_deadline_0 | random_dropout | 0.4000 | 0.9286 | 0.0419 | 0.2593 |
| delay_120_deadline_0 | type_dropout | 0.4127 | 0.9286 | 0.0397 | 0.2364 |
| delay_120_deadline_0 | mixed_dropout | 0.4194 | 0.9286 | 0.0386 | 0.2500 |
| delay_120_deadline_0 | observed_router | 0.3562 | 0.9286 | 0.0508 | 0.2167 |
| delay_120_deadline_30 | semantic_event | 0.5000 | 0.8571 | 0.0243 | 0.2955 |
| delay_120_deadline_30 | entity_context | 0.6190 | 0.9286 | 0.0166 | 0.3291 |
| delay_120_deadline_30 | random_dropout | 0.4000 | 0.9286 | 0.0419 | 0.2617 |
| delay_120_deadline_30 | type_dropout | 0.4194 | 0.9286 | 0.0386 | 0.2364 |
| delay_120_deadline_30 | mixed_dropout | 0.4262 | 0.9286 | 0.0375 | 0.2524 |
| delay_120_deadline_30 | observed_router | 0.3562 | 0.9286 | 0.0508 | 0.2167 |
| delay_120_deadline_120 | semantic_event | 0.6857 | 0.8571 | 0.0099 | 0.3889 |
| delay_120_deadline_120 | entity_context | 0.6667 | 0.8571 | 0.0110 | 0.3944 |
| delay_120_deadline_120 | random_dropout | 0.6667 | 0.8571 | 0.0110 | 0.3836 |
| delay_120_deadline_120 | type_dropout | 0.6316 | 0.8571 | 0.0132 | 0.3636 |
| delay_120_deadline_120 | mixed_dropout | 0.6316 | 0.8571 | 0.0132 | 0.3733 |
| delay_120_deadline_120 | observed_router | 0.6154 | 0.8571 | 0.0143 | 0.3415 |
| execve_absent | semantic_event | 0.8000 | 0.8571 | 0.0044 | 0.3824 |
| execve_absent | entity_context | 0.7059 | 0.8571 | 0.0088 | 0.4000 |
| execve_absent | random_dropout | 0.5714 | 0.8571 | 0.0177 | 0.3636 |
| execve_absent | type_dropout | 0.5000 | 0.9286 | 0.0276 | 0.3146 |
| execve_absent | mixed_dropout | 0.5106 | 0.8571 | 0.0232 | 0.3544 |
| execve_absent | observed_router | 0.5455 | 0.8571 | 0.0199 | 0.3133 |
| proctitle_absent | semantic_event | 0.4800 | 0.8571 | 0.0265 | 0.2800 |
| proctitle_absent | entity_context | 0.5306 | 0.9286 | 0.0243 | 0.3182 |
| proctitle_absent | random_dropout | 0.4906 | 0.9286 | 0.0287 | 0.2800 |
| proctitle_absent | type_dropout | 0.4643 | 0.9286 | 0.0320 | 0.2718 |
| proctitle_absent | mixed_dropout | 0.4800 | 0.8571 | 0.0265 | 0.2857 |
| proctitle_absent | observed_router | 0.3750 | 0.8571 | 0.0419 | 0.2137 |
| syscall_absent | semantic_event | 0.4407 | 0.9286 | 0.0353 | 0.0809 |
| syscall_absent | entity_context | 0.5200 | 0.9286 | 0.0254 | 0.1308 |
| syscall_absent | random_dropout | 0.8000 | 0.8571 | 0.0044 | 0.4333 |
| syscall_absent | type_dropout | 0.6667 | 0.9286 | 0.0132 | 0.1145 |
| syscall_absent | mixed_dropout | 0.8000 | 0.8571 | 0.0044 | 0.3611 |
| syscall_absent | observed_router | 0.8000 | 0.8571 | 0.0044 | 0.3768 |
| path_absent | semantic_event | 0.5306 | 0.9286 | 0.0243 | 0.3146 |
| path_absent | entity_context | 0.5652 | 0.9286 | 0.0210 | 0.2800 |
| path_absent | random_dropout | 0.6857 | 0.8571 | 0.0099 | 0.3457 |
| path_absent | type_dropout | 0.6667 | 0.8571 | 0.0110 | 0.3077 |
| path_absent | mixed_dropout | 0.6316 | 0.8571 | 0.0132 | 0.3333 |
| path_absent | observed_router | 0.6316 | 0.8571 | 0.0132 | 0.2745 |

Primary gates: `{"clean_f1_delta_min": {"delta": -0.03508771929824561, "limit": -0.02, "passed": false}, "command_records_absent_f1_delta_min": {"delta": 0.019354838709677413, "limit": 0.05, "passed": false}, "command_records_absent_flag_rate_delta_max": {"delta": -0.0033112582781456915, "limit": 0.005, "passed": true}, "command_records_absent_recall_delta_min": {"delta": 0.0, "limit": -0.02, "passed": true}, "random_50_mean_f1_delta_min": {"delta": 0.03059163059163067, "limit": -0.02, "passed": true}}`

## T1548

Status: COMPLETE. Primary screening: **FAIL**.

Support: `{"calibration": {"n": 1494, "negative": 1456, "positive": 38}, "development": {"n": 1894, "negative": 1846, "positive": 48}, "fit": {"n": 3932, "negative": 3844, "positive": 88}, "test": {"n": 920, "negative": 881, "positive": 39}}`

| Condition | Arm | Calibrated F1 | Recall | Other-label flag rate | F1 at0.5 |
|---|---|---:|---:|---:|---:|
| clean | semantic_event | 0.6923 | 0.6923 | 0.0136 | 0.6286 |
| clean | entity_context | 0.7179 | 0.7179 | 0.0125 | 0.6471 |
| clean | random_dropout | 0.7179 | 0.7179 | 0.0125 | 0.6346 |
| clean | type_dropout | 0.7089 | 0.7179 | 0.0136 | 0.6286 |
| clean | mixed_dropout | 0.7179 | 0.7179 | 0.0125 | 0.6286 |
| clean | observed_router | 0.7013 | 0.6923 | 0.0125 | 0.6337 |
| random_25 | semantic_event | 0.6191 | 0.6667 | 0.0216 | 0.5176 |
| random_25 | entity_context | 0.6537 | 0.6923 | 0.0189 | 0.5504 |
| random_25 | random_dropout | 0.6591 | 0.7094 | 0.0197 | 0.6166 |
| random_25 | type_dropout | 0.6302 | 0.6410 | 0.0174 | 0.6152 |
| random_25 | mixed_dropout | 0.6616 | 0.6838 | 0.0170 | 0.6159 |
| random_25 | observed_router | 0.6610 | 0.6239 | 0.0117 | 0.6110 |
| random_50 | semantic_event | 0.5756 | 0.5983 | 0.0212 | 0.3470 |
| random_50 | entity_context | 0.5932 | 0.5812 | 0.0166 | 0.4118 |
| random_50 | random_dropout | 0.6131 | 0.6581 | 0.0219 | 0.5589 |
| random_50 | type_dropout | 0.5742 | 0.5385 | 0.0148 | 0.6061 |
| random_50 | mixed_dropout | 0.6413 | 0.6496 | 0.0166 | 0.5783 |
| random_50 | observed_router | 0.6073 | 0.5470 | 0.0114 | 0.5620 |
| random_75 | semantic_event | 0.4566 | 0.3846 | 0.0132 | 0.2138 |
| random_75 | entity_context | 0.4566 | 0.3846 | 0.0132 | 0.2607 |
| random_75 | random_dropout | 0.4877 | 0.4615 | 0.0193 | 0.4360 |
| random_75 | type_dropout | 0.4104 | 0.3162 | 0.0098 | 0.4748 |
| random_75 | mixed_dropout | 0.4705 | 0.3761 | 0.0098 | 0.4378 |
| random_75 | observed_router | 0.4591 | 0.3590 | 0.0087 | 0.4374 |
| support_burst_60 | semantic_event | 0.6923 | 0.6923 | 0.0136 | 0.6286 |
| support_burst_60 | entity_context | 0.6750 | 0.6923 | 0.0159 | 0.6275 |
| support_burst_60 | random_dropout | 0.6750 | 0.6923 | 0.0159 | 0.6275 |
| support_burst_60 | type_dropout | 0.6750 | 0.6923 | 0.0159 | 0.6214 |
| support_burst_60 | mixed_dropout | 0.6835 | 0.6923 | 0.0148 | 0.6275 |
| support_burst_60 | observed_router | 0.6835 | 0.6923 | 0.0148 | 0.6095 |
| command_records_absent | semantic_event | 0.6095 | 0.8205 | 0.0386 | 0.3139 |
| command_records_absent | entity_context | 0.6226 | 0.8462 | 0.0386 | 0.3271 |
| command_records_absent | random_dropout | 0.7000 | 0.7179 | 0.0148 | 0.6226 |
| command_records_absent | type_dropout | 0.7000 | 0.7179 | 0.0148 | 0.6226 |
| command_records_absent | mixed_dropout | 0.7059 | 0.7692 | 0.0182 | 0.6226 |
| command_records_absent | observed_router | 0.6829 | 0.7179 | 0.0170 | 0.5926 |
| delay_30_deadline_0 | semantic_event | 0.6095 | 0.8205 | 0.0386 | 0.3139 |
| delay_30_deadline_0 | entity_context | 0.6226 | 0.8462 | 0.0386 | 0.3535 |
| delay_30_deadline_0 | random_dropout | 0.6905 | 0.7436 | 0.0182 | 0.6226 |
| delay_30_deadline_0 | type_dropout | 0.7089 | 0.7179 | 0.0136 | 0.6226 |
| delay_30_deadline_0 | mixed_dropout | 0.6977 | 0.7692 | 0.0193 | 0.6226 |
| delay_30_deadline_0 | observed_router | 0.6829 | 0.7179 | 0.0170 | 0.5926 |
| delay_30_deadline_30 | semantic_event | 0.6923 | 0.6923 | 0.0136 | 0.6286 |
| delay_30_deadline_30 | entity_context | 0.7179 | 0.7179 | 0.0125 | 0.6471 |
| delay_30_deadline_30 | random_dropout | 0.7179 | 0.7179 | 0.0125 | 0.6346 |
| delay_30_deadline_30 | type_dropout | 0.7089 | 0.7179 | 0.0136 | 0.6286 |
| delay_30_deadline_30 | mixed_dropout | 0.7179 | 0.7179 | 0.0125 | 0.6286 |
| delay_30_deadline_30 | observed_router | 0.7013 | 0.6923 | 0.0125 | 0.6337 |
| delay_120_deadline_0 | semantic_event | 0.6095 | 0.8205 | 0.0386 | 0.3139 |
| delay_120_deadline_0 | entity_context | 0.6226 | 0.8462 | 0.0386 | 0.3271 |
| delay_120_deadline_0 | random_dropout | 0.7000 | 0.7179 | 0.0148 | 0.6226 |
| delay_120_deadline_0 | type_dropout | 0.7000 | 0.7179 | 0.0148 | 0.6226 |
| delay_120_deadline_0 | mixed_dropout | 0.7059 | 0.7692 | 0.0182 | 0.6226 |
| delay_120_deadline_0 | observed_router | 0.6829 | 0.7179 | 0.0170 | 0.5926 |
| delay_120_deadline_30 | semantic_event | 0.6095 | 0.8205 | 0.0386 | 0.3139 |
| delay_120_deadline_30 | entity_context | 0.6226 | 0.8462 | 0.0386 | 0.3415 |
| delay_120_deadline_30 | random_dropout | 0.7000 | 0.7179 | 0.0148 | 0.6226 |
| delay_120_deadline_30 | type_dropout | 0.7000 | 0.7179 | 0.0148 | 0.6226 |
| delay_120_deadline_30 | mixed_dropout | 0.7059 | 0.7692 | 0.0182 | 0.6226 |
| delay_120_deadline_30 | observed_router | 0.6829 | 0.7179 | 0.0170 | 0.5926 |
| delay_120_deadline_120 | semantic_event | 0.6923 | 0.6923 | 0.0136 | 0.6286 |
| delay_120_deadline_120 | entity_context | 0.7179 | 0.7179 | 0.0125 | 0.6471 |
| delay_120_deadline_120 | random_dropout | 0.7179 | 0.7179 | 0.0125 | 0.6346 |
| delay_120_deadline_120 | type_dropout | 0.7089 | 0.7179 | 0.0136 | 0.6286 |
| delay_120_deadline_120 | mixed_dropout | 0.7179 | 0.7179 | 0.0125 | 0.6286 |
| delay_120_deadline_120 | observed_router | 0.7013 | 0.6923 | 0.0125 | 0.6337 |
| execve_absent | semantic_event | 0.6275 | 0.8205 | 0.0352 | 0.6168 |
| execve_absent | entity_context | 0.6337 | 0.8205 | 0.0341 | 0.6226 |
| execve_absent | random_dropout | 0.7160 | 0.7436 | 0.0148 | 0.6226 |
| execve_absent | type_dropout | 0.7089 | 0.7179 | 0.0136 | 0.6226 |
| execve_absent | mixed_dropout | 0.7179 | 0.7179 | 0.0125 | 0.6226 |
| execve_absent | observed_router | 0.7013 | 0.6923 | 0.0125 | 0.6095 |
| proctitle_absent | semantic_event | 0.6598 | 0.8205 | 0.0295 | 0.6055 |
| proctitle_absent | entity_context | 0.6804 | 0.8462 | 0.0284 | 0.6000 |
| proctitle_absent | random_dropout | 0.7368 | 0.7179 | 0.0102 | 0.6346 |
| proctitle_absent | type_dropout | 0.7179 | 0.7179 | 0.0125 | 0.6226 |
| proctitle_absent | mixed_dropout | 0.7179 | 0.7179 | 0.0125 | 0.6226 |
| proctitle_absent | observed_router | 0.7000 | 0.7179 | 0.0148 | 0.5926 |
| syscall_absent | semantic_event | 0.7324 | 0.6667 | 0.0068 | 0.6939 |
| syscall_absent | entity_context | 0.7059 | 0.6154 | 0.0057 | 0.6809 |
| syscall_absent | random_dropout | 0.7222 | 0.6667 | 0.0079 | 0.6735 |
| syscall_absent | type_dropout | 0.6333 | 0.4872 | 0.0023 | 0.6957 |
| syscall_absent | mixed_dropout | 0.7222 | 0.6667 | 0.0079 | 0.6809 |
| syscall_absent | observed_router | 0.7077 | 0.5897 | 0.0034 | 0.6813 |
| path_absent | semantic_event | 0.7027 | 0.6667 | 0.0102 | 0.6522 |
| path_absent | entity_context | 0.7222 | 0.6667 | 0.0079 | 0.6667 |
| path_absent | random_dropout | 0.6400 | 0.8205 | 0.0329 | 0.6226 |
| path_absent | type_dropout | 0.7013 | 0.6923 | 0.0125 | 0.6154 |
| path_absent | mixed_dropout | 0.6897 | 0.7692 | 0.0204 | 0.6095 |
| path_absent | observed_router | 0.6842 | 0.6667 | 0.0125 | 0.6598 |

Primary gates: `{"clean_f1_delta_min": {"delta": 0.0, "limit": -0.02, "passed": true}, "command_records_absent_f1_delta_min": {"delta": 0.005882352941176561, "limit": 0.05, "passed": false}, "command_records_absent_flag_rate_delta_max": {"delta": 0.00340522133938706, "limit": 0.005, "passed": true}, "command_records_absent_recall_delta_min": {"delta": 0.05128205128205132, "limit": -0.02, "passed": true}, "random_50_mean_f1_delta_min": {"delta": 0.028177602770433685, "limit": -0.02, "passed": true}}`

## T1105

Status: COMPLETE. Primary screening: **FAIL**.

Support: `{"calibration": {"n": 1494, "negative": 1407, "positive": 87}, "development": {"n": 1894, "negative": 1859, "positive": 35}, "fit": {"n": 3932, "negative": 3807, "positive": 125}, "test": {"n": 920, "negative": 903, "positive": 17}}`

| Condition | Arm | Calibrated F1 | Recall | Other-label flag rate | F1 at0.5 |
|---|---|---:|---:|---:|---:|
| clean | semantic_event | 0.7568 | 0.8235 | 0.0066 | 0.7368 |
| clean | entity_context | 0.7000 | 0.8235 | 0.0100 | 0.5957 |
| clean | random_dropout | 0.6667 | 0.8235 | 0.0122 | 0.5833 |
| clean | type_dropout | 0.6364 | 0.8235 | 0.0144 | 0.5714 |
| clean | mixed_dropout | 0.6364 | 0.8235 | 0.0144 | 0.5833 |
| clean | observed_router | 0.7179 | 0.8235 | 0.0089 | 0.6829 |
| random_25 | semantic_event | 0.4359 | 0.8627 | 0.0395 | 0.3996 |
| random_25 | entity_context | 0.5576 | 0.8039 | 0.0207 | 0.5271 |
| random_25 | random_dropout | 0.6396 | 0.8039 | 0.0137 | 0.5471 |
| random_25 | type_dropout | 0.5675 | 0.7843 | 0.0185 | 0.4412 |
| random_25 | mixed_dropout | 0.6264 | 0.8039 | 0.0144 | 0.5468 |
| random_25 | observed_router | 0.5633 | 0.8039 | 0.0199 | 0.4823 |
| random_50 | semantic_event | 0.2564 | 0.8627 | 0.0915 | 0.2368 |
| random_50 | entity_context | 0.3489 | 0.8039 | 0.0532 | 0.3274 |
| random_50 | random_dropout | 0.5173 | 0.7843 | 0.0240 | 0.3993 |
| random_50 | type_dropout | 0.3576 | 0.7451 | 0.0458 | 0.2824 |
| random_50 | mixed_dropout | 0.4489 | 0.7843 | 0.0329 | 0.3649 |
| random_50 | observed_router | 0.3615 | 0.7647 | 0.0472 | 0.3504 |
| random_75 | semantic_event | 0.1587 | 0.7255 | 0.1399 | 0.1361 |
| random_75 | entity_context | 0.2005 | 0.6863 | 0.0963 | 0.1946 |
| random_75 | random_dropout | 0.3290 | 0.6275 | 0.0410 | 0.2179 |
| random_75 | type_dropout | 0.2012 | 0.6078 | 0.0834 | 0.1761 |
| random_75 | mixed_dropout | 0.2951 | 0.6275 | 0.0491 | 0.2084 |
| random_75 | observed_router | 0.2182 | 0.6275 | 0.0779 | 0.2070 |
| support_burst_60 | semantic_event | 0.7568 | 0.8235 | 0.0066 | 0.7368 |
| support_burst_60 | entity_context | 0.6250 | 0.8824 | 0.0177 | 0.5769 |
| support_burst_60 | random_dropout | 0.5833 | 0.8235 | 0.0188 | 0.5000 |
| support_burst_60 | type_dropout | 0.5283 | 0.8235 | 0.0244 | 0.4590 |
| support_burst_60 | mixed_dropout | 0.5600 | 0.8235 | 0.0210 | 0.4667 |
| support_burst_60 | observed_router | 0.6364 | 0.8235 | 0.0144 | 0.5833 |
| command_records_absent | semantic_event | 0.4138 | 0.7059 | 0.0321 | 0.2258 |
| command_records_absent | entity_context | 0.4231 | 0.6471 | 0.0266 | 0.3607 |
| command_records_absent | random_dropout | 0.2203 | 0.7647 | 0.0975 | 0.1591 |
| command_records_absent | type_dropout | 0.2955 | 0.7647 | 0.0642 | 0.1958 |
| command_records_absent | mixed_dropout | 0.2766 | 0.7647 | 0.0709 | 0.2121 |
| command_records_absent | observed_router | 0.2029 | 0.8235 | 0.1185 | 0.1657 |
| delay_30_deadline_0 | semantic_event | 0.4138 | 0.7059 | 0.0321 | 0.2258 |
| delay_30_deadline_0 | entity_context | 0.4314 | 0.6471 | 0.0255 | 0.3729 |
| delay_30_deadline_0 | random_dropout | 0.2430 | 0.7647 | 0.0853 | 0.1761 |
| delay_30_deadline_0 | type_dropout | 0.3059 | 0.7647 | 0.0609 | 0.2188 |
| delay_30_deadline_0 | mixed_dropout | 0.2826 | 0.7647 | 0.0687 | 0.2205 |
| delay_30_deadline_0 | observed_router | 0.1986 | 0.8235 | 0.1218 | 0.1591 |
| delay_30_deadline_30 | semantic_event | 0.7568 | 0.8235 | 0.0066 | 0.7368 |
| delay_30_deadline_30 | entity_context | 0.7000 | 0.8235 | 0.0100 | 0.5957 |
| delay_30_deadline_30 | random_dropout | 0.6667 | 0.8235 | 0.0122 | 0.5833 |
| delay_30_deadline_30 | type_dropout | 0.6364 | 0.8235 | 0.0144 | 0.5714 |
| delay_30_deadline_30 | mixed_dropout | 0.6364 | 0.8235 | 0.0144 | 0.5833 |
| delay_30_deadline_30 | observed_router | 0.7179 | 0.8235 | 0.0089 | 0.6829 |
| delay_120_deadline_0 | semantic_event | 0.4138 | 0.7059 | 0.0321 | 0.2258 |
| delay_120_deadline_0 | entity_context | 0.4231 | 0.6471 | 0.0266 | 0.3607 |
| delay_120_deadline_0 | random_dropout | 0.2203 | 0.7647 | 0.0975 | 0.1591 |
| delay_120_deadline_0 | type_dropout | 0.2955 | 0.7647 | 0.0642 | 0.1958 |
| delay_120_deadline_0 | mixed_dropout | 0.2766 | 0.7647 | 0.0709 | 0.2121 |
| delay_120_deadline_0 | observed_router | 0.2029 | 0.8235 | 0.1185 | 0.1657 |
| delay_120_deadline_30 | semantic_event | 0.4138 | 0.7059 | 0.0321 | 0.2258 |
| delay_120_deadline_30 | entity_context | 0.4231 | 0.6471 | 0.0266 | 0.3607 |
| delay_120_deadline_30 | random_dropout | 0.2222 | 0.7647 | 0.0963 | 0.1609 |
| delay_120_deadline_30 | type_dropout | 0.2955 | 0.7647 | 0.0642 | 0.1944 |
| delay_120_deadline_30 | mixed_dropout | 0.2766 | 0.7647 | 0.0709 | 0.2105 |
| delay_120_deadline_30 | observed_router | 0.2029 | 0.8235 | 0.1185 | 0.1647 |
| delay_120_deadline_120 | semantic_event | 0.7568 | 0.8235 | 0.0066 | 0.7368 |
| delay_120_deadline_120 | entity_context | 0.7000 | 0.8235 | 0.0100 | 0.5957 |
| delay_120_deadline_120 | random_dropout | 0.6667 | 0.8235 | 0.0122 | 0.5833 |
| delay_120_deadline_120 | type_dropout | 0.6364 | 0.8235 | 0.0144 | 0.5714 |
| delay_120_deadline_120 | mixed_dropout | 0.6364 | 0.8235 | 0.0144 | 0.5833 |
| delay_120_deadline_120 | observed_router | 0.7179 | 0.8235 | 0.0089 | 0.6829 |
| execve_absent | semantic_event | 0.3659 | 0.8824 | 0.0554 | 0.3226 |
| execve_absent | entity_context | 0.4545 | 0.8824 | 0.0377 | 0.3704 |
| execve_absent | random_dropout | 0.6087 | 0.8235 | 0.0166 | 0.4828 |
| execve_absent | type_dropout | 0.5490 | 0.8235 | 0.0221 | 0.4912 |
| execve_absent | mixed_dropout | 0.5600 | 0.8235 | 0.0210 | 0.5091 |
| execve_absent | observed_router | 0.6087 | 0.8235 | 0.0166 | 0.5091 |
| proctitle_absent | semantic_event | 0.7778 | 0.8235 | 0.0055 | 0.7778 |
| proctitle_absent | entity_context | 0.7778 | 0.8235 | 0.0055 | 0.7179 |
| proctitle_absent | random_dropout | 0.4000 | 0.8235 | 0.0432 | 0.3093 |
| proctitle_absent | type_dropout | 0.4746 | 0.8235 | 0.0310 | 0.3836 |
| proctitle_absent | mixed_dropout | 0.4912 | 0.8235 | 0.0288 | 0.3784 |
| proctitle_absent | observed_router | 0.3714 | 0.7647 | 0.0443 | 0.3333 |
| syscall_absent | semantic_event | 0.4267 | 0.9412 | 0.0465 | 0.3636 |
| syscall_absent | entity_context | 0.6667 | 0.8824 | 0.0144 | 0.6522 |
| syscall_absent | random_dropout | 0.8750 | 0.8235 | 0.0011 | 0.8485 |
| syscall_absent | type_dropout | 0.8235 | 0.8235 | 0.0033 | 0.7778 |
| syscall_absent | mixed_dropout | 0.8750 | 0.8235 | 0.0011 | 0.8000 |
| syscall_absent | observed_router | 0.8485 | 0.8235 | 0.0022 | 0.8485 |
| path_absent | semantic_event | 0.7895 | 0.8824 | 0.0066 | 0.7692 |
| path_absent | entity_context | 0.6000 | 0.8824 | 0.0199 | 0.5926 |
| path_absent | random_dropout | 0.6667 | 0.8824 | 0.0144 | 0.5882 |
| path_absent | type_dropout | 0.4412 | 0.8824 | 0.0399 | 0.2885 |
| path_absent | mixed_dropout | 0.5882 | 0.8824 | 0.0210 | 0.4918 |
| path_absent | observed_router | 0.7568 | 0.8235 | 0.0066 | 0.7000 |

Primary gates: `{"clean_f1_delta_min": {"delta": -0.030303030303030276, "limit": -0.02, "passed": false}, "command_records_absent_f1_delta_min": {"delta": 0.05625676163000362, "limit": 0.05, "passed": true}, "command_records_absent_flag_rate_delta_max": {"delta": -0.026578073089701004, "limit": 0.005, "passed": true}, "command_records_absent_recall_delta_min": {"delta": 0.0, "limit": -0.02, "passed": true}, "random_50_mean_f1_delta_min": {"delta": -0.06845391616241486, "limit": -0.02, "passed": false}}`

## Interpretation limits

- AIT and Casino are already exposed development sources. No significance or population guarantee follows from passing descriptive gates.
- CAM-LDS, if qualified, uses a family-held-out interval-state proxy. It is not directly comparable to Casino annotation-onset targets or AIT rule labels.
- Router specialists use more parameters than one logistic regression; fit support counts unique underlying observed targets.
- Record-type removal is a synthetic log stress test, not a measured sensor outage. Waiting out injected delay restores clean evidence by construction.
- Invisible targets remain in denominators and get no alarm. The offline target roster is not a deployable detector trigger.
- Source labels, dependent events, small positive counts, recipe overlap and dataset shift limit generalization.
- No novel algorithm, complete APT detection, or improved real-world benign false-alarm rate is established.
