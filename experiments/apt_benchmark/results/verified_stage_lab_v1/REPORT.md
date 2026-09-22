# Verified operations, earlier activity, and broken workflow correspondence

**Completed controlled mechanism experiment. Algorithmic novelty and operational APT detection are not established.**

[Independent calculation audit](AUDIT.json): PASS.

**Observed clean four-outcome macro-F1, current + coverage controls to full context:** linked 0.7654 to 1.0000; crossed 0.3166 to 0.2222; factorial_all 0.4288 to 0.4167. The complete tables retain successful-request-only results, every stress condition, and the direct prior-evidence rule.

This experiment recognizes four completed application outcomes: neither, a remote hash computation, complete object persistence at the receiver, or both. They are harmless custom-service analogues performed by three loopback worker processes on one operating system. They are not verified malicious lateral movement or theft.

**Transfer means complete persisted object, not any bytes leaving the sender.** Every RPC carries a dummy buffer in its HTTP body, including hash-only and denied requests. Failed transfer operations can persist a partial object while receiving a negative completed-transfer label. Therefore a negative transfer label does not mean zero transmitted bytes, zero data exposure, or no exfiltration; a positive label does not establish unauthorized theft.

The model fits only episodes where the requested current operation matches the preceding operation. The **linked** test subset deliberately retains that engineered relationship; the **crossed** subset actively mismatches the two requested operations. The **factorial_all** population contains both subsets and fully crosses prior and current requests, making those requests independent by construction. It is their union, not an additional independent sample. A high linked score measures predictable scripted workflow, not general attack understanding.

The six main arms exclude current elapsed time. The timing arm is a separate diagnostic. The current baseline already includes observed prior-record volume and availability controls; adding history tests event-type, success, and byte information beyond those controls.

All values average three fits evaluated on identical observations. The seeds are not three independent collections; no confidence interval or significance claim is made. Counts can be fractional because they average fits.

## Execution and split counts

| Partition | Linked episodes | Crossed episodes |
|---|---:|---:|
| fit | 288 | 864 |
| calibration | 96 | 288 |
| test | 192 | 576 |

Only linked fit episodes train the models. Calibration predictions are saved; no calibrated threshold or tuning result is claimed. Whole blocks define the fixed splits. Stress versions and counterfactual twins add no independent physical runs.

## Primary clean comparison: matched, mismatched, and full-factorial workflows

| Arm | Linked all F1 | Crossed all F1 | Factorial all F1 | Linked status-200 F1 | Crossed status-200 F1 | Factorial status-200 F1 |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 0.7654 | 0.3166 | 0.4288 | 0.7654 | 0.0944 | 0.2621 |
| Current + roles | 0.7733 | 0.3102 | 0.4261 | 0.7733 | 0.0880 | 0.2594 |
| Current + earlier event meanings | 1.0000 | 0.2222 | 0.4167 | 1.0000 | 0.0000 | 0.2500 |
| Current + roles + earlier event meanings | 1.0000 | 0.2222 | 0.4167 | 1.0000 | 0.0000 | 0.2500 |
| Current + roles + wrong-source history | 0.7409 | 0.2970 | 0.4081 | 0.7409 | 0.0747 | 0.2415 |
| Earlier event meanings + coverage controls | 0.2143 | 0.2143 | 0.2143 | 0.1000 | 0.1000 | 0.1000 |
| DIAGNOSTIC: context + current elapsed time | 1.0000 | 0.2222 | 0.4167 | 1.0000 | 0.0000 | 0.2500 |
| Majority outcome | 0.2143 | 0.2143 | 0.2143 | 0.1000 | 0.1000 | 0.1000 |
| Direct prior-evidence rule | 1.0000 | 0.2222 | 0.4167 | 1.0000 | 0.0000 | 0.2500 |

**Read status-200 rows alongside the full population.** Authentication denials and failed operations have outcome “Neither”; these easier cases can raise overall accuracy. Status 200 removes those failures but still includes successful requests for neither operation. Four-class macro-F1 always includes all four classes.

## Paired contrasts

Every contrast is candidate minus reference on the same rows and fit seeds. AP is average precision for each operation bit, obtained by summing the appropriate class probabilities; it is distinct from four-class macro-F1.

### All test transactions

| Comparison / condition | Linked F1 change | Crossed F1 change | Factorial F1 change | Linked transfer AP change | Crossed transfer AP change | Factorial transfer AP change |
|---|---:|---:|---:|---:|---:|---:|
| Full context versus current + coverage controls / Clean observations | +23.46 pp | -9.44 pp | -1.21 pp | +14.11 pp | -0.65 pp | -0.35 pp |
| Full context versus current + coverage controls / Remote-job records removed | +3.03 pp | -7.33 pp | -4.95 pp | +0.00 pp | +2.16 pp | -0.67 pp |
| Full context versus current + coverage controls / File-write records removed | +4.17 pp | -7.26 pp | -4.56 pp | -1.07 pp | +0.50 pp | +0.15 pp |
| Full context versus current + coverage controls / Prior arrival shifted by 50 ms | +0.00 pp | -1.02 pp | -0.77 pp | -2.94 pp | -0.04 pp | -0.68 pp |
| Full context versus current + coverage controls / Role metadata permuted | +23.46 pp | -9.44 pp | -1.21 pp | +14.11 pp | -0.65 pp | -0.35 pp |
| Earlier event meanings beyond current controls / Clean observations | +23.46 pp | -9.44 pp | -1.21 pp | +14.11 pp | -0.65 pp | -0.35 pp |
| Earlier event meanings beyond current controls / Remote-job records removed | +3.03 pp | -7.33 pp | -4.95 pp | +0.00 pp | +2.16 pp | -0.67 pp |
| Earlier event meanings beyond current controls / File-write records removed | +4.17 pp | -7.26 pp | -4.56 pp | -1.07 pp | +0.50 pp | +0.15 pp |
| Earlier event meanings beyond current controls / Prior arrival shifted by 50 ms | +0.00 pp | -1.02 pp | -0.77 pp | -2.94 pp | -0.04 pp | -0.68 pp |
| Earlier event meanings beyond current controls / Role metadata permuted | +23.46 pp | -9.44 pp | -1.21 pp | +14.11 pp | -0.65 pp | -0.35 pp |
| Correct versus wrong-source history / Clean observations | +25.91 pp | -7.47 pp | +0.85 pp | +11.05 pp | -0.61 pp | -1.10 pp |
| Correct versus wrong-source history / Remote-job records removed | +5.56 pp | -8.80 pp | -4.99 pp | +0.00 pp | +3.25 pp | -0.25 pp |
| Correct versus wrong-source history / File-write records removed | +0.45 pp | -7.10 pp | -5.13 pp | -9.91 pp | -1.27 pp | -2.93 pp |
| Correct versus wrong-source history / Prior arrival shifted by 50 ms | +0.00 pp | -1.02 pp | -0.77 pp | +2.92 pp | -0.67 pp | +0.31 pp |
| Correct versus wrong-source history / Role metadata permuted | +21.96 pp | -6.77 pp | +0.41 pp | +9.81 pp | -0.72 pp | -2.37 pp |
| Full context versus direct prior-evidence rule / Clean observations | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +20.37 pp | +16.67 pp |
| Full context versus direct prior-evidence rule / Remote-job records removed | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +22.22 pp | +16.67 pp |
| Full context versus direct prior-evidence rule / File-write records removed | +0.00 pp | +0.00 pp | +0.00 pp | +33.33 pp | +33.33 pp | +33.33 pp |
| Full context versus direct prior-evidence rule / Prior arrival shifted by 50 ms | +0.00 pp | +0.00 pp | +0.00 pp | +33.33 pp | +33.07 pp | +33.14 pp |
| Full context versus direct prior-evidence rule / Role metadata permuted | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +20.37 pp | +16.67 pp |
| Roles beyond current + history / Clean observations | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp |
| Roles beyond current + history / Remote-job records removed | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp |
| Roles beyond current + history / File-write records removed | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp |
| Roles beyond current + history / Prior arrival shifted by 50 ms | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp |
| Roles beyond current + history / Role metadata permuted | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp |
### Status-200 transactions

