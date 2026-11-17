# H2, the "why", Layer 3 for the other four classifiers. Addendum to the rules, written before the run

Written 2026-11-14 12:11:09 EST, on the user's word of 12:08 EST ("yes under the same rules can you do the other 4 algorithms"). It adds to `results_h2_features/H2_FEATURES_RULE_BEFORE_RUN.md` (SHA-256 `0ccbf28d…a017201`), which stays as it is.

## What was already known when this was written
- Layers 1 and 2, and Layer 3 for XGBoost (`results_h2_features/`, run at 11:15 EST today): the same three command-text columns lead in every stage group.
- **Not known:** any SHAP value or model-based importance of logistic regression, random forest, gradient boosting or histogram gradient boosting on study 3 data. The shap library was installed and its source read before this was written; no study data was passed to it.

## The same rules
Items 1 to 12 of Layer 3 apply to each classifier unchanged: the main configuration (30 s windows, 40 columns); the nine models of the main trial, fitted again by the frozen `fit_model` with the frozen rows, weights and seed; every held-out window explained by the model that never saw its session; importance as the mean absolute SHAP value over the human windows and over the AI windows, averaged; share; top five; direction by the sign of Spearman's rho; "holds in every stage"; "stage-dependent"; the nine session drops; tier share; the net effect beside the ranking. Stage groups 1-4, 5 and 7; stage 6 indicative and in no rule. Descriptive and post hoc; no verdict.

## What has to differ: how the SHAP values are computed
Each classifier has its own exact method, and each is used. All are of the model's raw score, before calibration.

| Classifier | What the model is given | SHAP values | Scale |
|---|---|---|---|
| XGBoost | 40 columns, undefined values as they are | Its own TreeSHAP (as run at 11:15) | Log-odds |
| Random forest | 40 columns, undefined values as they are | TreeSHAP, path-dependent (shap 0.49.1, `TreeExplainer`) | Probability of AI; a forest has no log-odds |
| Histogram gradient boosting | 40 columns, undefined values as they are | TreeSHAP, path-dependent | Log-odds |
| Gradient boosting | 40 columns with undefined values set to the training median, and one added input, "the window has commands" (reading T5) | TreeSHAP, path-dependent | Log-odds |
| Logistic regression | The same 41 inputs, with log(1 + x) and standardizing (reading T6) | The exact SHAP value of a linear model whose inputs are taken as independent: coefficient times (input minus its mean over the fold's training rows, not weighted) | Log-odds |

1. **Void for a classifier unless** its nine models reproduce its saved held-out predictions (`results/trials/main__<model>.json`: calibrated P(AI) to 1e-9, the same call, all 951 windows), and for every window the SHAP values and the base value sum to the model's raw score (to 1e-4).
2. **The added input (gradient boosting, logistic regression).** It is 1 when `cmd_count` is above zero and so is a function of `cmd_count` alone. Its SHAP value is added to `cmd_count`'s before the absolute value is taken, so that every classifier is described over the same 40 columns. Its own share is written to the full table.
3. **Undefined values (gradient boosting, logistic regression).** The model receives the training median, and the SHAP value is what the model does with it. The direction (rule 6) still uses only the windows in which the column is defined.
4. **Comparing classifiers.** Shares are within a classifier and a stage group, so they can be set side by side. The net effect is in each classifier's own scale and is compared across classifiers by its sign only.
5. **XGBoost is computed again by the new code.** Its shares must equal `tables/L3_shap_by_stage_group.csv` (to 1e-9), or the run is void.

## Across the five classifiers (new, fixed here)
1. For each stage group and column: the number of the five classifiers that have it in their top five, and in their top ten.
2. **Agreed top column:** in the top five of at least four of the five classifiers in that stage group.
3. For each classifier and stage group: the share of command content with its 4 context columns (18 columns).
4. For each classifier: the columns that hold in every stage and those that are stage-dependent (rules 7 and 8); then, for each column, the number of classifiers for which it holds in every stage.
5. **Do the classifiers rely on the same columns?** Spearman's rho between the 40 shares of each pair of classifiers, in each stage group (10 pairs).
6. **Does a classifier rely on the same columns in every stage group?** Spearman's rho between its 40 shares in each pair of stage groups (3 pairs).

## Outputs
New folder `results_h2_features/five_classifiers/`: the Layer 3 tables for the five classifiers, the tables of the section above, a summary, and one figure: the share by column and stage group for each of the five classifiers, with a row for every column that is in the top five of any stage group for any classifier, ordered by its mean share over all windows across the five. The files written at 11:15 to 11:22 are not changed. Column names and numbers only.
