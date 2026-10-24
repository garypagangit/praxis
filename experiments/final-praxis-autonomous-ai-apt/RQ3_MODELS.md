# EXP-RQ3: classifier comparison

**Status:** prospective matched-study experiment not run; wording approved October 24, 2026. Earlier archive/synthetic screens are exploratory only. **Tracker:** E03/E04. **Selection freeze:** Nov 6; locked evaluation Nov 7.

**RQ3:** Among XGBoost, a decision tree, a random forest, SVM and a tabular transformer, which provides the strongest trial-level human-versus-autonomous-AI classification?

**Candidates:** decision tree, random forest, XGBoost, SVM and FT-Transformer. **References:** dummy, logistic regression, timing-only and metadata-only diagnostics. Freeze exact implementations and search spaces before training.

**H3:** SVM achieves higher trial-level macro-F1 than XGBoost, a decision tree, a random forest and a tabular transformer for human-versus-autonomous-AI classification.

| Element | Method |
| --- | --- |
| Independent variable | Classifier family; model-specific parameters tuned within frozen limits |
| Common inputs | Identical eligible trials, feature representation, outer partitions and metrics; transformations fitted within training folds |
| Primary response | Trial-level macro-F1 and paired candidate contrasts |
| Secondary responses | Human false-AI-label rate, per-class precision/recall, calibration where supported, inference/training cost |
| Tuning | Grouped inner validation, early stopping without test access, recorded evaluation/time budgets and seeds |
| Development selection | Freeze ranking/eligibility/tie-break rule; choose primary model from development results, not final test performance |
| Final comparison | Score all frozen candidates in one batch; retain all predictions, failures and uncertainty |
| Acceptance | Supported SVM superiority over every named comparator under frozen paired contrasts and multiplicity correction; ties or insufficient evidence do not support H3 |
| Limitation | Unrun/failed candidates are reported explicitly; a sequence transformer would change the representation and require a separate comparison |

Deliver candidate/search table, learning-curve diagnostics, run manifests, locked paired predictions and ranked results with uncertainty. Keep H1/H2/H3 shared-data dependence visible. [Fillable experiment record](templates/EXPERIMENT_TEMPLATE.md) · [Results record](templates/RESULTS_TEMPLATE.md).

[October 24 hypothesis rationale and revision history](../../PRAXIS_RESEARCH_DESIGN.md#october-24-revision-and-evidentiary-basis). Freeze exact contrasts, baselines and practical margins before final evaluation.
