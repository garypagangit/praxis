# OpTC Expanded Provenance Gate

Generated: 2026-05-15

Status: **LABEL-READY, DETECTOR NOT PROMOTED**

## Scope

This gate tests whether OpTC interval labels plus targeted eCAR host/day shards are strong enough for a narrow provenance-window detector feasibility claim.

- Red-team slices: `sysclient0201` day 1 / `23Sep19-red`, `sysclient0501` day 2 / `24Sep19`, and `sysclient0051` day 3 / `25Sept`
- Benign baselines: `sysclient0201`, `sysclient0501`, and `sysclient0051` from `benign/20-23Sep19`
- Target: `attack` vs `background` windows
- Excluded: `gray_buffer` windows
- Primary detector split: hold out one red-team host/day and train on the other red-team slices plus benign baselines, including the held-out host's clean baseline
- Strict generalization split: hold out the entire host, including its red-team and benign windows
- Pairwise stress split: train on one red-team host/day plus all benign baselines, then test on the other red-team host/days
- Sanity split: pooled stratified random split across all non-gray windows
- Conservative feature view: event counts plus aggregate window statistics; `exec__*` columns excluded
- Full feature view: event, exec, and aggregate behavior columns
- Time columns and label-derived columns excluded from all detector features

## Label Support

| Slice | Kind | Host | Day | Attack | Background | Gray buffer | Total |
|---|---|---|---|---:|---:|---:|---:|
| `sysclient0051_benign` | `benign_baseline` | `sysclient0051` | `benign_20_23Sep19` | `0` | `100` | `0` | `100` |
| `sysclient0051_day3` | `red_team` | `sysclient0051` | `3` | `41` | `107` | `52` | `200` |
| `sysclient0201_benign` | `benign_baseline` | `sysclient0201` | `benign_20_23Sep19` | `0` | `100` | `0` | `100` |
| `sysclient0201_day1` | `red_team` | `sysclient0201` | `1` | `112` | `54` | `34` | `200` |
| `sysclient0501_benign` | `benign_baseline` | `sysclient0501` | `benign_20_23Sep19` | `0` | `100` | `0` | `100` |
| `sysclient0501_day2` | `red_team` | `sysclient0501` | `2` | `82` | `21` | `22` | `125` |

## Host-Baselined Red-Day Holdout

