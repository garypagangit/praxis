# Final praxis decision: rare-stage protection and limited-label APT recognition

All required evidence is complete and audited: 50 original model runs, 60 stronger-control runs, ten review-policy pairs, and 20 external-transfer runs including the source-threshold diagnostic. Completion does not establish a novel method or deployment readiness.

## What remains worth pursuing

The review policy did not meet its frozen development criteria; this completed experiment does not support advancing that policy as a demonstrated improvement.

The TabICL comparison also passed the stronger equal-label control gate, preserving a candidate classification benefit for independent replication.

**No algorithmic novelty or independent attack-stage validation is established.** A positive development gate identifies work worth validating; it is not a completed novel praxis claim. The Sandworm experiment tests binary transfer on one capture and cannot validate the proposed InitialCompromise/Exfiltration protection.

| Frozen decision | Completed outcome |
|---|---|
| Original classification comparison | PASS |
| Original uncertainty-set comparison | FAIL |
| Stronger comparison at the same 192 labels | PASS |
| Rare-stage review policy | DEVELOPMENT_NEGATIVE |

Each outcome retains its original criterion. No new success threshold or combined score was introduced for this report.

## Rare-stage protection: exact criteria and absolute cost

The frozen gate requires all three conditions: (1) at least **+5 percentage points** in the mean paired difference of each seed's minimum InitialCompromise/Exfiltration routing recall, against **both** fixed single-model controls; (2) no more than **5 percentage points of mean recall loss for any attack stage**, against either control; and (3) normal-flow routing at or below **1.5% in every seed**. The rule therefore permits a limited average loss in an individual stage; it does not require every stage or seed to improve.

The two candidate channels each use a nominal 0.5% source-normal tail. Each fixed single-model control uses 1%. These calibration targets are distinct from the measured 1.5% per-seed development gate and provide no arbitrary-shift guarantee.

| Routing policy | Initial recall (mean routed/15) | Exfiltration recall (mean routed/106) | Queue attack precision | Mean reviewed flows | Review workload | Mean normal FPR | Maximum seed normal FPR |
|---|---:|---:|---:|---:|---:|---:|---:|
| Two-model review policy | 99.33% (14.90/15) | 99.91% (105.90/106) | 76.81% | 1027.9 | 3.34% | 0.80% | 0.96% |
| Fixed TabICL control | 99.33% (14.90/15) | 100.00% (106.00/106) | 73.53% | 1090.2 | 3.54% | 0.96% | 1.03% |
| Fixed source-CV-selected tree control | 88.00% (13.20/15) | 87.64% (92.90/106) | 70.37% | 954.1 | 3.10% | 0.94% | 1.06% |
| TabICL-only rescue ablation | 99.33% (14.90/15) | 99.91% (105.90/106) | 79.08% | 996.2 | 3.24% | 0.70% | 0.85% |

**Ceiling limitation:** the fixed TabICL control's mean minimum rare-stage recall was 99.33%. Even a perfect candidate could gain only 0.67 percentage points, below the frozen +5-point requirement. The registered negative outcome is retained. This is a failed added-value test with a ceiling-limited endpoint, not evidence that rare attacks cannot be detected.

**Second-model ablation:** adding the tree to the otherwise matching TabICL-only two-channel rule changed Initial and Exfiltration routing recall by +0.00 and +0.00 percentage points. It changed routed attacks by +1.6 and benign reviews by +30.1 per fitting seed. These are descriptive component costs, not replacement success criteria.

Recall here means reaching the review queue. Queue precision means the fraction of reviewed flows that are any attack; this binary gate does not output a stage-classification precision. Correct stage identification and successful analyst adjudication were not measured by the routing experiment. Counts are means over repeated fits on the same cases, not additional independent attacks.

The candidate needs 29,929 known-normal calibration labels beyond its shared 192 fitting labels; conformal controls use all 30,782 calibration labels. Only nominal **95% class-conditional (Mondrian) LAC** is forced to include InitialCompromise for every input with these 14 rare calibration cases, making the specified protective mapping review every flow. This is not a claim that 90% Mondrian or all conformal methods review everything.

## Original models and the stronger benign-label challenge

| Original model | Full-test macro-F1 | Macro ROC-AUC | Macro average precision |
|---|---:|---:|---:|
| lightgbm | 0.4496 | 0.9721 | 0.6369 |
| random_forest | 0.4378 | 0.9729 | 0.6620 |
| tabicl_v2 | 0.5444 | 0.9879 | 0.7765 |
| tabpfn_2_5_synthetic | 0.5408 | 0.9848 | 0.7333 |
| xgboost | 0.4359 | 0.9731 | 0.6164 |

Macro metrics weight the six labels equally, including NormalTraffic. AUC and average precision use one-versus-rest continuous scores; average precision summarizes the precision-recall curve. All entries average ten fits on the same development-test rows.

### Stage classification: lightgbm

