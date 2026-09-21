# Reliable APT recognition with limited labeled data: followup results

**Execution complete:** 50 original model/seed cells, 60 stronger-tree cells, and ten rare-stage review comparisons were audited. The original TabICL development gate is **PASS**; the stronger equal-label comparison is **PASS**; the rare-stage review policy is **DEVELOPMENT_NEGATIVE**.

These are development findings on the same feature-deduplicated SCVIC author-training split. Completion and arithmetic verification do not establish a novel method, independent attack-campaign generalization, or reliable deployment.

## Full original comparison

Unlike the earlier weighted prescreen, these models were evaluated on every one of the 30,787 development-test flows. Each used the same 32 fitting labels per class (192 total) across ten matched fitting seeds. Seeds reuse the same test flows and are not independent incidents.

| Model | Mean full-test macro-F1 |
|---|---:|
| lightgbm | 44.96% |
| random_forest | 43.78% |
| tabicl_v2 | 54.44% |
| tabpfn_2_5_synthetic | 54.08% |
| xgboost | 43.59% |

Macro-F1 gives all six classes equal weight; it is not accuracy. Boosted-tree hyperparameters and comparator families were selected using fitting-only cross-validation, never test outcomes. The foundation candidates were fixed in advance.

The original paired TabICL macro-F1 difference is +10.08 percentage points. Full uncertainty-set E4 result: **FAIL**. [Full E1/E4 evidence](E1_ANALYSIS.json).

## Stronger controls and additional normal examples

The new tree search used 12 XGBoost, 12 LightGBM, and six Random Forest settings in training-only three-fold cross-validation. No extra validation labels were used.

| Fitting condition | Tree family | Mean full-test macro-F1 | Normal false-alarm rate |
|---|---|---:|---:|
| abundant_benign_1024 | lightgbm | 64.87% | 0.44% |
| abundant_benign_1024 | random_forest | 64.33% | 0.36% |
| abundant_benign_1024 | xgboost | 67.05% | 0.31% |
| equal_32_per_class | lightgbm | 45.02% | 9.14% |
| equal_32_per_class | random_forest | 43.97% | 10.87% |
| equal_32_per_class | xgboost | 43.43% | 10.89% |

At the same 192-label budget, TabICL's mean difference versus the wider-CV-selected boosted tree was +10.24 percentage points. Both rare-stage recall guards remain part of the decision.

The abundant-normal condition used 1,024 normal labels and the same 160 attack labels, totaling 1,184. Its comparison with a 192-label foundation model is an explicitly unequal-budget deployment challenge, not a fair model-family ranking. [All controls and paired comparisons](COMPARISONS.json).

## Rare-stage review experiment

The fixed policy allocated a nominal 0.5% benign tail to a general attack score and 0.5% to a rare-stage rescue score combining TabICL and the original training-CV-selected tree. Both thresholds used source benign calibration examples only. The policy had to beat both fixed single-model controls, protect every attack stage, and remain at or below 1.5% observed normal-traffic routing in every seed.

Decision: **DEVELOPMENT_NEGATIVE**. Mean changes in minimum initial-compromise/exfiltration routing recall: single_tabicl: -0.09 percentage points; single_tree: +15.13 percentage points.

Sending a flow to review is not correct stage identification or successful human correction. No human review was performed. The proposed rule needs 29,929 known-normal calibration examples beyond the 192 fitting labels; the conformal controls use all 30,782 calibration labels. At nominal 95% class-conditional coverage, the 14 initial-compromise calibration cases force that stage into every set, making this policy's review mapping route every flow.

[Policy results](GATE_AGGREGATE.json) and [independent calculation audit](GATE_AUDIT.json).

## Independent evidence and praxis decision

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

The [audited external evidence](TRANSFER_SUMMARY.json) retains every seed, procedure-level detected/missed count, and raw-flow multiplicity sensitivity. The raw view reweights the same unique-query predictions; it is not a separate inference run.

Direct prior work already covers these combinations, including tree-to-foundation rescue, few-label adaptation, cross-dataset transfer, and conformal prediction. This review policy is a development adaptation tested under rare-stage and false-alert constraints; there is no first-method claim. A defensible praxis contribution still requires a specific positive benefit and independent evidence with the relevant attack-stage labels. See the [novelty review and publication-status distinctions](../../tabular_followup/NOVELTY_POSITION.md) and [method boundaries](../../tabular_followup/RARE_STAGE_DESIGN.md).

Remaining limits: only 15 initial-compromise and 106 exfiltration development-test examples; correlated flows and fitting seeds; fixed dataset label interpretation; no analyst workload study; no missing-log, early-warning, actor-attribution, or unknown-stage guarantee. All outcomes, including failed gates, are retained.
