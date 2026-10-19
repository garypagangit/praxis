# EXP-RQ3: classifier comparison

**Status:** draft / not run. **Tracker:** E03/E04. **Selection freeze:** Nov 6; locked evaluation Nov 7.

**RQ3:** Which candidate provides the strongest trial-level attribution under the same grouped evaluation and bounded tuning protocol?

**Candidates:** decision tree, random forest, XGBoost, SVM and FT-Transformer. **References:** dummy, logistic regression, timing-only and metadata-only diagnostics. Freeze exact implementations and search spaces before training.

**H3:** A candidate has a practically meaningful advantage over the others. Freeze the minimum important difference and corrected comparison family before scoring. If this cannot be supported, report a tie or inconclusive comparison.

| Element | Method |
| --- | --- |
| Independent variable | Classifier family; model-specific parameters tuned within frozen limits |
| Common inputs | Identical eligible trials, feature representation, outer partitions and metrics; transformations fitted within training folds |
| Primary response | Trial-level macro-F1 and paired candidate contrasts |
| Secondary responses | Human false-AI-label rate, per-class precision/recall, calibration where supported, inference/training cost |
| Tuning | Grouped inner validation, early stopping without test access, recorded evaluation/time budgets and seeds |
| Development selection | Freeze ranking/eligibility/tie-break rule; choose primary model from development results, not final test performance |
| Final comparison | Score all frozen candidates in one batch; retain all predictions, failures and uncertainty |
| Acceptance | Practical superiority under corrected comparisons; selecting a cheaper model in a statistical tie is an engineering decision, not proof of superior accuracy |
| Limitation | Unrun/failed candidates are reported explicitly; a sequence transformer would change the representation and require a separate comparison |

Deliver candidate/search table, learning-curve diagnostics, run manifests, locked paired predictions and ranked results with uncertainty. Keep H1/H2/H3 shared-data dependence visible. [Fillable experiment record](templates/EXPERIMENT_TEMPLATE.md) · [Results record](templates/RESULTS_TEMPLATE.md).