| Source label | Same test cases | Precision | Recall | F1 | ROC-AUC | Average precision |
|---|---:|---:|---:|---:|---:|---:|
| DataExfiltration | 106 | 0.3449 | 0.7245 | 0.4647 | 0.9743 | 0.4815 |
| InitialCompromise | 15 | 0.0227 | 0.9333 | 0.0438 | 0.9896 | 0.6260 |
| LateralMovement | 144 | 0.1321 | 0.6903 | 0.2147 | 0.9340 | 0.3769 |
| NormalTraffic | 29929 | 0.9996 | 0.9056 | 0.9501 | 0.9866 | 0.9996 |
| Pivoting | 425 | 0.6554 | 0.6720 | 0.6607 | 0.9691 | 0.7092 |
| Reconnaissance | 168 | 0.2632 | 0.7780 | 0.3636 | 0.9791 | 0.6284 |

### Stage classification: random_forest

| Source label | Same test cases | Precision | Recall | F1 | ROC-AUC | Average precision |
|---|---:|---:|---:|---:|---:|---:|
| DataExfiltration | 106 | 0.3362 | 0.7538 | 0.4616 | 0.9807 | 0.5238 |
| InitialCompromise | 15 | 0.0161 | 0.9000 | 0.0313 | 0.9775 | 0.6698 |
| LateralMovement | 144 | 0.1569 | 0.6729 | 0.2419 | 0.9272 | 0.3795 |
| NormalTraffic | 29929 | 0.9995 | 0.8958 | 0.9446 | 0.9929 | 0.9998 |
| Pivoting | 425 | 0.5446 | 0.6360 | 0.5762 | 0.9796 | 0.7420 |
| Reconnaissance | 168 | 0.2697 | 0.7363 | 0.3714 | 0.9797 | 0.6572 |

### Stage classification: tabicl_v2

| Source label | Same test cases | Precision | Recall | F1 | ROC-AUC | Average precision |
|---|---:|---:|---:|---:|---:|---:|
| DataExfiltration | 106 | 0.4906 | 0.8170 | 0.6112 | 0.9951 | 0.5888 |
| InitialCompromise | 15 | 0.0179 | 0.9333 | 0.0349 | 0.9938 | 0.8461 |
| LateralMovement | 144 | 0.1543 | 0.7493 | 0.2476 | 0.9581 | 0.4945 |
| NormalTraffic | 29929 | 0.9996 | 0.9274 | 0.9618 | 0.9960 | 0.9999 |
| Pivoting | 425 | 0.9024 | 0.6802 | 0.7752 | 0.9928 | 0.8817 |
| Reconnaissance | 168 | 0.5332 | 0.8518 | 0.6358 | 0.9916 | 0.8481 |

### Stage classification: tabpfn_2_5_synthetic

| Source label | Same test cases | Precision | Recall | F1 | ROC-AUC | Average precision |
|---|---:|---:|---:|---:|---:|---:|
| DataExfiltration | 106 | 0.4976 | 0.7755 | 0.6043 | 0.9936 | 0.5404 |
| InitialCompromise | 15 | 0.0173 | 0.9200 | 0.0336 | 0.9906 | 0.7388 |
| LateralMovement | 144 | 0.1172 | 0.7208 | 0.1927 | 0.9457 | 0.4385 |
| NormalTraffic | 29929 | 0.9996 | 0.9169 | 0.9560 | 0.9936 | 0.9998 |
| Pivoting | 425 | 0.8808 | 0.6689 | 0.7593 | 0.9927 | 0.8657 |
| Reconnaissance | 168 | 0.6104 | 0.8423 | 0.6991 | 0.9923 | 0.8163 |

### Stage classification: xgboost

| Source label | Same test cases | Precision | Recall | F1 | ROC-AUC | Average precision |
|---|---:|---:|---:|---:|---:|---:|
| DataExfiltration | 106 | 0.3258 | 0.7396 | 0.4458 | 0.9805 | 0.4859 |
| InitialCompromise | 15 | 0.0152 | 0.9333 | 0.0298 | 0.9893 | 0.5007 |
| LateralMovement | 144 | 0.1427 | 0.6875 | 0.2298 | 0.9227 | 0.4017 |
| NormalTraffic | 29929 | 0.9995 | 0.8902 | 0.9411 | 0.9891 | 0.9997 |
| Pivoting | 425 | 0.6024 | 0.6694 | 0.6284 | 0.9789 | 0.7036 |
| Reconnaissance | 168 | 0.2407 | 0.7565 | 0.3405 | 0.9780 | 0.6069 |

### Stronger controls and additional benign examples


| Stronger tree family | Macro-F1: 192 labels | Macro-F1: 1,184 labels |
|---|---:|---:|
| lightgbm | 0.4502 | 0.6487 |
| random_forest | 0.4397 | 0.6433 |
| xgboost | 0.4343 | 0.6705 |