| Comparison / condition | Linked F1 change | Crossed F1 change | Factorial F1 change | Linked transfer AP change | Crossed transfer AP change | Factorial transfer AP change |
|---|---:|---:|---:|---:|---:|---:|
| Full context versus current + coverage controls / Clean observations | +23.46 pp | -9.44 pp | -1.21 pp | +14.11 pp | -0.65 pp | -0.35 pp |
| Full context versus current + coverage controls / Remote-job records removed | +3.03 pp | -7.33 pp | -4.95 pp | +0.00 pp | +2.16 pp | -0.67 pp |
| Full context versus current + coverage controls / File-write records removed | +4.17 pp | -7.26 pp | -4.56 pp | -1.07 pp | +0.50 pp | +0.15 pp |
| Full context versus current + coverage controls / Prior arrival shifted by 50 ms | +0.00 pp | -1.02 pp | -0.77 pp | -2.94 pp | -0.04 pp | -0.68 pp |
| Full context versus current + coverage controls / Role metadata permuted | +23.46 pp | -9.44 pp | -1.21 pp | +14.11 pp | -0.65 pp | -0.35 pp |
| Earlier event meanings beyond current controls / Clean observations | +23.46 pp | -9.44 pp | -1.21 pp | +14.11 pp | -0.65 pp | -0.35 pp |
| Earlier event meanings beyond current controls / Remote-job records removed | +3.03 pp | -7.33 pp | -4.95 pp | +0.00 pp | +2.16 pp | -0.67 pp |
| Earlier event meanings beyond current controls / File-write records removed | +4.17 pp | -7.26 pp | -4.56 pp | -1.07 pp | +0.50 pp | +0.15 pp |
| Earlier event meanings beyond current controls / Prior arrival shifted by 50 ms | +0.00 pp | -1.02 pp | -0.77 pp | -2.94 pp | -0.04 pp | -0.68 pp |
| Earlier event meanings beyond current controls / Role metadata permuted | +23.46 pp | -9.44 pp | -1.21 pp | +14.11 pp | -0.65 pp | -0.35 pp |
| Correct versus wrong-source history / Clean observations | +25.91 pp | -7.47 pp | +0.85 pp | +11.05 pp | -0.64 pp | -1.13 pp |
| Correct versus wrong-source history / Remote-job records removed | +5.56 pp | -8.80 pp | -4.99 pp | +0.00 pp | +3.25 pp | -0.25 pp |
| Correct versus wrong-source history / File-write records removed | +0.45 pp | -7.10 pp | -5.13 pp | -9.91 pp | -1.27 pp | -2.93 pp |
| Correct versus wrong-source history / Prior arrival shifted by 50 ms | +0.00 pp | -1.02 pp | -0.77 pp | +2.92 pp | -0.67 pp | +0.31 pp |
| Correct versus wrong-source history / Role metadata permuted | +21.96 pp | -6.77 pp | +0.41 pp | +9.81 pp | -0.73 pp | -2.37 pp |
| Full context versus direct prior-evidence rule / Clean observations | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | -1.85 pp | +0.00 pp |
| Full context versus direct prior-evidence rule / Remote-job records removed | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp |
| Full context versus direct prior-evidence rule / File-write records removed | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp |
| Full context versus direct prior-evidence rule / Prior arrival shifted by 50 ms | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | -0.26 pp | -0.19 pp |
| Full context versus direct prior-evidence rule / Role metadata permuted | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | -1.85 pp | +0.00 pp |
| Roles beyond current + history / Clean observations | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp |
| Roles beyond current + history / Remote-job records removed | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp |
| Roles beyond current + history / File-write records removed | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp |
| Roles beyond current + history / Prior arrival shifted by 50 ms | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp |
| Roles beyond current + history / Role metadata permuted | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp | +0.00 pp |

## Complete outcome results

All seven learned arms and both comparators are retained under every condition. “Remote” means completed hash computation; “transfer” means a complete persisted object with matching bytes and hash. Neither output identifies malicious intent or absence of partial exposure. Precision, recall, F1, AP, and ROC AUC are available for both outputs and every subset in [EVIDENCE.json](EVIDENCE.json), including all seed-level confusion matrices.

### Clean observations

#### Linked test population

| Arm | All accuracy | All macro-F1 | Status-200 accuracy | Status-200 macro-F1 |
|---|---:|---:|---:|---:|
| Current + coverage controls | 92.19% | 0.7654 | 76.56% | 0.7654 |
| Current + roles | 92.71% | 0.7733 | 78.12% | 0.7733 |
| Current + earlier event meanings | 100.00% | 1.0000 | 100.00% | 1.0000 |
| Current + roles + earlier event meanings | 100.00% | 1.0000 | 100.00% | 1.0000 |
| Current + roles + wrong-source history | 91.67% | 0.7409 | 75.00% | 0.7409 |
| Earlier event meanings + coverage controls | 75.00% | 0.2143 | 25.00% | 0.1000 |
| DIAGNOSTIC: context + current elapsed time | 100.00% | 1.0000 | 100.00% | 1.0000 |
| Majority outcome | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Direct prior-evidence rule | 100.00% | 1.0000 | 100.00% | 1.0000 |

Status-200 remote outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 77.42% | 75.00% | 0.7619 | 0.8602 | 0.8828 | 24.00 / 7.00 / 8.00 |
| Current + roles | 73.68% | 87.50% | 0.8000 | 0.8861 | 0.8838 | 28.00 / 10.00 / 4.00 |
| Current + earlier event meanings | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Current + roles + earlier event meanings | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Current + roles + wrong-source history | 71.05% | 84.38% | 0.7714 | 0.8913 | 0.8779 | 27.00 / 11.00 / 5.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 1.0000 | 1.0000 | 0.00 / 0.00 / 32.00 |
| DIAGNOSTIC: context + current elapsed time | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Direct prior-evidence rule | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |

Status-200 transfer outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 75.76% | 78.12% | 0.7692 | 0.8589 | 0.8828 | 25.00 / 8.00 / 7.00 |
| Current + roles | 84.62% | 68.75% | 0.7586 | 0.8890 | 0.8838 | 22.00 / 4.00 / 10.00 |
| Current + earlier event meanings | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Current + roles + earlier event meanings | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Current + roles + wrong-source history | 80.77% | 65.62% | 0.7241 | 0.8895 | 0.8770 | 21.00 / 5.00 / 11.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 1.0000 | 1.0000 | 0.00 / 0.00 / 32.00 |
| DIAGNOSTIC: context + current elapsed time | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Direct prior-evidence rule | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |

#### Crossed test population

| Arm | All accuracy | All macro-F1 | Status-200 accuracy | Status-200 macro-F1 |
|---|---:|---:|---:|---:|
| Current + coverage controls | 69.79% | 0.3166 | 9.38% | 0.0944 |
| Current + roles | 69.62% | 0.3102 | 8.85% | 0.0880 |
| Current + earlier event meanings | 66.67% | 0.2222 | 0.00% | 0.0000 |
| Current + roles + earlier event meanings | 66.67% | 0.2222 | 0.00% | 0.0000 |
| Current + roles + wrong-source history | 69.10% | 0.2970 | 7.29% | 0.0747 |
| Earlier event meanings + coverage controls | 75.00% | 0.2143 | 25.00% | 0.1000 |
| DIAGNOSTIC: context + current elapsed time | 66.67% | 0.2222 | 0.00% | 0.0000 |
| Majority outcome | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Direct prior-evidence rule | 66.67% | 0.2222 | 0.00% | 0.0000 |

Status-200 remote outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 45.45% | 41.67% | 0.4348 | 0.4397 | 0.3935 | 40.00 / 48.00 / 56.00 |
| Current + roles | 43.52% | 48.96% | 0.4608 | 0.4171 | 0.3748 | 47.00 / 61.00 / 49.00 |
| Current + earlier event meanings | 33.33% | 33.33% | 0.3333 | 0.4259 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Current + roles + earlier event meanings | 33.33% | 33.33% | 0.3333 | 0.4259 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Current + roles + wrong-source history | 41.44% | 47.92% | 0.4444 | 0.4263 | 0.3655 | 46.00 / 65.00 / 50.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.4214 | 0.3414 | 0.00 / 0.00 / 96.00 |
| DIAGNOSTIC: context + current elapsed time | 33.33% | 33.33% | 0.3333 | 0.4259 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |
| Direct prior-evidence rule | 33.33% | 33.33% | 0.3333 | 0.4444 | 0.3333 | 32.00 / 64.00 / 64.00 |

Status-200 transfer outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 40.38% | 43.75% | 0.4200 | 0.4324 | 0.3659 | 42.00 / 62.00 / 54.00 |
| Current + roles | 40.48% | 35.42% | 0.3778 | 0.4252 | 0.3778 | 34.00 / 50.00 / 62.00 |
| Current + earlier event meanings | 33.33% | 33.33% | 0.3333 | 0.4259 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Current + roles + earlier event meanings | 33.33% | 33.33% | 0.3333 | 0.4259 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Current + roles + wrong-source history | 39.51% | 33.33% | 0.3616 | 0.4324 | 0.3846 | 32.00 / 49.00 / 64.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.4132 | 0.3310 | 0.00 / 0.00 / 96.00 |
| DIAGNOSTIC: context + current elapsed time | 33.33% | 33.33% | 0.3333 | 0.4259 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |
| Direct prior-evidence rule | 33.33% | 33.33% | 0.3333 | 0.4444 | 0.3333 | 32.00 / 64.00 / 64.00 |

#### Factorial_all test population

| Arm | All accuracy | All macro-F1 | Status-200 accuracy | Status-200 macro-F1 |
|---|---:|---:|---:|---:|
| Current + coverage controls | 75.39% | 0.4288 | 26.17% | 0.2621 |
| Current + roles | 75.39% | 0.4261 | 26.17% | 0.2594 |
| Current + earlier event meanings | 75.00% | 0.4167 | 25.00% | 0.2500 |
| Current + roles + earlier event meanings | 75.00% | 0.4167 | 25.00% | 0.2500 |
| Current + roles + wrong-source history | 74.74% | 0.4081 | 24.22% | 0.2415 |
| Earlier event meanings + coverage controls | 75.00% | 0.2143 | 25.00% | 0.1000 |
| DIAGNOSTIC: context + current elapsed time | 75.00% | 0.4167 | 25.00% | 0.2500 |
| Majority outcome | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Direct prior-evidence rule | 75.00% | 0.4167 | 25.00% | 0.2500 |

Status-200 remote outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 53.78% | 50.00% | 0.5182 | 0.5042 | 0.5132 | 64.00 / 55.00 / 64.00 |
| Current + roles | 51.37% | 58.59% | 0.5474 | 0.4875 | 0.5025 | 75.00 / 71.00 / 53.00 |
| Current + earlier event meanings | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Current + roles + earlier event meanings | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Current + roles + wrong-source history | 48.99% | 57.03% | 0.5271 | 0.5018 | 0.4922 | 73.00 / 76.00 / 55.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5133 | 0.5094 | 0.00 / 0.00 / 128.00 |
| DIAGNOSTIC: context + current elapsed time | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |
| Direct prior-evidence rule | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |

Status-200 transfer outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 48.91% | 52.34% | 0.5057 | 0.5035 | 0.4976 | 67.00 / 70.00 / 61.00 |
| Current + roles | 50.91% | 43.75% | 0.4706 | 0.5013 | 0.5007 | 56.00 / 54.00 / 72.00 |
| Current + earlier event meanings | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Current + roles + earlier event meanings | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Current + roles + wrong-source history | 49.53% | 41.41% | 0.4511 | 0.5113 | 0.5075 | 53.00 / 54.00 / 75.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5024 | 0.5043 | 0.00 / 0.00 / 128.00 |
| DIAGNOSTIC: context + current elapsed time | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |
| Direct prior-evidence rule | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |

### Remote-job records removed

#### Linked test population

