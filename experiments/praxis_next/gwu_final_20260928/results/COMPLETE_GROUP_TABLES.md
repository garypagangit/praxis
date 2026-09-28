# Complete group-mean results

All 308 arm/condition/budget group means are retained. PX080-082 means use three fits on the same records. PX083 uses three perturbations for random-loss conditions and one deterministic view otherwise. Counts may therefore be fractional. No displayed group is an independent campaign.

Full per-fit precision, recall, F1, average precision, ROC-AUC, class supports, warning destinations and confusion counts are in the CSV tables. Blank ranking metrics mean unavailable; they are not replaced with invented estimates.

## PX080

| Condition / view / budget | Arm | Macro-F1 | Exact recall: movement / exfil. | Exfil. warning recall | Benign flags |
|---|---|---:|---:|---:|---:|
| clean | current_roles | 0.7545 | 78.10% / 67.50% | 67.60% | 139.33 |
| clean | context | 0.7658 | 52.38% / 67.21% | 67.64% | 48.33 |
| clean | fixed_fusion | 0.7655 | 60.00% / 67.42% | 67.54% | 76.00 |
| clean | confidence_gate | 0.7650 | 60.00% / 67.42% | 67.54% | 77.00 |
| clean | ordinary_gate | 0.7659 | 64.76% / 67.36% | 67.68% | 85.67 |
| clean | stage_harm_gate | 0.7560 | 69.52% / 67.28% | 67.81% | 109.00 |
| clean | context_dropout | 0.7589 | 51.43% / 67.41% | 67.83% | 68.67 |
| missing_half | current_roles | 0.7545 | 78.10% / 67.50% | 67.60% | 139.33 |
| missing_half | context | 0.6626 | 29.52% / 66.99% | 67.27% | 28.67 |
| missing_half | fixed_fusion | 0.7602 | 44.76% / 67.33% | 67.41% | 54.33 |
| missing_half | confidence_gate | 0.7592 | 44.76% / 67.33% | 67.40% | 54.33 |
| missing_half | ordinary_gate | 0.7598 | 52.38% / 67.30% | 67.52% | 74.33 |
| missing_half | stage_harm_gate | 0.7561 | 60.95% / 67.17% | 67.55% | 93.67 |
| missing_half | context_dropout | 0.7595 | 62.86% / 67.43% | 67.77% | 95.00 |
| missing_all | current_roles | 0.7545 | 78.10% / 67.50% | 67.60% | 139.33 |
| missing_all | context | 0.4339 | 0.00% / 66.75% | 66.75% | 0.00 |
| missing_all | fixed_fusion | 0.7285 | 18.10% / 67.30% | 67.30% | 29.67 |
| missing_all | confidence_gate | 0.7265 | 18.10% / 67.29% | 67.29% | 29.67 |
| missing_all | ordinary_gate | 0.7419 | 36.19% / 67.23% | 67.23% | 62.33 |
| missing_all | stage_harm_gate | 0.7422 | 42.86% / 67.02% | 67.11% | 77.00 |
| missing_all | context_dropout | 0.7587 | 68.57% / 67.50% | 67.64% | 116.00 |
| stale_5min | current_roles | 0.7545 | 78.10% / 67.50% | 67.60% | 139.33 |
| stale_5min | context | 0.7261 | 21.90% / 67.22% | 67.83% | 37.67 |
| stale_5min | fixed_fusion | 0.7491 | 41.90% / 67.41% | 67.56% | 67.67 |
| stale_5min | confidence_gate | 0.7485 | 41.90% / 67.42% | 67.57% | 69.00 |
| stale_5min | ordinary_gate | 0.7456 | 49.52% / 67.30% | 67.68% | 85.00 |
| stale_5min | stage_harm_gate | 0.7472 | 63.81% / 67.33% | 67.88% | 113.33 |
| stale_5min | context_dropout | 0.7514 | 48.57% / 67.39% | 67.88% | 77.67 |
| wrong_host | current_roles | 0.7545 | 78.10% / 67.50% | 67.60% | 139.33 |
| wrong_host | context | 0.4559 | 0.00% / 66.80% | 66.80% | 0.00 |
| wrong_host | fixed_fusion | 0.7286 | 19.05% / 67.31% | 67.31% | 32.33 |
| wrong_host | confidence_gate | 0.7267 | 19.05% / 67.30% | 67.30% | 32.67 |
| wrong_host | ordinary_gate | 0.7406 | 35.24% / 67.24% | 67.24% | 61.67 |
| wrong_host | stage_harm_gate | 0.7430 | 44.76% / 67.03% | 67.13% | 81.33 |
| wrong_host | context_dropout | 0.7589 | 68.57% / 67.50% | 67.64% | 114.67 |

## PX081