For the fitting-CV-selected boosted tree, adding 992 normal examples changed macro-F1 from **0.4421 to 0.6543** and normal false alarms from **10.04% to 0.40%**. The same 160 attack fitting labels were retained; total fitting labels rose from 192 to 1,184.

The detection cost matters: pooled attack detection changed **98.40% to 95.70%**; lateral-movement detection as any attack changed **94.24% to 83.06%**. These are binary detection rates, distinct from correctly identifying the stage. More benign labels improved an established baseline with a security tradeoff; the unequal-label condition is not a fair model-family victory or a new algorithm.

This comparison does **not establish tree architecture superiority**: the foundation models received 192 fitting labels while the abundant-benign trees received 1,184. No matched abundant-benign foundation-model arm was run. Isolating an architecture effect would require the same label budget and fitting data.

The [independently audited benign-control report](../strong_benign_controls_v1/REPORT.md) documents all stage tradeoffs. Its tree predictions are hash-matched to this final comparison. The abundant-benign models were not the models evaluated in Sandworm transfer.

## External binary transfer: separate operating points

### External Sandworm transfer: primary decision rule

The independent target contains 2,091 unique flows: 2,054 normal and 37 attacks. Its attack labels describe procedures, with no exfiltration class. This binary transfer check cannot validate six-stage recognition or the rare-stage protection claim.

The primary decision is fixed: flag a flow when the source-trained classifier's highest-probability class is not NormalTraffic. The table reports arithmetic means across ten source-fitting seeds on the same target capture; these are not ten independent attack incidents.

| Model | Attack recall | Normal false-alarm rate | Attack precision | Attack F1 | Binary macro-F1 | ROC-AUC | Average precision |
|---|---:|---:|---:|---:|---:|---:|---:|
| TabICL | 44.32% | 28.21% | 2.65% | 4.91% | 43.42% | 0.7089 | 0.0380 |
| Source-CV-selected tree | 76.22% | 40.97% | 3.47% | 6.61% | 40.00% | 0.7473 | 0.1054 |

Attack recall measures how many attacks are caught; precision measures how many flagged flows are attacks. The normal false-alarm rate reports the cost to benign traffic. ROC-AUC and average precision describe ranking quality and do not replace these operating-point measurements.

For context, predicting normal for every flow detects no attacks yet reaches 49.55% binary macro-F1. The constant-score average-precision reference is 0.0177. This is an arithmetic reference, not another fitted model or success gate.

**At the primary argmax operating point, this transfer result does not establish a useful deployable detector.** A relative gain over a weak comparator does not resolve missed attacks, false alarms, or analyst workload; the absolute values above must support any practical claim. One small capture cannot establish broad deployment reliability.

### External Sandworm transfer: separate source-threshold diagnostic

Diagnostic status: **COMPLETE_AUDITED**.

This predeclared secondary operating point uses 29,929 labeled source-normal calibration examples per model and seed. It flags target scores strictly above the source-calibrated threshold for a nominal 1% benign tail. No target labels select that threshold. The table is separate from the primary argmax results above; a 1% source target does not guarantee 1% false alarms on Sandworm.

| Model | Attack recall | Normal false-alarm rate | Attack precision | Attack F1 | Binary macro-F1 | ROC-AUC | Average precision |
|---|---:|---:|---:|---:|---:|---:|---:|
| TabICL | 3.78% | 2.20% | 1.14% | 1.67% | 49.84% | 0.7089 | 0.0380 |
| Source-CV-selected tree | 14.32% | 4.41% | 5.44% | 7.66% | 52.32% | 0.7473 | 0.1054 |

Changing this threshold changes detection and false alarms; it does not change the underlying ranking scores, so ROC-AUC and average precision can remain identical to the primary table. Judge this diagnostic's practical value from its own recall, precision, and false-alarm rate.

The [audited external evidence](../tabular_followup_v1/TRANSFER_SUMMARY.json) retains every seed, procedure-level detected/missed count, and raw-flow multiplicity sensitivity. The raw view reweights the same unique-query predictions; it is not a separate inference run.

## Limits of the praxis claim

The [novelty review](../../tabular_followup/NOVELTY_POSITION.md), [focused benign-label novelty note](../../tabular_followup/BENIGN_LABEL_NOVELTY_NOTE.md), and [frozen method design](../../tabular_followup/RARE_STAGE_DESIGN.md) document relevant overlap and distinguish publication status. Conditional candidacy above follows the registered development gates only. A defensible new contribution still needs a clearly distinct mechanism or applied finding and independent evidence for the relevant attack stages.

These results do not establish early warning, actor attribution, robustness to missing or delayed logs, or unknown-stage protection. Fifteen InitialCompromise cases and 106 Exfiltration cases are reused across fitting seeds; no independent-incident confidence claim follows. The official SCVIC author holdout remains unavailable.

[Decision evidence and source hashes](DECISION_EVIDENCE.json). No new model fit, inference, threshold search, or human review was performed to create this report.