| Arm | All accuracy | All macro-F1 | Status-200 accuracy | Status-200 macro-F1 |
|---|---:|---:|---:|---:|
| Current + coverage controls | 79.69% | 0.3732 | 39.06% | 0.3030 |
| Current + roles | 78.12% | 0.3480 | 34.38% | 0.2778 |
| Current + earlier event meanings | 83.33% | 0.4035 | 50.00% | 0.3333 |
| Current + roles + earlier event meanings | 83.33% | 0.4035 | 50.00% | 0.3333 |
| Current + roles + wrong-source history | 78.12% | 0.3480 | 34.38% | 0.2778 |
| Earlier event meanings + coverage controls | 75.00% | 0.2143 | 25.00% | 0.1000 |
| DIAGNOSTIC: context + current elapsed time | 83.33% | 0.4035 | 50.00% | 0.3333 |
| Majority outcome | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Direct prior-evidence rule | 83.33% | 0.4035 | 50.00% | 0.3333 |

Status-200 remote outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 53.33% | 25.00% | 0.3404 | 0.5033 | 0.4883 | 8.00 / 7.00 / 24.00 |
| Current + roles | 52.38% | 34.38% | 0.4151 | 0.5056 | 0.5215 | 11.00 / 10.00 / 21.00 |
| Current + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Current + roles + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Current + roles + wrong-source history | 52.38% | 34.38% | 0.4151 | 0.5027 | 0.5122 | 11.00 / 10.00 / 21.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.4876 | 0.4727 | 0.00 / 0.00 / 32.00 |
| DIAGNOSTIC: context + current elapsed time | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Direct prior-evidence rule | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |

Status-200 transfer outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 100.00% | 53.12% | 0.6939 | 1.0000 | 1.0000 | 17.00 / 0.00 / 15.00 |
| Current + roles | 100.00% | 34.38% | 0.5116 | 1.0000 | 1.0000 | 11.00 / 0.00 / 21.00 |
| Current + earlier event meanings | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Current + roles + earlier event meanings | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Current + roles + wrong-source history | 100.00% | 34.38% | 0.5116 | 1.0000 | 1.0000 | 11.00 / 0.00 / 21.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 1.0000 | 1.0000 | 0.00 / 0.00 / 32.00 |
| DIAGNOSTIC: context + current elapsed time | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Direct prior-evidence rule | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |

#### Crossed test population

| Arm | All accuracy | All macro-F1 | Status-200 accuracy | Status-200 macro-F1 |
|---|---:|---:|---:|---:|
| Current + coverage controls | 73.78% | 0.3482 | 21.35% | 0.1844 |
| Current + roles | 73.61% | 0.3383 | 20.83% | 0.1746 |
| Current + earlier event meanings | 72.22% | 0.2749 | 16.67% | 0.1111 |
| Current + roles + earlier event meanings | 72.22% | 0.2749 | 16.67% | 0.1111 |
| Current + roles + wrong-source history | 74.31% | 0.3629 | 22.92% | 0.1991 |
| Earlier event meanings + coverage controls | 75.00% | 0.2143 | 25.00% | 0.1000 |
| DIAGNOSTIC: context + current elapsed time | 72.22% | 0.2749 | 16.67% | 0.1111 |
| Majority outcome | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Direct prior-evidence rule | 72.22% | 0.2749 | 16.67% | 0.1111 |

Status-200 remote outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 49.02% | 26.04% | 0.3401 | 0.5052 | 0.5201 | 25.00 / 26.00 / 71.00 |
| Current + roles | 48.33% | 30.21% | 0.3718 | 0.4938 | 0.5024 | 29.00 / 31.00 / 67.00 |
| Current + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |
| Current + roles + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |
| Current + roles + wrong-source history | 50.91% | 29.17% | 0.3709 | 0.4920 | 0.5147 | 28.00 / 27.00 / 68.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5094 | 0.5228 | 0.00 / 0.00 / 96.00 |
| DIAGNOSTIC: context + current elapsed time | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |
| Direct prior-evidence rule | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |

Status-200 transfer outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 35.56% | 16.67% | 0.2270 | 0.4229 | 0.3182 | 16.00 / 29.00 / 80.00 |
| Current + roles | 30.56% | 11.46% | 0.1667 | 0.4047 | 0.3330 | 11.00 / 25.00 / 85.00 |
| Current + earlier event meanings | 33.33% | 33.33% | 0.3333 | 0.4444 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Current + roles + earlier event meanings | 33.33% | 33.33% | 0.3333 | 0.4444 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Current + roles + wrong-source history | 39.02% | 16.67% | 0.2336 | 0.4119 | 0.3373 | 16.00 / 25.00 / 80.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.4147 | 0.3061 | 0.00 / 0.00 / 96.00 |
| DIAGNOSTIC: context + current elapsed time | 33.33% | 33.33% | 0.3333 | 0.4444 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |
| Direct prior-evidence rule | 33.33% | 33.33% | 0.3333 | 0.4444 | 0.3333 | 32.00 / 64.00 / 64.00 |

#### Factorial_all test population

| Arm | All accuracy | All macro-F1 | Status-200 accuracy | Status-200 macro-F1 |
|---|---:|---:|---:|---:|
| Current + coverage controls | 75.26% | 0.3565 | 25.78% | 0.2162 |
| Current + roles | 74.74% | 0.3398 | 24.22% | 0.1995 |
| Current + earlier event meanings | 75.00% | 0.3070 | 25.00% | 0.1667 |
| Current + roles + earlier event meanings | 75.00% | 0.3070 | 25.00% | 0.1667 |
| Current + roles + wrong-source history | 75.26% | 0.3569 | 25.78% | 0.2166 |
| Earlier event meanings + coverage controls | 75.00% | 0.2143 | 25.00% | 0.1000 |
| DIAGNOSTIC: context + current elapsed time | 75.00% | 0.3070 | 25.00% | 0.1667 |
| Majority outcome | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Direct prior-evidence rule | 75.00% | 0.3070 | 25.00% | 0.1667 |

Status-200 remote outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 50.00% | 25.78% | 0.3402 | 0.5041 | 0.5122 | 33.00 / 33.00 / 95.00 |
| Current + roles | 49.38% | 31.25% | 0.3828 | 0.4938 | 0.5074 | 40.00 / 41.00 / 88.00 |
| Current + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |
| Current + roles + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |
| Current + roles + wrong-source history | 51.32% | 30.47% | 0.3824 | 0.4897 | 0.5125 | 39.00 / 37.00 / 89.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5036 | 0.5104 | 0.00 / 0.00 / 128.00 |
| DIAGNOSTIC: context + current elapsed time | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |
| Direct prior-evidence rule | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |

Status-200 transfer outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 53.23% | 25.78% | 0.3474 | 0.5067 | 0.5011 | 33.00 / 29.00 / 95.00 |
| Current + roles | 46.81% | 17.19% | 0.2514 | 0.4926 | 0.5010 | 22.00 / 25.00 / 106.00 |
| Current + earlier event meanings | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Current + roles + earlier event meanings | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Current + roles + wrong-source history | 51.92% | 21.09% | 0.3000 | 0.5025 | 0.5051 | 27.00 / 25.00 / 101.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.4899 | 0.4836 | 0.00 / 0.00 / 128.00 |
| DIAGNOSTIC: context + current elapsed time | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |
| Direct prior-evidence rule | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |

### File-write records removed

#### Linked test population

| Arm | All accuracy | All macro-F1 | Status-200 accuracy | Status-200 macro-F1 |
|---|---:|---:|---:|---:|
| Current + coverage controls | 79.17% | 0.3618 | 37.50% | 0.2917 |
| Current + roles | 81.25% | 0.3907 | 43.75% | 0.3205 |
| Current + earlier event meanings | 83.33% | 0.4035 | 50.00% | 0.3333 |
| Current + roles + earlier event meanings | 83.33% | 0.4035 | 50.00% | 0.3333 |
| Current + roles + wrong-source history | 81.25% | 0.3990 | 43.75% | 0.3288 |
| Earlier event meanings + coverage controls | 75.00% | 0.2143 | 25.00% | 0.1000 |
| DIAGNOSTIC: context + current elapsed time | 83.33% | 0.4035 | 50.00% | 0.3333 |
| Majority outcome | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Direct prior-evidence rule | 83.33% | 0.4035 | 50.00% | 0.3333 |

Status-200 remote outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 100.00% | 50.00% | 0.6667 | 1.0000 | 1.0000 | 16.00 / 0.00 / 16.00 |
| Current + roles | 100.00% | 71.88% | 0.8364 | 1.0000 | 1.0000 | 23.00 / 0.00 / 9.00 |
| Current + earlier event meanings | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Current + roles + earlier event meanings | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Current + roles + wrong-source history | 100.00% | 65.62% | 0.7925 | 1.0000 | 1.0000 | 21.00 / 0.00 / 11.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 1.0000 | 1.0000 | 0.00 / 0.00 / 32.00 |
| DIAGNOSTIC: context + current elapsed time | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Direct prior-evidence rule | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |

Status-200 transfer outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 50.00% | 25.00% | 0.3333 | 0.5107 | 0.5269 | 8.00 / 8.00 / 24.00 |
| Current + roles | 55.56% | 15.62% | 0.2439 | 0.5147 | 0.4819 | 5.00 / 4.00 / 27.00 |
| Current + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Current + roles + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Current + roles + wrong-source history | 63.64% | 21.88% | 0.3256 | 0.5991 | 0.5532 | 7.00 / 4.00 / 25.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5107 | 0.5269 | 0.00 / 0.00 / 32.00 |
| DIAGNOSTIC: context + current elapsed time | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Direct prior-evidence rule | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |

#### Crossed test population

| Arm | All accuracy | All macro-F1 | Status-200 accuracy | Status-200 macro-F1 |
|---|---:|---:|---:|---:|
| Current + coverage controls | 73.78% | 0.3474 | 21.35% | 0.1837 |
| Current + roles | 73.09% | 0.3316 | 19.27% | 0.1679 |
| Current + earlier event meanings | 72.22% | 0.2749 | 16.67% | 0.1111 |
| Current + roles + earlier event meanings | 72.22% | 0.2749 | 16.67% | 0.1111 |
| Current + roles + wrong-source history | 73.44% | 0.3458 | 20.31% | 0.1821 |
| Earlier event meanings + coverage controls | 75.00% | 0.2143 | 25.00% | 0.1000 |
| DIAGNOSTIC: context + current elapsed time | 72.22% | 0.2749 | 16.67% | 0.1111 |
| Majority outcome | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Direct prior-evidence rule | 72.22% | 0.2749 | 16.67% | 0.1111 |

Status-200 remote outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 34.88% | 15.62% | 0.2158 | 0.4314 | 0.3466 | 15.00 / 28.00 / 81.00 |
| Current + roles | 32.14% | 18.75% | 0.2368 | 0.4062 | 0.3262 | 18.00 / 38.00 / 78.00 |
| Current + earlier event meanings | 33.33% | 33.33% | 0.3333 | 0.4444 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Current + roles + earlier event meanings | 33.33% | 33.33% | 0.3333 | 0.4444 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Current + roles + wrong-source history | 33.85% | 22.92% | 0.2733 | 0.4224 | 0.3312 | 22.00 / 43.00 / 74.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.4314 | 0.3467 | 0.00 / 0.00 / 96.00 |
| DIAGNOSTIC: context + current elapsed time | 33.33% | 33.33% | 0.3333 | 0.4444 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |
| Direct prior-evidence rule | 33.33% | 33.33% | 0.3333 | 0.4444 | 0.3333 | 32.00 / 64.00 / 64.00 |

Status-200 transfer outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 49.06% | 27.08% | 0.3490 | 0.4950 | 0.4929 | 26.00 / 27.00 / 70.00 |
| Current + roles | 47.50% | 19.79% | 0.2794 | 0.5028 | 0.5011 | 19.00 / 21.00 / 77.00 |
| Current + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |
| Current + roles + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |
| Current + roles + wrong-source history | 54.84% | 17.71% | 0.2677 | 0.5127 | 0.5227 | 17.00 / 14.00 / 79.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5127 | 0.5033 | 0.00 / 0.00 / 96.00 |
| DIAGNOSTIC: context + current elapsed time | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |
| Direct prior-evidence rule | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |

#### Factorial_all test population

| Arm | All accuracy | All macro-F1 | Status-200 accuracy | Status-200 macro-F1 |
|---|---:|---:|---:|---:|
| Current + coverage controls | 75.13% | 0.3526 | 25.39% | 0.2123 |
| Current + roles | 75.13% | 0.3511 | 25.39% | 0.2108 |
| Current + earlier event meanings | 75.00% | 0.3070 | 25.00% | 0.1667 |
| Current + roles + earlier event meanings | 75.00% | 0.3070 | 25.00% | 0.1667 |
| Current + roles + wrong-source history | 75.39% | 0.3583 | 26.17% | 0.2180 |
| Earlier event meanings + coverage controls | 75.00% | 0.2143 | 25.00% | 0.1000 |
| DIAGNOSTIC: context + current elapsed time | 75.00% | 0.3070 | 25.00% | 0.1667 |
| Majority outcome | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Direct prior-evidence rule | 75.00% | 0.3070 | 25.00% | 0.1667 |

Status-200 remote outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 52.54% | 24.22% | 0.3316 | 0.5095 | 0.5122 | 31.00 / 28.00 / 97.00 |
| Current + roles | 51.90% | 32.03% | 0.3961 | 0.5077 | 0.5107 | 41.00 / 38.00 / 87.00 |
| Current + earlier event meanings | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Current + roles + earlier event meanings | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Current + roles + wrong-source history | 50.00% | 33.59% | 0.4019 | 0.5170 | 0.4957 | 43.00 / 43.00 / 85.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5095 | 0.5123 | 0.00 / 0.00 / 128.00 |
| DIAGNOSTIC: context + current elapsed time | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |
| Direct prior-evidence rule | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |

Status-200 transfer outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 49.28% | 26.56% | 0.3452 | 0.4985 | 0.5013 | 34.00 / 35.00 / 94.00 |
| Current + roles | 48.98% | 18.75% | 0.2712 | 0.5032 | 0.4956 | 24.00 / 25.00 / 104.00 |
| Current + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |
| Current + roles + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |
| Current + roles + wrong-source history | 57.14% | 18.75% | 0.2824 | 0.5293 | 0.5308 | 24.00 / 18.00 / 104.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5118 | 0.5090 | 0.00 / 0.00 / 128.00 |
| DIAGNOSTIC: context + current elapsed time | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |
| Direct prior-evidence rule | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |

### Prior arrival shifted by 50 ms

#### Linked test population

| Arm | All accuracy | All macro-F1 | Status-200 accuracy | Status-200 macro-F1 |
|---|---:|---:|---:|---:|
| Current + coverage controls | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Current + roles | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Current + earlier event meanings | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Current + roles + earlier event meanings | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Current + roles + wrong-source history | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Earlier event meanings + coverage controls | 75.00% | 0.2143 | 25.00% | 0.1000 |
| DIAGNOSTIC: context + current elapsed time | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Majority outcome | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Direct prior-evidence rule | 75.00% | 0.2143 | 25.00% | 0.1000 |

Status-200 remote outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 0.00% | 0.00% | 0.0000 | 0.4924 | 0.4766 | 0.00 / 0.00 / 32.00 |
| Current + roles | 0.00% | 0.00% | 0.0000 | 0.5380 | 0.5571 | 0.00 / 0.00 / 32.00 |
| Current + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Current + roles + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Current + roles + wrong-source history | 0.00% | 0.00% | 0.0000 | 0.5128 | 0.5293 | 0.00 / 0.00 / 32.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.4844 | 0.00 / 0.00 / 32.00 |
| DIAGNOSTIC: context + current elapsed time | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Direct prior-evidence rule | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |

Status-200 transfer outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5294 | 0.5542 | 0.00 / 0.00 / 32.00 |
| Current + roles | 0.00% | 0.00% | 0.0000 | 0.4706 | 0.4746 | 0.00 / 0.00 / 32.00 |
| Current + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Current + roles + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Current + roles + wrong-source history | 0.00% | 0.00% | 0.0000 | 0.4708 | 0.4741 | 0.00 / 0.00 / 32.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5079 | 0.5156 | 0.00 / 0.00 / 32.00 |
| DIAGNOSTIC: context + current elapsed time | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Direct prior-evidence rule | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |

#### Crossed test population

| Arm | All accuracy | All macro-F1 | Status-200 accuracy | Status-200 macro-F1 |
|---|---:|---:|---:|---:|
| Current + coverage controls | 75.17% | 0.2247 | 25.52% | 0.1106 |
| Current + roles | 75.17% | 0.2247 | 25.52% | 0.1106 |
| Current + earlier event meanings | 75.00% | 0.2145 | 25.00% | 0.1004 |
| Current + roles + earlier event meanings | 75.00% | 0.2145 | 25.00% | 0.1004 |
| Current + roles + wrong-source history | 75.17% | 0.2247 | 25.52% | 0.1106 |
| Earlier event meanings + coverage controls | 75.00% | 0.2143 | 25.00% | 0.1000 |
| DIAGNOSTIC: context + current elapsed time | 75.00% | 0.2145 | 25.00% | 0.1004 |
| Majority outcome | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Direct prior-evidence rule | 75.00% | 0.2145 | 25.00% | 0.1004 |

Status-200 remote outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5173 | 0.5322 | 0.00 / 0.00 / 96.00 |
| Current + roles | 0.00% | 0.00% | 0.0000 | 0.5115 | 0.5079 | 0.00 / 0.00 / 96.00 |
| Current + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.4948 | 0.00 / 1.00 / 96.00 |
| Current + roles + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.4948 | 0.00 / 1.00 / 96.00 |
| Current + roles + wrong-source history | 0.00% | 0.00% | 0.0000 | 0.5150 | 0.5217 | 0.00 / 0.00 / 96.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.4955 | 0.4843 | 0.00 / 0.00 / 96.00 |
| DIAGNOSTIC: context + current elapsed time | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.4948 | 0.00 / 1.00 / 96.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |
| Direct prior-evidence rule | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.4948 | 0.00 / 1.00 / 96.00 |

Status-200 transfer outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 100.00% | 1.04% | 0.0206 | 0.4978 | 0.4876 | 1.00 / 0.00 / 95.00 |
| Current + roles | 100.00% | 1.04% | 0.0206 | 0.5055 | 0.5011 | 1.00 / 0.00 / 95.00 |
| Current + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.4974 | 0.4948 | 0.00 / 0.00 / 96.00 |
| Current + roles + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.4974 | 0.4948 | 0.00 / 0.00 / 96.00 |
| Current + roles + wrong-source history | 100.00% | 1.04% | 0.0206 | 0.5041 | 0.4971 | 1.00 / 0.00 / 95.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5052 | 0.5050 | 0.00 / 0.00 / 96.00 |
| DIAGNOSTIC: context + current elapsed time | 0.00% | 0.00% | 0.0000 | 0.4974 | 0.4948 | 0.00 / 0.00 / 96.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |
| Direct prior-evidence rule | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |

#### Factorial_all test population

| Arm | All accuracy | All macro-F1 | Status-200 accuracy | Status-200 macro-F1 |
|---|---:|---:|---:|---:|
| Current + coverage controls | 75.13% | 0.2221 | 25.39% | 0.1080 |
| Current + roles | 75.13% | 0.2221 | 25.39% | 0.1080 |
| Current + earlier event meanings | 75.00% | 0.2144 | 25.00% | 0.1003 |
| Current + roles + earlier event meanings | 75.00% | 0.2144 | 25.00% | 0.1003 |
| Current + roles + wrong-source history | 75.13% | 0.2221 | 25.39% | 0.1080 |
| Earlier event meanings + coverage controls | 75.00% | 0.2143 | 25.00% | 0.1000 |
| DIAGNOSTIC: context + current elapsed time | 75.00% | 0.2144 | 25.00% | 0.1003 |
| Majority outcome | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Direct prior-evidence rule | 75.00% | 0.2144 | 25.00% | 0.1003 |

Status-200 remote outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5101 | 0.5185 | 0.00 / 0.00 / 128.00 |
| Current + roles | 0.00% | 0.00% | 0.0000 | 0.5156 | 0.5199 | 0.00 / 0.00 / 128.00 |
| Current + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.4961 | 0.00 / 1.00 / 128.00 |
| Current + roles + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.4961 | 0.00 / 1.00 / 128.00 |
| Current + roles + wrong-source history | 0.00% | 0.00% | 0.0000 | 0.5120 | 0.5236 | 0.00 / 0.00 / 128.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.4961 | 0.4843 | 0.00 / 0.00 / 128.00 |
| DIAGNOSTIC: context + current elapsed time | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.4961 | 0.00 / 1.00 / 128.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |
| Direct prior-evidence rule | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.4961 | 0.00 / 1.00 / 128.00 |

