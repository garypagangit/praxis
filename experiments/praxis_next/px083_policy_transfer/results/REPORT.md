# PX-083 — Casino-trained context-selection policy on Casino and CAM-LDS

**Secondary development replication on already exposed data.** T1105 is Ingress Tool Transfer; this experiment does not detect lateral movement or forecast exfiltration. Other-label flags are not benign false alarms.

Two Ridge selectors were fitted on 1,494 Casino clean-calibration scores, including 87 T1105 positives, then applied unchanged to both datasets. No native classifiers were retrained. Saved prediction tables: 294; runtime 27.24 CPU seconds.

The ordinary selector learns the difference in binary errors at score >0.5. The target-cost selector multiplies errors on T1105 training examples by four. This is a declared design choice. Both receive only native scores and observable visibility. Every arm uses the same strict 0.5 threshold. Original calibrated native-control results are retained separately and were not used to fit the selectors.

## Complete comparisons

Random-loss rows average three perturbations of the same events. Other rows contain one deterministic view. These are not independent fitting seeds or campaigns. Higher F1/recall is better; fewer other-label flags and lower target-cost error are better.

### casino

| Condition | Arm | F1 | Recall | Other-label flags | Cost error |
|---|---|---:|---:|---:|---:|
| clean | current | 0.7368 | 82.35% | 7.00 | 0.020652 |
| clean | context | 0.5957 | 82.35% | 16.00 | 0.030435 |
| clean | fixed_fusion | 0.7179 | 82.35% | 8.00 | 0.021739 |
| clean | confidence_gate | 0.7179 | 82.35% | 8.00 | 0.021739 |
| clean | ordinary_gate | 0.7368 | 82.35% | 7.00 | 0.020652 |
| clean | target_cost_gate | 0.5957 | 82.35% | 16.00 | 0.030435 |
| clean | mixed_dropout | 0.5833 | 82.35% | 17.00 | 0.031522 |
| random_25 | current | 0.3996 | 86.27% | 41.67 | 0.055435 |
| random_25 | context | 0.5271 | 82.35% | 22.33 | 0.037319 |
| random_25 | fixed_fusion | 0.4665 | 84.31% | 30.33 | 0.044565 |
| random_25 | confidence_gate | 0.4665 | 84.31% | 30.33 | 0.044565 |
| random_25 | ordinary_gate | 0.3996 | 86.27% | 41.67 | 0.055435 |
| random_25 | target_cost_gate | 0.5271 | 82.35% | 22.33 | 0.037319 |
| random_25 | mixed_dropout | 0.5468 | 82.35% | 20.67 | 0.035507 |
| random_50 | current | 0.2368 | 88.24% | 94.67 | 0.111594 |
| random_50 | context | 0.3274 | 80.39% | 53.00 | 0.072101 |
| random_50 | fixed_fusion | 0.2768 | 84.31% | 72.33 | 0.090217 |
| random_50 | confidence_gate | 0.2768 | 84.31% | 72.33 | 0.090217 |
| random_50 | ordinary_gate | 0.2368 | 88.24% | 94.67 | 0.111594 |
| random_50 | target_cost_gate | 0.3274 | 80.39% | 53.00 | 0.072101 |
| random_50 | mixed_dropout | 0.3649 | 78.43% | 43.00 | 0.062681 |
| random_75 | current | 0.1361 | 72.55% | 150.67 | 0.184058 |
| random_75 | context | 0.1946 | 68.63% | 91.00 | 0.122101 |
| random_75 | fixed_fusion | 0.1678 | 70.59% | 114.33 | 0.146014 |
| random_75 | confidence_gate | 0.1678 | 70.59% | 114.33 | 0.146014 |
| random_75 | ordinary_gate | 0.1361 | 72.55% | 150.67 | 0.184058 |
| random_75 | target_cost_gate | 0.1946 | 68.63% | 91.00 | 0.122101 |
| random_75 | mixed_dropout | 0.2084 | 62.75% | 75.00 | 0.109058 |
| support_burst_60 | current | 0.7368 | 82.35% | 7.00 | 0.020652 |
| support_burst_60 | context | 0.5769 | 88.24% | 20.00 | 0.030435 |
| support_burst_60 | fixed_fusion | 0.6818 | 88.24% | 12.00 | 0.021739 |
| support_burst_60 | confidence_gate | 0.6818 | 88.24% | 12.00 | 0.021739 |
| support_burst_60 | ordinary_gate | 0.7368 | 82.35% | 7.00 | 0.020652 |
| support_burst_60 | target_cost_gate | 0.5769 | 88.24% | 20.00 | 0.030435 |
| support_burst_60 | mixed_dropout | 0.4667 | 82.35% | 29.00 | 0.044565 |
| command_records_absent | current | 0.2258 | 82.35% | 93.00 | 0.114130 |
| command_records_absent | context | 0.3607 | 64.71% | 33.00 | 0.061957 |
| command_records_absent | fixed_fusion | 0.4138 | 70.59% | 29.00 | 0.053261 |
| command_records_absent | confidence_gate | 0.4138 | 70.59% | 29.00 | 0.053261 |
| command_records_absent | ordinary_gate | 0.2258 | 82.35% | 93.00 | 0.114130 |
| command_records_absent | target_cost_gate | 0.3607 | 64.71% | 33.00 | 0.061957 |
| command_records_absent | mixed_dropout | 0.2121 | 82.35% | 101.00 | 0.122826 |
| delay_30_deadline_0 | current | 0.2258 | 82.35% | 93.00 | 0.114130 |
| delay_30_deadline_0 | context | 0.3729 | 64.71% | 31.00 | 0.059783 |
| delay_30_deadline_0 | fixed_fusion | 0.4364 | 70.59% | 26.00 | 0.050000 |
| delay_30_deadline_0 | confidence_gate | 0.4364 | 70.59% | 26.00 | 0.050000 |
| delay_30_deadline_0 | ordinary_gate | 0.2258 | 82.35% | 93.00 | 0.114130 |
| delay_30_deadline_0 | target_cost_gate | 0.3729 | 64.71% | 31.00 | 0.059783 |
| delay_30_deadline_0 | mixed_dropout | 0.2205 | 82.35% | 96.00 | 0.117391 |
| delay_30_deadline_30 | current | 0.7368 | 82.35% | 7.00 | 0.020652 |
| delay_30_deadline_30 | context | 0.5957 | 82.35% | 16.00 | 0.030435 |
| delay_30_deadline_30 | fixed_fusion | 0.7179 | 82.35% | 8.00 | 0.021739 |
| delay_30_deadline_30 | confidence_gate | 0.7179 | 82.35% | 8.00 | 0.021739 |
| delay_30_deadline_30 | ordinary_gate | 0.7368 | 82.35% | 7.00 | 0.020652 |
| delay_30_deadline_30 | target_cost_gate | 0.5957 | 82.35% | 16.00 | 0.030435 |
| delay_30_deadline_30 | mixed_dropout | 0.5833 | 82.35% | 17.00 | 0.031522 |
| delay_120_deadline_0 | current | 0.2258 | 82.35% | 93.00 | 0.114130 |
| delay_120_deadline_0 | context | 0.3607 | 64.71% | 33.00 | 0.061957 |
| delay_120_deadline_0 | fixed_fusion | 0.4138 | 70.59% | 29.00 | 0.053261 |
| delay_120_deadline_0 | confidence_gate | 0.4138 | 70.59% | 29.00 | 0.053261 |
| delay_120_deadline_0 | ordinary_gate | 0.2258 | 82.35% | 93.00 | 0.114130 |
| delay_120_deadline_0 | target_cost_gate | 0.3607 | 64.71% | 33.00 | 0.061957 |
| delay_120_deadline_0 | mixed_dropout | 0.2121 | 82.35% | 101.00 | 0.122826 |
| delay_120_deadline_30 | current | 0.2258 | 82.35% | 93.00 | 0.114130 |
| delay_120_deadline_30 | context | 0.3607 | 64.71% | 33.00 | 0.061957 |
| delay_120_deadline_30 | fixed_fusion | 0.4138 | 70.59% | 29.00 | 0.053261 |
| delay_120_deadline_30 | confidence_gate | 0.4138 | 70.59% | 29.00 | 0.053261 |
| delay_120_deadline_30 | ordinary_gate | 0.2258 | 82.35% | 93.00 | 0.114130 |
| delay_120_deadline_30 | target_cost_gate | 0.3607 | 64.71% | 33.00 | 0.061957 |
| delay_120_deadline_30 | mixed_dropout | 0.2105 | 82.35% | 102.00 | 0.123913 |
| delay_120_deadline_120 | current | 0.7368 | 82.35% | 7.00 | 0.020652 |
| delay_120_deadline_120 | context | 0.5957 | 82.35% | 16.00 | 0.030435 |
| delay_120_deadline_120 | fixed_fusion | 0.7179 | 82.35% | 8.00 | 0.021739 |
| delay_120_deadline_120 | confidence_gate | 0.7179 | 82.35% | 8.00 | 0.021739 |
| delay_120_deadline_120 | ordinary_gate | 0.7368 | 82.35% | 7.00 | 0.020652 |
| delay_120_deadline_120 | target_cost_gate | 0.5957 | 82.35% | 16.00 | 0.030435 |
| delay_120_deadline_120 | mixed_dropout | 0.5833 | 82.35% | 17.00 | 0.031522 |
| execve_absent | current | 0.3226 | 88.24% | 61.00 | 0.075000 |
| execve_absent | context | 0.3704 | 88.24% | 49.00 | 0.061957 |
| execve_absent | fixed_fusion | 0.4000 | 88.24% | 43.00 | 0.055435 |
| execve_absent | confidence_gate | 0.4000 | 88.24% | 43.00 | 0.055435 |
| execve_absent | ordinary_gate | 0.3226 | 88.24% | 61.00 | 0.075000 |
| execve_absent | target_cost_gate | 0.3704 | 88.24% | 49.00 | 0.061957 |
| execve_absent | mixed_dropout | 0.5091 | 82.35% | 24.00 | 0.039130 |
| proctitle_absent | current | 0.7778 | 82.35% | 5.00 | 0.018478 |
| proctitle_absent | context | 0.7179 | 82.35% | 8.00 | 0.021739 |
| proctitle_absent | fixed_fusion | 0.7778 | 82.35% | 5.00 | 0.018478 |
| proctitle_absent | confidence_gate | 0.7778 | 82.35% | 5.00 | 0.018478 |
| proctitle_absent | ordinary_gate | 0.7778 | 82.35% | 5.00 | 0.018478 |
| proctitle_absent | target_cost_gate | 0.7179 | 82.35% | 8.00 | 0.021739 |
| proctitle_absent | mixed_dropout | 0.3784 | 82.35% | 43.00 | 0.059783 |
| syscall_absent | current | 0.3636 | 94.12% | 55.00 | 0.064130 |
| syscall_absent | context | 0.6522 | 88.24% | 14.00 | 0.023913 |
| syscall_absent | fixed_fusion | 0.5263 | 88.24% | 25.00 | 0.035870 |
| syscall_absent | confidence_gate | 0.5263 | 88.24% | 25.00 | 0.035870 |
| syscall_absent | ordinary_gate | 0.3636 | 94.12% | 55.00 | 0.064130 |
| syscall_absent | target_cost_gate | 0.6522 | 88.24% | 14.00 | 0.023913 |
| syscall_absent | mixed_dropout | 0.8000 | 82.35% | 4.00 | 0.017391 |
| path_absent | current | 0.7692 | 88.24% | 7.00 | 0.016304 |
| path_absent | context | 0.5926 | 94.12% | 21.00 | 0.027174 |
| path_absent | fixed_fusion | 0.6522 | 88.24% | 14.00 | 0.023913 |
| path_absent | confidence_gate | 0.6522 | 88.24% | 14.00 | 0.023913 |
| path_absent | ordinary_gate | 0.7692 | 88.24% | 7.00 | 0.016304 |
| path_absent | target_cost_gate | 0.5926 | 94.12% | 21.00 | 0.027174 |
| path_absent | mixed_dropout | 0.4918 | 88.24% | 29.00 | 0.040217 |

