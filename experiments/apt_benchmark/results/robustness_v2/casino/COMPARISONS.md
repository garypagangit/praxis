# casino: structured-loss comparisons

All changes compare against random-record-dropout training. Both operating points remain separate; each arm retains its frozen clean-calibration threshold.

Baseline replication: **PASS**.

Each positive-bearing test run supplies one win/tie/loss vote after averaging matched corruption seeds. Runs with no positive examples are excluded from these votes; their negatives remain in pooled metrics. These votes are descriptive, not independent significance tests.

## T1068

Status: **COMPLETE**.

Positive-bearing runs: 8; excluded zero-positive runs: 10.

### Fixed score > 0.5

| Condition | Arm | F1 | F1 change | Recall change | Other-label flag-rate change | Positive-run F1 W/T/L |
|---|---|---:|---:|---:|---:|---:|
| clean | semantic_event | 0.3889 | +0.0053 | +0.0000 | -0.0011 | 2/4/2 |
| clean | entity_context | 0.3944 | +0.0108 | +0.0000 | -0.0022 | 1/6/1 |
| clean | random_dropout | 0.3836 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| clean | type_dropout | 0.3636 | -0.0199 | +0.0000 | +0.0044 | 2/4/2 |
| clean | mixed_dropout | 0.3733 | -0.0102 | +0.0000 | +0.0022 | 1/5/2 |
| clean | observed_router | 0.3415 | -0.0421 | +0.0000 | +0.0099 | 0/4/4 |
| random_25 | semantic_event | 0.2117 | -0.1280 | +0.0476 | +0.0567 | 1/0/7 |
| random_25 | entity_context | 0.2409 | -0.0987 | +0.0000 | +0.0346 | 0/0/8 |
| random_25 | random_dropout | 0.3396 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| random_25 | type_dropout | 0.2118 | -0.1278 | -0.0238 | +0.0489 | 0/0/8 |
| random_25 | mixed_dropout | 0.3033 | -0.0363 | +0.0000 | +0.0099 | 0/0/8 |
| random_25 | observed_router | 0.2777 | -0.0619 | +0.0000 | +0.0184 | 0/0/8 |
| random_50 | semantic_event | 0.1544 | -0.1383 | +0.0238 | +0.0912 | 0/0/8 |
| random_50 | entity_context | 0.1809 | -0.1118 | +0.0238 | +0.0640 | 1/0/7 |
| random_50 | random_dropout | 0.2927 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| random_50 | type_dropout | 0.1556 | -0.1371 | +0.0000 | +0.0854 | 0/0/8 |
| random_50 | mixed_dropout | 0.2571 | -0.0356 | +0.0000 | +0.0132 | 0/0/8 |
| random_50 | observed_router | 0.2346 | -0.0581 | -0.0714 | +0.0166 | 1/0/7 |
| random_75 | semantic_event | 0.1067 | -0.1156 | +0.0238 | +0.1247 | 0/0/8 |
| random_75 | entity_context | 0.1101 | -0.1122 | -0.0238 | +0.1049 | 0/0/8 |
| random_75 | random_dropout | 0.2223 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| random_75 | type_dropout | 0.1137 | -0.1086 | +0.0000 | +0.1041 | 0/0/8 |
| random_75 | mixed_dropout | 0.2134 | -0.0089 | +0.0000 | +0.0040 | 0/1/7 |
| random_75 | observed_router | 0.2042 | -0.0181 | -0.0476 | +0.0033 | 2/0/6 |
| support_burst_60 | semantic_event | 0.3889 | -0.0174 | +0.0714 | +0.0077 | 1/3/4 |
| support_burst_60 | entity_context | 0.3881 | -0.0182 | +0.0000 | +0.0033 | 1/3/4 |
| support_burst_60 | random_dropout | 0.4062 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| support_burst_60 | type_dropout | 0.3714 | -0.0348 | +0.0000 | +0.0066 | 1/4/3 |
| support_burst_60 | mixed_dropout | 0.3939 | -0.0123 | +0.0000 | +0.0022 | 0/6/2 |
| support_burst_60 | observed_router | 0.4127 | +0.0064 | +0.0000 | -0.0011 | 3/4/1 |
| command_records_absent | semantic_event | 0.2955 | +0.0362 | -0.0714 | -0.0210 | 5/2/1 |
| command_records_absent | entity_context | 0.3291 | +0.0699 | -0.0714 | -0.0309 | 5/3/0 |
| command_records_absent | random_dropout | 0.2593 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| command_records_absent | type_dropout | 0.2364 | -0.0229 | -0.0714 | +0.0033 | 2/4/2 |
| command_records_absent | mixed_dropout | 0.2500 | -0.0093 | -0.0714 | -0.0033 | 4/3/1 |
| command_records_absent | observed_router | 0.2167 | -0.0426 | -0.0714 | +0.0143 | 1/3/4 |
| delay_30_deadline_0 | semantic_event | 0.2955 | +0.0362 | -0.0714 | -0.0210 | 5/2/1 |
| delay_30_deadline_0 | entity_context | 0.3291 | +0.0699 | -0.0714 | -0.0309 | 5/3/0 |
| delay_30_deadline_0 | random_dropout | 0.2593 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_30_deadline_0 | type_dropout | 0.2545 | -0.0047 | +0.0000 | +0.0022 | 3/4/1 |
| delay_30_deadline_0 | mixed_dropout | 0.2524 | -0.0068 | -0.0714 | -0.0044 | 3/4/1 |
| delay_30_deadline_0 | observed_router | 0.2167 | -0.0426 | -0.0714 | +0.0143 | 1/3/4 |
| delay_30_deadline_30 | semantic_event | 0.3889 | +0.0053 | +0.0000 | -0.0011 | 2/4/2 |
| delay_30_deadline_30 | entity_context | 0.3944 | +0.0108 | +0.0000 | -0.0022 | 1/6/1 |
| delay_30_deadline_30 | random_dropout | 0.3836 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_30_deadline_30 | type_dropout | 0.3636 | -0.0199 | +0.0000 | +0.0044 | 2/4/2 |
| delay_30_deadline_30 | mixed_dropout | 0.3733 | -0.0102 | +0.0000 | +0.0022 | 1/5/2 |
| delay_30_deadline_30 | observed_router | 0.3415 | -0.0421 | +0.0000 | +0.0099 | 0/4/4 |
| delay_120_deadline_0 | semantic_event | 0.2955 | +0.0362 | -0.0714 | -0.0210 | 5/2/1 |
| delay_120_deadline_0 | entity_context | 0.3291 | +0.0699 | -0.0714 | -0.0309 | 5/3/0 |
| delay_120_deadline_0 | random_dropout | 0.2593 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_120_deadline_0 | type_dropout | 0.2364 | -0.0229 | -0.0714 | +0.0033 | 2/4/2 |
| delay_120_deadline_0 | mixed_dropout | 0.2500 | -0.0093 | -0.0714 | -0.0033 | 4/3/1 |
| delay_120_deadline_0 | observed_router | 0.2167 | -0.0426 | -0.0714 | +0.0143 | 1/3/4 |
| delay_120_deadline_30 | semantic_event | 0.2955 | +0.0338 | -0.0714 | -0.0199 | 5/2/1 |
| delay_120_deadline_30 | entity_context | 0.3291 | +0.0674 | -0.0714 | -0.0298 | 5/3/0 |
| delay_120_deadline_30 | random_dropout | 0.2617 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_120_deadline_30 | type_dropout | 0.2364 | -0.0253 | -0.0714 | +0.0044 | 2/3/3 |
| delay_120_deadline_30 | mixed_dropout | 0.2524 | -0.0093 | -0.0714 | -0.0033 | 3/4/1 |
| delay_120_deadline_30 | observed_router | 0.2167 | -0.0450 | -0.0714 | +0.0155 | 1/3/4 |
| delay_120_deadline_120 | semantic_event | 0.3889 | +0.0053 | +0.0000 | -0.0011 | 2/4/2 |
| delay_120_deadline_120 | entity_context | 0.3944 | +0.0108 | +0.0000 | -0.0022 | 1/6/1 |
| delay_120_deadline_120 | random_dropout | 0.3836 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_120_deadline_120 | type_dropout | 0.3636 | -0.0199 | +0.0000 | +0.0044 | 2/4/2 |
| delay_120_deadline_120 | mixed_dropout | 0.3733 | -0.0102 | +0.0000 | +0.0022 | 1/5/2 |
| delay_120_deadline_120 | observed_router | 0.3415 | -0.0421 | +0.0000 | +0.0099 | 0/4/4 |
| execve_absent | semantic_event | 0.3824 | +0.0187 | -0.0714 | -0.0088 | 3/2/3 |
| execve_absent | entity_context | 0.4000 | +0.0364 | -0.0714 | -0.0121 | 4/3/1 |
| execve_absent | random_dropout | 0.3636 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| execve_absent | type_dropout | 0.3146 | -0.0490 | +0.0000 | +0.0132 | 0/5/3 |
| execve_absent | mixed_dropout | 0.3544 | -0.0092 | +0.0000 | +0.0022 | 1/5/2 |
| execve_absent | observed_router | 0.3133 | -0.0504 | -0.0714 | +0.0077 | 0/5/3 |
| proctitle_absent | semantic_event | 0.2800 | +0.0000 | +0.0000 | +0.0000 | 3/4/1 |
| proctitle_absent | entity_context | 0.3182 | +0.0382 | +0.0000 | -0.0132 | 4/4/0 |
| proctitle_absent | random_dropout | 0.2800 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| proctitle_absent | type_dropout | 0.2718 | -0.0082 | +0.0000 | +0.0033 | 2/4/2 |
| proctitle_absent | mixed_dropout | 0.2857 | +0.0057 | +0.0000 | -0.0022 | 4/4/0 |
| proctitle_absent | observed_router | 0.2137 | -0.0663 | +0.0000 | +0.0342 | 0/4/4 |
| syscall_absent | semantic_event | 0.0809 | -0.3524 | +0.0714 | +0.3146 | 0/0/8 |
| syscall_absent | entity_context | 0.1308 | -0.3025 | +0.0714 | +0.1689 | 0/0/8 |
| syscall_absent | random_dropout | 0.4333 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| syscall_absent | type_dropout | 0.1145 | -0.3188 | +0.0000 | +0.1843 | 0/0/8 |
| syscall_absent | mixed_dropout | 0.3611 | -0.0722 | +0.0000 | +0.0132 | 0/3/5 |
| syscall_absent | observed_router | 0.3768 | -0.0565 | +0.0000 | +0.0099 | 0/4/4 |
| path_absent | semantic_event | 0.3146 | -0.0311 | +0.0000 | +0.0088 | 2/3/3 |
| path_absent | entity_context | 0.2800 | -0.0657 | +0.0000 | +0.0210 | 0/4/4 |
| path_absent | random_dropout | 0.3457 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| path_absent | type_dropout | 0.3077 | -0.0380 | +0.0000 | +0.0110 | 0/5/3 |
| path_absent | mixed_dropout | 0.3333 | -0.0123 | +0.0000 | +0.0033 | 1/5/2 |
| path_absent | observed_router | 0.2745 | -0.0712 | +0.0000 | +0.0232 | 0/1/7 |