Status-200 transfer outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 100.00% | 0.78% | 0.0155 | 0.5049 | 0.5040 | 1.00 / 0.00 / 127.00 |
| Current + roles | 100.00% | 0.78% | 0.0155 | 0.4966 | 0.4947 | 1.00 / 0.00 / 127.00 |
| Current + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.4981 | 0.4961 | 0.00 / 0.00 / 128.00 |
| Current + roles + earlier event meanings | 0.00% | 0.00% | 0.0000 | 0.4981 | 0.4961 | 0.00 / 0.00 / 128.00 |
| Current + roles + wrong-source history | 100.00% | 0.78% | 0.0155 | 0.4949 | 0.4906 | 1.00 / 0.00 / 127.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5059 | 0.5077 | 0.00 / 0.00 / 128.00 |
| DIAGNOSTIC: context + current elapsed time | 0.00% | 0.00% | 0.0000 | 0.4981 | 0.4961 | 0.00 / 0.00 / 128.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |
| Direct prior-evidence rule | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |

### Role metadata permuted

#### Linked test population

| Arm | All accuracy | All macro-F1 | Status-200 accuracy | Status-200 macro-F1 |
|---|---:|---:|---:|---:|
| Current + coverage controls | 92.19% | 0.7654 | 76.56% | 0.7654 |
| Current + roles | 90.62% | 0.7176 | 71.88% | 0.7176 |
| Current + earlier event meanings | 100.00% | 1.0000 | 100.00% | 1.0000 |
| Current + roles + earlier event meanings | 100.00% | 1.0000 | 100.00% | 1.0000 |
| Current + roles + wrong-source history | 92.71% | 0.7804 | 78.12% | 0.7804 |
| Earlier event meanings + coverage controls | 75.00% | 0.2143 | 25.00% | 0.1000 |
| DIAGNOSTIC: context + current elapsed time | 100.00% | 1.0000 | 100.00% | 1.0000 |
| Majority outcome | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Direct prior-evidence rule | 100.00% | 1.0000 | 100.00% | 1.0000 |

Status-200 remote outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 77.42% | 75.00% | 0.7619 | 0.8602 | 0.8828 | 24.00 / 7.00 / 8.00 |
| Current + roles | 70.59% | 75.00% | 0.7273 | 0.8732 | 0.8662 | 24.00 / 10.00 / 8.00 |
| Current + earlier event meanings | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Current + roles + earlier event meanings | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Current + roles + wrong-source history | 76.47% | 81.25% | 0.7879 | 0.9041 | 0.8936 | 26.00 / 8.00 / 6.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 1.0000 | 1.0000 | 0.00 / 0.00 / 32.00 |
| DIAGNOSTIC: context + current elapsed time | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Direct prior-evidence rule | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |

Status-200 transfer outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 75.76% | 78.12% | 0.7692 | 0.8589 | 0.8828 | 25.00 / 8.00 / 7.00 |
| Current + roles | 73.33% | 68.75% | 0.7097 | 0.8769 | 0.8662 | 22.00 / 8.00 / 10.00 |
| Current + earlier event meanings | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Current + roles + earlier event meanings | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Current + roles + wrong-source history | 80.00% | 75.00% | 0.7742 | 0.9019 | 0.8936 | 24.00 / 6.00 / 8.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 1.0000 | 1.0000 | 0.00 / 0.00 / 32.00 |
| DIAGNOSTIC: context + current elapsed time | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 32.00 |
| Direct prior-evidence rule | 100.00% | 100.00% | 1.0000 | 1.0000 | 1.0000 | 32.00 / 0.00 / 0.00 |

#### Crossed test population

| Arm | All accuracy | All macro-F1 | Status-200 accuracy | Status-200 macro-F1 |
|---|---:|---:|---:|---:|
| Current + coverage controls | 69.79% | 0.3166 | 9.38% | 0.0944 |
| Current + roles | 69.62% | 0.3098 | 8.85% | 0.0876 |
| Current + earlier event meanings | 66.67% | 0.2222 | 0.00% | 0.0000 |
| Current + roles + earlier event meanings | 66.67% | 0.2222 | 0.00% | 0.0000 |
| Current + roles + wrong-source history | 68.92% | 0.2899 | 6.77% | 0.0677 |
| Earlier event meanings + coverage controls | 75.00% | 0.2143 | 25.00% | 0.1000 |
| DIAGNOSTIC: context + current elapsed time | 66.67% | 0.2222 | 0.00% | 0.0000 |
| Majority outcome | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Direct prior-evidence rule | 66.67% | 0.2222 | 0.00% | 0.0000 |

Status-200 remote outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 45.45% | 41.67% | 0.4348 | 0.4397 | 0.3935 | 40.00 / 48.00 / 56.00 |
| Current + roles | 40.00% | 41.67% | 0.4082 | 0.4275 | 0.3627 | 40.00 / 60.00 / 56.00 |
| Current + earlier event meanings | 33.33% | 33.33% | 0.3333 | 0.4259 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Current + roles + earlier event meanings | 33.33% | 33.33% | 0.3333 | 0.4259 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Current + roles + wrong-source history | 39.81% | 42.71% | 0.4121 | 0.4316 | 0.3753 | 41.00 / 62.00 / 55.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.4214 | 0.3414 | 0.00 / 0.00 / 96.00 |
| DIAGNOSTIC: context + current elapsed time | 33.33% | 33.33% | 0.3333 | 0.4259 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |
| Direct prior-evidence rule | 33.33% | 33.33% | 0.3333 | 0.4444 | 0.3333 | 32.00 / 64.00 / 64.00 |

Status-200 transfer outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 40.38% | 43.75% | 0.4200 | 0.4324 | 0.3659 | 42.00 / 62.00 / 54.00 |
| Current + roles | 44.57% | 42.71% | 0.4362 | 0.4193 | 0.3796 | 41.00 / 51.00 / 55.00 |
| Current + earlier event meanings | 33.33% | 33.33% | 0.3333 | 0.4259 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Current + roles + earlier event meanings | 33.33% | 33.33% | 0.3333 | 0.4259 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Current + roles + wrong-source history | 40.45% | 37.50% | 0.3892 | 0.4333 | 0.3822 | 36.00 / 53.00 / 60.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.4132 | 0.3310 | 0.00 / 0.00 / 96.00 |
| DIAGNOSTIC: context + current elapsed time | 33.33% | 33.33% | 0.3333 | 0.4259 | 0.3333 | 32.00 / 64.00 / 64.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 96.00 |
| Direct prior-evidence rule | 33.33% | 33.33% | 0.3333 | 0.4444 | 0.3333 | 32.00 / 64.00 / 64.00 |