| Feature mode | Held-out red slice | Detector | Accuracy | Macro-F1 | ROC-AUC | AP | Attack recall | Background recall |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `event_aggregate` | `sysclient0051_day3` | `extra_trees_balanced` | 0.4730 | 0.4398 | 0.4953 | 0.2797 | 0.4146 | 0.4953 |
| `event_aggregate` | `sysclient0051_day3` | `logreg_balanced` | 0.5270 | 0.4898 | 0.5220 | 0.2979 | 0.4634 | 0.5514 |
| `event_aggregate` | `sysclient0051_day3` | `mlp_small` | 0.5878 | 0.4553 | 0.4810 | 0.2712 | 0.1707 | 0.7477 |
| `event_aggregate` | `sysclient0051_day3` | `random_forest_balanced` | 0.5068 | 0.4565 | 0.5028 | 0.2989 | 0.3659 | 0.5607 |
| `event_aggregate` | `sysclient0201_day1` | `extra_trees_balanced` | 0.2410 | 0.2187 | 0.1787 | 0.5453 | 0.3036 | 0.1111 |
| `event_aggregate` | `sysclient0201_day1` | `logreg_balanced` | 0.3434 | 0.2688 | 0.1774 | 0.5675 | 0.4911 | 0.0370 |
| `event_aggregate` | `sysclient0201_day1` | `mlp_small` | 0.3675 | 0.3264 | 0.3889 | 0.6628 | 0.0893 | 0.9444 |
| `event_aggregate` | `sysclient0201_day1` | `random_forest_balanced` | 0.1988 | 0.1922 | 0.1293 | 0.5014 | 0.2143 | 0.1667 |
| `event_aggregate` | `sysclient0501_day2` | `extra_trees_balanced` | 0.4951 | 0.4517 | 0.4460 | 0.7415 | 0.4878 | 0.5238 |
| `event_aggregate` | `sysclient0501_day2` | `logreg_balanced` | 0.6602 | 0.5314 | 0.5755 | 0.8566 | 0.7439 | 0.3333 |
| `event_aggregate` | `sysclient0501_day2` | `mlp_small` | 0.2913 | 0.2913 | 0.4593 | 0.7468 | 0.1829 | 0.7143 |
| `event_aggregate` | `sysclient0501_day2` | `random_forest_balanced` | 0.3689 | 0.3602 | 0.4675 | 0.7459 | 0.3049 | 0.6190 |
| `all_behavior` | `sysclient0051_day3` | `extra_trees_balanced` | 0.5878 | 0.5100 | 0.4775 | 0.2742 | 0.3415 | 0.6822 |
| `all_behavior` | `sysclient0051_day3` | `logreg_balanced` | 0.5811 | 0.5111 | 0.5443 | 0.3196 | 0.3659 | 0.6636 |
| `all_behavior` | `sysclient0051_day3` | `mlp_small` | 0.6757 | 0.5216 | 0.4944 | 0.3105 | 0.1951 | 0.8598 |
| `all_behavior` | `sysclient0051_day3` | `random_forest_balanced` | 0.6622 | 0.5016 | 0.5448 | 0.3108 | 0.1707 | 0.8505 |
| `all_behavior` | `sysclient0201_day1` | `extra_trees_balanced` | 0.4458 | 0.3340 | 0.2285 | 0.5583 | 0.6339 | 0.0556 |
| `all_behavior` | `sysclient0201_day1` | `logreg_balanced` | 0.4880 | 0.4298 | 0.3403 | 0.5955 | 0.5982 | 0.2593 |
| `all_behavior` | `sysclient0201_day1` | `mlp_small` | 0.3614 | 0.3261 | 0.3626 | 0.6366 | 0.0982 | 0.9074 |
| `all_behavior` | `sysclient0201_day1` | `random_forest_balanced` | 0.3916 | 0.2892 | 0.1310 | 0.4950 | 0.5714 | 0.0185 |
| `all_behavior` | `sysclient0501_day2` | `extra_trees_balanced` | 0.5922 | 0.4122 | 0.3020 | 0.7001 | 0.7195 | 0.0952 |
| `all_behavior` | `sysclient0501_day2` | `logreg_balanced` | 0.4660 | 0.3819 | 0.3508 | 0.7430 | 0.5244 | 0.2381 |
| `all_behavior` | `sysclient0501_day2` | `mlp_small` | 0.1942 | 0.1865 | 0.2288 | 0.6723 | 0.0610 | 0.7143 |
| `all_behavior` | `sysclient0501_day2` | `random_forest_balanced` | 0.5146 | 0.4121 | 0.3810 | 0.7270 | 0.5854 | 0.2381 |

## Strict Host Holdout

