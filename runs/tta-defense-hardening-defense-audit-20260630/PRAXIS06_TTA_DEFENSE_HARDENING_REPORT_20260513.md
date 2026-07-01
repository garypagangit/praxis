# Praxis 06 TTA Defense Hardening Report

Generated: 2026-07-01T00:24:11.650531+00:00

## Scope

This report does not replace the locked 2026-05-09 replay. Original seeds use their validation-selected locked thresholds. Extra seeds, when present, use a fixed canonical extension (`uncertainty=0.50`, `recon_rescue=0.50`, `de_keep=0.00`) with no new threshold search.

## Seed Extension Summary

| method | threshold_source | accuracy_mean | macro_f1_mean | macro_f1_std | recon_f1_mean | recon_f1_std | de_f1_mean | de_f1_std | pr_auc_mean | override_rate_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| frozen | fixed_canonical_extension_no_new_search | 0.8849 | 0.7165 | 0.0412 | 0.0615 | 0.0902 | 0.6318 | 0.1667 | 0.7919 | nan |
| frozen | original_locked_validation_selection | 0.8984 | 0.7685 | 0.0118 | 0.0250 | 0.0401 | 0.9157 | 0.0260 | 0.8732 | nan |
| locked_hybrid | fixed_canonical_extension_no_new_search | 0.9165 | 0.8341 | 0.0173 | 0.5219 | 0.0472 | 0.7559 | 0.1198 | 0.8165 | 0.0649 |
| locked_hybrid | original_locked_validation_selection | 0.9243 | 0.8658 | 0.0146 | 0.5050 | 0.0825 | 0.9202 | 0.0038 | 0.8738 | 0.0470 |

## BN Stream-Order Ablation

| method | threshold_source | macro_f1_mean | recon_f1_mean | de_f1_mean | override_rate_mean |
| --- | --- | --- | --- | --- | --- |
| frozen | fixed_canonical_extension_no_new_search | 0.7165 | 0.0615 | 0.6318 | nan |
| frozen | original_locked_validation_selection | 0.7685 | 0.0250 | 0.9157 | nan |
| locked_hybrid_bn_shuffled_stream | fixed_canonical_extension_no_new_search | 0.7778 | 0.3414 | 0.6590 | 0.0480 |
| locked_hybrid_bn_shuffled_stream | original_locked_validation_selection | 0.8352 | 0.3364 | 0.9293 | 0.0298 |

## Validation-Distribution Sensitivity

| sample_seed | macro_f1_mean | macro_f1_std | recon_f1_mean | recon_f1_std | de_f1_mean | de_f1_std | override_rate_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 101 | 0.8335 | 0.0354 | 0.4397 | 0.1431 | 0.8263 | 0.1220 | 0.0479 |
| 202 | 0.8428 | 0.0306 | 0.4858 | 0.0689 | 0.8263 | 0.1220 | 0.0519 |

## Override Decomposition

| split | override_rate_mean | override_to_recon_fraction_mean | override_to_de_fraction_mean | override_from_de_sum | protected_de_count_mean |
| --- | --- | --- | --- | --- | --- |
| test | 0.0572 | 0.8075 | 0.1064 | 0 | 1682.2857 |
| test_shuffle_bn_order | 0.0402 | 0.8000 | 0.0897 | 0 | 1682.2857 |

## DE Safety

| seed | split | true_de_rows_in_detail | true_de_frozen_correct | true_de_hybrid_correct | changed_to_de_count | changed_to_de_true_de_count | changed_to_de_non_de_count | changed_to_de_mean_tta_conf | changed_to_de_max_tta_conf | changed_from_de_count | changed_from_de_true_de_count | changed_from_de_mean_frozen_conf |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | test | 2192 | 2025 | 2030 | 53 | 5 | 48 | 0.7102 | 0.9864 | 0 | 0 | nan |
| 42 | test_shuffle_bn_order | 2192 | 2025 | 2069 | 72 | 44 | 28 | 0.6542 | 0.8989 | 0 | 0 | nan |
| 43 | test | 2192 | 2087 | 2092 | 90 | 5 | 85 | 0.7539 | 0.9982 | 0 | 0 | nan |
| 43 | test_shuffle_bn_order | 2192 | 2087 | 2099 | 60 | 12 | 48 | 0.6070 | 0.9327 | 0 | 0 | nan |
| 44 | test | 2192 | 1881 | 2066 | 223 | 185 | 38 | 0.8240 | 0.9969 | 0 | 0 | nan |
| 44 | test_shuffle_bn_order | 2192 | 1881 | 2071 | 212 | 190 | 22 | 0.7942 | 0.9425 | 0 | 0 | nan |
| 45 | test | 2192 | 1083 | 1710 | 775 | 627 | 148 | 0.8084 | 0.9860 | 0 | 0 | nan |
| 45 | test_shuffle_bn_order | 2192 | 1083 | 1808 | 847 | 725 | 122 | 0.5926 | 0.8792 | 0 | 0 | nan |
| 46 | test | 2192 | 1502 | 1829 | 367 | 327 | 40 | 0.7852 | 0.9991 | 0 | 0 | nan |
| 46 | test_shuffle_bn_order | 2192 | 1502 | 1508 | 33 | 6 | 27 | 0.6055 | 0.9267 | 0 | 0 | nan |
| 47 | test | 2192 | 582 | 1039 | 487 | 457 | 30 | 0.8927 | 0.9823 | 0 | 0 | nan |
| 47 | test_shuffle_bn_order | 2192 | 582 | 591 | 20 | 9 | 11 | 0.5184 | 0.7582 | 0 | 0 | nan |
| 48 | test | 2192 | 1372 | 1787 | 1085 | 415 | 670 | 0.5402 | 0.8478 | 0 | 0 | nan |
| 48 | test_shuffle_bn_order | 2192 | 1372 | 1410 | 838 | 38 | 800 | 0.4854 | 0.6947 | 0 | 0 | nan |

## Feature-Shift Diagnostic

| dataset | split | features | median_abs_standardized_mean_shift | p90_abs_standardized_mean_shift | max_abs_standardized_mean_shift | median_abs_log_std_ratio | p90_abs_log_std_ratio | features_std_ratio_gt_2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Unraveled | test | 67 | 0.0165 | 0.1877 | 0.3253 | 0.1192 | 1.3202 | 11 |
| Unraveled | val | 67 | 0.0897 | 0.5702 | 1.0262 | 0.3861 | 2.6548 | 18 |

## Main Artifact Files

- `fixed_locked_seed_extension_metrics.csv`
- `validation_distribution_sensitivity.csv`
- `override_flow.csv`
- `de_safety_analysis.csv`
- `pr_operating_points.csv`
- `figure_recon_pr_operating_points.png`
- `figure_de_pr_operating_points.png`
- `feature_shift_summary.csv`

## Interpretation Notes

- PR-AUC should be framed as representation quality / ranking signal. The main result is a locked operating-point and decision-policy improvement, not a broad probability-quality gain.
- BN-adapt protocol: single pass, unlabeled stream, `DataLoader(..., shuffle=False)`, batch size 4096 by default, dropout in eval mode, BatchNorm layers in train mode, PyTorch BatchNorm1d default momentum unless changed by the model, and no test labels.
- DAPT remains a negative TTA feasibility check. The feature-shift diagnostic is a mechanism clue, not a new external-validity claim.