### Frozen calibration threshold

| Condition | Arm | F1 | F1 change | Recall change | Other-label flag-rate change | Positive-run F1 W/T/L |
|---|---|---:|---:|---:|---:|---:|
| clean | semantic_event | 0.6857 | +0.0190 | +0.0000 | -0.0011 | 1/5/2 |
| clean | entity_context | 0.6667 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| clean | random_dropout | 0.6667 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| clean | type_dropout | 0.6316 | -0.0351 | +0.0000 | +0.0022 | 0/6/2 |
| clean | mixed_dropout | 0.6316 | -0.0351 | +0.0000 | +0.0022 | 0/6/2 |
| clean | observed_router | 0.6154 | -0.0513 | +0.0000 | +0.0033 | 1/4/3 |
| random_25 | semantic_event | 0.3591 | -0.2431 | +0.0238 | +0.0291 | 0/0/8 |
| random_25 | entity_context | 0.4846 | -0.1176 | +0.0714 | +0.0132 | 1/0/7 |
| random_25 | random_dropout | 0.6022 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| random_25 | type_dropout | 0.4395 | -0.1627 | +0.0238 | +0.0162 | 1/0/7 |
| random_25 | mixed_dropout | 0.6077 | +0.0055 | +0.0000 | -0.0004 | 1/6/1 |
| random_25 | observed_router | 0.5588 | -0.0434 | +0.0238 | +0.0040 | 1/2/5 |
| random_50 | semantic_event | 0.2393 | -0.2562 | +0.0238 | +0.0511 | 0/0/8 |
| random_50 | entity_context | 0.3043 | -0.1913 | +0.0714 | +0.0342 | 0/0/8 |
| random_50 | random_dropout | 0.4955 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| random_50 | type_dropout | 0.2921 | -0.2034 | +0.0952 | +0.0401 | 0/0/8 |
| random_50 | mixed_dropout | 0.5261 | +0.0306 | +0.0238 | -0.0011 | 3/4/1 |
| random_50 | observed_router | 0.4578 | -0.0377 | +0.0476 | +0.0066 | 2/2/4 |
| random_75 | semantic_event | 0.1663 | -0.1762 | +0.0476 | +0.0600 | 1/0/7 |
| random_75 | entity_context | 0.1624 | -0.1800 | -0.0238 | +0.0497 | 1/0/7 |
| random_75 | random_dropout | 0.3424 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| random_75 | type_dropout | 0.1689 | -0.1735 | +0.0238 | +0.0541 | 1/0/7 |
| random_75 | mixed_dropout | 0.3209 | -0.0215 | -0.0476 | -0.0007 | 2/3/3 |
| random_75 | observed_router | 0.2068 | -0.1356 | -0.0476 | +0.0250 | 1/0/7 |
| support_burst_60 | semantic_event | 0.6857 | -0.0416 | +0.0000 | +0.0022 | 1/4/3 |
| support_burst_60 | entity_context | 0.7273 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| support_burst_60 | random_dropout | 0.7273 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| support_burst_60 | type_dropout | 0.6875 | -0.0398 | -0.0714 | +0.0000 | 0/7/1 |
| support_burst_60 | mixed_dropout | 0.7273 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| support_burst_60 | observed_router | 0.7742 | +0.0469 | +0.0000 | -0.0022 | 1/7/0 |
| command_records_absent | semantic_event | 0.5000 | +0.1000 | -0.0714 | -0.0177 | 4/3/1 |
| command_records_absent | entity_context | 0.6190 | +0.2190 | +0.0000 | -0.0254 | 5/3/0 |
| command_records_absent | random_dropout | 0.4000 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| command_records_absent | type_dropout | 0.4127 | +0.0127 | +0.0000 | -0.0022 | 2/4/2 |
| command_records_absent | mixed_dropout | 0.4194 | +0.0194 | +0.0000 | -0.0033 | 2/5/1 |
| command_records_absent | observed_router | 0.3562 | -0.0438 | +0.0000 | +0.0088 | 0/3/5 |
| delay_30_deadline_0 | semantic_event | 0.5000 | +0.0806 | -0.0714 | -0.0143 | 3/4/1 |
| delay_30_deadline_0 | entity_context | 0.6190 | +0.1997 | +0.0000 | -0.0221 | 5/3/0 |
| delay_30_deadline_0 | random_dropout | 0.4194 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_30_deadline_0 | type_dropout | 0.4194 | +0.0000 | +0.0000 | +0.0000 | 1/4/3 |
| delay_30_deadline_0 | mixed_dropout | 0.4407 | +0.0213 | +0.0000 | -0.0033 | 1/6/1 |
| delay_30_deadline_0 | observed_router | 0.3562 | -0.0632 | +0.0000 | +0.0121 | 0/3/5 |
| delay_30_deadline_30 | semantic_event | 0.6857 | +0.0190 | +0.0000 | -0.0011 | 1/5/2 |
| delay_30_deadline_30 | entity_context | 0.6667 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_30_deadline_30 | random_dropout | 0.6667 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_30_deadline_30 | type_dropout | 0.6316 | -0.0351 | +0.0000 | +0.0022 | 0/6/2 |
| delay_30_deadline_30 | mixed_dropout | 0.6316 | -0.0351 | +0.0000 | +0.0022 | 0/6/2 |
| delay_30_deadline_30 | observed_router | 0.6154 | -0.0513 | +0.0000 | +0.0033 | 1/4/3 |
| delay_120_deadline_0 | semantic_event | 0.5000 | +0.1000 | -0.0714 | -0.0177 | 4/3/1 |
| delay_120_deadline_0 | entity_context | 0.6190 | +0.2190 | +0.0000 | -0.0254 | 5/3/0 |
| delay_120_deadline_0 | random_dropout | 0.4000 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_120_deadline_0 | type_dropout | 0.4127 | +0.0127 | +0.0000 | -0.0022 | 2/4/2 |
| delay_120_deadline_0 | mixed_dropout | 0.4194 | +0.0194 | +0.0000 | -0.0033 | 2/5/1 |
| delay_120_deadline_0 | observed_router | 0.3562 | -0.0438 | +0.0000 | +0.0088 | 0/3/5 |
| delay_120_deadline_30 | semantic_event | 0.5000 | +0.1000 | -0.0714 | -0.0177 | 4/3/1 |
| delay_120_deadline_30 | entity_context | 0.6190 | +0.2190 | +0.0000 | -0.0254 | 5/3/0 |
| delay_120_deadline_30 | random_dropout | 0.4000 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_120_deadline_30 | type_dropout | 0.4194 | +0.0194 | +0.0000 | -0.0033 | 2/4/2 |
| delay_120_deadline_30 | mixed_dropout | 0.4262 | +0.0262 | +0.0000 | -0.0044 | 2/5/1 |
| delay_120_deadline_30 | observed_router | 0.3562 | -0.0438 | +0.0000 | +0.0088 | 0/3/5 |
| delay_120_deadline_120 | semantic_event | 0.6857 | +0.0190 | +0.0000 | -0.0011 | 1/5/2 |
| delay_120_deadline_120 | entity_context | 0.6667 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_120_deadline_120 | random_dropout | 0.6667 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_120_deadline_120 | type_dropout | 0.6316 | -0.0351 | +0.0000 | +0.0022 | 0/6/2 |
| delay_120_deadline_120 | mixed_dropout | 0.6316 | -0.0351 | +0.0000 | +0.0022 | 0/6/2 |
| delay_120_deadline_120 | observed_router | 0.6154 | -0.0513 | +0.0000 | +0.0033 | 1/4/3 |
| execve_absent | semantic_event | 0.8000 | +0.2286 | +0.0000 | -0.0132 | 5/3/0 |
| execve_absent | entity_context | 0.7059 | +0.1345 | +0.0000 | -0.0088 | 5/3/0 |
| execve_absent | random_dropout | 0.5714 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| execve_absent | type_dropout | 0.5000 | -0.0714 | +0.0714 | +0.0099 | 1/4/3 |
| execve_absent | mixed_dropout | 0.5106 | -0.0608 | +0.0000 | +0.0055 | 0/4/4 |
| execve_absent | observed_router | 0.5455 | -0.0260 | +0.0000 | +0.0022 | 0/6/2 |
| proctitle_absent | semantic_event | 0.4800 | -0.0106 | -0.0714 | -0.0022 | 2/3/3 |
| proctitle_absent | entity_context | 0.5306 | +0.0400 | +0.0000 | -0.0044 | 1/6/1 |
| proctitle_absent | random_dropout | 0.4906 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| proctitle_absent | type_dropout | 0.4643 | -0.0263 | +0.0000 | +0.0033 | 1/5/2 |
| proctitle_absent | mixed_dropout | 0.4800 | -0.0106 | -0.0714 | -0.0022 | 1/5/2 |
| proctitle_absent | observed_router | 0.3750 | -0.1156 | -0.0714 | +0.0132 | 0/3/5 |
| syscall_absent | semantic_event | 0.4407 | -0.3593 | +0.0714 | +0.0309 | 1/1/6 |
| syscall_absent | entity_context | 0.5200 | -0.2800 | +0.0714 | +0.0210 | 1/2/5 |
| syscall_absent | random_dropout | 0.8000 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| syscall_absent | type_dropout | 0.6667 | -0.1333 | +0.0714 | +0.0088 | 1/3/4 |
| syscall_absent | mixed_dropout | 0.8000 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| syscall_absent | observed_router | 0.8000 | +0.0000 | +0.0000 | +0.0000 | 1/6/1 |
| path_absent | semantic_event | 0.5306 | -0.1551 | +0.0714 | +0.0143 | 1/2/5 |
| path_absent | entity_context | 0.5652 | -0.1205 | +0.0714 | +0.0110 | 1/4/3 |
| path_absent | random_dropout | 0.6857 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| path_absent | type_dropout | 0.6667 | -0.0190 | +0.0000 | +0.0011 | 0/7/1 |
| path_absent | mixed_dropout | 0.6316 | -0.0541 | +0.0000 | +0.0033 | 0/6/2 |
| path_absent | observed_router | 0.6316 | -0.0541 | +0.0000 | +0.0033 | 1/3/4 |