| Feature mode | Held-out red slice | Detector | Accuracy | Macro-F1 | ROC-AUC | AP | Attack recall | Background recall |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `event_aggregate` | `sysclient0051_day3` | `extra_trees_balanced` | 0.4932 | 0.4667 | 0.4997 | 0.2818 | 0.4878 | 0.4953 |
| `event_aggregate` | `sysclient0051_day3` | `logreg_balanced` | 0.5541 | 0.5189 | 0.5341 | 0.3132 | 0.5122 | 0.5701 |
| `event_aggregate` | `sysclient0051_day3` | `mlp_small` | 0.4932 | 0.4554 | 0.4876 | 0.2705 | 0.4146 | 0.5234 |
| `event_aggregate` | `sysclient0051_day3` | `random_forest_balanced` | 0.5135 | 0.4829 | 0.5158 | 0.3212 | 0.4878 | 0.5234 |
| `event_aggregate` | `sysclient0201_day1` | `extra_trees_balanced` | 0.3072 | 0.2787 | 0.2452 | 0.5617 | 0.3750 | 0.1667 |
| `event_aggregate` | `sysclient0201_day1` | `logreg_balanced` | 0.3614 | 0.3083 | 0.2606 | 0.6087 | 0.4732 | 0.1296 |
| `event_aggregate` | `sysclient0201_day1` | `mlp_small` | 0.3313 | 0.2783 | 0.3818 | 0.6233 | 0.0446 | 0.9259 |
| `event_aggregate` | `sysclient0201_day1` | `random_forest_balanced` | 0.1928 | 0.1755 | 0.1480 | 0.5155 | 0.2500 | 0.0741 |
| `event_aggregate` | `sysclient0501_day2` | `extra_trees_balanced` | 0.4563 | 0.4278 | 0.4994 | 0.7642 | 0.4268 | 0.5714 |
| `event_aggregate` | `sysclient0501_day2` | `logreg_balanced` | 0.5922 | 0.5155 | 0.5232 | 0.8403 | 0.6220 | 0.4762 |
| `event_aggregate` | `sysclient0501_day2` | `mlp_small` | 0.1845 | 0.1713 | 0.3444 | 0.7134 | 0.0366 | 0.7619 |
| `event_aggregate` | `sysclient0501_day2` | `random_forest_balanced` | 0.4369 | 0.4211 | 0.5389 | 0.7673 | 0.3780 | 0.6667 |
| `all_behavior` | `sysclient0051_day3` | `extra_trees_balanced` | 0.5608 | 0.4904 | 0.5095 | 0.2963 | 0.3415 | 0.6449 |
| `all_behavior` | `sysclient0051_day3` | `logreg_balanced` | 0.6014 | 0.5131 | 0.5389 | 0.2977 | 0.3171 | 0.7103 |
| `all_behavior` | `sysclient0051_day3` | `mlp_small` | 0.6351 | 0.4845 | 0.4687 | 0.2979 | 0.1707 | 0.8131 |
| `all_behavior` | `sysclient0051_day3` | `random_forest_balanced` | 0.6014 | 0.4636 | 0.5452 | 0.3111 | 0.1707 | 0.7664 |
| `all_behavior` | `sysclient0201_day1` | `extra_trees_balanced` | 0.4699 | 0.3384 | 0.2953 | 0.6024 | 0.6786 | 0.0370 |
| `all_behavior` | `sysclient0201_day1` | `logreg_balanced` | 0.4759 | 0.4302 | 0.3831 | 0.6141 | 0.5625 | 0.2963 |
| `all_behavior` | `sysclient0201_day1` | `mlp_small` | 0.3373 | 0.3326 | 0.3505 | 0.6424 | 0.1875 | 0.6481 |
| `all_behavior` | `sysclient0201_day1` | `random_forest_balanced` | 0.4157 | 0.3019 | 0.1356 | 0.4945 | 0.6071 | 0.0185 |
| `all_behavior` | `sysclient0501_day2` | `extra_trees_balanced` | 0.5437 | 0.4030 | 0.3560 | 0.7170 | 0.6463 | 0.1429 |
| `all_behavior` | `sysclient0501_day2` | `logreg_balanced` | 0.4078 | 0.3254 | 0.2497 | 0.6939 | 0.4756 | 0.1429 |
| `all_behavior` | `sysclient0501_day2` | `mlp_small` | 0.3010 | 0.2977 | 0.2497 | 0.6882 | 0.2317 | 0.5714 |
| `all_behavior` | `sysclient0501_day2` | `random_forest_balanced` | 0.5534 | 0.4787 | 0.4675 | 0.7592 | 0.5854 | 0.4286 |

## Pairwise Red-Host Stress

