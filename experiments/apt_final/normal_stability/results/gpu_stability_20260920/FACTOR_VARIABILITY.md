# Encoder and reference-bank variability

Status: `POSTHOC_DESCRIPTIVE_NO_THRESHOLD_CHANGES`.

Each cell shows **encoder range / bank range**, in percentage points. A range compares seeds while the other seed, fold, strategy and condition are fixed; the table averages these ranges equally over the fixed settings and folds.

These are descriptive seed associations, not causes or percentages of explained variation. The two ranges are not additive. Folds overlap and attack results reuse exposed test data, so these repeats are not independent campaigns.

Local-feature encoder range is zero by construction. Its duplicate encoder copies are excluded from bank summaries and case counts. Bank seed also controls view assignment when the reference mixes clean and masked views.

| Dataset | Strategy | Representation | Condition | Unique cases per phase | Normal FPR | Attack FPR | Attack recall | Attack F1 |
|---|---|---|---|---:|---:|---:|---:|---:|
| cadets | clean | gin_knn | clean | 36 | 26.44 / 5.69 | 31.75 / 10.49 | 66.44 / 8.31 | 40.06 / 8.56 |
| cadets | clean | gin_knn | masked | 36 | 17.13 / 2.11 | 13.63 / 4.84 | 21.37 / 8.44 | 3.86 / 1.13 |
| cadets | clean | local_knn | clean | 12 | 0.00 / 0.11 | 0.00 / 0.73 | 0.00 / 0.08 | 0.00 / 0.12 |
| cadets | clean | local_knn | masked | 12 | 0.00 / 1.46 | 0.00 / 1.74 | 0.00 / 0.08 | 0.00 / 0.10 |
| cadets | clean | mlp_knn | clean | 36 | 0.20 / 0.14 | 0.16 / 0.19 | 0.03 / 0.02 | 0.04 / 0.04 |
| cadets | clean | mlp_knn | masked | 36 | 1.71 / 1.17 | 2.08 / 1.20 | 0.07 / 0.02 | 0.26 / 0.15 |
| cadets | pooled_calibration | gin_knn | clean | 36 | 0.03 / 0.02 | 0.03 / 0.03 | 0.00 / 0.00 | 0.00 / 0.00 |
| cadets | pooled_calibration | gin_knn | masked | 36 | 0.42 / 0.25 | 0.59 / 0.24 | 0.01 / 0.01 | 0.03 / 0.02 |
| cadets | pooled_calibration | local_knn | clean | 12 | 0.00 / 0.13 | 0.00 / 0.12 | 0.00 / 0.03 | 0.00 / 0.04 |
| cadets | pooled_calibration | local_knn | masked | 12 | 0.00 / 0.12 | 0.00 / 0.18 | 0.00 / 0.02 | 0.00 / 0.03 |
| cadets | pooled_calibration | mlp_knn | clean | 36 | 0.17 / 0.09 | 0.17 / 0.10 | 0.22 / 0.05 | 0.41 / 0.10 |
| cadets | pooled_calibration | mlp_knn | masked | 36 | 0.71 / 0.45 | 1.39 / 0.47 | 0.13 / 0.03 | 0.18 / 0.04 |
| cadets | pooled_reference_calibration | gin_knn | clean | 36 | 45.68 / 0.13 | 31.43 / 0.13 | 49.82 / 8.33 | 25.12 / 7.97 |
| cadets | pooled_reference_calibration | gin_knn | masked | 36 | 15.61 / 0.22 | 8.25 / 0.12 | 36.90 / 0.02 | 31.28 / 0.32 |
| cadets | pooled_reference_calibration | local_knn | clean | 12 | 0.00 / 0.07 | 0.00 / 0.10 | 0.00 / 0.02 | 0.00 / 0.03 |
| cadets | pooled_reference_calibration | local_knn | masked | 12 | 0.00 / 0.12 | 0.00 / 0.11 | 0.00 / 0.02 | 0.00 / 0.03 |
| cadets | pooled_reference_calibration | mlp_knn | clean | 36 | 0.22 / 0.13 | 0.17 / 0.14 | 0.10 / 0.06 | 0.16 / 0.10 |
| cadets | pooled_reference_calibration | mlp_knn | masked | 36 | 0.27 / 0.17 | 0.23 / 0.15 | 0.07 / 0.04 | 0.11 / 0.06 |
| theia | clean | gin_knn | clean | 36 | 2.47 / 0.41 | 1.13 / 0.50 | 41.91 / 6.99 | 36.77 / 6.79 |
| theia | clean | gin_knn | masked | 36 | 4.52 / 0.95 | 5.57 / 1.05 | 6.41 / 3.70 | 2.04 / 1.24 |
| theia | clean | local_knn | clean | 12 | 0.00 / 0.11 | 0.00 / 0.08 | 0.00 / 1.43 | 0.00 / 2.48 |
| theia | clean | local_knn | masked | 12 | 0.00 / 1.66 | 0.00 / 2.12 | 0.00 / 10.83 | 0.00 / 11.53 |
| theia | clean | mlp_knn | clean | 36 | 0.09 / 0.08 | 0.06 / 0.06 | 4.98 / 3.68 | 7.84 / 5.59 |
| theia | clean | mlp_knn | masked | 36 | 0.48 / 0.46 | 0.57 / 0.57 | 1.07 / 0.91 | 0.33 / 0.25 |
| theia | pooled_calibration | gin_knn | clean | 36 | 0.00 / 0.00 | 0.02 / 0.01 | 0.00 / 0.00 | 0.00 / 0.00 |
| theia | pooled_calibration | gin_knn | masked | 36 | 1.79 / 0.01 | 1.84 / 0.01 | 14.10 / 3.53 | 19.80 / 4.95 |
| theia | pooled_calibration | local_knn | clean | 12 | 0.00 / 0.10 | 0.00 / 0.10 | 0.00 / 0.08 | 0.00 / 0.15 |
| theia | pooled_calibration | local_knn | masked | 12 | 0.00 / 0.12 | 0.00 / 0.15 | 0.00 / 0.01 | 0.00 / 0.02 |
| theia | pooled_calibration | mlp_knn | clean | 36 | 0.35 / 0.06 | 0.33 / 0.05 | 0.03 / 0.01 | 0.07 / 0.02 |
| theia | pooled_calibration | mlp_knn | masked | 36 | 1.51 / 0.23 | 1.53 / 0.23 | 0.04 / 0.01 | 0.06 / 0.01 |
| theia | pooled_reference_calibration | gin_knn | clean | 36 | 0.51 / 0.15 | 0.69 / 0.25 | 42.64 / 7.06 | 31.24 / 6.55 |
| theia | pooled_reference_calibration | gin_knn | masked | 36 | 0.53 / 0.25 | 0.99 / 0.32 | 43.53 / 0.31 | 50.22 / 1.13 |
| theia | pooled_reference_calibration | local_knn | clean | 12 | 0.00 / 0.16 | 0.00 / 0.12 | 0.00 / 0.77 | 0.00 / 1.31 |
| theia | pooled_reference_calibration | local_knn | masked | 12 | 0.00 / 0.11 | 0.00 / 0.09 | 0.00 / 0.11 | 0.00 / 0.20 |
| theia | pooled_reference_calibration | mlp_knn | clean | 36 | 0.22 / 0.16 | 0.20 / 0.15 | 0.24 / 0.11 | 0.43 / 0.20 |
| theia | pooled_reference_calibration | mlp_knn | masked | 36 | 0.28 / 0.11 | 0.26 / 0.12 | 0.03 / 0.01 | 0.04 / 0.02 |

Normal FPR is the alert fraction in held-out normal graphs; attack FPR uses benchmark-negative entities. Exact per-fold ranges, maxima and input hashes are in `FACTOR_VARIABILITY.json`. No model, calibration threshold or decision was changed.

Input RESULTS SHA256: `641db8528ffd1f4e2adaf8dd5595767baf5c74a0f442637dd4ccde8defb6ec01`.
Input config SHA256: `cc902c0309250d64d4fd690d83fbc816f6f5c28ea60f03a7278a26e02273c58e`.
Analysis script SHA256: `155c982898afda90336eac6e8343e4dcb014699e3d82ae87dc87bafcef8495dd`.