## T1548

Status: **COMPLETE**.

Positive-bearing runs: 12; excluded zero-positive runs: 6.

### Fixed score > 0.5

| Condition | Arm | F1 | F1 change | Recall change | Other-label flag-rate change | Positive-run F1 W/T/L |
|---|---|---:|---:|---:|---:|---:|
| clean | semantic_event | 0.6286 | -0.0060 | +0.0000 | +0.0011 | 1/9/2 |
| clean | entity_context | 0.6471 | +0.0124 | +0.0000 | -0.0023 | 2/10/0 |
| clean | random_dropout | 0.6346 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| clean | type_dropout | 0.6286 | -0.0060 | +0.0000 | +0.0011 | 0/11/1 |
| clean | mixed_dropout | 0.6286 | -0.0060 | +0.0000 | +0.0011 | 0/11/1 |
| clean | observed_router | 0.6337 | -0.0010 | -0.0256 | -0.0023 | 0/10/2 |
| random_25 | semantic_event | 0.5176 | -0.0990 | +0.0000 | +0.0231 | 1/3/8 |
| random_25 | entity_context | 0.5504 | -0.0662 | -0.0085 | +0.0136 | 1/3/8 |
| random_25 | random_dropout | 0.6166 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| random_25 | type_dropout | 0.6152 | -0.0014 | -0.0513 | -0.0049 | 3/5/4 |
| random_25 | mixed_dropout | 0.6159 | -0.0007 | -0.0085 | -0.0008 | 1/9/2 |
| random_25 | observed_router | 0.6110 | -0.0056 | -0.0342 | -0.0023 | 1/6/5 |
| random_50 | semantic_event | 0.3470 | -0.2120 | +0.0427 | +0.0844 | 0/1/11 |
| random_50 | entity_context | 0.4118 | -0.1471 | +0.0171 | +0.0477 | 0/1/11 |
| random_50 | random_dropout | 0.5589 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| random_50 | type_dropout | 0.6061 | +0.0472 | -0.0684 | -0.0166 | 8/2/2 |
| random_50 | mixed_dropout | 0.5783 | +0.0193 | -0.0085 | -0.0049 | 6/5/1 |
| random_50 | observed_router | 0.5620 | +0.0031 | -0.0256 | -0.0034 | 4/4/4 |
| random_75 | semantic_event | 0.2138 | -0.2222 | -0.0085 | +0.1192 | 0/0/12 |
| random_75 | entity_context | 0.2607 | -0.1754 | -0.0171 | +0.0738 | 1/1/10 |
| random_75 | random_dropout | 0.4360 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| random_75 | type_dropout | 0.4748 | +0.0387 | -0.1453 | -0.0306 | 6/2/4 |
| random_75 | mixed_dropout | 0.4378 | +0.0018 | -0.0256 | -0.0045 | 4/6/2 |
| random_75 | observed_router | 0.4374 | +0.0013 | -0.0342 | -0.0061 | 5/4/3 |
| support_burst_60 | semantic_event | 0.6286 | +0.0011 | +0.0256 | +0.0023 | 1/9/2 |
| support_burst_60 | entity_context | 0.6275 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| support_burst_60 | random_dropout | 0.6275 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| support_burst_60 | type_dropout | 0.6214 | -0.0061 | +0.0000 | +0.0011 | 0/11/1 |
| support_burst_60 | mixed_dropout | 0.6275 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| support_burst_60 | observed_router | 0.6095 | -0.0179 | +0.0000 | +0.0034 | 0/10/2 |
| command_records_absent | semantic_event | 0.3139 | -0.3087 | +0.0513 | +0.1305 | 0/5/7 |
| command_records_absent | entity_context | 0.3271 | -0.2955 | +0.0513 | +0.1203 | 0/5/7 |
| command_records_absent | random_dropout | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| command_records_absent | type_dropout | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| command_records_absent | mixed_dropout | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| command_records_absent | observed_router | 0.5926 | -0.0300 | -0.0256 | +0.0034 | 0/10/2 |
| delay_30_deadline_0 | semantic_event | 0.3139 | -0.3087 | +0.0513 | +0.1305 | 0/5/7 |
| delay_30_deadline_0 | entity_context | 0.3535 | -0.2691 | +0.0513 | +0.1022 | 0/5/7 |
| delay_30_deadline_0 | random_dropout | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_30_deadline_0 | type_dropout | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_30_deadline_0 | mixed_dropout | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_30_deadline_0 | observed_router | 0.5926 | -0.0300 | -0.0256 | +0.0034 | 0/10/2 |
| delay_30_deadline_30 | semantic_event | 0.6286 | -0.0060 | +0.0000 | +0.0011 | 1/9/2 |
| delay_30_deadline_30 | entity_context | 0.6471 | +0.0124 | +0.0000 | -0.0023 | 2/10/0 |
| delay_30_deadline_30 | random_dropout | 0.6346 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_30_deadline_30 | type_dropout | 0.6286 | -0.0060 | +0.0000 | +0.0011 | 0/11/1 |
| delay_30_deadline_30 | mixed_dropout | 0.6286 | -0.0060 | +0.0000 | +0.0011 | 0/11/1 |
| delay_30_deadline_30 | observed_router | 0.6337 | -0.0010 | -0.0256 | -0.0023 | 0/10/2 |
| delay_120_deadline_0 | semantic_event | 0.3139 | -0.3087 | +0.0513 | +0.1305 | 0/5/7 |
| delay_120_deadline_0 | entity_context | 0.3271 | -0.2955 | +0.0513 | +0.1203 | 0/5/7 |
| delay_120_deadline_0 | random_dropout | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_120_deadline_0 | type_dropout | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_120_deadline_0 | mixed_dropout | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_120_deadline_0 | observed_router | 0.5926 | -0.0300 | -0.0256 | +0.0034 | 0/10/2 |
| delay_120_deadline_30 | semantic_event | 0.3139 | -0.3087 | +0.0513 | +0.1305 | 0/5/7 |
| delay_120_deadline_30 | entity_context | 0.3415 | -0.2812 | +0.0513 | +0.1101 | 0/5/7 |
| delay_120_deadline_30 | random_dropout | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_120_deadline_30 | type_dropout | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_120_deadline_30 | mixed_dropout | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_120_deadline_30 | observed_router | 0.5926 | -0.0300 | -0.0256 | +0.0034 | 0/10/2 |
| delay_120_deadline_120 | semantic_event | 0.6286 | -0.0060 | +0.0000 | +0.0011 | 1/9/2 |
| delay_120_deadline_120 | entity_context | 0.6471 | +0.0124 | +0.0000 | -0.0023 | 2/10/0 |
| delay_120_deadline_120 | random_dropout | 0.6346 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_120_deadline_120 | type_dropout | 0.6286 | -0.0060 | +0.0000 | +0.0011 | 0/11/1 |
| delay_120_deadline_120 | mixed_dropout | 0.6286 | -0.0060 | +0.0000 | +0.0011 | 0/11/1 |
| delay_120_deadline_120 | observed_router | 0.6337 | -0.0010 | -0.0256 | -0.0023 | 0/10/2 |
| execve_absent | semantic_event | 0.6168 | -0.0058 | +0.0000 | +0.0011 | 0/11/1 |
| execve_absent | entity_context | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| execve_absent | random_dropout | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| execve_absent | type_dropout | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| execve_absent | mixed_dropout | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| execve_absent | observed_router | 0.6095 | -0.0131 | -0.0256 | +0.0000 | 0/11/1 |
| proctitle_absent | semantic_event | 0.6055 | -0.0291 | +0.0000 | +0.0057 | 0/9/3 |
| proctitle_absent | entity_context | 0.6000 | -0.0346 | +0.0000 | +0.0068 | 0/9/3 |
| proctitle_absent | random_dropout | 0.6346 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| proctitle_absent | type_dropout | 0.6226 | -0.0120 | +0.0000 | +0.0023 | 0/11/1 |
| proctitle_absent | mixed_dropout | 0.6226 | -0.0120 | +0.0000 | +0.0023 | 0/11/1 |
| proctitle_absent | observed_router | 0.5926 | -0.0420 | -0.0256 | +0.0057 | 0/9/3 |
| syscall_absent | semantic_event | 0.6939 | +0.0204 | +0.0256 | -0.0011 | 2/10/0 |
| syscall_absent | entity_context | 0.6809 | +0.0074 | -0.0256 | -0.0034 | 2/9/1 |
| syscall_absent | random_dropout | 0.6735 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| syscall_absent | type_dropout | 0.6957 | +0.0222 | -0.0256 | -0.0057 | 3/8/1 |
| syscall_absent | mixed_dropout | 0.6809 | +0.0074 | -0.0256 | -0.0034 | 3/8/1 |
| syscall_absent | observed_router | 0.6813 | +0.0078 | -0.0513 | -0.0057 | 3/7/2 |
| path_absent | semantic_event | 0.6522 | +0.0295 | -0.0769 | -0.0125 | 3/7/2 |
| path_absent | entity_context | 0.6667 | +0.0440 | -0.0769 | -0.0148 | 4/6/2 |
| path_absent | random_dropout | 0.6226 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| path_absent | type_dropout | 0.6154 | -0.0073 | -0.0256 | -0.0011 | 1/10/1 |
| path_absent | mixed_dropout | 0.6095 | -0.0131 | -0.0256 | +0.0000 | 0/11/1 |
| path_absent | observed_router | 0.6598 | +0.0372 | -0.0256 | -0.0091 | 3/9/0 |