| Train slice | Feature mode | Test red slices | Detector | Accuracy | Macro-F1 | ROC-AUC | AP | Attack recall | Background recall |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| `sysclient0051_day3_plus_benign` | `event_aggregate` | `other_red_days` | `extra_trees_balanced` | 0.3160 | 0.2884 | 0.4816 | 0.7116 | 0.0825 | 0.9200 |
| `sysclient0051_day3_plus_benign` | `event_aggregate` | `other_red_days` | `logreg_balanced` | 0.5799 | 0.5636 | 0.6495 | 0.8528 | 0.5361 | 0.6933 |
| `sysclient0051_day3_plus_benign` | `event_aggregate` | `other_red_days` | `mlp_small` | 0.2788 | 0.2180 | 0.3700 | 0.6477 | 0.0000 | 1.0000 |
| `sysclient0051_day3_plus_benign` | `event_aggregate` | `other_red_days` | `random_forest_balanced` | 0.2788 | 0.2280 | 0.5270 | 0.7286 | 0.0155 | 0.9600 |
| `sysclient0201_day1_plus_benign` | `event_aggregate` | `other_red_days` | `extra_trees_balanced` | 0.5060 | 0.5046 | 0.5238 | 0.4839 | 0.4634 | 0.5469 |
| `sysclient0201_day1_plus_benign` | `event_aggregate` | `other_red_days` | `logreg_balanced` | 0.5817 | 0.5771 | 0.5952 | 0.5789 | 0.6992 | 0.4688 |
| `sysclient0201_day1_plus_benign` | `event_aggregate` | `other_red_days` | `mlp_small` | 0.4741 | 0.4023 | 0.5163 | 0.5013 | 0.1301 | 0.8047 |
| `sysclient0201_day1_plus_benign` | `event_aggregate` | `other_red_days` | `random_forest_balanced` | 0.5100 | 0.4985 | 0.5295 | 0.4861 | 0.3659 | 0.6484 |
| `sysclient0501_day2_plus_benign` | `event_aggregate` | `other_red_days` | `extra_trees_balanced` | 0.4586 | 0.4543 | 0.4799 | 0.4845 | 0.3791 | 0.5342 |
| `sysclient0501_day2_plus_benign` | `event_aggregate` | `other_red_days` | `logreg_balanced` | 0.4395 | 0.4372 | 0.4542 | 0.5009 | 0.3856 | 0.4907 |
| `sysclient0501_day2_plus_benign` | `event_aggregate` | `other_red_days` | `mlp_small` | 0.5127 | 0.4174 | 0.5156 | 0.5174 | 0.1111 | 0.8944 |
| `sysclient0501_day2_plus_benign` | `event_aggregate` | `other_red_days` | `random_forest_balanced` | 0.4459 | 0.4326 | 0.4583 | 0.4761 | 0.3007 | 0.5839 |
| `sysclient0051_day3_plus_benign` | `all_behavior` | `other_red_days` | `extra_trees_balanced` | 0.3494 | 0.3362 | 0.5132 | 0.7387 | 0.1443 | 0.8800 |
| `sysclient0051_day3_plus_benign` | `all_behavior` | `other_red_days` | `logreg_balanced` | 0.5130 | 0.4970 | 0.5375 | 0.7510 | 0.4794 | 0.6000 |
| `sysclient0051_day3_plus_benign` | `all_behavior` | `other_red_days` | `mlp_small` | 0.3271 | 0.3031 | 0.4446 | 0.7155 | 0.0979 | 0.9200 |
| `sysclient0051_day3_plus_benign` | `all_behavior` | `other_red_days` | `random_forest_balanced` | 0.3086 | 0.2784 | 0.5762 | 0.7645 | 0.0722 | 0.9200 |
| `sysclient0201_day1_plus_benign` | `all_behavior` | `other_red_days` | `extra_trees_balanced` | 0.6255 | 0.6254 | 0.6284 | 0.5542 | 0.6260 | 0.6250 |
| `sysclient0201_day1_plus_benign` | `all_behavior` | `other_red_days` | `logreg_balanced` | 0.6175 | 0.6168 | 0.6085 | 0.5712 | 0.5854 | 0.6484 |
| `sysclient0201_day1_plus_benign` | `all_behavior` | `other_red_days` | `mlp_small` | 0.5139 | 0.4155 | 0.4955 | 0.5063 | 0.1057 | 0.9062 |
| `sysclient0201_day1_plus_benign` | `all_behavior` | `other_red_days` | `random_forest_balanced` | 0.6135 | 0.6035 | 0.6877 | 0.6224 | 0.4634 | 0.7578 |
| `sysclient0501_day2_plus_benign` | `all_behavior` | `other_red_days` | `extra_trees_balanced` | 0.4713 | 0.4703 | 0.5495 | 0.5428 | 0.4379 | 0.5031 |
| `sysclient0501_day2_plus_benign` | `all_behavior` | `other_red_days` | `logreg_balanced` | 0.5191 | 0.5165 | 0.4887 | 0.4978 | 0.4575 | 0.5776 |
| `sysclient0501_day2_plus_benign` | `all_behavior` | `other_red_days` | `mlp_small` | 0.4809 | 0.4098 | 0.4299 | 0.4689 | 0.1373 | 0.8075 |
| `sysclient0501_day2_plus_benign` | `all_behavior` | `other_red_days` | `random_forest_balanced` | 0.4809 | 0.4719 | 0.5493 | 0.5300 | 0.3595 | 0.5963 |

