# camlds: structured-loss comparisons

All changes compare against random-record-dropout training. Both operating points remain separate; each arm retains its frozen clean-calibration threshold.

Baseline replication: **NOT_REQUESTED**.

Each positive-bearing test run supplies one win/tie/loss vote after averaging matched corruption seeds. Runs with no positive examples are excluded from these votes; their negatives remain in pooled metrics. These votes are descriptive, not independent significance tests.

## T1105

Status: **COMPLETE**.

Positive-bearing runs: 18; excluded zero-positive runs: 0.

### Fixed score > 0.5

| Condition | Arm | F1 | F1 change | Recall change | Other-label flag-rate change | Positive-run F1 W/T/L |
|---|---|---:|---:|---:|---:|---:|
| clean | semantic_event | 0.0495 | -0.0003 | +0.1200 | +0.1190 | 7/1/10 |
| clean | entity_context | 0.0534 | +0.0036 | +0.1300 | +0.0652 | 8/0/10 |
| clean | random_dropout | 0.0498 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| clean | type_dropout | 0.0520 | +0.0022 | +0.1300 | +0.0871 | 8/0/10 |
| clean | mixed_dropout | 0.0527 | +0.0030 | +0.1000 | +0.0482 | 7/0/11 |
| clean | observed_router | 0.0529 | +0.0032 | +0.1000 | +0.0453 | 8/1/9 |
| random_25 | semantic_event | 0.0454 | -0.0041 | -0.1967 | -0.1449 | 7/0/11 |
| random_25 | entity_context | 0.0468 | -0.0027 | -0.0733 | -0.0351 | 6/0/12 |
| random_25 | random_dropout | 0.0495 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| random_25 | type_dropout | 0.0509 | +0.0014 | +0.0567 | +0.0336 | 10/0/8 |
| random_25 | mixed_dropout | 0.0515 | +0.0019 | +0.1200 | +0.0849 | 11/0/7 |
| random_25 | observed_router | 0.0486 | -0.0009 | +0.0533 | +0.0647 | 7/0/11 |
| random_50 | semantic_event | 0.0452 | -0.0045 | -0.4267 | -0.3804 | 8/0/10 |
| random_50 | entity_context | 0.0469 | -0.0028 | -0.1967 | -0.1588 | 5/0/13 |
| random_50 | random_dropout | 0.0497 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| random_50 | type_dropout | 0.0502 | +0.0005 | -0.1233 | -0.1231 | 8/0/10 |
| random_50 | mixed_dropout | 0.0491 | -0.0006 | +0.0033 | +0.0118 | 7/0/11 |
| random_50 | observed_router | 0.0489 | -0.0007 | -0.0367 | -0.0253 | 8/0/10 |
| random_75 | semantic_event | 0.0493 | +0.0030 | -0.3367 | -0.3555 | 8/0/10 |
| random_75 | entity_context | 0.0446 | -0.0017 | -0.1633 | -0.1546 | 8/0/10 |
| random_75 | random_dropout | 0.0463 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| random_75 | type_dropout | 0.0411 | -0.0052 | -0.1900 | -0.1557 | 6/0/12 |
| random_75 | mixed_dropout | 0.0467 | +0.0004 | -0.0033 | -0.0081 | 14/0/4 |
| random_75 | observed_router | 0.0430 | -0.0033 | -0.0867 | -0.0572 | 6/0/12 |
| support_burst_60 | semantic_event | 0.0495 | +0.0008 | -0.0200 | -0.0343 | 9/2/7 |
| support_burst_60 | entity_context | 0.0490 | +0.0003 | +0.0600 | +0.0523 | 5/0/13 |
| support_burst_60 | random_dropout | 0.0486 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| support_burst_60 | type_dropout | 0.0479 | -0.0007 | +0.0500 | +0.0633 | 4/0/14 |
| support_burst_60 | mixed_dropout | 0.0488 | +0.0001 | +0.0200 | +0.0173 | 2/1/15 |
| support_burst_60 | observed_router | 0.0495 | +0.0008 | +0.0700 | +0.0523 | 6/0/12 |
| command_records_absent | semantic_event | 0.0000 | -0.0503 | -0.7600 | -0.6917 | 0/1/17 |
| command_records_absent | entity_context | 0.0384 | -0.0119 | -0.6100 | -0.5301 | 4/1/13 |
| command_records_absent | random_dropout | 0.0503 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| command_records_absent | type_dropout | 0.0530 | +0.0027 | +0.0800 | +0.0338 | 6/1/11 |
| command_records_absent | mixed_dropout | 0.0532 | +0.0028 | +0.0800 | +0.0321 | 7/0/11 |
| command_records_absent | observed_router | 0.0521 | +0.0018 | +0.1200 | +0.0837 | 9/1/8 |
| delay_30_deadline_0 | semantic_event | 0.0000 | -0.0573 | -0.4500 | -0.3466 | 0/0/18 |
| delay_30_deadline_0 | entity_context | 0.0319 | -0.0254 | -0.4100 | -0.3113 | 3/0/15 |
| delay_30_deadline_0 | random_dropout | 0.0573 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| delay_30_deadline_0 | type_dropout | 0.0522 | -0.0050 | +0.4400 | +0.4361 | 7/0/11 |
| delay_30_deadline_0 | mixed_dropout | 0.0518 | -0.0055 | +0.3400 | +0.3514 | 7/0/11 |
| delay_30_deadline_0 | observed_router | 0.0498 | -0.0075 | +0.4000 | +0.4385 | 6/0/12 |
| delay_30_deadline_30 | semantic_event | 0.0495 | -0.0003 | +0.1200 | +0.1190 | 7/1/10 |
| delay_30_deadline_30 | entity_context | 0.0534 | +0.0036 | +0.1300 | +0.0652 | 8/0/10 |
| delay_30_deadline_30 | random_dropout | 0.0498 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| delay_30_deadline_30 | type_dropout | 0.0520 | +0.0022 | +0.1300 | +0.0871 | 8/0/10 |
| delay_30_deadline_30 | mixed_dropout | 0.0527 | +0.0030 | +0.1000 | +0.0482 | 7/0/11 |
| delay_30_deadline_30 | observed_router | 0.0529 | +0.0032 | +0.1000 | +0.0453 | 8/1/9 |
| delay_120_deadline_0 | semantic_event | 0.0000 | -0.0503 | -0.7600 | -0.6917 | 0/1/17 |
| delay_120_deadline_0 | entity_context | 0.0384 | -0.0119 | -0.6100 | -0.5301 | 4/1/13 |
| delay_120_deadline_0 | random_dropout | 0.0503 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| delay_120_deadline_0 | type_dropout | 0.0530 | +0.0027 | +0.0800 | +0.0338 | 6/1/11 |
| delay_120_deadline_0 | mixed_dropout | 0.0532 | +0.0028 | +0.0800 | +0.0321 | 7/0/11 |
| delay_120_deadline_0 | observed_router | 0.0521 | +0.0018 | +0.1200 | +0.0837 | 9/1/8 |
| delay_120_deadline_30 | semantic_event | 0.0000 | -0.0510 | -0.7800 | -0.7011 | 0/0/18 |
| delay_120_deadline_30 | entity_context | 0.0331 | -0.0179 | -0.7000 | -0.6101 | 4/0/14 |
| delay_120_deadline_30 | random_dropout | 0.0510 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| delay_120_deadline_30 | type_dropout | 0.0531 | +0.0021 | +0.0800 | +0.0419 | 8/0/10 |
| delay_120_deadline_30 | mixed_dropout | 0.0529 | +0.0020 | +0.0800 | +0.0438 | 7/0/11 |
| delay_120_deadline_30 | observed_router | 0.0515 | +0.0005 | +0.1000 | +0.0847 | 9/0/9 |
| delay_120_deadline_120 | semantic_event | 0.0495 | -0.0003 | +0.1200 | +0.1190 | 7/1/10 |
| delay_120_deadline_120 | entity_context | 0.0534 | +0.0036 | +0.1300 | +0.0652 | 8/0/10 |
| delay_120_deadline_120 | random_dropout | 0.0498 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| delay_120_deadline_120 | type_dropout | 0.0520 | +0.0022 | +0.1300 | +0.0871 | 8/0/10 |
| delay_120_deadline_120 | mixed_dropout | 0.0527 | +0.0030 | +0.1000 | +0.0482 | 7/0/11 |
| delay_120_deadline_120 | observed_router | 0.0529 | +0.0032 | +0.1000 | +0.0453 | 8/1/9 |
| execve_absent | semantic_event | 0.0478 | -0.0052 | +0.0100 | +0.0927 | 6/1/11 |
| execve_absent | entity_context | 0.0514 | -0.0017 | -0.0900 | -0.0582 | 10/1/7 |
| execve_absent | random_dropout | 0.0531 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| execve_absent | type_dropout | 0.0524 | -0.0007 | +0.0300 | +0.0370 | 3/0/15 |
| execve_absent | mixed_dropout | 0.0525 | -0.0006 | +0.0200 | +0.0260 | 2/1/15 |
| execve_absent | observed_router | 0.0504 | -0.0027 | -0.0400 | +0.0029 | 6/2/10 |
| proctitle_absent | semantic_event | 0.0075 | -0.0396 | -0.6600 | -0.6113 | 1/1/16 |
| proctitle_absent | entity_context | 0.0406 | -0.0065 | -0.4500 | -0.4174 | 6/1/11 |
| proctitle_absent | random_dropout | 0.0471 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| proctitle_absent | type_dropout | 0.0530 | +0.0059 | +0.2000 | +0.1020 | 12/0/6 |
| proctitle_absent | mixed_dropout | 0.0515 | +0.0044 | +0.1800 | +0.1068 | 12/0/6 |
| proctitle_absent | observed_router | 0.0518 | +0.0047 | +0.1700 | +0.0927 | 11/1/6 |
| syscall_absent | semantic_event | 0.0404 | -0.0098 | -0.7400 | -0.6780 | 7/0/11 |
| syscall_absent | entity_context | 0.0445 | -0.0057 | -0.3000 | -0.2171 | 4/0/14 |
| syscall_absent | random_dropout | 0.0502 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| syscall_absent | type_dropout | 0.0497 | -0.0005 | -0.3300 | -0.3064 | 7/0/11 |
| syscall_absent | mixed_dropout | 0.0510 | +0.0007 | +0.0200 | +0.0071 | 5/2/11 |
| syscall_absent | observed_router | 0.0483 | -0.0019 | -0.0600 | -0.0268 | 7/0/11 |
| path_absent | semantic_event | 0.0494 | +0.0009 | +0.2800 | +0.2565 | 8/0/10 |
| path_absent | entity_context | 0.0506 | +0.0021 | +0.2600 | +0.2159 | 12/0/6 |
| path_absent | random_dropout | 0.0485 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| path_absent | type_dropout | 0.0508 | +0.0023 | +0.2500 | +0.2027 | 11/0/7 |
| path_absent | mixed_dropout | 0.0499 | +0.0015 | +0.0800 | +0.0560 | 7/0/11 |
| path_absent | observed_router | 0.0496 | +0.0011 | +0.0900 | +0.0703 | 7/1/10 |