### camlds

| Condition | Arm | F1 | Recall | Other-label flags | Cost error |
|---|---|---:|---:|---:|---:|
| clean | current | 0.0495 | 87.00% | 3329.00 | 0.803279 |
| clean | context | 0.0534 | 88.00% | 3108.00 | 0.749822 |
| clean | fixed_fusion | 0.0524 | 88.00% | 3171.00 | 0.764790 |
| clean | confidence_gate | 0.0524 | 88.00% | 3171.00 | 0.764790 |
| clean | ordinary_gate | 0.0495 | 87.00% | 3325.00 | 0.802328 |
| clean | target_cost_gate | 0.0534 | 88.00% | 3108.00 | 0.749822 |
| clean | mixed_dropout | 0.0527 | 85.00% | 3038.00 | 0.736042 |
| random_25 | current | 0.0454 | 49.33% | 2023.33 | 0.528867 |
| random_25 | context | 0.0468 | 61.67% | 2474.33 | 0.624297 |
| random_25 | fixed_fusion | 0.0475 | 59.00% | 2323.00 | 0.590877 |
| random_25 | confidence_gate | 0.0475 | 59.00% | 2323.00 | 0.590877 |
| random_25 | ordinary_gate | 0.0455 | 49.33% | 2020.00 | 0.528075 |
| random_25 | target_cost_gate | 0.0468 | 61.67% | 2474.33 | 0.624297 |
| random_25 | mixed_dropout | 0.0515 | 81.00% | 2967.33 | 0.723054 |
| random_50 | current | 0.0452 | 28.00% | 1112.33 | 0.332700 |
| random_50 | context | 0.0469 | 51.00% | 2022.67 | 0.527124 |
| random_50 | fixed_fusion | 0.0472 | 45.00% | 1760.67 | 0.470579 |
| random_50 | confidence_gate | 0.0472 | 45.00% | 1760.67 | 0.470579 |
| random_50 | ordinary_gate | 0.0452 | 28.00% | 1111.00 | 0.332383 |
| random_50 | target_cost_gate | 0.0469 | 51.00% | 2022.67 | 0.527124 |
| random_50 | mixed_dropout | 0.0491 | 71.00% | 2724.00 | 0.674745 |
| random_75 | current | 0.0493 | 15.00% | 493.00 | 0.197909 |
| random_75 | context | 0.0446 | 32.33% | 1318.33 | 0.377524 |
| random_75 | fixed_fusion | 0.0427 | 24.33% | 1013.67 | 0.312743 |
| random_75 | confidence_gate | 0.0427 | 24.33% | 1013.67 | 0.312743 |
| random_75 | ordinary_gate | 0.0493 | 15.00% | 493.00 | 0.197909 |
| random_75 | target_cost_gate | 0.0446 | 32.33% | 1318.33 | 0.377524 |
| random_75 | mixed_dropout | 0.0467 | 48.33% | 1920.33 | 0.505346 |
| support_burst_60 | current | 0.0495 | 87.00% | 3329.00 | 0.803279 |
| support_burst_60 | context | 0.0490 | 95.00% | 3685.00 | 0.880257 |
| support_burst_60 | fixed_fusion | 0.0500 | 92.00% | 3491.00 | 0.837016 |
| support_burst_60 | confidence_gate | 0.0500 | 92.00% | 3491.00 | 0.837016 |
| support_burst_60 | ordinary_gate | 0.0495 | 87.00% | 3326.00 | 0.802566 |
| support_burst_60 | target_cost_gate | 0.0490 | 95.00% | 3685.00 | 0.880257 |
| support_burst_60 | mixed_dropout | 0.0488 | 91.00% | 3541.00 | 0.849846 |
| command_records_absent | current | 0.0000 | 0.00% | 2.00 | 0.095510 |
| command_records_absent | context | 0.0384 | 15.00% | 666.00 | 0.239012 |
| command_records_absent | fixed_fusion | 0.0000 | 0.00% | 4.00 | 0.095985 |
| command_records_absent | confidence_gate | 0.0000 | 0.00% | 4.00 | 0.095985 |
| command_records_absent | ordinary_gate | 0.0000 | 0.00% | 2.00 | 0.095510 |
| command_records_absent | target_cost_gate | 0.0384 | 15.00% | 666.00 | 0.239012 |
| command_records_absent | mixed_dropout | 0.0532 | 84.00% | 2976.00 | 0.722262 |
| delay_30_deadline_0 | current | 0.0000 | 0.00% | 2.00 | 0.095510 |
| delay_30_deadline_0 | context | 0.0319 | 4.00% | 147.00 | 0.126158 |
| delay_30_deadline_0 | fixed_fusion | 0.0000 | 0.00% | 13.00 | 0.098123 |
| delay_30_deadline_0 | confidence_gate | 0.0000 | 0.00% | 13.00 | 0.098123 |
| delay_30_deadline_0 | ordinary_gate | 0.0000 | 0.00% | 2.00 | 0.095510 |
| delay_30_deadline_0 | target_cost_gate | 0.0319 | 4.00% | 147.00 | 0.126158 |
| delay_30_deadline_0 | mixed_dropout | 0.0518 | 79.00% | 2870.00 | 0.701829 |
| delay_30_deadline_30 | current | 0.0495 | 87.00% | 3329.00 | 0.803279 |
| delay_30_deadline_30 | context | 0.0534 | 88.00% | 3108.00 | 0.749822 |
| delay_30_deadline_30 | fixed_fusion | 0.0524 | 88.00% | 3171.00 | 0.764790 |
| delay_30_deadline_30 | confidence_gate | 0.0524 | 88.00% | 3171.00 | 0.764790 |
| delay_30_deadline_30 | ordinary_gate | 0.0495 | 87.00% | 3325.00 | 0.802328 |
| delay_30_deadline_30 | target_cost_gate | 0.0534 | 88.00% | 3108.00 | 0.749822 |
| delay_30_deadline_30 | mixed_dropout | 0.0527 | 85.00% | 3038.00 | 0.736042 |
| delay_120_deadline_0 | current | 0.0000 | 0.00% | 2.00 | 0.095510 |
| delay_120_deadline_0 | context | 0.0384 | 15.00% | 666.00 | 0.239012 |
| delay_120_deadline_0 | fixed_fusion | 0.0000 | 0.00% | 4.00 | 0.095985 |
| delay_120_deadline_0 | confidence_gate | 0.0000 | 0.00% | 4.00 | 0.095985 |
| delay_120_deadline_0 | ordinary_gate | 0.0000 | 0.00% | 2.00 | 0.095510 |
| delay_120_deadline_0 | target_cost_gate | 0.0384 | 15.00% | 666.00 | 0.239012 |
| delay_120_deadline_0 | mixed_dropout | 0.0532 | 84.00% | 2976.00 | 0.722262 |
| delay_120_deadline_30 | current | 0.0000 | 0.00% | 2.00 | 0.095510 |
| delay_120_deadline_30 | context | 0.0331 | 8.00% | 376.00 | 0.176764 |
| delay_120_deadline_30 | fixed_fusion | 0.0000 | 0.00% | 6.00 | 0.096460 |
| delay_120_deadline_30 | confidence_gate | 0.0000 | 0.00% | 6.00 | 0.096460 |
| delay_120_deadline_30 | ordinary_gate | 0.0000 | 0.00% | 2.00 | 0.095510 |
| delay_120_deadline_30 | target_cost_gate | 0.0331 | 8.00% | 376.00 | 0.176764 |
| delay_120_deadline_30 | mixed_dropout | 0.0529 | 86.00% | 3063.00 | 0.741031 |
| delay_120_deadline_120 | current | 0.0495 | 87.00% | 3329.00 | 0.803279 |
| delay_120_deadline_120 | context | 0.0534 | 88.00% | 3108.00 | 0.749822 |
| delay_120_deadline_120 | fixed_fusion | 0.0524 | 88.00% | 3171.00 | 0.764790 |
| delay_120_deadline_120 | confidence_gate | 0.0524 | 88.00% | 3171.00 | 0.764790 |
| delay_120_deadline_120 | ordinary_gate | 0.0495 | 87.00% | 3325.00 | 0.802328 |
| delay_120_deadline_120 | target_cost_gate | 0.0534 | 88.00% | 3108.00 | 0.749822 |
| delay_120_deadline_120 | mixed_dropout | 0.0527 | 85.00% | 3038.00 | 0.736042 |
| execve_absent | current | 0.0478 | 84.00% | 3327.00 | 0.805655 |
| execve_absent | context | 0.0514 | 74.00% | 2707.00 | 0.667855 |
| execve_absent | fixed_fusion | 0.0506 | 77.00% | 2865.00 | 0.702542 |
| execve_absent | confidence_gate | 0.0506 | 77.00% | 2865.00 | 0.702542 |
| execve_absent | ordinary_gate | 0.0479 | 84.00% | 3321.00 | 0.804229 |
| execve_absent | target_cost_gate | 0.0514 | 74.00% | 2707.00 | 0.667855 |
| execve_absent | mixed_dropout | 0.0525 | 85.00% | 3053.00 | 0.739606 |
| proctitle_absent | current | 0.0075 | 1.00% | 165.00 | 0.133286 |
| proctitle_absent | context | 0.0406 | 22.00% | 962.00 | 0.302685 |
| proctitle_absent | fixed_fusion | 0.0000 | 0.00% | 27.00 | 0.101449 |
| proctitle_absent | confidence_gate | 0.0000 | 0.00% | 27.00 | 0.101449 |
| proctitle_absent | ordinary_gate | 0.0075 | 1.00% | 165.00 | 0.133286 |
| proctitle_absent | target_cost_gate | 0.0406 | 22.00% | 962.00 | 0.302685 |
| proctitle_absent | mixed_dropout | 0.0515 | 85.00% | 3116.00 | 0.754574 |
| syscall_absent | current | 0.0404 | 9.00% | 336.00 | 0.166310 |
| syscall_absent | context | 0.0445 | 53.00% | 2230.00 | 0.574483 |
| syscall_absent | fixed_fusion | 0.0457 | 52.00% | 2122.00 | 0.549774 |
| syscall_absent | confidence_gate | 0.0457 | 52.00% | 2122.00 | 0.549774 |
| syscall_absent | ordinary_gate | 0.0404 | 9.00% | 336.00 | 0.166310 |
| syscall_absent | target_cost_gate | 0.0445 | 53.00% | 2230.00 | 0.574483 |
| syscall_absent | mixed_dropout | 0.0510 | 85.00% | 3151.00 | 0.762889 |
| path_absent | current | 0.0494 | 96.00% | 3692.00 | 0.880969 |
| path_absent | context | 0.0506 | 94.00% | 3525.00 | 0.843193 |
| path_absent | fixed_fusion | 0.0494 | 94.00% | 3610.00 | 0.863388 |
| path_absent | confidence_gate | 0.0494 | 94.00% | 3610.00 | 0.863388 |
| path_absent | ordinary_gate | 0.0495 | 96.00% | 3684.00 | 0.879069 |
| path_absent | target_cost_gate | 0.0506 | 94.00% | 3525.00 | 0.843193 |
| path_absent | mixed_dropout | 0.0499 | 76.00% | 2868.00 | 0.704205 |