## Pooled Random Sanity Results

| Feature mode | Detector | Split | Accuracy | Macro-F1 | ROC-AUC | AP | Attack recall | Background recall |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `event_aggregate` | `extra_trees_balanced` | `validation` | 0.7692 | 0.7451 | 0.7903 | 0.6583 | 0.7021 | 0.8021 |
| `event_aggregate` | `extra_trees_balanced` | `test` | 0.7222 | 0.6907 | 0.7754 | 0.6482 | 0.6170 | 0.7732 |
| `event_aggregate` | `logreg_balanced` | `validation` | 0.7483 | 0.7178 | 0.8059 | 0.7151 | 0.6383 | 0.8021 |
| `event_aggregate` | `logreg_balanced` | `test` | 0.7153 | 0.6780 | 0.7734 | 0.6639 | 0.5745 | 0.7835 |
| `event_aggregate` | `mlp_small` | `validation` | 0.7273 | 0.6413 | 0.7061 | 0.5820 | 0.3617 | 0.9062 |
| `event_aggregate` | `mlp_small` | `test` | 0.7222 | 0.6069 | 0.7210 | 0.5654 | 0.2766 | 0.9381 |
| `event_aggregate` | `random_forest_balanced` | `validation` | 0.8042 | 0.7640 | 0.8076 | 0.7224 | 0.5957 | 0.9062 |
| `event_aggregate` | `random_forest_balanced` | `test` | 0.7361 | 0.6891 | 0.7826 | 0.6543 | 0.5319 | 0.8351 |
| `all_behavior` | `extra_trees_balanced` | `validation` | 0.8671 | 0.8518 | 0.9444 | 0.9090 | 0.8298 | 0.8854 |
| `all_behavior` | `extra_trees_balanced` | `test` | 0.8889 | 0.8750 | 0.9434 | 0.8818 | 0.8511 | 0.9072 |
| `all_behavior` | `logreg_balanced` | `validation` | 0.8392 | 0.8240 | 0.8985 | 0.8077 | 0.8298 | 0.8438 |
| `all_behavior` | `logreg_balanced` | `test` | 0.8403 | 0.8276 | 0.9412 | 0.8926 | 0.8723 | 0.8247 |
| `all_behavior` | `mlp_small` | `validation` | 0.6084 | 0.5344 | 0.5818 | 0.3822 | 0.3191 | 0.7500 |
| `all_behavior` | `mlp_small` | `test` | 0.6597 | 0.5965 | 0.6839 | 0.4907 | 0.4043 | 0.7835 |
| `all_behavior` | `random_forest_balanced` | `validation` | 0.8811 | 0.8674 | 0.9499 | 0.9048 | 0.8511 | 0.8958 |
| `all_behavior` | `random_forest_balanced` | `test` | 0.8889 | 0.8750 | 0.9487 | 0.9056 | 0.8511 | 0.9072 |

## Decision

The OpTC expansion clears label support across red-team and benign baseline slices, but the detector does not clear the conservative host-baselined holdout floor. Use this as a strong label/data unlock and keep detector claims blocked.

## Artifacts

| Artifact | Path |
|---|---|
| Summary JSON | `runs\optc-cross-host-gate-20260515\summary.json` |
| Metrics CSV | `runs\optc-cross-host-gate-20260515\metrics.csv` |
| Split assignments | `runs\optc-cross-host-gate-20260515\split_assignments.csv` |
