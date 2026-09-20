# Full descriptive results

Means summarize overlapping development repeats; they are not independent campaign estimates.
Local-feature copies across encoder seeds are excluded. FPR means the fraction of normal or benchmark-negative entities flagged.
Conditions: clean or 50% of retained relationships removed. All rates below are percentages.

| Dataset | Strategy | Representation | Condition | Unique cases | Recall mean (min) | Test FPR mean (max) | F1 mean | Normal FPR mean (max) |
|---|---|---|---|---:|---:|---:|---:|---:|
| cadets | clean | gin_knn | clean | 36 | 30.54 (0.00) | 21.54 (63.30) | 20.22 | 32.75 (67.01) |
| cadets | clean | gin_knn | masked | 36 | 58.46 (0.01) | 56.33 (77.65) | 7.29 | 55.27 (82.34) |
| cadets | clean | local_knn | clean | 12 | 0.27 (0.11) | 1.37 (4.13) | 0.39 | 1.04 (1.72) |
| cadets | clean | local_knn | masked | 12 | 0.26 (0.08) | 3.46 (9.62) | 0.26 | 3.19 (9.37) |
| cadets | clean | mlp_knn | clean | 36 | 0.33 (0.26) | 1.03 (1.55) | 0.52 | 1.00 (1.80) |
| cadets | clean | mlp_knn | masked | 36 | 50.79 (50.61) | 49.39 (52.21) | 6.90 | 49.49 (52.72) |
| cadets | pooled_calibration | gin_knn | clean | 36 | 0.00 (0.00) | 0.01 (0.10) | 0.00 | 0.01 (0.20) |
| cadets | pooled_calibration | gin_knn | masked | 36 | 0.01 (0.00) | 0.22 (1.35) | 0.01 | 0.18 (1.46) |
| cadets | pooled_calibration | local_knn | clean | 12 | 0.14 (0.11) | 0.99 (1.21) | 0.22 | 0.86 (1.43) |
| cadets | pooled_calibration | local_knn | masked | 12 | 0.12 (0.08) | 1.29 (2.17) | 0.17 | 1.18 (1.79) |
| cadets | pooled_calibration | mlp_knn | clean | 36 | 0.12 (0.00) | 0.17 (0.40) | 0.23 | 0.16 (0.36) |
| cadets | pooled_calibration | mlp_knn | masked | 36 | 0.08 (0.01) | 1.01 (2.33) | 0.12 | 0.87 (1.90) |
| cadets | pooled_reference_calibration | gin_knn | clean | 36 | 19.42 (0.00) | 16.04 (63.54) | 10.86 | 20.37 (66.86) |
| cadets | pooled_reference_calibration | gin_knn | masked | 36 | 12.33 (0.00) | 6.03 (32.46) | 10.46 | 8.80 (32.22) |
| cadets | pooled_reference_calibration | local_knn | clean | 12 | 0.14 (0.11) | 1.16 (1.36) | 0.22 | 1.01 (1.58) |
| cadets | pooled_reference_calibration | local_knn | masked | 12 | 0.11 (0.08) | 1.15 (1.79) | 0.17 | 1.05 (1.56) |
| cadets | pooled_reference_calibration | mlp_knn | clean | 36 | 0.27 (0.08) | 0.75 (1.00) | 0.45 | 0.70 (1.34) |
| cadets | pooled_reference_calibration | mlp_knn | masked | 36 | 0.17 (0.05) | 1.41 (2.09) | 0.24 | 1.32 (2.03) |
| theia | clean | gin_knn | clean | 36 | 82.35 (0.03) | 2.12 (4.18) | 75.57 | 2.16 (7.79) |
| theia | clean | gin_knn | masked | 36 | 90.48 (42.02) | 50.99 (61.03) | 21.76 | 52.08 (58.27) |
| theia | clean | local_knn | clean | 12 | 1.59 (0.11) | 0.99 (1.12) | 2.75 | 0.98 (1.29) |
| theia | clean | local_knn | masked | 12 | 24.76 (0.06) | 4.23 (6.78) | 22.58 | 3.51 (5.46) |
| theia | clean | mlp_knn | clean | 36 | 2.41 (0.09) | 1.01 (1.17) | 3.90 | 1.01 (1.23) |
| theia | clean | mlp_knn | masked | 36 | 42.52 (41.67) | 48.86 (49.38) | 11.21 | 49.85 (51.01) |
| theia | pooled_calibration | gin_knn | clean | 36 | 0.00 (0.00) | 0.01 (0.04) | 0.00 | 0.00 (0.01) |
| theia | pooled_calibration | gin_knn | masked | 36 | 4.70 (0.00) | 0.62 (3.70) | 6.60 | 0.60 (3.91) |
| theia | pooled_calibration | local_knn | clean | 12 | 0.14 (0.10) | 0.84 (0.96) | 0.25 | 0.85 (1.08) |
| theia | pooled_calibration | local_knn | masked | 12 | 0.07 (0.06) | 1.17 (1.40) | 0.11 | 1.08 (1.22) |
| theia | pooled_calibration | mlp_knn | clean | 36 | 0.03 (0.01) | 0.25 (0.51) | 0.05 | 0.24 (0.60) |
| theia | pooled_calibration | mlp_knn | masked | 36 | 0.03 (0.01) | 0.88 (1.75) | 0.05 | 0.87 (1.77) |
| theia | pooled_reference_calibration | gin_knn | clean | 36 | 81.77 (18.80) | 1.29 (1.94) | 80.71 | 0.77 (1.56) |
| theia | pooled_reference_calibration | gin_knn | masked | 36 | 35.56 (0.79) | 1.62 (3.15) | 42.68 | 1.12 (2.01) |
| theia | pooled_reference_calibration | local_knn | clean | 12 | 0.39 (0.05) | 1.05 (1.22) | 0.67 | 1.05 (1.39) |
| theia | pooled_reference_calibration | local_knn | masked | 12 | 0.10 (0.04) | 0.91 (1.06) | 0.18 | 0.92 (1.18) |
| theia | pooled_reference_calibration | mlp_knn | clean | 36 | 0.18 (0.09) | 0.81 (1.06) | 0.33 | 0.83 (1.20) |
| theia | pooled_reference_calibration | mlp_knn | masked | 36 | 0.07 (0.04) | 1.20 (1.50) | 0.12 | 1.15 (1.41) |