### Frozen calibration threshold

| Condition | Arm | F1 | F1 change | Recall change | Other-label flag-rate change | Positive-run F1 W/T/L |
|---|---|---:|---:|---:|---:|---:|
| clean | semantic_event | 0.0000 | +0.0000 | +0.0000 | -0.0032 | 0/18/0 |
| clean | entity_context | 0.0141 | +0.0141 | +0.0100 | +0.0063 | 1/17/0 |
| clean | random_dropout | 0.0000 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| clean | type_dropout | 0.0147 | +0.0147 | +0.0100 | +0.0049 | 1/17/0 |
| clean | mixed_dropout | 0.0000 | +0.0000 | +0.0000 | +0.0002 | 0/18/0 |
| clean | observed_router | 0.0252 | +0.0252 | +0.0200 | +0.0102 | 2/16/0 |
| random_25 | semantic_event | 0.0051 | -0.0049 | -0.0033 | -0.0011 | 0/17/1 |
| random_25 | entity_context | 0.0137 | +0.0037 | +0.0067 | +0.0134 | 2/15/1 |
| random_25 | random_dropout | 0.0100 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| random_25 | type_dropout | 0.0191 | +0.0091 | +0.0100 | +0.0096 | 2/15/1 |
| random_25 | mixed_dropout | 0.0101 | +0.0000 | +0.0000 | -0.0002 | 0/18/0 |
| random_25 | observed_router | 0.0354 | +0.0254 | +0.0933 | +0.1029 | 13/4/1 |
| random_50 | semantic_event | 0.0052 | +0.0002 | +0.0000 | -0.0012 | 0/18/0 |
| random_50 | entity_context | 0.0334 | +0.0285 | +0.0433 | +0.0350 | 6/11/1 |
| random_50 | random_dropout | 0.0050 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| random_50 | type_dropout | 0.0379 | +0.0329 | +0.0400 | +0.0225 | 9/9/0 |
| random_50 | mixed_dropout | 0.0144 | +0.0094 | +0.0067 | +0.0012 | 2/16/0 |
| random_50 | observed_router | 0.0380 | +0.0331 | +0.1467 | +0.1565 | 14/3/1 |
| random_75 | semantic_event | 0.0000 | -0.0048 | -0.0033 | -0.0085 | 0/17/1 |
| random_75 | entity_context | 0.0235 | +0.0188 | +0.0300 | +0.0341 | 6/11/1 |
| random_75 | random_dropout | 0.0048 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| random_75 | type_dropout | 0.0279 | +0.0231 | +0.0500 | +0.0569 | 9/8/1 |
| random_75 | mixed_dropout | 0.0086 | +0.0038 | +0.0033 | +0.0038 | 2/15/1 |
| random_75 | observed_router | 0.0371 | +0.0323 | +0.1567 | +0.1713 | 14/3/1 |
| support_burst_60 | semantic_event | 0.0000 | -0.0105 | -0.0100 | -0.0214 | 0/17/1 |
| support_burst_60 | entity_context | 0.0429 | +0.0324 | +0.4500 | +0.4646 | 15/2/1 |
| support_burst_60 | random_dropout | 0.0105 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| support_burst_60 | type_dropout | 0.0451 | +0.0346 | +0.4700 | +0.4605 | 15/2/1 |
| support_burst_60 | mixed_dropout | 0.0078 | -0.0027 | +0.0000 | +0.0158 | 0/17/1 |
| support_burst_60 | observed_router | 0.0450 | +0.0345 | +0.4800 | +0.4719 | 15/2/1 |
| command_records_absent | semantic_event | 0.0000 | -0.0111 | -0.0100 | -0.0192 | 0/17/1 |
| command_records_absent | entity_context | 0.0000 | -0.0111 | -0.0100 | -0.0192 | 0/17/1 |
| command_records_absent | random_dropout | 0.0111 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| command_records_absent | type_dropout | 0.0000 | -0.0111 | -0.0100 | -0.0165 | 0/17/1 |
| command_records_absent | mixed_dropout | 0.0142 | +0.0031 | +0.0000 | -0.0095 | 1/17/0 |
| command_records_absent | observed_router | 0.0074 | -0.0037 | +0.0000 | +0.0217 | 0/17/1 |
| delay_30_deadline_0 | semantic_event | 0.0000 | -0.0082 | -0.0100 | -0.0350 | 0/17/1 |
| delay_30_deadline_0 | entity_context | 0.0000 | -0.0082 | -0.0100 | -0.0348 | 0/17/1 |
| delay_30_deadline_0 | random_dropout | 0.0082 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| delay_30_deadline_0 | type_dropout | 0.0143 | +0.0061 | +0.0000 | -0.0256 | 1/17/0 |
| delay_30_deadline_0 | mixed_dropout | 0.0096 | +0.0015 | +0.0000 | -0.0090 | 1/17/0 |
| delay_30_deadline_0 | observed_router | 0.0143 | +0.0061 | +0.0200 | +0.0423 | 2/15/1 |
| delay_30_deadline_30 | semantic_event | 0.0000 | +0.0000 | +0.0000 | -0.0032 | 0/18/0 |
| delay_30_deadline_30 | entity_context | 0.0141 | +0.0141 | +0.0100 | +0.0063 | 1/17/0 |
| delay_30_deadline_30 | random_dropout | 0.0000 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| delay_30_deadline_30 | type_dropout | 0.0147 | +0.0147 | +0.0100 | +0.0049 | 1/17/0 |
| delay_30_deadline_30 | mixed_dropout | 0.0000 | +0.0000 | +0.0000 | +0.0002 | 0/18/0 |
| delay_30_deadline_30 | observed_router | 0.0252 | +0.0252 | +0.0200 | +0.0102 | 2/16/0 |
| delay_120_deadline_0 | semantic_event | 0.0000 | -0.0111 | -0.0100 | -0.0192 | 0/17/1 |
| delay_120_deadline_0 | entity_context | 0.0000 | -0.0111 | -0.0100 | -0.0192 | 0/17/1 |
| delay_120_deadline_0 | random_dropout | 0.0111 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| delay_120_deadline_0 | type_dropout | 0.0000 | -0.0111 | -0.0100 | -0.0165 | 0/17/1 |
| delay_120_deadline_0 | mixed_dropout | 0.0142 | +0.0031 | +0.0000 | -0.0095 | 1/17/0 |
| delay_120_deadline_0 | observed_router | 0.0074 | -0.0037 | +0.0000 | +0.0217 | 0/17/1 |
| delay_120_deadline_30 | semantic_event | 0.0000 | -0.0106 | -0.0100 | -0.0214 | 0/17/1 |
| delay_120_deadline_30 | entity_context | 0.0000 | -0.0106 | -0.0100 | -0.0214 | 0/17/1 |
| delay_120_deadline_30 | random_dropout | 0.0106 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| delay_120_deadline_30 | type_dropout | 0.0000 | -0.0106 | -0.0100 | -0.0180 | 0/17/1 |
| delay_120_deadline_30 | mixed_dropout | 0.0117 | +0.0011 | +0.0000 | -0.0044 | 1/17/0 |
| delay_120_deadline_30 | observed_router | 0.0137 | +0.0031 | +0.0100 | +0.0248 | 1/16/1 |
| delay_120_deadline_120 | semantic_event | 0.0000 | +0.0000 | +0.0000 | -0.0032 | 0/18/0 |
| delay_120_deadline_120 | entity_context | 0.0141 | +0.0141 | +0.0100 | +0.0063 | 1/17/0 |
| delay_120_deadline_120 | random_dropout | 0.0000 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| delay_120_deadline_120 | type_dropout | 0.0147 | +0.0147 | +0.0100 | +0.0049 | 1/17/0 |
| delay_120_deadline_120 | mixed_dropout | 0.0000 | +0.0000 | +0.0000 | +0.0002 | 0/18/0 |
| delay_120_deadline_120 | observed_router | 0.0252 | +0.0252 | +0.0200 | +0.0102 | 2/16/0 |
| execve_absent | semantic_event | 0.0000 | -0.0078 | -0.0100 | -0.0372 | 0/17/1 |
| execve_absent | entity_context | 0.0000 | -0.0078 | -0.0100 | -0.0343 | 0/17/1 |
| execve_absent | random_dropout | 0.0078 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| execve_absent | type_dropout | 0.0147 | +0.0069 | +0.0000 | -0.0292 | 1/17/0 |
| execve_absent | mixed_dropout | 0.0096 | +0.0018 | +0.0000 | -0.0114 | 1/17/0 |
| execve_absent | observed_router | 0.0212 | +0.0134 | +0.0200 | +0.0061 | 2/15/1 |
| proctitle_absent | semantic_event | 0.0000 | +0.0000 | +0.0000 | -0.0005 | 0/18/0 |
| proctitle_absent | entity_context | 0.0000 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| proctitle_absent | random_dropout | 0.0000 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| proctitle_absent | type_dropout | 0.0000 | +0.0000 | +0.0000 | +0.0019 | 0/18/0 |
| proctitle_absent | mixed_dropout | 0.0000 | +0.0000 | +0.0000 | +0.0017 | 0/18/0 |
| proctitle_absent | observed_router | 0.0000 | +0.0000 | +0.0000 | +0.0032 | 0/18/0 |
| syscall_absent | semantic_event | 0.0000 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| syscall_absent | entity_context | 0.0000 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| syscall_absent | random_dropout | 0.0000 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| syscall_absent | type_dropout | 0.0000 | +0.0000 | +0.0000 | -0.0005 | 0/18/0 |
| syscall_absent | mixed_dropout | 0.0000 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| syscall_absent | observed_router | 0.0447 | +0.0447 | +0.4300 | +0.4334 | 15/3/0 |
| path_absent | semantic_event | 0.0370 | +0.0370 | +0.0500 | +0.0392 | 5/13/0 |
| path_absent | entity_context | 0.0577 | +0.0577 | +0.1600 | +0.1059 | 11/7/0 |
| path_absent | random_dropout | 0.0000 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| path_absent | type_dropout | 0.0341 | +0.0341 | +0.0500 | +0.0448 | 4/14/0 |
| path_absent | mixed_dropout | 0.0000 | +0.0000 | +0.0000 | +0.0000 | 0/18/0 |
| path_absent | observed_router | 0.0244 | +0.0244 | +0.0200 | +0.0141 | 2/16/0 |

## Limits

- Pooled means average the fixed corruption seeds; masks are not independent attacks or independently fitted models.
- Undefined class-dependent metrics stay null; averages require all seed values to be defined.
- Other-label flag rates do not measure independently verified benign false alarms.
- Higher F1 may reflect fewer false flags or different recall. Primary gates and both operating points must remain visible.
- This report performs no fitting or inference and publishes no prediction arrays. It does not establish novelty or deployment guarantees.
