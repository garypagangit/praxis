# ait: structured-loss comparisons

All changes compare against random-record-dropout training. Both operating points remain separate; each arm retains its frozen clean-calibration threshold.

Baseline replication: **PASS**.

Each positive-bearing test run supplies one win/tie/loss vote after averaging matched corruption seeds. Runs with no positive examples are excluded from these votes; their negatives remain in pooled metrics. These votes are descriptive, not independent significance tests.

## escalate

Status: **COMPLETE**.

Positive-bearing runs: 2; excluded zero-positive runs: 0.

### Fixed score > 0.5

| Condition | Arm | F1 | F1 change | Recall change | Other-label flag-rate change | Positive-run F1 W/T/L |
|---|---|---:|---:|---:|---:|---:|
| clean | semantic_event | 0.6833 | -0.0297 | +0.0000 | +0.0008 | 0/1/1 |
| clean | entity_context | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| clean | random_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| clean | type_dropout | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| clean | mixed_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| clean | observed_router | 0.7193 | +0.0063 | +0.0000 | -0.0002 | 1/1/0 |
| random_25 | semantic_event | 0.6109 | +0.0066 | +0.0000 | -0.0002 | 1/1/0 |
| random_25 | entity_context | 0.6231 | +0.0188 | +0.0000 | -0.0005 | 1/1/0 |
| random_25 | random_dropout | 0.6043 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| random_25 | type_dropout | 0.6231 | +0.0188 | +0.0000 | -0.0005 | 1/1/0 |
| random_25 | mixed_dropout | 0.6105 | +0.0062 | +0.0000 | -0.0002 | 1/1/0 |
| random_25 | observed_router | 0.6105 | +0.0062 | +0.0000 | -0.0002 | 1/1/0 |
| random_50 | semantic_event | 0.4882 | +0.0202 | +0.0000 | -0.0005 | 1/1/0 |
| random_50 | entity_context | 0.4818 | +0.0138 | +0.0000 | -0.0004 | 1/1/0 |
| random_50 | random_dropout | 0.4680 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| random_50 | type_dropout | 0.4818 | +0.0138 | +0.0000 | -0.0004 | 1/1/0 |
| random_50 | mixed_dropout | 0.4756 | +0.0076 | +0.0076 | -0.0001 | 1/1/0 |
| random_50 | observed_router | 0.4699 | +0.0019 | +0.0000 | -0.0001 | 1/1/0 |
| random_75 | semantic_event | 0.3549 | +0.0185 | +0.0000 | -0.0006 | 1/1/0 |
| random_75 | entity_context | 0.3432 | +0.0067 | +0.0000 | -0.0002 | 1/1/0 |
| random_75 | random_dropout | 0.3364 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| random_75 | type_dropout | 0.3432 | +0.0067 | +0.0000 | -0.0002 | 1/1/0 |
| random_75 | mixed_dropout | 0.3502 | +0.0138 | +0.0076 | -0.0002 | 1/1/0 |
| random_75 | observed_router | 0.3414 | +0.0050 | +0.0000 | -0.0002 | 1/1/0 |
| support_burst_60 | semantic_event | 0.6833 | +0.0848 | +0.0000 | -0.0027 | 1/1/0 |
| support_burst_60 | entity_context | 0.6165 | +0.0180 | +0.0000 | -0.0006 | 1/1/0 |
| support_burst_60 | random_dropout | 0.5985 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| support_burst_60 | type_dropout | 0.6165 | +0.0180 | +0.0000 | -0.0006 | 1/1/0 |
| support_burst_60 | mixed_dropout | 0.5985 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| support_burst_60 | observed_router | 0.6029 | +0.0044 | +0.0000 | -0.0002 | 1/1/0 |
| command_records_absent | semantic_event | 0.6833 | -0.0297 | +0.0000 | +0.0008 | 0/1/1 |
| command_records_absent | entity_context | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| command_records_absent | random_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| command_records_absent | type_dropout | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| command_records_absent | mixed_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| command_records_absent | observed_router | 0.7193 | +0.0063 | +0.0000 | -0.0002 | 1/1/0 |
| delay_30_deadline_0 | semantic_event | 0.6833 | -0.0297 | +0.0000 | +0.0008 | 0/1/1 |
| delay_30_deadline_0 | entity_context | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| delay_30_deadline_0 | random_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| delay_30_deadline_0 | type_dropout | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| delay_30_deadline_0 | mixed_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| delay_30_deadline_0 | observed_router | 0.7193 | +0.0063 | +0.0000 | -0.0002 | 1/1/0 |
| delay_30_deadline_30 | semantic_event | 0.6833 | -0.0297 | +0.0000 | +0.0008 | 0/1/1 |
| delay_30_deadline_30 | entity_context | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| delay_30_deadline_30 | random_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| delay_30_deadline_30 | type_dropout | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| delay_30_deadline_30 | mixed_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| delay_30_deadline_30 | observed_router | 0.7193 | +0.0063 | +0.0000 | -0.0002 | 1/1/0 |
| delay_120_deadline_0 | semantic_event | 0.6833 | -0.0297 | +0.0000 | +0.0008 | 0/1/1 |
| delay_120_deadline_0 | entity_context | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| delay_120_deadline_0 | random_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| delay_120_deadline_0 | type_dropout | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| delay_120_deadline_0 | mixed_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| delay_120_deadline_0 | observed_router | 0.7193 | +0.0063 | +0.0000 | -0.0002 | 1/1/0 |
| delay_120_deadline_30 | semantic_event | 0.6833 | -0.0297 | +0.0000 | +0.0008 | 0/1/1 |
| delay_120_deadline_30 | entity_context | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| delay_120_deadline_30 | random_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| delay_120_deadline_30 | type_dropout | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| delay_120_deadline_30 | mixed_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| delay_120_deadline_30 | observed_router | 0.7193 | +0.0063 | +0.0000 | -0.0002 | 1/1/0 |
| delay_120_deadline_120 | semantic_event | 0.6833 | -0.0297 | +0.0000 | +0.0008 | 0/1/1 |
| delay_120_deadline_120 | entity_context | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| delay_120_deadline_120 | random_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| delay_120_deadline_120 | type_dropout | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| delay_120_deadline_120 | mixed_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| delay_120_deadline_120 | observed_router | 0.7193 | +0.0063 | +0.0000 | -0.0002 | 1/1/0 |
| execve_absent | semantic_event | 0.6833 | -0.0297 | +0.0000 | +0.0008 | 0/1/1 |
| execve_absent | entity_context | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| execve_absent | random_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| execve_absent | type_dropout | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| execve_absent | mixed_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| execve_absent | observed_router | 0.7193 | +0.0063 | +0.0000 | -0.0002 | 1/1/0 |
| proctitle_absent | semantic_event | 0.6833 | -0.0297 | +0.0000 | +0.0008 | 0/1/1 |
| proctitle_absent | entity_context | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| proctitle_absent | random_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| proctitle_absent | type_dropout | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| proctitle_absent | mixed_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| proctitle_absent | observed_router | 0.7193 | +0.0063 | +0.0000 | -0.0002 | 1/1/0 |
| syscall_absent | semantic_event | 0.6833 | -0.0297 | +0.0000 | +0.0008 | 0/1/1 |
| syscall_absent | entity_context | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| syscall_absent | random_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| syscall_absent | type_dropout | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| syscall_absent | mixed_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| syscall_absent | observed_router | 0.7193 | +0.0063 | +0.0000 | -0.0002 | 1/1/0 |
| path_absent | semantic_event | 0.6833 | -0.0297 | +0.0000 | +0.0008 | 0/1/1 |
| path_absent | entity_context | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| path_absent | random_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| path_absent | type_dropout | 0.7321 | +0.0191 | +0.0000 | -0.0005 | 1/1/0 |
| path_absent | mixed_dropout | 0.7130 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| path_absent | observed_router | 0.7193 | +0.0063 | +0.0000 | -0.0002 | 1/1/0 |