### Frozen calibration threshold

| Condition | Arm | F1 | F1 change | Recall change | Other-label flag-rate change | Positive-run F1 W/T/L |
|---|---|---:|---:|---:|---:|---:|
| clean | semantic_event | 0.6923 | -0.0256 | -0.0256 | +0.0011 | 1/9/2 |
| clean | entity_context | 0.7179 | +0.0000 | +0.0000 | +0.0000 | 1/10/1 |
| clean | random_dropout | 0.7179 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| clean | type_dropout | 0.7089 | -0.0091 | +0.0000 | +0.0011 | 0/11/1 |
| clean | mixed_dropout | 0.7179 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| clean | observed_router | 0.7013 | -0.0167 | -0.0256 | +0.0000 | 0/11/1 |
| random_25 | semantic_event | 0.6191 | -0.0400 | -0.0427 | +0.0019 | 0/4/8 |
| random_25 | entity_context | 0.6537 | -0.0054 | -0.0171 | -0.0008 | 3/4/5 |
| random_25 | random_dropout | 0.6591 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| random_25 | type_dropout | 0.6302 | -0.0289 | -0.0684 | -0.0023 | 2/2/8 |
| random_25 | mixed_dropout | 0.6616 | +0.0025 | -0.0256 | -0.0026 | 2/7/3 |
| random_25 | observed_router | 0.6610 | +0.0019 | -0.0855 | -0.0079 | 4/4/4 |
| random_50 | semantic_event | 0.5756 | -0.0376 | -0.0598 | -0.0008 | 4/3/5 |
| random_50 | entity_context | 0.5932 | -0.0199 | -0.0769 | -0.0053 | 6/2/4 |
| random_50 | random_dropout | 0.6131 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| random_50 | type_dropout | 0.5742 | -0.0389 | -0.1197 | -0.0072 | 3/2/7 |
| random_50 | mixed_dropout | 0.6413 | +0.0282 | -0.0085 | -0.0053 | 7/4/1 |
| random_50 | observed_router | 0.6073 | -0.0058 | -0.1111 | -0.0106 | 4/3/5 |
| random_75 | semantic_event | 0.4566 | -0.0311 | -0.0769 | -0.0061 | 3/5/4 |
| random_75 | entity_context | 0.4566 | -0.0311 | -0.0769 | -0.0061 | 3/5/4 |
| random_75 | random_dropout | 0.4877 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| random_75 | type_dropout | 0.4104 | -0.0773 | -0.1453 | -0.0095 | 3/3/6 |
| random_75 | mixed_dropout | 0.4705 | -0.0172 | -0.0855 | -0.0095 | 3/6/3 |
| random_75 | observed_router | 0.4591 | -0.0287 | -0.1026 | -0.0106 | 3/4/5 |
| support_burst_60 | semantic_event | 0.6923 | +0.0173 | +0.0000 | -0.0023 | 1/10/1 |
| support_burst_60 | entity_context | 0.6750 | +0.0000 | +0.0000 | +0.0000 | 1/10/1 |
| support_burst_60 | random_dropout | 0.6750 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| support_burst_60 | type_dropout | 0.6750 | +0.0000 | +0.0000 | +0.0000 | 1/10/1 |
| support_burst_60 | mixed_dropout | 0.6835 | +0.0085 | +0.0000 | -0.0011 | 1/11/0 |
| support_burst_60 | observed_router | 0.6835 | +0.0085 | +0.0000 | -0.0011 | 1/10/1 |
| command_records_absent | semantic_event | 0.6095 | -0.0905 | +0.1026 | +0.0238 | 3/4/5 |
| command_records_absent | entity_context | 0.6226 | -0.0774 | +0.1282 | +0.0238 | 3/4/5 |
| command_records_absent | random_dropout | 0.7000 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| command_records_absent | type_dropout | 0.7000 | +0.0000 | +0.0000 | +0.0000 | 1/10/1 |
| command_records_absent | mixed_dropout | 0.7059 | +0.0059 | +0.0513 | +0.0034 | 2/9/1 |
| command_records_absent | observed_router | 0.6829 | -0.0171 | +0.0000 | +0.0023 | 2/8/2 |
| delay_30_deadline_0 | semantic_event | 0.6095 | -0.0810 | +0.0769 | +0.0204 | 3/4/5 |
| delay_30_deadline_0 | entity_context | 0.6226 | -0.0678 | +0.1026 | +0.0204 | 4/4/4 |
| delay_30_deadline_0 | random_dropout | 0.6905 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_30_deadline_0 | type_dropout | 0.7089 | +0.0184 | -0.0256 | -0.0045 | 1/9/2 |
| delay_30_deadline_0 | mixed_dropout | 0.6977 | +0.0072 | +0.0256 | +0.0011 | 2/8/2 |
| delay_30_deadline_0 | observed_router | 0.6829 | -0.0075 | -0.0256 | -0.0011 | 1/8/3 |
| delay_30_deadline_30 | semantic_event | 0.6923 | -0.0256 | -0.0256 | +0.0011 | 1/9/2 |
| delay_30_deadline_30 | entity_context | 0.7179 | +0.0000 | +0.0000 | +0.0000 | 1/10/1 |
| delay_30_deadline_30 | random_dropout | 0.7179 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_30_deadline_30 | type_dropout | 0.7089 | -0.0091 | +0.0000 | +0.0011 | 0/11/1 |
| delay_30_deadline_30 | mixed_dropout | 0.7179 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_30_deadline_30 | observed_router | 0.7013 | -0.0167 | -0.0256 | +0.0000 | 0/11/1 |
| delay_120_deadline_0 | semantic_event | 0.6095 | -0.0905 | +0.1026 | +0.0238 | 3/4/5 |
| delay_120_deadline_0 | entity_context | 0.6226 | -0.0774 | +0.1282 | +0.0238 | 3/4/5 |
| delay_120_deadline_0 | random_dropout | 0.7000 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_120_deadline_0 | type_dropout | 0.7000 | +0.0000 | +0.0000 | +0.0000 | 1/10/1 |
| delay_120_deadline_0 | mixed_dropout | 0.7059 | +0.0059 | +0.0513 | +0.0034 | 2/9/1 |
| delay_120_deadline_0 | observed_router | 0.6829 | -0.0171 | +0.0000 | +0.0023 | 2/8/2 |
| delay_120_deadline_30 | semantic_event | 0.6095 | -0.0905 | +0.1026 | +0.0238 | 3/4/5 |
| delay_120_deadline_30 | entity_context | 0.6226 | -0.0774 | +0.1282 | +0.0238 | 3/4/5 |
| delay_120_deadline_30 | random_dropout | 0.7000 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_120_deadline_30 | type_dropout | 0.7000 | +0.0000 | +0.0000 | +0.0000 | 1/10/1 |
| delay_120_deadline_30 | mixed_dropout | 0.7059 | +0.0059 | +0.0513 | +0.0034 | 2/9/1 |
| delay_120_deadline_30 | observed_router | 0.6829 | -0.0171 | +0.0000 | +0.0023 | 2/8/2 |
| delay_120_deadline_120 | semantic_event | 0.6923 | -0.0256 | -0.0256 | +0.0011 | 1/9/2 |
| delay_120_deadline_120 | entity_context | 0.7179 | +0.0000 | +0.0000 | +0.0000 | 1/10/1 |
| delay_120_deadline_120 | random_dropout | 0.7179 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_120_deadline_120 | type_dropout | 0.7089 | -0.0091 | +0.0000 | +0.0011 | 0/11/1 |
| delay_120_deadline_120 | mixed_dropout | 0.7179 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| delay_120_deadline_120 | observed_router | 0.7013 | -0.0167 | -0.0256 | +0.0000 | 0/11/1 |
| execve_absent | semantic_event | 0.6275 | -0.0886 | +0.0769 | +0.0204 | 3/5/4 |
| execve_absent | entity_context | 0.6337 | -0.0824 | +0.0769 | +0.0193 | 3/4/5 |
| execve_absent | random_dropout | 0.7160 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| execve_absent | type_dropout | 0.7089 | -0.0072 | -0.0256 | -0.0011 | 1/9/2 |
| execve_absent | mixed_dropout | 0.7179 | +0.0019 | -0.0256 | -0.0023 | 1/10/1 |
| execve_absent | observed_router | 0.7013 | -0.0148 | -0.0513 | -0.0023 | 1/9/2 |
| proctitle_absent | semantic_event | 0.6598 | -0.0770 | +0.1026 | +0.0193 | 3/5/4 |
| proctitle_absent | entity_context | 0.6804 | -0.0564 | +0.1282 | +0.0182 | 3/5/4 |
| proctitle_absent | random_dropout | 0.7368 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| proctitle_absent | type_dropout | 0.7179 | -0.0189 | +0.0000 | +0.0023 | 0/11/1 |
| proctitle_absent | mixed_dropout | 0.7179 | -0.0189 | +0.0000 | +0.0023 | 0/11/1 |
| proctitle_absent | observed_router | 0.7000 | -0.0368 | +0.0000 | +0.0045 | 0/11/1 |
| syscall_absent | semantic_event | 0.7324 | +0.0102 | +0.0000 | -0.0011 | 1/10/1 |
| syscall_absent | entity_context | 0.7059 | -0.0163 | -0.0513 | -0.0023 | 1/9/2 |
| syscall_absent | random_dropout | 0.7222 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| syscall_absent | type_dropout | 0.6333 | -0.0889 | -0.1795 | -0.0057 | 0/9/3 |
| syscall_absent | mixed_dropout | 0.7222 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| syscall_absent | observed_router | 0.7077 | -0.0145 | -0.0769 | -0.0045 | 1/9/2 |
| path_absent | semantic_event | 0.7027 | +0.0627 | -0.1538 | -0.0227 | 3/5/4 |
| path_absent | entity_context | 0.7222 | +0.0822 | -0.1538 | -0.0250 | 5/3/4 |
| path_absent | random_dropout | 0.6400 | +0.0000 | +0.0000 | +0.0000 | 0/12/0 |
| path_absent | type_dropout | 0.7013 | +0.0613 | -0.1282 | -0.0204 | 3/5/4 |
| path_absent | mixed_dropout | 0.6897 | +0.0497 | -0.0513 | -0.0125 | 3/7/2 |
| path_absent | observed_router | 0.6842 | +0.0442 | -0.1538 | -0.0204 | 4/4/4 |

