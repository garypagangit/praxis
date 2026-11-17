# EDA run 3: rule written before the run (2026-11-15, 00:26 EST)

Written before any run 3 table or figure existed, on the user's word (2026-11-15, 00:17 EST: "take a look at Pagan's GML paper's EDA which was Dr. Ng's approved EDA format and see how we can get those same type of charts and data into our EDA. You can create a separate eda run 3 update if that is necessary ... (in the paper there should be no mention of study 3, eda pass 3, freeze 2)").

## 1. What run 3 is
A re-cut of the feature EDA for the research questions and hypotheses as they now stand (handoff `real_lab3_rq_hq_update_handoff.md` §2), in the figure format of the reference praxis (Pagan, Figures 4-1 to 4-11). Pass 1 and Pass 2 already hold counterparts of those figures (E1 to E12). They were drawn for the first hypothesis set: they rank all 60 columns, so the input-channel columns lead every ranked figure; they mark the 0.95 flag; they label the stage groups by number; and none shows the features that H1 now names. Run 3 changes four things and nothing else:
1. Ranked figures cover the main configuration only (40 columns: behavior 18, command content 14, and the 8 context columns that go with them).
2. Stage groups carry the names of the paper's Table 3-2: Discovery (stages 1 to 4), Execution (stage 5), Account manipulation (stage 6), Lateral movement and collection (stage 7).
3. Two figures are added for the features H1 names, by class and by stage group.
4. No figure carries a study-internal name (study 3, pass, freeze, flag, handoff) or a marker of the first hypothesis set.

Run 3 is a description. It fits no model, changes no feature, score, split or frozen file, and gives no verdict on a hypothesis. It follows the scoring, like Pass 2.

## 2. Rows and inputs
- Handoff rules 2 to 7 of `real_lab3_eda_handoff.md` §1 apply unchanged.
- **Counts** (windows by session, class and stage group) come from all kept windows, through the Pass 1 tables.
- **Feature values** come from the rows marked `train` in `data/splits/splits_w30.csv` and from no other row: 582 windows (425 human, 157 AI), loaded with the Pass 2 loader, which stops if a row of another split is present.
- **No command text and no recorder or audit record is opened.** `per_command.jsonl` and `data/windows/` are not on the input list. Program names appear only through the Pass 2 table `E8_*`.
- Inputs: `data/splits/splits_w30.csv`, `data/description/window_description_w30.csv`, `data/features/w30/features.csv`, `data/features/w30/feature_columns.json`, `data/labels/sessions.csv`, `data/description/sessions.csv`, `reports/05_windows_report.json`, and tables of `reports/eda/tables/`. Each is checked before it is read: against Freeze 1 or Freeze 2 where a freeze lists it, otherwise against the hash recorded in `reports/eda/pass2_checks.json` (SHA-256 `9a89d5a0…482ee3`).
- 30-second windows only.

## 3. Fixed before the run
- **Main configuration:** the columns whose tier, or whose `goes_with` for context columns, is behavior or command content (40).
- **Ranking:** single-feature AUC on training rows, as in `T4_feature_profile_w30.csv`; ties keep that table's order. **Top 20:** the first 20 main-configuration columns after the near-duplicate merge of `T6_near_duplicates_w30.csv` (a merged member is skipped).
- **The features H1 names** ("command length, flags, pipes, chaining and redirects") are these six columns, chosen here from their definitions and not from their values: `cmd_len_mean`, `cmd_len_max`, `flags_per_cmd`, `pipes_per_cmd`, `chain_ratio`, `redirect_ratio`.
- **Stage groups in by-stage figures:** those with at least 10 training windows in both classes (Pass 2's rule): discovery, execution, lateral movement and collection. Account manipulation has no AI training window and is not drawn.
- **Statistics:** as defined in handoff §6 and applied in Pass 2. AUC and same-stage AUC are taken from the Pass 2 tables and recomputed only as a check. Medians and quartiles use linear interpolation on the rows where the feature is defined. Spearman's rho is on the rows where both features are defined. A by-stage value resting on fewer than 10 windows in either class is marked indicative.
- **Data example:** for each session, the first training window in feature-table order that holds at least two commands. Numeric columns only: `cmd_count`, `gap_median`, `exec_count`, `output_bytes`, `cmd_len_mean`, `flags_per_cmd`, `pipes_per_cmd`, `chain_ratio`, `redirect_ratio`.

## 4. Outputs (all new files)
Code in `code/eda_run3/`; tables in `reports/eda_run3/tables/` (CSV); figures in `reports/eda_run3/figures/` (PNG at 300 dpi and SVG), drawn from the tables only. Style is that of Pass 1 and Pass 2 (handoff §9).

| Figure | Reference figure | Content | Source |
|---|---|---|---|
| EDA01 data example | 4-1 | Nine rows of the feature table, one per session | New table R1 |
| EDA02 dataset summary | 4-2 | Overview, column breakdown, kept windows per session, kept windows by class and stage group with counts and percent | Pass 1 and Pass 2 tables |
| EDA03 activity by elapsed time | 4-3 | As E3 | Pass 1 table, redrawn unchanged |
| EDA04 windows by stage group | 4-4 | As E4, stage groups named | Pass 1 tables |
| EDA05 stage timeline | 4-6 | As E6, stage groups named | Pass 1 tables |
| EDA06 window activity | 4-7 | Left panel of E7 only; the entry-style panel is input-channel data and stays with Pass 2 | Pass 2 table |
| EDA07 programs by stage group | 4-8 | As E8, stage groups named | Pass 2 tables |
| EDA08 feature correlation | 4-9 | Spearman's rho, top 20 of the main configuration | New table R9 |
| EDA09 single-feature AUC | 4-10 (model-free) | Top 20 of the main configuration, by tier | Pass 2 table T4, as R10 |
| EDA10 command features by class | 4-11 (model-free) | The six H1 columns: one point per training window, class median and interquartile range, session medians | New tables R11 |
| EDA11 command features by stage group | none | The six H1 columns within each stage group, by class, with the same-stage AUC | New table R12 |
| EDA12 AUC within stage groups | none | As E12, top 20 of the main configuration, stage groups named | Pass 2 table T7, as R13 |

The reference's SHAP figures (4-10, 4-11) have their model-based counterparts in `results_h2_features/`; run 3 does not redo them.

## 5. Checks
1. Both freeze files and `pass2_checks.json` hash as recorded, before and after; no file outside `code/eda_run3/` and `reports/eda_run3/` is created or changed.
2. Training rows only: zero rows of another split loaded; every file opened is logged with its hash.
3. Counts agree: class totals 425 and 157; training windows by stage group equal `T7_stage_group_training_windows_w30.csv`; every AUC, median and same-stage AUC that run 3 recomputes equals the Pass 2 table to four decimals; Spearman values shared with `E9_spearman_top20.csv` are equal.
4. The preprocessing's leak-audit patterns over every text file in `reports/eda_run3/`: zero hits beyond the session labels.
5. A second run gives the same file hashes.
6. Each figure is looked at as rendered. No figure text holds "study 3", "pass", "freeze", "flag" or "handoff".
