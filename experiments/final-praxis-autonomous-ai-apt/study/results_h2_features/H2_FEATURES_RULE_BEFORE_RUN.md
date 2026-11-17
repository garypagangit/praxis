# H2, the "why": which features carry the separation in each ATT&CK stage group. Rules, written before the run

Written 2026-11-14 11:12:34 EST, on the user's word of 11:10 EST ("I agree with the design, please write the rule file, run layer 3, and assemble all three layers into one table and figure").

## What this is
- An explanation placed under H2, in three layers. It is **descriptive and post hoc**. It gives no verdict and changes nothing about H2, whose outcome rests on the stage test of `results_h2_stage/` alone.
- Nothing in `results/`, `results_h2_stage/`, `data/`, `reports/` or the frozen code is written or changed. New code goes to `code/h2_features/`, new outputs to `results_h2_features/`.
- Outputs hold column names and numbers only. No command text, program name or window text is read or written.

## What was already known when this was written
- **Layer 1** exists (EDA Pass 2, 2026-11-13) and has been read: single-feature AUC within each stage group on training windows.
- **Layer 2** exists in `results/tables/T_by_stage_group.csv`. The rows for the main configuration and for no command content have been read. The rows for no context have not been looked at by stage group.
- **Layer 3** does not exist. No SHAP value or model-based importance has been computed on study 3 data.

## Stage groups
Stages 1-4, stage 5 and stage 7 (the three with at least 10 windows of each class). Stage 6 is computed, marked indicative, and used in no rule.

## Layer 1: single features by stage group (assembled, not recomputed)
1. Source: `reports/eda/tables/T7_same_stage_auc_all_features_w30.csv`, restricted to the 40 columns of the main configuration. Training windows of the within-session split. The AUC is the one kept in the direction the column has over all training rows (Pass 2 reading P2-4).
2. **Top:** the five columns with the highest AUC in the stage group.
3. Tier mean: the mean of that AUC over the columns of the tier that are in the main configuration: behavior (18), command content (14), context (8).

## Layer 2: feature tiers by stage group (from the saved held-out predictions; nothing fitted)
1. Source: the saved predictions of the trials `main`, `no_command_content` and `no_context`, five classifiers, with the stage group joined after scoring.
2. Quantity: macro-F1 within the stage group, and two differences: **what command content adds** (main minus no command content; the 14 command-content columns and their 4 context columns) and **what context adds** (main minus no context; the 8 context columns).
3. Each difference gets a 95% percentile interval from the frozen draws (2,000 resamples of whole sessions within each class, seed 42, reading T14), paired on the same resamples.
4. The assembled table shows XGBoost and the range over the five classifiers.

## Layer 3: what the fitted model relies on, by stage group (new)
1. **Model.** XGBoost, main configuration (30 s windows, 40 columns): the nine models of the main trial, each fitted on eight sessions by the frozen `fit_model` with the frozen rows, weights and seed. Every held-out window is explained by the model that never saw its session.
2. **The run is void unless** the nine models reproduce the saved held-out predictions of `results/trials/main__xgb.json` for all 951 windows (calibrated P(AI) to 1e-9 and the same call), Freeze 1 and Freeze 2 are unchanged before and after, and the libraries equal the plumbing log's.
3. **SHAP values.** XGBoost's own TreeSHAP (`pred_contribs`), in the model's log-odds, before calibration. Check: for every window the 40 contributions and the base value sum to the model's margin (to 1e-3).
4. **Importance of a column in a stage group.** The mean absolute SHAP value over the human windows of the stage group and the mean over its AI windows, averaged, so that the classes count equally as they do in macro-F1. **Share** is that importance divided by the sum over the 40 columns. The plain mean over all windows is reported beside it.
5. **Top:** the five columns with the largest share in the stage group.
6. **Direction.** The sign of Spearman's rho between the column's value and its SHAP value, over the windows of the stage group in which the column is defined: positive means a higher value pushes toward AI. It needs at least 10 such windows and variation in both; otherwise the column has no direction there.
7. **Holds in every stage:** in the top ten of all three stage groups, with the same direction in all three.
8. **Stage-dependent:** in the top five of at least one stage group and not "holds in every stage".
9. **Robustness.** Each ranking is recomputed nine times, each time with one session's windows left out of the averages (no model is refitted). The lowest and highest rank are reported. A drop that leaves under 10 windows of either class in the stage group is marked indicative and still reported.
10. **Tier share:** the sum of the shares over behavior (18), command content (14) and context (8).
11. **Reported beside the ranking, not used for it:** the mean SHAP value over the AI windows minus the mean over the human windows (how far the column moves AI windows toward AI, relative to human windows, in log-odds).
12. Near-duplicate columns (Pass 2, T6) are not merged; the model splits credit between them, and the table says which they are.
13. **Only XGBoost is run.** It is the classifier H3 names. Random forest, which the earlier plan (F11) named for this pass, can be added under the same rules.

## The assembled table and figure
- **One table:** tier rows, then feature rows. The feature rows are every column that is in the top five of any of the three stage groups in Layer 1 or in Layer 3. For each stage group: Layer 1 AUC and rank, Layer 2 difference (tier rows only), Layer 3 share, rank, rank range and direction; and whether the column holds in every stage.
- **One figure,** three panels, in the Pass 1 figure style: Layer 2 macro-F1 by stage group with and without each tier; Layer 3 share by column and stage group; Layer 1 AUC for the same columns.
- The full Layer 3 table (40 columns by stage group) and the full Layer 2 table (five classifiers) are written beside them.