| Condition / view / budget | Arm | Macro-F1 | Exact recall: movement / exfil. | Exfil. warning recall | Benign flags |
|---|---|---:|---:|---:|---:|
| clean / B1 | none | 0.7523 | 78.10% / 67.52% | 67.52% | 164.00 |
| clean / B1 | roles_first | 0.7136 | 85.71% / 67.52% | 88.34% | 179.67 |
| clean / B1 | history_first | 0.7136 | 85.71% / 67.52% | 88.34% | 179.67 |
| clean / B1 | random | 0.7136 | 85.71% / 67.52% | 88.34% | 179.67 |
| clean / B1 | entropy | 0.7139 | 81.90% / 67.52% | 87.95% | 174.00 |
| clean / B1 | harm | 0.7500 | 81.90% / 67.52% | 67.83% | 169.67 |
| clean / B2 | none | 0.7523 | 78.10% / 67.52% | 67.52% | 164.00 |
| clean / B2 | roles_first | 0.7136 | 85.71% / 67.52% | 88.34% | 179.67 |
| clean / B2 | history_first | 0.7594 | 58.10% / 67.13% | 67.17% | 86.67 |
| clean / B2 | random | 0.7213 | 76.19% / 67.34% | 77.75% | 133.67 |
| clean / B2 | entropy | 0.7181 | 63.81% / 67.29% | 87.58% | 101.33 |
| clean / B2 | harm | 0.7551 | 61.90% / 67.25% | 67.33% | 107.33 |
| clean / B3 | none | 0.7523 | 78.10% / 67.52% | 67.52% | 164.00 |
| clean / B3 | roles_first | 0.7153 | 68.57% / 67.15% | 85.20% | 115.33 |
| clean / B3 | history_first | 0.7153 | 68.57% / 67.15% | 85.20% | 115.33 |
| clean / B3 | random | 0.7153 | 68.57% / 67.15% | 85.20% | 115.33 |
| clean / B3 | entropy | 0.7148 | 65.71% / 67.29% | 85.18% | 111.33 |
| clean / B3 | harm | 0.7379 | 69.52% / 67.18% | 76.25% | 122.33 |
| clean | full_context_reference (unrestricted reference) | 0.7153 | 68.57% / 67.15% | 85.20% | 115.33 |
| delayed_unavailable / B1 | none | 0.7523 | 78.10% / 67.52% | 67.52% | 164.00 |
| delayed_unavailable / B1 | roles_first | 0.7167 | 83.81% / 67.52% | 81.81% | 173.33 |
| delayed_unavailable / B1 | history_first | 0.7167 | 83.81% / 67.52% | 81.81% | 173.33 |
| delayed_unavailable / B1 | random | 0.7167 | 83.81% / 67.52% | 81.81% | 173.33 |
| delayed_unavailable / B1 | entropy | 0.7168 | 80.95% / 67.52% | 81.54% | 169.67 |
| delayed_unavailable / B1 | harm | 0.7509 | 80.95% / 67.52% | 67.73% | 167.67 |
| delayed_unavailable / B2 | none | 0.7523 | 78.10% / 67.52% | 67.52% | 164.00 |
| delayed_unavailable / B2 | roles_first | 0.7167 | 83.81% / 67.52% | 81.81% | 173.33 |
| delayed_unavailable / B2 | history_first | 0.7547 | 71.43% / 67.39% | 67.41% | 135.00 |
| delayed_unavailable / B2 | random | 0.7223 | 77.14% / 67.46% | 74.73% | 156.67 |
| delayed_unavailable / B2 | entropy | 0.7187 | 76.19% / 67.44% | 81.41% | 143.33 |
| delayed_unavailable / B2 | harm | 0.7544 | 74.29% / 67.42% | 67.46% | 144.33 |
| delayed_unavailable / B3 | none | 0.7523 | 78.10% / 67.52% | 67.52% | 164.00 |
| delayed_unavailable / B3 | roles_first | 0.7172 | 80.00% / 67.48% | 81.28% | 160.00 |
| delayed_unavailable / B3 | history_first | 0.7273 | 75.24% / 67.41% | 72.90% | 141.67 |
| delayed_unavailable / B3 | random | 0.7202 | 78.10% / 67.44% | 77.20% | 153.33 |
| delayed_unavailable / B3 | entropy | 0.7180 | 75.24% / 67.43% | 81.00% | 144.00 |
| delayed_unavailable / B3 | harm | 0.7427 | 75.24% / 67.43% | 69.20% | 146.33 |
| delayed_unavailable | full_context_reference (unrestricted reference) | 0.7153 | 68.57% / 67.15% | 85.20% | 115.33 |
| wrong_host_history / B1 | none | 0.7523 | 78.10% / 67.52% | 67.52% | 164.00 |
| wrong_host_history / B1 | roles_first | 0.7136 | 85.71% / 67.52% | 88.34% | 179.67 |
| wrong_host_history / B1 | history_first | 0.7136 | 85.71% / 67.52% | 88.34% | 179.67 |
| wrong_host_history / B1 | random | 0.7136 | 85.71% / 67.52% | 88.34% | 179.67 |
| wrong_host_history / B1 | entropy | 0.7139 | 81.90% / 67.52% | 87.95% | 174.00 |
| wrong_host_history / B1 | harm | 0.7500 | 81.90% / 67.52% | 67.83% | 169.67 |
| wrong_host_history / B2 | none | 0.7523 | 78.10% / 67.52% | 67.52% | 164.00 |
| wrong_host_history / B2 | roles_first | 0.7136 | 85.71% / 67.52% | 88.34% | 179.67 |
| wrong_host_history / B2 | history_first | 0.5449 | 23.81% / 66.89% | 66.89% | 39.67 |
| wrong_host_history / B2 | random | 0.6577 | 58.10% / 67.22% | 77.61% | 110.33 |
| wrong_host_history / B2 | entropy | 0.5687 | 40.00% / 67.20% | 87.46% | 66.00 |
| wrong_host_history / B2 | harm | 0.6921 | 40.95% / 67.08% | 67.13% | 81.00 |
| wrong_host_history / B3 | none | 0.7523 | 78.10% / 67.52% | 67.52% | 164.00 |
| wrong_host_history / B3 | roles_first | 0.6793 | 43.81% / 66.96% | 77.38% | 74.00 |
| wrong_host_history / B3 | history_first | 0.6793 | 43.81% / 66.96% | 77.38% | 74.00 |
| wrong_host_history / B3 | random | 0.6793 | 43.81% / 66.96% | 77.38% | 74.00 |
| wrong_host_history / B3 | entropy | 0.6873 | 40.00% / 67.22% | 77.52% | 73.00 |
| wrong_host_history / B3 | harm | 0.6763 | 43.81% / 67.01% | 77.37% | 87.00 |
| wrong_host_history | full_context_reference (unrestricted reference) | 0.6793 | 43.81% / 66.96% | 77.38% | 74.00 |