## T1105

Status: **COMPLETE**.

Positive-bearing runs: 8; excluded zero-positive runs: 10.

### Fixed score > 0.5

| Condition | Arm | F1 | F1 change | Recall change | Other-label flag-rate change | Positive-run F1 W/T/L |
|---|---|---:|---:|---:|---:|---:|
| clean | semantic_event | 0.7368 | +0.1535 | +0.0000 | -0.0111 | 1/6/1 |
| clean | entity_context | 0.5957 | +0.0124 | +0.0000 | -0.0011 | 1/6/1 |
| clean | random_dropout | 0.5833 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| clean | type_dropout | 0.5714 | -0.0119 | +0.0000 | +0.0011 | 0/7/1 |
| clean | mixed_dropout | 0.5833 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| clean | observed_router | 0.6829 | +0.0996 | +0.0000 | -0.0078 | 2/5/1 |
| random_25 | semantic_event | 0.3996 | -0.1475 | +0.0392 | +0.0236 | 2/1/5 |
| random_25 | entity_context | 0.5271 | -0.0201 | +0.0000 | +0.0022 | 2/2/4 |
| random_25 | random_dropout | 0.5471 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| random_25 | type_dropout | 0.4412 | -0.1060 | -0.0196 | +0.0122 | 1/1/6 |
| random_25 | mixed_dropout | 0.5468 | -0.0003 | +0.0000 | +0.0004 | 3/4/1 |
| random_25 | observed_router | 0.4823 | -0.0648 | -0.0196 | +0.0066 | 1/2/5 |
| random_50 | semantic_event | 0.2368 | -0.1626 | +0.0588 | +0.0609 | 0/1/7 |
| random_50 | entity_context | 0.3274 | -0.0719 | -0.0196 | +0.0148 | 1/1/6 |
| random_50 | random_dropout | 0.3993 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| random_50 | type_dropout | 0.2824 | -0.1170 | -0.0196 | +0.0295 | 1/1/6 |
| random_50 | mixed_dropout | 0.3649 | -0.0344 | -0.0392 | +0.0037 | 1/3/4 |
| random_50 | observed_router | 0.3504 | -0.0490 | -0.0392 | +0.0078 | 2/1/5 |
| random_75 | semantic_event | 0.1361 | -0.0818 | +0.0980 | +0.0890 | 1/1/6 |
| random_75 | entity_context | 0.1946 | -0.0233 | +0.0588 | +0.0229 | 2/1/5 |
| random_75 | random_dropout | 0.2179 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| random_75 | type_dropout | 0.1761 | -0.0417 | +0.0392 | +0.0325 | 1/2/5 |
| random_75 | mixed_dropout | 0.2084 | -0.0095 | +0.0000 | +0.0052 | 0/2/6 |
| random_75 | observed_router | 0.2070 | -0.0108 | +0.0000 | +0.0059 | 1/3/4 |
| support_burst_60 | semantic_event | 0.7368 | +0.2368 | +0.0000 | -0.0199 | 3/5/0 |
| support_burst_60 | entity_context | 0.5769 | +0.0769 | +0.0588 | -0.0055 | 5/3/0 |
| support_burst_60 | random_dropout | 0.5000 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| support_burst_60 | type_dropout | 0.4590 | -0.0410 | +0.0000 | +0.0055 | 0/6/2 |
| support_burst_60 | mixed_dropout | 0.4667 | -0.0333 | +0.0000 | +0.0044 | 1/4/3 |
| support_burst_60 | observed_router | 0.5833 | +0.0833 | +0.0000 | -0.0089 | 1/6/1 |
| command_records_absent | semantic_event | 0.2258 | +0.0667 | +0.0000 | -0.0576 | 7/1/0 |
| command_records_absent | entity_context | 0.3607 | +0.2016 | -0.1765 | -0.1240 | 6/1/1 |
| command_records_absent | random_dropout | 0.1591 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| command_records_absent | type_dropout | 0.1958 | +0.0367 | +0.0000 | -0.0365 | 6/2/0 |
| command_records_absent | mixed_dropout | 0.2121 | +0.0530 | +0.0000 | -0.0487 | 7/1/0 |
| command_records_absent | observed_router | 0.1657 | +0.0066 | +0.0000 | -0.0078 | 6/2/0 |
| delay_30_deadline_0 | semantic_event | 0.2258 | +0.0497 | +0.0000 | -0.0388 | 7/1/0 |
| delay_30_deadline_0 | entity_context | 0.3729 | +0.1968 | -0.1765 | -0.1074 | 6/1/1 |
| delay_30_deadline_0 | random_dropout | 0.1761 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_30_deadline_0 | type_dropout | 0.2188 | +0.0426 | +0.0000 | -0.0343 | 7/1/0 |
| delay_30_deadline_0 | mixed_dropout | 0.2205 | +0.0444 | +0.0000 | -0.0354 | 7/1/0 |
| delay_30_deadline_0 | observed_router | 0.1591 | -0.0170 | +0.0000 | +0.0188 | 3/3/2 |
| delay_30_deadline_30 | semantic_event | 0.7368 | +0.1535 | +0.0000 | -0.0111 | 1/6/1 |
| delay_30_deadline_30 | entity_context | 0.5957 | +0.0124 | +0.0000 | -0.0011 | 1/6/1 |
| delay_30_deadline_30 | random_dropout | 0.5833 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_30_deadline_30 | type_dropout | 0.5714 | -0.0119 | +0.0000 | +0.0011 | 0/7/1 |
| delay_30_deadline_30 | mixed_dropout | 0.5833 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_30_deadline_30 | observed_router | 0.6829 | +0.0996 | +0.0000 | -0.0078 | 2/5/1 |
| delay_120_deadline_0 | semantic_event | 0.2258 | +0.0667 | +0.0000 | -0.0576 | 7/1/0 |
| delay_120_deadline_0 | entity_context | 0.3607 | +0.2016 | -0.1765 | -0.1240 | 6/1/1 |
| delay_120_deadline_0 | random_dropout | 0.1591 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_120_deadline_0 | type_dropout | 0.1958 | +0.0367 | +0.0000 | -0.0365 | 6/2/0 |
| delay_120_deadline_0 | mixed_dropout | 0.2121 | +0.0530 | +0.0000 | -0.0487 | 7/1/0 |
| delay_120_deadline_0 | observed_router | 0.1657 | +0.0066 | +0.0000 | -0.0078 | 6/2/0 |
| delay_120_deadline_30 | semantic_event | 0.2258 | +0.0649 | +0.0000 | -0.0554 | 7/1/0 |
| delay_120_deadline_30 | entity_context | 0.3607 | +0.1997 | -0.1765 | -0.1218 | 6/1/1 |
| delay_120_deadline_30 | random_dropout | 0.1609 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_120_deadline_30 | type_dropout | 0.1944 | +0.0335 | +0.0000 | -0.0332 | 6/2/0 |
| delay_120_deadline_30 | mixed_dropout | 0.2105 | +0.0496 | +0.0000 | -0.0454 | 7/1/0 |
| delay_120_deadline_30 | observed_router | 0.1647 | +0.0038 | +0.0000 | -0.0044 | 6/2/0 |
| delay_120_deadline_120 | semantic_event | 0.7368 | +0.1535 | +0.0000 | -0.0111 | 1/6/1 |
| delay_120_deadline_120 | entity_context | 0.5957 | +0.0124 | +0.0000 | -0.0011 | 1/6/1 |
| delay_120_deadline_120 | random_dropout | 0.5833 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_120_deadline_120 | type_dropout | 0.5714 | -0.0119 | +0.0000 | +0.0011 | 0/7/1 |
| delay_120_deadline_120 | mixed_dropout | 0.5833 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_120_deadline_120 | observed_router | 0.6829 | +0.0996 | +0.0000 | -0.0078 | 2/5/1 |
| execve_absent | semantic_event | 0.3226 | -0.1602 | +0.0588 | +0.0377 | 1/3/4 |
| execve_absent | entity_context | 0.3704 | -0.1124 | +0.0588 | +0.0244 | 0/2/6 |
| execve_absent | random_dropout | 0.4828 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| execve_absent | type_dropout | 0.4912 | +0.0085 | +0.0000 | -0.0011 | 2/5/1 |
| execve_absent | mixed_dropout | 0.5091 | +0.0263 | +0.0000 | -0.0033 | 2/5/1 |
| execve_absent | observed_router | 0.5091 | +0.0263 | +0.0000 | -0.0033 | 2/6/0 |
| proctitle_absent | semantic_event | 0.7778 | +0.4685 | -0.0588 | -0.0664 | 7/1/0 |
| proctitle_absent | entity_context | 0.7179 | +0.4087 | -0.0588 | -0.0631 | 7/1/0 |
| proctitle_absent | random_dropout | 0.3093 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| proctitle_absent | type_dropout | 0.3836 | +0.0743 | -0.0588 | -0.0255 | 6/1/1 |
| proctitle_absent | mixed_dropout | 0.3784 | +0.0691 | -0.0588 | -0.0244 | 4/3/1 |
| proctitle_absent | observed_router | 0.3333 | +0.0241 | -0.1176 | -0.0188 | 3/3/2 |
| syscall_absent | semantic_event | 0.3636 | -0.4848 | +0.1176 | +0.0587 | 0/1/7 |
| syscall_absent | entity_context | 0.6522 | -0.1963 | +0.0588 | +0.0133 | 1/4/3 |
| syscall_absent | random_dropout | 0.8485 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| syscall_absent | type_dropout | 0.7778 | -0.0707 | +0.0000 | +0.0033 | 0/7/1 |
| syscall_absent | mixed_dropout | 0.8000 | -0.0485 | +0.0000 | +0.0022 | 0/7/1 |
| syscall_absent | observed_router | 0.8485 | +0.0000 | +0.0000 | +0.0000 | 1/7/0 |
| path_absent | semantic_event | 0.7692 | +0.1810 | +0.0000 | -0.0133 | 4/4/0 |
| path_absent | entity_context | 0.5926 | +0.0044 | +0.0588 | +0.0022 | 2/4/2 |
| path_absent | random_dropout | 0.5882 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| path_absent | type_dropout | 0.2885 | -0.2998 | +0.0000 | +0.0587 | 0/2/6 |
| path_absent | mixed_dropout | 0.4918 | -0.0964 | +0.0000 | +0.0111 | 0/4/4 |
| path_absent | observed_router | 0.7000 | +0.1118 | -0.0588 | -0.0111 | 2/5/1 |