#### Factorial_all test population

| Arm | All accuracy | All macro-F1 | Status-200 accuracy | Status-200 macro-F1 |
|---|---:|---:|---:|---:|
| Current + coverage controls | 75.39% | 0.4288 | 26.17% | 0.2621 |
| Current + roles | 74.87% | 0.4117 | 24.61% | 0.2451 |
| Current + earlier event meanings | 75.00% | 0.4167 | 25.00% | 0.2500 |
| Current + roles + earlier event meanings | 75.00% | 0.4167 | 25.00% | 0.2500 |
| Current + roles + wrong-source history | 74.87% | 0.4125 | 24.61% | 0.2459 |
| Earlier event meanings + coverage controls | 75.00% | 0.2143 | 25.00% | 0.1000 |
| DIAGNOSTIC: context + current elapsed time | 75.00% | 0.4167 | 25.00% | 0.2500 |
| Majority outcome | 75.00% | 0.2143 | 25.00% | 0.1000 |
| Direct prior-evidence rule | 75.00% | 0.4167 | 25.00% | 0.2500 |

Status-200 remote outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 53.78% | 50.00% | 0.5182 | 0.5042 | 0.5132 | 64.00 / 55.00 / 64.00 |
| Current + roles | 47.76% | 50.00% | 0.4885 | 0.5004 | 0.4855 | 64.00 / 70.00 / 64.00 |
| Current + earlier event meanings | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Current + roles + earlier event meanings | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Current + roles + wrong-source history | 48.91% | 52.34% | 0.5057 | 0.5149 | 0.5019 | 67.00 / 70.00 / 61.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5133 | 0.5094 | 0.00 / 0.00 / 128.00 |
| DIAGNOSTIC: context + current elapsed time | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |
| Direct prior-evidence rule | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |

Status-200 transfer outcome:

| Arm | Precision | Recall | F1 | AP | ROC AUC | TP / FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Current + coverage controls | 48.91% | 52.34% | 0.5057 | 0.5035 | 0.4976 | 67.00 / 70.00 / 61.00 |
| Current + roles | 51.64% | 49.22% | 0.5040 | 0.5018 | 0.5012 | 63.00 / 59.00 / 65.00 |
| Current + earlier event meanings | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Current + roles + earlier event meanings | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Current + roles + wrong-source history | 50.42% | 46.88% | 0.4858 | 0.5237 | 0.5119 | 60.00 / 59.00 / 68.00 |
| Earlier event meanings + coverage controls | 0.00% | 0.00% | 0.0000 | 0.5024 | 0.5043 | 0.00 / 0.00 / 128.00 |
| DIAGNOSTIC: context + current elapsed time | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |
| Majority outcome | 0.00% | 0.00% | 0.0000 | 0.5000 | 0.5000 | 0.00 / 0.00 / 128.00 |
| Direct prior-evidence rule | 50.00% | 50.00% | 0.5000 | 0.5000 | 0.5000 | 64.00 / 64.00 / 64.00 |

## Hidden-policy identifiability check

Each completed-operation observation is copied into two counterfactual interpretations with opposite hidden authorization labels. The technical feature vector and prediction remain identical. These are not extra physical executions or independent samples. With policy context withheld, the paired construction forces accuracy and ROC AUC to 0.5; this is an identifiability demonstration, not empirical chance performance on a real maliciousness benchmark.

| Arm | Linked underlying operations | Crossed underlying operations | Factorial underlying operations | Accuracy / AUC in each population |
|---|---:|---:|---:|---:|
| Current + coverage controls | 48 | 144 | 192 | linked: 50.00% / 0.5000; crossed: 50.00% / 0.5000; factorial_all: 50.00% / 0.5000 |
| Current + roles | 48 | 144 | 192 | linked: 50.00% / 0.5000; crossed: 50.00% / 0.5000; factorial_all: 50.00% / 0.5000 |
| Current + earlier event meanings | 48 | 144 | 192 | linked: 50.00% / 0.5000; crossed: 50.00% / 0.5000; factorial_all: 50.00% / 0.5000 |
| Current + roles + earlier event meanings | 48 | 144 | 192 | linked: 50.00% / 0.5000; crossed: 50.00% / 0.5000; factorial_all: 50.00% / 0.5000 |
| Current + roles + wrong-source history | 48 | 144 | 192 | linked: 50.00% / 0.5000; crossed: 50.00% / 0.5000; factorial_all: 50.00% / 0.5000 |
| Earlier event meanings + coverage controls | 48 | 144 | 192 | linked: 50.00% / 0.5000; crossed: 50.00% / 0.5000; factorial_all: 50.00% / 0.5000 |
| DIAGNOSTIC: context + current elapsed time | 48 | 144 | 192 | linked: 50.00% / 0.5000; crossed: 50.00% / 0.5000; factorial_all: 50.00% / 0.5000 |

## Interpretation boundaries

- The direct rule reads earlier successful remote-job and file-write evidence and uses the current success status. Matching that rule does not establish special value from machine learning.
- The role permutation changes logical metadata for identical worker processes. It is not a new host population, a real organizational role change, or domain-transfer validation.
- The 50 ms condition is a synthetic arrival shift. It is not a measured production delay distribution or a clock-synchronization repair experiment. Dropping remote-job or file-write records removes one observation channel while preserving the fixed outcomes and test queries.
- The observations describe post-transaction interpretation with only strictly earlier history. They do not demonstrate warning before an action occurs, blocking, or prevented exfiltration.
- The authorization twins expose missing policy information. They do not substitute for independently executed normal-admin and malicious attack campaigns.
- The literature note describes prospective design requirements. This realized run did not execute separate authorized-admin and unauthorized-attack campaigns; it executed harmless operation/outcome combinations and later paired opposite hidden-policy interpretations.
- The separately implemented audit verifies saved calculations and operation artifacts. It is not independent human labeling, peer review, or external deployment validation.

The applicable research context and prior-art overlap are in [LITERATURE_SCOPE.md](../../verified_stage_lab/LITERATURE_SCOPE.md). The defensible contribution is measured sensitivity to information and workflow assumptions, if supported by the audited results; novelty remains unestablished.

## Provenance

- Frozen protocol SHA256: `82904540f172ef6f05b43aa3463434f0b2b60e2f5624bd83f473fddde818b753`.
- Private completed summary SHA256: `95032c56e7a8f1d5e793c48545497e98324bfa1f12b4d967cec7183b02aa185e`.
- Public files contain aggregate metrics and hashes. Raw observations, probabilities, model files, worker receipts, and private paths are excluded.
- [SUMMARY.json](SUMMARY.json) provides the compact result index; [EVIDENCE.json](EVIDENCE.json) preserves the full aggregate and seed-level metric roster; [PUBLICATION.json](PUBLICATION.json) binds these public files.