## PX082

| Condition / view / budget | Arm | Macro-F1 | Exact recall: movement / exfil. | Exfil. warning recall | Benign flags |
|---|---|---:|---:|---:|---:|
| current | past_only_anchor | 0.7365 | 25.93% / 67.25% | 67.27% | 24.00 |
| current | time_mixed_anchor | 0.7997 | 61.11% / 98.72% | 99.28% | 88.67 |
| current | conventional_random | 0.8093 | 57.84% / 92.15% | 99.74% | 84.00 |
| current_history | past_only_anchor | 0.7582 | 29.63% / 66.40% | 66.86% | 14.33 |
| current_history | time_mixed_anchor | 0.7964 | 57.41% / 84.59% | 84.71% | 47.67 |
| current_history | conventional_random | 0.8507 | 64.71% / 97.48% | 99.72% | 49.33 |

## PX083

### casino

| Condition | Arm | T1105 F1 | Recall | AP / ROC-AUC | Other-label flags |
|---|---|---:|---:|---:|---:|
| clean | current | 0.7368 | 82.35% | 0.8674 / 0.9607 | 7.00 |
| clean | context | 0.5957 | 82.35% | 0.8522 / 0.9762 | 16.00 |
| clean | fixed_fusion | 0.7179 | 82.35% | 0.8606 / 0.9711 | 8.00 |
| clean | mixed_dropout | 0.5833 | 82.35% | 0.8438 / 0.9693 | 17.00 |
| clean | confidence_gate | 0.7179 | 82.35% | 0.8717 / 0.9684 | 8.00 |
| clean | ordinary_gate | 0.7368 | 82.35% | 0.8672 / 0.9682 | 7.00 |
| clean | target_cost_gate | 0.5957 | 82.35% | 0.8580 / 0.9667 | 16.00 |
| random_25 | current | 0.3996 | 86.27% | 0.7923 / 0.9622 | 41.67 |
| random_25 | context | 0.5271 | 82.35% | 0.8028 / 0.9714 | 22.33 |
| random_25 | fixed_fusion | 0.4665 | 84.31% | 0.8057 / 0.9678 | 30.33 |
| random_25 | mixed_dropout | 0.5468 | 82.35% | 0.8109 / 0.9623 | 20.67 |
| random_25 | confidence_gate | 0.4665 | 84.31% | 0.7988 / 0.9652 | 30.33 |
| random_25 | ordinary_gate | 0.3996 | 86.27% | 0.8025 / 0.9651 | 41.67 |
| random_25 | target_cost_gate | 0.5271 | 82.35% | 0.8055 / 0.9647 | 22.33 |
| random_50 | current | 0.2368 | 88.24% | 0.6548 / 0.9468 | 94.67 |
| random_50 | context | 0.3274 | 80.39% | 0.7210 / 0.9545 | 53.00 |
| random_50 | fixed_fusion | 0.2768 | 84.31% | 0.6934 / 0.9511 | 72.33 |
| random_50 | mixed_dropout | 0.3649 | 78.43% | 0.7728 / 0.9556 | 43.00 |
| random_50 | confidence_gate | 0.2768 | 84.31% | 0.6700 / 0.9494 | 72.33 |
| random_50 | ordinary_gate | 0.2368 | 88.24% | 0.7181 / 0.9520 | 94.67 |
| random_50 | target_cost_gate | 0.3274 | 80.39% | 0.7211 / 0.9512 | 53.00 |
| random_75 | current | 0.1361 | 72.55% | 0.5075 / 0.8203 | 150.67 |
| random_75 | context | 0.1946 | 68.63% | 0.5781 / 0.8252 | 91.00 |
| random_75 | fixed_fusion | 0.1678 | 70.59% | 0.5482 / 0.8238 | 114.33 |
| random_75 | mixed_dropout | 0.2084 | 62.75% | 0.5962 / 0.8339 | 75.00 |
| random_75 | confidence_gate | 0.1678 | 70.59% | 0.5257 / 0.8217 | 114.33 |
| random_75 | ordinary_gate | 0.1361 | 72.55% | 0.5753 / 0.8255 | 150.67 |
| random_75 | target_cost_gate | 0.1946 | 68.63% | 0.5783 / 0.8256 | 91.00 |
| support_burst_60 | current | 0.7368 | 82.35% | 0.8674 / 0.9607 | 7.00 |
| support_burst_60 | context | 0.5769 | 88.24% | 0.8500 / 0.9647 | 20.00 |
| support_burst_60 | fixed_fusion | 0.6818 | 88.24% | 0.8644 / 0.9650 | 12.00 |
| support_burst_60 | mixed_dropout | 0.4667 | 82.35% | 0.8161 / 0.9565 | 29.00 |
| support_burst_60 | confidence_gate | 0.6818 | 88.24% | 0.8581 / 0.9616 | 12.00 |
| support_burst_60 | ordinary_gate | 0.7368 | 82.35% | 0.8630 / 0.9618 | 7.00 |
| support_burst_60 | target_cost_gate | 0.5769 | 88.24% | 0.8518 / 0.9591 | 20.00 |
| command_records_absent | current | 0.2258 | 82.35% | 0.6714 / 0.9414 | 93.00 |
| command_records_absent | context | 0.3607 | 64.71% | 0.6319 / 0.9479 | 33.00 |
| command_records_absent | fixed_fusion | 0.4138 | 70.59% | 0.6424 / 0.9510 | 29.00 |
| command_records_absent | mixed_dropout | 0.2121 | 82.35% | 0.6939 / 0.9415 | 101.00 |
| command_records_absent | confidence_gate | 0.4138 | 70.59% | 0.6722 / 0.9496 | 29.00 |
| command_records_absent | ordinary_gate | 0.2258 | 82.35% | 0.6368 / 0.9506 | 93.00 |
| command_records_absent | target_cost_gate | 0.3607 | 64.71% | 0.6339 / 0.9480 | 33.00 |
| delay_30_deadline_0 | current | 0.2258 | 82.35% | 0.6714 / 0.9414 | 93.00 |
| delay_30_deadline_0 | context | 0.3729 | 64.71% | 0.6224 / 0.9505 | 31.00 |
| delay_30_deadline_0 | fixed_fusion | 0.4364 | 70.59% | 0.6427 / 0.9525 | 26.00 |
| delay_30_deadline_0 | mixed_dropout | 0.2205 | 82.35% | 0.6919 / 0.9426 | 96.00 |
| delay_30_deadline_0 | confidence_gate | 0.4364 | 70.59% | 0.6499 / 0.9506 | 26.00 |
| delay_30_deadline_0 | ordinary_gate | 0.2258 | 82.35% | 0.6369 / 0.9511 | 93.00 |
| delay_30_deadline_0 | target_cost_gate | 0.3729 | 64.71% | 0.6241 / 0.9492 | 31.00 |
| delay_30_deadline_30 | current | 0.7368 | 82.35% | 0.8674 / 0.9607 | 7.00 |
| delay_30_deadline_30 | context | 0.5957 | 82.35% | 0.8522 / 0.9762 | 16.00 |
| delay_30_deadline_30 | fixed_fusion | 0.7179 | 82.35% | 0.8606 / 0.9711 | 8.00 |
| delay_30_deadline_30 | mixed_dropout | 0.5833 | 82.35% | 0.8438 / 0.9693 | 17.00 |
| delay_30_deadline_30 | confidence_gate | 0.7179 | 82.35% | 0.8717 / 0.9684 | 8.00 |
| delay_30_deadline_30 | ordinary_gate | 0.7368 | 82.35% | 0.8672 / 0.9682 | 7.00 |
| delay_30_deadline_30 | target_cost_gate | 0.5957 | 82.35% | 0.8580 / 0.9667 | 16.00 |
| delay_120_deadline_0 | current | 0.2258 | 82.35% | 0.6714 / 0.9414 | 93.00 |
| delay_120_deadline_0 | context | 0.3607 | 64.71% | 0.6319 / 0.9479 | 33.00 |
| delay_120_deadline_0 | fixed_fusion | 0.4138 | 70.59% | 0.6424 / 0.9510 | 29.00 |
| delay_120_deadline_0 | mixed_dropout | 0.2121 | 82.35% | 0.6939 / 0.9415 | 101.00 |
| delay_120_deadline_0 | confidence_gate | 0.4138 | 70.59% | 0.6722 / 0.9496 | 29.00 |
| delay_120_deadline_0 | ordinary_gate | 0.2258 | 82.35% | 0.6368 / 0.9506 | 93.00 |
| delay_120_deadline_0 | target_cost_gate | 0.3607 | 64.71% | 0.6339 / 0.9480 | 33.00 |
| delay_120_deadline_30 | current | 0.2258 | 82.35% | 0.6714 / 0.9414 | 93.00 |
| delay_120_deadline_30 | context | 0.3607 | 64.71% | 0.6335 / 0.9495 | 33.00 |
| delay_120_deadline_30 | fixed_fusion | 0.4138 | 70.59% | 0.6428 / 0.9522 | 29.00 |
| delay_120_deadline_30 | mixed_dropout | 0.2105 | 82.35% | 0.6958 / 0.9423 | 102.00 |
| delay_120_deadline_30 | confidence_gate | 0.4138 | 70.59% | 0.6732 / 0.9500 | 29.00 |
| delay_120_deadline_30 | ordinary_gate | 0.2258 | 82.35% | 0.6368 / 0.9507 | 93.00 |
| delay_120_deadline_30 | target_cost_gate | 0.3607 | 64.71% | 0.6349 / 0.9484 | 33.00 |
| delay_120_deadline_120 | current | 0.7368 | 82.35% | 0.8674 / 0.9607 | 7.00 |
| delay_120_deadline_120 | context | 0.5957 | 82.35% | 0.8522 / 0.9762 | 16.00 |
| delay_120_deadline_120 | fixed_fusion | 0.7179 | 82.35% | 0.8606 / 0.9711 | 8.00 |
| delay_120_deadline_120 | mixed_dropout | 0.5833 | 82.35% | 0.8438 / 0.9693 | 17.00 |
| delay_120_deadline_120 | confidence_gate | 0.7179 | 82.35% | 0.8717 / 0.9684 | 8.00 |
| delay_120_deadline_120 | ordinary_gate | 0.7368 | 82.35% | 0.8672 / 0.9682 | 7.00 |
| delay_120_deadline_120 | target_cost_gate | 0.5957 | 82.35% | 0.8580 / 0.9667 | 16.00 |
| execve_absent | current | 0.3226 | 88.24% | 0.8508 / 0.9724 | 61.00 |
| execve_absent | context | 0.3704 | 88.24% | 0.8408 / 0.9836 | 49.00 |
| execve_absent | fixed_fusion | 0.4000 | 88.24% | 0.8556 / 0.9785 | 43.00 |
| execve_absent | mixed_dropout | 0.5091 | 82.35% | 0.8138 / 0.9653 | 24.00 |
| execve_absent | confidence_gate | 0.4000 | 88.24% | 0.8526 / 0.9780 | 43.00 |
| execve_absent | ordinary_gate | 0.3226 | 88.24% | 0.8530 / 0.9774 | 61.00 |
| execve_absent | target_cost_gate | 0.3704 | 88.24% | 0.8388 / 0.9775 | 49.00 |
| proctitle_absent | current | 0.7778 | 82.35% | 0.8081 / 0.9476 | 5.00 |
| proctitle_absent | context | 0.7179 | 82.35% | 0.7788 / 0.9666 | 8.00 |
| proctitle_absent | fixed_fusion | 0.7778 | 82.35% | 0.7816 / 0.9616 | 5.00 |
| proctitle_absent | mixed_dropout | 0.3784 | 82.35% | 0.7978 / 0.9542 | 43.00 |
| proctitle_absent | confidence_gate | 0.7778 | 82.35% | 0.8230 / 0.9597 | 5.00 |
| proctitle_absent | ordinary_gate | 0.7778 | 82.35% | 0.7840 / 0.9592 | 5.00 |
| proctitle_absent | target_cost_gate | 0.7179 | 82.35% | 0.7852 / 0.9575 | 8.00 |
| syscall_absent | current | 0.3636 | 94.12% | 0.8738 / 0.9505 | 55.00 |
| syscall_absent | context | 0.6522 | 88.24% | 0.8762 / 0.9488 | 14.00 |
| syscall_absent | fixed_fusion | 0.5263 | 88.24% | 0.8760 / 0.9495 | 25.00 |
| syscall_absent | mixed_dropout | 0.8000 | 82.35% | 0.8748 / 0.9543 | 4.00 |
| syscall_absent | confidence_gate | 0.5263 | 88.24% | 0.8695 / 0.9487 | 25.00 |
| syscall_absent | ordinary_gate | 0.3636 | 94.12% | 0.8701 / 0.9487 | 55.00 |
| syscall_absent | target_cost_gate | 0.6522 | 88.24% | 0.8765 / 0.9486 | 14.00 |
| path_absent | current | 0.7692 | 88.24% | 0.8712 / 0.9558 | 7.00 |
| path_absent | context | 0.5926 | 94.12% | 0.8698 / 0.9761 | 21.00 |
| path_absent | fixed_fusion | 0.6522 | 88.24% | 0.8665 / 0.9696 | 14.00 |
| path_absent | mixed_dropout | 0.4918 | 88.24% | 0.8559 / 0.9764 | 29.00 |
| path_absent | confidence_gate | 0.6522 | 88.24% | 0.8626 / 0.9566 | 14.00 |
| path_absent | ordinary_gate | 0.7692 | 88.24% | 0.8548 / 0.9563 | 7.00 |
| path_absent | target_cost_gate | 0.5926 | 94.12% | 0.8685 / 0.9570 | 21.00 |