### Frozen calibration threshold

| Condition | Arm | F1 | F1 change | Recall change | Other-label flag-rate change | Positive-run F1 W/T/L |
|---|---|---:|---:|---:|---:|---:|
| clean | semantic_event | 0.7568 | +0.0901 | +0.0000 | -0.0055 | 2/5/1 |
| clean | entity_context | 0.7000 | +0.0333 | +0.0000 | -0.0022 | 1/7/0 |
| clean | random_dropout | 0.6667 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| clean | type_dropout | 0.6364 | -0.0303 | +0.0000 | +0.0022 | 0/7/1 |
| clean | mixed_dropout | 0.6364 | -0.0303 | +0.0000 | +0.0022 | 0/7/1 |
| clean | observed_router | 0.7179 | +0.0513 | +0.0000 | -0.0033 | 2/5/1 |
| random_25 | semantic_event | 0.4359 | -0.2037 | +0.0588 | +0.0258 | 2/1/5 |
| random_25 | entity_context | 0.5576 | -0.0820 | +0.0000 | +0.0070 | 2/2/4 |
| random_25 | random_dropout | 0.6396 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| random_25 | type_dropout | 0.5675 | -0.0721 | -0.0196 | +0.0048 | 1/3/4 |
| random_25 | mixed_dropout | 0.6264 | -0.0132 | +0.0000 | +0.0007 | 1/4/3 |
| random_25 | observed_router | 0.5633 | -0.0763 | +0.0000 | +0.0063 | 1/3/4 |
| random_50 | semantic_event | 0.2564 | -0.2610 | +0.0784 | +0.0676 | 0/1/7 |
| random_50 | entity_context | 0.3489 | -0.1684 | +0.0196 | +0.0292 | 1/1/6 |
| random_50 | random_dropout | 0.5173 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| random_50 | type_dropout | 0.3576 | -0.1597 | -0.0392 | +0.0218 | 1/1/6 |
| random_50 | mixed_dropout | 0.4489 | -0.0685 | +0.0000 | +0.0089 | 1/3/4 |
| random_50 | observed_router | 0.3615 | -0.1559 | -0.0196 | +0.0233 | 1/1/6 |
| random_75 | semantic_event | 0.1587 | -0.1703 | +0.0980 | +0.0989 | 0/1/7 |
| random_75 | entity_context | 0.2005 | -0.1285 | +0.0588 | +0.0554 | 0/1/7 |
| random_75 | random_dropout | 0.3290 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| random_75 | type_dropout | 0.2012 | -0.1278 | -0.0196 | +0.0425 | 0/1/7 |
| random_75 | mixed_dropout | 0.2951 | -0.0339 | +0.0000 | +0.0081 | 2/2/4 |
| random_75 | observed_router | 0.2182 | -0.1108 | +0.0000 | +0.0369 | 0/1/7 |
| support_burst_60 | semantic_event | 0.7568 | +0.1734 | +0.0000 | -0.0122 | 3/4/1 |
| support_burst_60 | entity_context | 0.6250 | +0.0417 | +0.0588 | -0.0011 | 3/5/0 |
| support_burst_60 | random_dropout | 0.5833 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| support_burst_60 | type_dropout | 0.5283 | -0.0550 | +0.0000 | +0.0055 | 0/5/3 |
| support_burst_60 | mixed_dropout | 0.5600 | -0.0233 | +0.0000 | +0.0022 | 0/6/2 |
| support_burst_60 | observed_router | 0.6364 | +0.0530 | +0.0000 | -0.0044 | 2/5/1 |
| command_records_absent | semantic_event | 0.4138 | +0.1935 | -0.0588 | -0.0653 | 6/1/1 |
| command_records_absent | entity_context | 0.4231 | +0.2027 | -0.1176 | -0.0709 | 6/1/1 |
| command_records_absent | random_dropout | 0.2203 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| command_records_absent | type_dropout | 0.2955 | +0.0751 | +0.0000 | -0.0332 | 5/2/1 |
| command_records_absent | mixed_dropout | 0.2766 | +0.0563 | +0.0000 | -0.0266 | 5/2/1 |
| command_records_absent | observed_router | 0.2029 | -0.0174 | +0.0588 | +0.0210 | 2/3/3 |
| delay_30_deadline_0 | semantic_event | 0.4138 | +0.1708 | -0.0588 | -0.0532 | 6/1/1 |
| delay_30_deadline_0 | entity_context | 0.4314 | +0.1884 | -0.1176 | -0.0598 | 6/1/1 |
| delay_30_deadline_0 | random_dropout | 0.2430 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_30_deadline_0 | type_dropout | 0.3059 | +0.0629 | +0.0000 | -0.0244 | 4/2/2 |
| delay_30_deadline_0 | mixed_dropout | 0.2826 | +0.0396 | +0.0000 | -0.0166 | 4/2/2 |
| delay_30_deadline_0 | observed_router | 0.1986 | -0.0444 | +0.0588 | +0.0365 | 1/1/6 |
| delay_30_deadline_30 | semantic_event | 0.7568 | +0.0901 | +0.0000 | -0.0055 | 2/5/1 |
| delay_30_deadline_30 | entity_context | 0.7000 | +0.0333 | +0.0000 | -0.0022 | 1/7/0 |
| delay_30_deadline_30 | random_dropout | 0.6667 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_30_deadline_30 | type_dropout | 0.6364 | -0.0303 | +0.0000 | +0.0022 | 0/7/1 |
| delay_30_deadline_30 | mixed_dropout | 0.6364 | -0.0303 | +0.0000 | +0.0022 | 0/7/1 |
| delay_30_deadline_30 | observed_router | 0.7179 | +0.0513 | +0.0000 | -0.0033 | 2/5/1 |
| delay_120_deadline_0 | semantic_event | 0.4138 | +0.1935 | -0.0588 | -0.0653 | 6/1/1 |
| delay_120_deadline_0 | entity_context | 0.4231 | +0.2027 | -0.1176 | -0.0709 | 6/1/1 |
| delay_120_deadline_0 | random_dropout | 0.2203 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_120_deadline_0 | type_dropout | 0.2955 | +0.0751 | +0.0000 | -0.0332 | 5/2/1 |
| delay_120_deadline_0 | mixed_dropout | 0.2766 | +0.0563 | +0.0000 | -0.0266 | 5/2/1 |
| delay_120_deadline_0 | observed_router | 0.2029 | -0.0174 | +0.0588 | +0.0210 | 2/3/3 |
| delay_120_deadline_30 | semantic_event | 0.4138 | +0.1916 | -0.0588 | -0.0642 | 6/1/1 |
| delay_120_deadline_30 | entity_context | 0.4231 | +0.2009 | -0.1176 | -0.0698 | 6/1/1 |
| delay_120_deadline_30 | random_dropout | 0.2222 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_120_deadline_30 | type_dropout | 0.2955 | +0.0732 | +0.0000 | -0.0321 | 4/3/1 |
| delay_120_deadline_30 | mixed_dropout | 0.2766 | +0.0544 | +0.0000 | -0.0255 | 4/3/1 |
| delay_120_deadline_30 | observed_router | 0.2029 | -0.0193 | +0.0588 | +0.0221 | 1/4/3 |
| delay_120_deadline_120 | semantic_event | 0.7568 | +0.0901 | +0.0000 | -0.0055 | 2/5/1 |
| delay_120_deadline_120 | entity_context | 0.7000 | +0.0333 | +0.0000 | -0.0022 | 1/7/0 |
| delay_120_deadline_120 | random_dropout | 0.6667 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| delay_120_deadline_120 | type_dropout | 0.6364 | -0.0303 | +0.0000 | +0.0022 | 0/7/1 |
| delay_120_deadline_120 | mixed_dropout | 0.6364 | -0.0303 | +0.0000 | +0.0022 | 0/7/1 |
| delay_120_deadline_120 | observed_router | 0.7179 | +0.0513 | +0.0000 | -0.0033 | 2/5/1 |
| execve_absent | semantic_event | 0.3659 | -0.2428 | +0.0588 | +0.0388 | 0/3/5 |
| execve_absent | entity_context | 0.4545 | -0.1542 | +0.0588 | +0.0210 | 0/2/6 |
| execve_absent | random_dropout | 0.6087 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| execve_absent | type_dropout | 0.5490 | -0.0597 | +0.0000 | +0.0055 | 0/5/3 |
| execve_absent | mixed_dropout | 0.5600 | -0.0487 | +0.0000 | +0.0044 | 0/6/2 |
| execve_absent | observed_router | 0.6087 | +0.0000 | +0.0000 | +0.0000 | 0/7/1 |
| proctitle_absent | semantic_event | 0.7778 | +0.3778 | +0.0000 | -0.0377 | 6/2/0 |
| proctitle_absent | entity_context | 0.7778 | +0.3778 | +0.0000 | -0.0377 | 6/2/0 |
| proctitle_absent | random_dropout | 0.4000 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| proctitle_absent | type_dropout | 0.4746 | +0.0746 | +0.0000 | -0.0122 | 4/4/0 |
| proctitle_absent | mixed_dropout | 0.4912 | +0.0912 | +0.0000 | -0.0144 | 5/3/0 |
| proctitle_absent | observed_router | 0.3714 | -0.0286 | -0.0588 | +0.0011 | 2/2/4 |
| syscall_absent | semantic_event | 0.4267 | -0.4483 | +0.1176 | +0.0454 | 0/1/7 |
| syscall_absent | entity_context | 0.6667 | -0.2083 | +0.0588 | +0.0133 | 0/4/4 |
| syscall_absent | random_dropout | 0.8750 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| syscall_absent | type_dropout | 0.8235 | -0.0515 | +0.0000 | +0.0022 | 0/7/1 |
| syscall_absent | mixed_dropout | 0.8750 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| syscall_absent | observed_router | 0.8485 | -0.0265 | +0.0000 | +0.0011 | 0/8/0 |
| path_absent | semantic_event | 0.7895 | +0.1228 | +0.0000 | -0.0078 | 1/7/0 |
| path_absent | entity_context | 0.6000 | -0.0667 | +0.0000 | +0.0055 | 0/6/2 |
| path_absent | random_dropout | 0.6667 | +0.0000 | +0.0000 | +0.0000 | 0/8/0 |
| path_absent | type_dropout | 0.4412 | -0.2255 | +0.0000 | +0.0255 | 0/4/4 |
| path_absent | mixed_dropout | 0.5882 | -0.0784 | +0.0000 | +0.0066 | 0/5/3 |
| path_absent | observed_router | 0.7568 | +0.0901 | -0.0588 | -0.0078 | 1/5/2 |

## Limits

- Pooled means average the fixed corruption seeds; masks are not independent attacks or independently fitted models.
- Undefined class-dependent metrics stay null; averages require all seed values to be defined.
- Other-label flag rates do not measure independently verified benign false alarms.
- Higher F1 may reflect fewer false flags or different recall. Primary gates and both operating points must remain visible.
- This report performs no fitting or inference and publishes no prediction arrays. It does not establish novelty or deployment guarantees.
