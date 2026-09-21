# More normal-traffic examples reduce false alarms, with attack-detection tradeoffs

Audited development results, 2026-09-21T14:47:33.988083+00:00. **60/60 tree runs complete.**

## Finding in plain language

Teaching the existing models more about normal traffic substantially reduced false alarms and improved their overall classification score. The attack-training examples were unchanged. However, the models missed more lateral-movement activity. This is a measured development improvement with a security tradeoff, not a new algorithm or a validated deployment.

For the training-CV-selected tree, macro-F1 changed 0.4421 → 0.6543, and the normal false-alarm rate changed 10.04% → 0.40%. Overall attack detection changed 98.40% → 95.70%.

## What changed

Both conditions used the same 32 examples of each of five attack classes. The first used 32 normal examples; the second used 1,024. That adds 992 benign fitting labels, increasing the total from 192 to 1,184. Each condition used the same wider hyperparameter search and fitting-only cross-validation. XGBoost versus LightGBM was selected by training CV, with XGBoost winning exact ties; test scores never selected the model.

Each of the ten seeds was evaluated on the same 30,787 unique development-test flows from the SCVIC author training corpus. The source author holdout was unavailable. These are not ten independent incidents.

## All model families

Values show 192-label → 1,184-label conditions; means across ten seeds.

| Model | Macro-F1 | Normal false alarms | Initial-stage recall | Exfiltration-stage recall |
|---|---:|---:|---:|---:|
| xgboost | 0.4343 → 0.6705 | 10.89% → 0.31% | 92.67% → 92.00% | 73.40% → 74.81% |
| lightgbm | 0.4502 → 0.6487 | 9.14% → 0.44% | 93.33% → 94.00% | 71.60% → 72.64% |
| random_forest | 0.4397 → 0.6433 | 10.87% → 0.36% | 90.67% → 88.67% | 75.57% → 75.94% |
| cv_selected_gbdt | 0.4421 → 0.6543 | 10.04% → 0.40% | 93.33% → 93.33% | 71.60% → 72.83% |

## The security tradeoff

Correctly naming an attack stage and noticing any attack are different measurements. The first requires the right stage label; the second counts any non-normal prediction as detection.

| Actual stage | Correct stage identification | Detected as any attack |
|---|---:|---:|
| DataExfiltration | 71.60% → 72.83% | 100.00% → 99.91% |
| InitialCompromise | 93.33% → 93.33% | 100.00% → 98.00% |
| LateralMovement | 69.79% → 63.33% | 94.24% → 83.06% |
| Pivoting | 67.36% → 65.36% | 99.34% → 98.33% |
| Reconnaissance | 76.37% → 76.55% | 98.45% → 97.02% |

The table uses the training-CV-selected tree, not the best family chosen from test results. In particular, the reduction in lateral-activity detection must be considered alongside the large false-alarm reduction. No new pass/fail criterion was applied to this descriptive unequal-label comparison.

## What this means for the praxis

- This supplies a stronger practical baseline for the foundation-model and review-policy experiments.
- It shows why normal-traffic label availability must be disclosed: a balanced 192-label baseline can be a poor operational comparator when more benign examples are available.
- More training data and tree classifiers are established methods. This result alone does not establish novelty. The [literature review](../../tabular_followup/NOVELTY_POSITION.md) documents direct overlap.
- These trees have not been independently tested on Sandworm in the abundant-benign condition. The earlier negative Sandworm result used the original 192-label models; do not mix those results.
- InitialCompromise has only 15 test examples and DataExfiltration has 106. Repeated seeds reuse these cases; no independent-incident confidence or generalization guarantee follows.
- Early identification, actor identity, and robustness to missing or delayed logs were not measured here.

## Evidence and remaining work

[SUMMARY.json](SUMMARY.json) retains all seed-level tree summaries. [AUDIT.json](AUDIT.json) is the exact independent audit that verifies input, support, CV, imputation, prediction and completion hashes and recomputes metrics. Its foundation comparison is an explicitly incomplete snapshot; no foundation winner is declared here.

The frozen full foundation runs, rare-stage review gate, and source-calibrated Sandworm threshold diagnostic continue under the existing [completion process](../../tabular_followup/RUN_STATUS.md). Their source, settings and criteria were not changed in response to this finding.