## Why matching metrics do not show a new adaptive advantage

A post-result diagnostic found only 11 nonzero expert-error comparisons among 1494 Casino calibration rows. The selectors change score sources, but different probability vectors can still lead to identical 0.5 decisions. No model was refitted for this diagnostic.

| Dataset | Gate | Reference | Identical hard-decision views | Identical score views |
|---|---|---|---:|---:|
| casino | ordinary_gate | current | 21/21 | 0/21 |
| casino | target_cost_gate | context | 21/21 | 0/21 |
| camlds | ordinary_gate | current | 9/21 | 0/21 |
| camlds | target_cost_gate | context | 21/21 | 0/21 |

## Original native thresholds: clean-condition supplement

These thresholds were chosen in the earlier experiments. They are displayed to expose the operating-point limitation; they were not used to select or retrain the new gates.

| Dataset | Native arm | Original threshold | Recall | F1 | Other-label flags |
|---|---|---:|---:|---:|---:|
| casino | semantic_event | 0.5191 | 82.35% | 0.7568 | 6 |
| casino | entity_context | 0.5322 | 82.35% | 0.7000 | 9 |
| casino | mixed_dropout | 0.5709 | 82.35% | 0.6364 | 13 |
| camlds | semantic_event | 0.6491 | 0.00% | 0.0000 | 2 |
| camlds | entity_context | 0.6627 | 1.00% | 0.0141 | 41 |
| camlds | mixed_dropout | 0.6723 | 0.00% | 0.0000 | 16 |

## Limits

- Casino evaluates 920 targets/17 T1105 positives across18 runs. CAM-LDS evaluates4,209 targets/100 positives across18 runs from one held-out family. Repeated family recipes and author annotation uncertainty remain.
- Casino target units represent annotation-onset proxies; CAM-LDS target units represent labeled time intervals. No pooled accuracy or claim of identical operational decisions is appropriate.
- The two score policies transfer unchanged; the underlying classifiers were trained separately on their native datasets. This is policy transfer only.
- CAM-LDS calibration (68 rows/8 positives from one run) is not used to train or tune these policies. Its old thresholds appear only in the descriptive native-control supplement.
- The offline annotated target roster is not a production alert trigger. Invisible targets count as misses and produce no alarm.
- Missing/delayed-record interventions are synthetic. Waiting out the complete injected delay restores clean data by construction, not by information recovery.
- Existing test outcomes were previously examined. Computation and source checks do not turn this into independent confirmation or establish algorithm novelty.

[Frozen protocol](../PROTOCOL.md) · [Qualified sources](../INPUTS.json) · [All metrics](METRICS.json) · [Audit](AUDIT.json) · [Original thresholds](ORIGINAL_THRESHOLD_CONTROLS.json)
