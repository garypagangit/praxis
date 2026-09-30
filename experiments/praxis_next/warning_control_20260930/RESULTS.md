# PX-085--087: local replay and independent AWS audit

Exploratory replay of the previously examined UNRAVELED campaign. Full replay ran locally; AWS independently recomputed aggregate metrics and rank-rule checks with two CPU processes after the large payload transfer failed. All arms are retained in results/ALL_ARMS.csv. Means below are across three fitting seeds, not independent campaigns.

## Original decisions and fixed stopping: clean, budget 2

| Policy | Cost | F1 | Exfil warning % | Movement warning % | Benign false alerts |
|---|---:|---:|---:|---:|---:|
| none | 0.00 | 0.7523 | 67.52 | 78.10 | 164.0 |
| roles_first | 1.00 | 0.7136 | 88.34 | 85.71 | 179.7 |
| history_first | 2.00 | 0.7594 | 67.17 | 58.10 | 86.7 |
| entropy | 1.28 | 0.7181 | 87.58 | 63.81 | 101.3 |
| harm | 1.03 | 0.7551 | 67.33 | 61.90 | 107.3 |
| roles_stop50 | 0.93 | 0.7135 | 88.35 | 85.71 | 180.3 |
| roles_stop90 | 0.93 | 0.7135 | 88.34 | 85.71 | 179.7 |

## Supported-stage gate, target alpha 5%: same rows

| Policy | Cost | F1 | Exfil warning % | Movement warning % | Benign false alerts |
|---|---:|---:|---:|---:|---:|
| none | 0.00 | 0.7523 | 67.52 | 78.10 | 164.0 |
| roles_first | 1.00 | 0.7136 | 88.34 | 85.71 | 179.7 |
| history_first | 2.00 | 0.7594 | 67.17 | 58.10 | 86.7 |
| entropy | 1.28 | 0.7181 | 87.58 | 63.81 | 101.3 |
| harm | 1.03 | 0.7551 | 67.33 | 61.90 | 107.3 |
| roles_stop50 | 0.93 | 0.7135 | 88.35 | 85.71 | 180.3 |
| roles_stop90 | 0.93 | 0.7135 | 88.34 | 85.71 | 179.7 |

Movement has zero calibration support. Its test recall is measured, but it has no supported-stage risk claim. All-stage fail-closed warns on every row. Chronological flow data do not establish exchangeability; no deployment risk guarantee is claimed.

## Mean-ensemble warning losses

For each fixed state, the table counts attack rows where some seed warned but the probability mean calls the row benign. This directly tests the supplied mean-retention claim.

| State | Stage | Single-seed misses | Mean misses | Union misses | Mean loses a seed warning |

|---|---|---|---:|---:|---:|

| 0 | other_attack | [38, 43, 38] | 41 | 31 | 10 |

| 0 | movement | [7, 8, 8] | 7 | 7 | 0 |

| 0 | exfiltration | [1118, 1119, 1117] | 1119 | 1117 | 2 |

| 1 | other_attack | [40, 39, 39] | 39 | 30 | 9 |

| 1 | movement | [3, 8, 4] | 3 | 3 | 0 |

| 1 | exfiltration | [43, 61, 1100] | 1100 | 42 | 1058 |

| 2 | other_attack | [62, 70, 72] | 66 | 52 | 14 |

| 2 | movement | [7, 19, 18] | 16 | 6 | 10 |

| 2 | exfiltration | [1132, 1127, 1131] | 1129 | 1126 | 3 |

| 3 | other_attack | [67, 64, 63] | 68 | 48 | 20 |

| 3 | movement | [3, 12, 18] | 10 | 3 | 7 |

| 3 | exfiltration | [217, 204, 1107] | 256 | 139 | 117 |

## Limits

No new fitting or independent dataset was included. Acquisition costs and delivery failures are inherited simulations. Fixed-state ensembles require three model evaluations and are unrestricted references under delayed delivery. Novelty remains unconfirmed. The oracle decomposition cannot be deployed because it inspects hypothetical expert outcomes. Conformal thresholds are established methods; empirical target attainment on this campaign would not prove a general guarantee.