### Frozen calibration threshold

| Condition | Arm | F1 | F1 change | Recall change | Other-label flag-rate change | Positive-run F1 W/T/L |
|---|---|---:|---:|---:|---:|---:|
| clean | semantic_event | 0.5694 | -0.1027 | +0.0000 | +0.0035 | 0/1/1 |
| clean | entity_context | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| clean | random_dropout | 0.6721 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| clean | type_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| clean | mixed_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| clean | observed_router | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| random_25 | semantic_event | 0.5156 | -0.0678 | +0.0000 | +0.0022 | 0/1/1 |
| random_25 | entity_context | 0.5888 | +0.0054 | +0.0000 | -0.0002 | 1/1/0 |
| random_25 | random_dropout | 0.5833 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| random_25 | type_dropout | 0.5888 | +0.0054 | +0.0000 | -0.0002 | 1/1/0 |
| random_25 | mixed_dropout | 0.5853 | +0.0019 | +0.0000 | -0.0001 | 1/1/0 |
| random_25 | observed_router | 0.5853 | +0.0019 | +0.0000 | -0.0001 | 1/1/0 |
| random_50 | semantic_event | 0.4268 | -0.0249 | -0.0076 | +0.0007 | 0/1/1 |
| random_50 | entity_context | 0.4561 | +0.0044 | +0.0000 | -0.0002 | 1/1/0 |
| random_50 | random_dropout | 0.4517 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| random_50 | type_dropout | 0.4561 | +0.0044 | +0.0000 | -0.0002 | 1/1/0 |
| random_50 | mixed_dropout | 0.4513 | -0.0004 | +0.0000 | +0.0000 | 0/1/1 |
| random_50 | observed_router | 0.4476 | -0.0041 | -0.0076 | -0.0001 | 0/1/1 |
| random_75 | semantic_event | 0.3290 | -0.0094 | -0.0152 | -0.0002 | 0/1/1 |
| random_75 | entity_context | 0.3382 | -0.0002 | +0.0000 | +0.0000 | 1/1/0 |
| random_75 | random_dropout | 0.3384 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| random_75 | type_dropout | 0.3382 | -0.0002 | +0.0000 | +0.0000 | 1/1/0 |
| random_75 | mixed_dropout | 0.3353 | -0.0031 | +0.0000 | +0.0001 | 0/1/1 |
| random_75 | observed_router | 0.3285 | -0.0099 | -0.0076 | +0.0001 | 0/1/1 |
| support_burst_60 | semantic_event | 0.5694 | -0.0040 | +0.0000 | +0.0002 | 0/1/1 |
| support_burst_60 | entity_context | 0.5734 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| support_burst_60 | random_dropout | 0.5734 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| support_burst_60 | type_dropout | 0.5734 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| support_burst_60 | mixed_dropout | 0.5734 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| support_burst_60 | observed_router | 0.5734 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| command_records_absent | semantic_event | 0.5694 | -0.1027 | +0.0000 | +0.0035 | 0/1/1 |
| command_records_absent | entity_context | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| command_records_absent | random_dropout | 0.6721 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| command_records_absent | type_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| command_records_absent | mixed_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| command_records_absent | observed_router | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_30_deadline_0 | semantic_event | 0.5694 | -0.1027 | +0.0000 | +0.0035 | 0/1/1 |
| delay_30_deadline_0 | entity_context | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_30_deadline_0 | random_dropout | 0.6721 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| delay_30_deadline_0 | type_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_30_deadline_0 | mixed_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_30_deadline_0 | observed_router | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_30_deadline_30 | semantic_event | 0.5694 | -0.1027 | +0.0000 | +0.0035 | 0/1/1 |
| delay_30_deadline_30 | entity_context | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_30_deadline_30 | random_dropout | 0.6721 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| delay_30_deadline_30 | type_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_30_deadline_30 | mixed_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_30_deadline_30 | observed_router | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_120_deadline_0 | semantic_event | 0.5694 | -0.1027 | +0.0000 | +0.0035 | 0/1/1 |
| delay_120_deadline_0 | entity_context | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_120_deadline_0 | random_dropout | 0.6721 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| delay_120_deadline_0 | type_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_120_deadline_0 | mixed_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_120_deadline_0 | observed_router | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_120_deadline_30 | semantic_event | 0.5694 | -0.1027 | +0.0000 | +0.0035 | 0/1/1 |
| delay_120_deadline_30 | entity_context | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_120_deadline_30 | random_dropout | 0.6721 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| delay_120_deadline_30 | type_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_120_deadline_30 | mixed_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_120_deadline_30 | observed_router | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_120_deadline_120 | semantic_event | 0.5694 | -0.1027 | +0.0000 | +0.0035 | 0/1/1 |
| delay_120_deadline_120 | entity_context | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_120_deadline_120 | random_dropout | 0.6721 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| delay_120_deadline_120 | type_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_120_deadline_120 | mixed_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| delay_120_deadline_120 | observed_router | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| execve_absent | semantic_event | 0.5694 | -0.1027 | +0.0000 | +0.0035 | 0/1/1 |
| execve_absent | entity_context | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| execve_absent | random_dropout | 0.6721 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| execve_absent | type_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| execve_absent | mixed_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| execve_absent | observed_router | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| proctitle_absent | semantic_event | 0.5694 | -0.1027 | +0.0000 | +0.0035 | 0/1/1 |
| proctitle_absent | entity_context | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| proctitle_absent | random_dropout | 0.6721 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| proctitle_absent | type_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| proctitle_absent | mixed_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| proctitle_absent | observed_router | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| syscall_absent | semantic_event | 0.5694 | -0.1135 | -0.0227 | +0.0035 | 0/1/1 |
| syscall_absent | entity_context | 0.6942 | +0.0113 | +0.0000 | -0.0003 | 1/1/0 |
| syscall_absent | random_dropout | 0.6829 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| syscall_absent | type_dropout | 0.6942 | +0.0113 | +0.0000 | -0.0003 | 1/1/0 |
| syscall_absent | mixed_dropout | 0.6885 | +0.0056 | +0.0000 | -0.0002 | 1/1/0 |
| syscall_absent | observed_router | 0.6885 | +0.0056 | +0.0000 | -0.0002 | 1/1/0 |
| path_absent | semantic_event | 0.5694 | -0.1027 | +0.0000 | +0.0035 | 0/1/1 |
| path_absent | entity_context | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| path_absent | random_dropout | 0.6721 | +0.0000 | +0.0000 | +0.0000 | 0/2/0 |
| path_absent | type_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| path_absent | mixed_dropout | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |
| path_absent | observed_router | 0.6833 | +0.0112 | +0.0000 | -0.0003 | 1/1/0 |

## Limits

- Pooled means average the fixed corruption seeds; masks are not independent attacks or independently fitted models.
- Undefined class-dependent metrics stay null; averages require all seed values to be defined.
- Other-label flag rates do not measure independently verified benign false alarms.
- Higher F1 may reflect fewer false flags or different recall. Primary gates and both operating points must remain visible.
- This report performs no fitting or inference and publishes no prediction arrays. It does not establish novelty or deployment guarantees.