### camlds

| Condition | Arm | T1105 F1 | Recall | AP / ROC-AUC | Other-label flags |
|---|---|---:|---:|---:|---:|
| clean | current | 0.0495 | 87.00% | 0.0238 / 0.5087 | 3329.00 |
| clean | context | 0.0534 | 88.00% | 0.0277 / 0.5595 | 3108.00 |
| clean | fixed_fusion | 0.0524 | 88.00% | 0.0249 / 0.5381 | 3171.00 |
| clean | mixed_dropout | 0.0527 | 85.00% | 0.0276 / 0.5660 | 3038.00 |
| clean | confidence_gate | 0.0524 | 88.00% | 0.0250 / 0.5348 | 3171.00 |
| clean | ordinary_gate | 0.0495 | 87.00% | 0.0234 / 0.5070 | 3325.00 |
| clean | target_cost_gate | 0.0534 | 88.00% | 0.0277 / 0.5593 | 3108.00 |
| random_25 | current | 0.0454 | 49.33% | 0.0241 / 0.5064 | 2023.33 |
| random_25 | context | 0.0468 | 61.67% | 0.0290 / 0.5239 | 2474.33 |
| random_25 | fixed_fusion | 0.0475 | 59.00% | 0.0259 / 0.5159 | 2323.00 |
| random_25 | mixed_dropout | 0.0515 | 81.00% | 0.0259 / 0.5317 | 2967.33 |
| random_25 | confidence_gate | 0.0475 | 59.00% | 0.0286 / 0.5209 | 2323.00 |
| random_25 | ordinary_gate | 0.0455 | 49.33% | 0.0248 / 0.5164 | 2020.00 |
| random_25 | target_cost_gate | 0.0468 | 61.67% | 0.0290 / 0.5242 | 2474.33 |
| random_50 | current | 0.0452 | 28.00% | 0.0248 / 0.5101 | 1112.33 |
| random_50 | context | 0.0469 | 51.00% | 0.0296 / 0.5277 | 2022.67 |
| random_50 | fixed_fusion | 0.0472 | 45.00% | 0.0300 / 0.5214 | 1760.67 |
| random_50 | mixed_dropout | 0.0491 | 71.00% | 0.0262 / 0.5279 | 2724.00 |
| random_50 | confidence_gate | 0.0472 | 45.00% | 0.0293 / 0.5246 | 1760.67 |
| random_50 | ordinary_gate | 0.0452 | 28.00% | 0.0256 / 0.5175 | 1111.00 |
| random_50 | target_cost_gate | 0.0469 | 51.00% | 0.0295 / 0.5257 | 2022.67 |
| random_75 | current | 0.0493 | 15.00% | 0.0250 / 0.5040 | 493.00 |
| random_75 | context | 0.0446 | 32.33% | 0.0254 / 0.4976 | 1318.33 |
| random_75 | fixed_fusion | 0.0427 | 24.33% | 0.0249 / 0.4999 | 1013.67 |
| random_75 | mixed_dropout | 0.0467 | 48.33% | 0.0242 / 0.4964 | 1920.33 |
| random_75 | confidence_gate | 0.0427 | 24.33% | 0.0253 / 0.4980 | 1013.67 |
| random_75 | ordinary_gate | 0.0493 | 15.00% | 0.0253 / 0.5053 | 493.00 |
| random_75 | target_cost_gate | 0.0446 | 32.33% | 0.0254 / 0.4987 | 1318.33 |
| support_burst_60 | current | 0.0495 | 87.00% | 0.0238 / 0.5087 | 3329.00 |
| support_burst_60 | context | 0.0490 | 95.00% | 0.0223 / 0.4862 | 3685.00 |
| support_burst_60 | fixed_fusion | 0.0500 | 92.00% | 0.0224 / 0.4956 | 3491.00 |
| support_burst_60 | mixed_dropout | 0.0488 | 91.00% | 0.0216 / 0.4811 | 3541.00 |
| support_burst_60 | confidence_gate | 0.0500 | 92.00% | 0.0224 / 0.4907 | 3491.00 |
| support_burst_60 | ordinary_gate | 0.0495 | 87.00% | 0.0238 / 0.5079 | 3326.00 |
| support_burst_60 | target_cost_gate | 0.0490 | 95.00% | 0.0223 / 0.4862 | 3685.00 |
| command_records_absent | current | 0.0000 | 0.00% | 0.0241 / 0.5046 | 2.00 |
| command_records_absent | context | 0.0384 | 15.00% | 0.0250 / 0.5338 | 666.00 |
| command_records_absent | fixed_fusion | 0.0000 | 0.00% | 0.0245 / 0.5254 | 4.00 |
| command_records_absent | mixed_dropout | 0.0532 | 84.00% | 0.0256 / 0.5444 | 2976.00 |
| command_records_absent | confidence_gate | 0.0000 | 0.00% | 0.0242 / 0.5293 | 4.00 |
| command_records_absent | ordinary_gate | 0.0000 | 0.00% | 0.0253 / 0.5378 | 2.00 |
| command_records_absent | target_cost_gate | 0.0384 | 15.00% | 0.0247 / 0.5305 | 666.00 |
| delay_30_deadline_0 | current | 0.0000 | 0.00% | 0.0241 / 0.5046 | 2.00 |
| delay_30_deadline_0 | context | 0.0319 | 4.00% | 0.0249 / 0.5306 | 147.00 |
| delay_30_deadline_0 | fixed_fusion | 0.0000 | 0.00% | 0.0238 / 0.5191 | 13.00 |
| delay_30_deadline_0 | mixed_dropout | 0.0518 | 79.00% | 0.0289 / 0.5706 | 2870.00 |
| delay_30_deadline_0 | confidence_gate | 0.0000 | 0.00% | 0.0244 / 0.5241 | 13.00 |
| delay_30_deadline_0 | ordinary_gate | 0.0000 | 0.00% | 0.0247 / 0.5269 | 2.00 |
| delay_30_deadline_0 | target_cost_gate | 0.0319 | 4.00% | 0.0252 / 0.5280 | 147.00 |
| delay_30_deadline_30 | current | 0.0495 | 87.00% | 0.0238 / 0.5087 | 3329.00 |
| delay_30_deadline_30 | context | 0.0534 | 88.00% | 0.0277 / 0.5595 | 3108.00 |
| delay_30_deadline_30 | fixed_fusion | 0.0524 | 88.00% | 0.0249 / 0.5381 | 3171.00 |
| delay_30_deadline_30 | mixed_dropout | 0.0527 | 85.00% | 0.0276 / 0.5660 | 3038.00 |
| delay_30_deadline_30 | confidence_gate | 0.0524 | 88.00% | 0.0250 / 0.5348 | 3171.00 |
| delay_30_deadline_30 | ordinary_gate | 0.0495 | 87.00% | 0.0234 / 0.5070 | 3325.00 |
| delay_30_deadline_30 | target_cost_gate | 0.0534 | 88.00% | 0.0277 / 0.5593 | 3108.00 |
| delay_120_deadline_0 | current | 0.0000 | 0.00% | 0.0241 / 0.5046 | 2.00 |
| delay_120_deadline_0 | context | 0.0384 | 15.00% | 0.0250 / 0.5338 | 666.00 |
| delay_120_deadline_0 | fixed_fusion | 0.0000 | 0.00% | 0.0245 / 0.5254 | 4.00 |
| delay_120_deadline_0 | mixed_dropout | 0.0532 | 84.00% | 0.0256 / 0.5444 | 2976.00 |
| delay_120_deadline_0 | confidence_gate | 0.0000 | 0.00% | 0.0242 / 0.5293 | 4.00 |
| delay_120_deadline_0 | ordinary_gate | 0.0000 | 0.00% | 0.0253 / 0.5378 | 2.00 |
| delay_120_deadline_0 | target_cost_gate | 0.0384 | 15.00% | 0.0247 / 0.5305 | 666.00 |
| delay_120_deadline_30 | current | 0.0000 | 0.00% | 0.0241 / 0.5046 | 2.00 |
| delay_120_deadline_30 | context | 0.0331 | 8.00% | 0.0247 / 0.5294 | 376.00 |
| delay_120_deadline_30 | fixed_fusion | 0.0000 | 0.00% | 0.0242 / 0.5211 | 6.00 |
| delay_120_deadline_30 | mixed_dropout | 0.0529 | 86.00% | 0.0259 / 0.5443 | 3063.00 |
| delay_120_deadline_30 | confidence_gate | 0.0000 | 0.00% | 0.0244 / 0.5272 | 6.00 |
| delay_120_deadline_30 | ordinary_gate | 0.0000 | 0.00% | 0.0249 / 0.5315 | 2.00 |
| delay_120_deadline_30 | target_cost_gate | 0.0331 | 8.00% | 0.0242 / 0.5241 | 376.00 |
| delay_120_deadline_120 | current | 0.0495 | 87.00% | 0.0238 / 0.5087 | 3329.00 |
| delay_120_deadline_120 | context | 0.0534 | 88.00% | 0.0277 / 0.5595 | 3108.00 |
| delay_120_deadline_120 | fixed_fusion | 0.0524 | 88.00% | 0.0249 / 0.5381 | 3171.00 |
| delay_120_deadline_120 | mixed_dropout | 0.0527 | 85.00% | 0.0276 / 0.5660 | 3038.00 |
| delay_120_deadline_120 | confidence_gate | 0.0524 | 88.00% | 0.0250 / 0.5348 | 3171.00 |
| delay_120_deadline_120 | ordinary_gate | 0.0495 | 87.00% | 0.0234 / 0.5070 | 3325.00 |
| delay_120_deadline_120 | target_cost_gate | 0.0534 | 88.00% | 0.0277 / 0.5593 | 3108.00 |
| execve_absent | current | 0.0478 | 84.00% | 0.0243 / 0.5096 | 3327.00 |
| execve_absent | context | 0.0514 | 74.00% | 0.0257 / 0.5388 | 2707.00 |
| execve_absent | fixed_fusion | 0.0506 | 77.00% | 0.0245 / 0.5227 | 2865.00 |
| execve_absent | mixed_dropout | 0.0525 | 85.00% | 0.0294 / 0.5795 | 3053.00 |
| execve_absent | confidence_gate | 0.0506 | 77.00% | 0.0248 / 0.5272 | 2865.00 |
| execve_absent | ordinary_gate | 0.0479 | 84.00% | 0.0235 / 0.5023 | 3321.00 |
| execve_absent | target_cost_gate | 0.0514 | 74.00% | 0.0256 / 0.5343 | 2707.00 |
| proctitle_absent | current | 0.0075 | 1.00% | 0.0237 / 0.5038 | 165.00 |
| proctitle_absent | context | 0.0406 | 22.00% | 0.0243 / 0.5299 | 962.00 |
| proctitle_absent | fixed_fusion | 0.0000 | 0.00% | 0.0243 / 0.5294 | 27.00 |
| proctitle_absent | mixed_dropout | 0.0515 | 85.00% | 0.0255 / 0.5381 | 3116.00 |
| proctitle_absent | confidence_gate | 0.0000 | 0.00% | 0.0252 / 0.5366 | 27.00 |
| proctitle_absent | ordinary_gate | 0.0075 | 1.00% | 0.0245 / 0.5282 | 165.00 |
| proctitle_absent | target_cost_gate | 0.0406 | 22.00% | 0.0243 / 0.5308 | 962.00 |
| syscall_absent | current | 0.0404 | 9.00% | 0.0251 / 0.5275 | 336.00 |
| syscall_absent | context | 0.0445 | 53.00% | 0.0276 / 0.5144 | 2230.00 |
| syscall_absent | fixed_fusion | 0.0457 | 52.00% | 0.0247 / 0.5172 | 2122.00 |
| syscall_absent | mixed_dropout | 0.0510 | 85.00% | 0.0246 / 0.5189 | 3151.00 |
| syscall_absent | confidence_gate | 0.0457 | 52.00% | 0.0279 / 0.5247 | 2122.00 |
| syscall_absent | ordinary_gate | 0.0404 | 9.00% | 0.0249 / 0.5224 | 336.00 |
| syscall_absent | target_cost_gate | 0.0445 | 53.00% | 0.0277 / 0.5179 | 2230.00 |
| path_absent | current | 0.0494 | 96.00% | 0.0275 / 0.5628 | 3692.00 |
| path_absent | context | 0.0506 | 94.00% | 0.0293 / 0.5723 | 3525.00 |
| path_absent | fixed_fusion | 0.0494 | 94.00% | 0.0306 / 0.5783 | 3610.00 |
| path_absent | mixed_dropout | 0.0499 | 76.00% | 0.0276 / 0.5488 | 2868.00 |
| path_absent | confidence_gate | 0.0494 | 94.00% | 0.0288 / 0.5666 | 3610.00 |
| path_absent | ordinary_gate | 0.0495 | 96.00% | 0.0277 / 0.5661 | 3684.00 |
| path_absent | target_cost_gate | 0.0506 | 94.00% | 0.0293 / 0.5724 | 3525.00 |
