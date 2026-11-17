# Real lab logs, study 3: exploratory data analysis (EDA) handoff

Drafted 2026-11-11 (EST) for whoever runs the EDA once the study 3 preprocessing has run. It sits beside `real_lab3_preprocessing_design.md` (the rules that produce the data) and `praxis_paper_plan.md` (where the results go). The model for the figures is the EDA of the reference praxis (Pagan, GWU D.Eng., graph machine learning to detect APT on DAPT-2020): its Section 3.3 method and its Figures 4-1 to 4-11.

**Status: Pass 1 was run on Nov 13 (05:12–05:41 EST; `real_lab3_eda_pass1_feature_run.md`). Pass 2 and Pass 3 have not been run. On Nov 13 at 06:11 EST the user moved Pass 2 after the trials, as a report only (§12a; F16 of the feature and trial design).** All nine sessions are in hand as of Nov 13 (preprocessing design §0, §2). All six decisions in §11 are settled: numbers 1, 3 and 4 on Nov 12 as F11 of `real_lab3_feature_trial_design.md`; 2, 5 and 6 on Nov 13, between 05:51 and 05:57 EST.

## 0. Summary
- **Purpose.** Describe the matched dataset before any model is scored, check that no single column gives the classes away, and show how the strongest features relate to the ATT&CK stage groups. The outputs replace the study 2 and 2b placeholders in Sections 4.2, 4.3 and 4.8 of the paper.
- **What the figures have to show**, in the paper's framing:
  1. Both classes worked the same exercise from the same starting prompt, on all three ranges, and the data is what was collected (T1, T9, E2, E4).
  2. Where each class spent its time across the seven stages (E4, E6).
  3. What the operators did on the host, by class (E7, E8, E11).
  4. No shortcut and little redundancy among the features (T5, T6, E9, E10).
  5. Which features hold within a stage and which follow the stage mix (T7, T8, E12).
- **Three passes.**

| Pass | When | Rows read | Produces |
|---|---|---|---|
| 1. Describe the dataset | After Freeze 1 | All kept windows, design columns only: no feature values, no text | T1–T3; E2, E3, E4, E6 |
| 2. Feature EDA | After the feature table is built, before Freeze 2 | Training rows only | T4–T9; E1, E5, E7–E12 |
| 3. After the trials | After both freezes and the trials | As the trial plan says | Model-based importance, the true counterpart of the reference's SHAP figures, if it is added to the trial plan (§11, decision 4) |

- **Numbering.** E1 to E11 are the study 3 counterparts of reference Figures 4-1 to 4-11, in the same order. E12 has no reference counterpart. T1 to T9 are tables.

## 1. Rules
1. **Nothing runs early.** Pass 1 waits for Freeze 1. Pass 2 waits for the feature table.
2. **Read only** `data/` and `reports/` in `Log Collection/study 3/`. Never the evidence folder, `set_aside/`, the harness archives, the private key map or the test-label file.
3. **Rows.** Pass 1 may read every kept window, but only its session, class, login order, window index, stage group and split. Counting windows is a description of the design. Pass 2 reads feature values and command text from rows marked `train` in the frozen split file and from no other row. The loader filters to `train`, logs the row count for each split value and stops if a row of any other split is present.
4. **No model is fitted.** Single-feature AUC is a rank statistic of one column.
5. **The EDA cannot select or tune.** No feature is added, dropped or re-weighted because it is strong or weak. Two actions are allowed: correcting a feature that is shown to record the collection instead of the operator (logged, before Freeze 2), and merging near-duplicates for reporting.
6. **Description-only columns stay description only.** Elapsed time, window index, login order, how a login ended and the lab range appear in EDA figures and never become features.
7. **Nothing sensitive in an output.** No credential, client address or participant identity in any table, figure or excerpt. Target machine names and the attack accounts are part of the shared lab and may appear; their passwords may not.
8. **Code and outputs.** Scripts in `code/eda/`, outputs in `reports/eda/tables/` (CSV) and `reports/eda/figures/` (PNG at 300 dpi, plus SVG). The code never writes to `data/` or to the evidence folder. One command rebuilds everything. Figures are drawn from the CSV tables, not from the data directly, so every plotted number can be traced.
9. **Libraries.** pandas, NumPy, SciPy and Matplotlib (Seaborn optional), as in the reference. The preprocessing stays standard library only; the EDA is separate code. Versions go in Appendix C.
10. **Wording.** American English. Final numbers are written without highlight; yellow highlight is only for placeholders.

## 2. Inputs

| Needed | Comes from | Used by |
|---|---|---|
| Verification report and step reports (counts for each rule) | `reports/` (Freeze 1) | T1, checks |
| Session table and login table (class, logins used, duration) | `data/` labels sidecar | T1, E2, E3 |
| Window index: session key, login order in the session, window start, stage, stage group, split | `data/` windows and split file | Pass 1 |
| Stage acceptance times on each session's timeline | Preprocessing, from the stage-boundary files | E6 |
| Cleaned recorder and audit records for each window | `data/` | E1 |
| Feature table: one row per kept window, with the tier of every column | Feature step | Pass 2 |
| Per-command table for training rows: reconstructed command text, entry mode, programs started | Feature step | E5, E7, E8 |

Two of these are requests to the steps that come first, made now so that no amendment is needed after a freeze:
- **Preprocessing:** write a description sidecar holding, for each kept window, the login's order in its session and the window's elapsed working time (used logins laid end to end), and the stage acceptance times on the same clock. It is a separate file, never joined to the feature table.
- **Feature step:** write the per-command table when the command text is reconstructed.

## 3. What carries over from the reference method

| Reference praxis, Section 3.3 | Study 3 |
|---|---|
| Dataset imported with pandas; key statistics, distribution summaries and feature-level descriptive measures | The same: counts by class, session and stage group; median, interquartile range and zero share of every feature by class (T2, T4) |
| Null check: no missing values across 85 features, so no imputation | Undefined-value audit: the share of windows in which each feature is undefined, by class. Gap statistics and entropies are undefined below two or three commands, so "is defined" is audited like a feature (T4, T5) |
| Matplotlib and Seaborn | Matplotlib, with SciPy for the rank statistics |
| Line charts, correlation heatmaps and distribution plots | Bars, heatmaps, distribution plots and dumbbells (§4) |
| EDA run on the full dataset | Counts from all kept windows; feature values and text from training rows only (rule 3) |
| No counterpart | Added for this study: shortcut audit, same-stage AUC, Kruskal–Wallis ε², per-session robustness, range check |

## 4. Figure map: reference praxis to study 3

"Direct" means the same question and chart form. "Adapted" means the same question asked of different columns. "Replaced" means the reference's columns do not exist here and the nearest question is asked instead.

| ID | Reference figure | Study 3 counterpart | Match | Pass |
|---|---|---|---|---|
| E1 | 4-1 DAPT-2020 data example (row preview) | Data example: a short excerpt of cleaned recorder and audit records for one human and one AI window, and the feature rows built from them | Direct | 2 |
| E2 | 4-2 Statistical summary of network flows (overview panel, column breakdown, flows per day, class distribution) | Statistical summary of the dataset: overview panel, feature columns by tier, kept windows per session, class distribution with counts and percent | Direct | 1 (tier counts added in 2) |
| E3 | 4-3 APT flow activity by hour and day of week (heatmap and hourly bar) | Activity by elapsed working time: sessions by 5-minute bins, and kept windows per session | Replaced. Clock time is removed when windows are built because it identifies the session, so hour and weekday are not plotted | 1 |
| E4 | 4-4 Top 15 source IPs by APT flow count, stacked by stage, with a stage donut | Kept windows per session, stacked by stage group, with the stage share of each class. The sessions take the place of the source addresses | Adapted | 1 |
| E5 | 4-5 Top 15 destination IPs targeted, with unique sources per destination | Lab machines named in commands, by class, with the number of sessions that addressed each | Adapted. Optional | 2 |
| E6 | 4-6 APT stage activity per source IP over time (dominant-stage and flow-count heatmaps) | Stage timeline per session: the stage group being worked in each 5-minute bin | Direct | 1 |
| E7 | 4-7 Protocol distribution, overall and by class | Window activity type and command entry mode, by class | Adapted | 2 |
| E8 | 4-8 Top destination ports (stage composition per port; port by stage heatmap with APT-only ports outlined) | Top 15 programs executed (stage composition per program; program by stage group heatmap for each class, with programs run by only one class outlined) | Direct | 2 |
| E9 | 4-9 Pearson correlation heatmap, top 20 features | Spearman correlation heatmap, top 20 features. Spearman because the features are zero-heavy counts and the near-duplicate rule is defined on it | Direct | 2 |
| E10 | 4-10 SHAP analysis, full feature list stacked by stage | Single-feature AUC for the full feature list by tier, with the 0.95 flag line. Model-free; the SHAP version is a Pass 3 item | Adapted | 2 |
| E11 | 4-11 SHAP beeswarm, top 20 | Distributions of the strongest features by class, one point per window and one marker per session median. Model-free | Adapted | 2 |
| E12 | None | Top 20 features: AUC over all training windows against AUC within the same stage group (the paper's current Figure 4-4) | Study 3 only | 2 |

## 5. Pass 1: describe the dataset

**Tables**
- **T1 Dataset summary by session.** Class, lab range, logins used, raw records, classifier-input records, logged minutes, kept 30-second windows. Counts are taken from the step reports, not recounted. Extends the paper's Table 4-1.
- **T2 Kept windows by stage group and class**, and the same by session. The class table is the paper's Table 4-2; the session table goes to Appendix D. Beside each window count the class table shows the number of sessions that supply it and the share of the largest one.
- **T3 Split counts.** Train, validation, test and unused rows by class and session, for 30-second and 60-second windows.

**Figures**

| ID | Form | Data and rule |
|---|---|---|
| E2 | Three panels. Left: text block (sessions by class, logins used, raw records, classifier-input records, kept windows, window length, feature columns by tier, columns with undefined values). Middle: kept windows per session, bars colored by class. Right: class distribution with counts and percent | T1, T2; tier counts filled in during Pass 2 |
| E3 | Heatmap, one row per session (humans first), one column per 5-minute bin of elapsed working time. Cell: kept windows in the bin, 0 to 10. Right: bar of kept windows per session with logged minutes as text | Description sidecar. If the longest session needs more than 60 columns, use 10-minute bins for all sessions |
| E4 | Left: one horizontal stacked bar per session, segments are the four stage groups, length is kept windows. Right: stage share of each class as two 100 percent bars. The reference used a donut; two bars compare more easily | T2. Replaces the current Figure 4-1 |
| E6 | Same grid as E3. Cell color: the stage group worked in most of the bin's kept windows (ties go to the later stage); gray where no window was kept. Ticks mark accepted stages | Description sidecar. Note under the figure that P009's used login starts at stage 5 and that P010's used logins are separated by a validator outage. Ticks show the operator's own acceptances only (preprocessing design A13). E3 and E6 share a grid so they can be stacked as one figure |

## 5a. Readings approved at implementation (Pass 1)
Where §5, §9 and §10 left a detail open, the Pass 1 code applies these. The user approved them on Nov 13, between 05:51 and 05:57 EST.

| # | Reading | Where |
|---|---|---|
| E1 | **Session labels and the leak audit.** The handoff asks for sessions labeled as in Table 4-1 (P001 …) and for zero hits from the leak-audit patterns over `reports/eda/`. The pattern `participant_code` matches those labels. The check counts the nine session labels on their own line (516 occurrences) and treats anything else any pattern finds as a hit. There are none | `run_eda.py` |
| E2 | **The session labels come from the windows step report**, which holds each session's label beside its key. The private key map is not opened | `eda_common.py` |
| E3 | **Figure files are not searched as text** (PNG pixels, SVG outlines). Every string drawn comes from the tables and the captions file, which are searched | `run_eda.py` |
| E4 | **In E3 a bin with no kept window is gray**, the ramp runs from 1 to 10, and bins after a session's end are left blank. No bin holds more than 10 | `pass1_figures.py` |
| E5 | **E6's two notes are drawn in the figure** as well as written in the caption | `pass1_figures.py` |
| E6 | **Text is 9 pt in the file**, so it is at least 8 pt when the figure is placed 5.6 in wide. The font is DejaVu Sans, which Matplotlib carries. `make_figs.py` and the Word template are not in the study folder, so the figures follow §9 of the handoff and were not set beside the existing Chapter 4 figures | `pass1_figures.py` |
| E7 | **One table was added:** split rows by stage group and class (`T3_split_rows_by_stage_group.csv`) | `pass1_tables.py` |

Found in Pass 1 and carried into Pass 2: the AI class has no stage 6 training row at either window length (its three 30-second windows of stage 6 are in the test split), so the same-stage tables and E12 can cover stages 1–4, 5 and 7 only.

## 6. Pass 2: feature EDA on training rows

**Definitions**
- **Single-feature AUC.** For one feature, a = the share of (AI window, human window) pairs in which the AI value is higher, ties counted as one half, over rows where the feature is defined. AUC = max(a, 1 − a). "Higher in" is AI when a ≥ 0.5.
- **Defined share.** The share of windows in which the feature is defined, by class. The 0/1 "is defined" indicator gets its own AUC.
- **Session robustness.** The AUC is recomputed nine times, each time without one session's rows. The minimum and maximum are reported. This is the same audit run inside every leave-one-session-out fold.
- **Shortcut flag.** A feature is flagged when its AUC, or the AUC of its indicator, is 0.95 or higher. A flagged feature is checked against the cleaned recordings: does it describe what the operator did, or how the session was recorded?
- **Near-duplicates.** Spearman ρ on rows where both features are defined. Walking down the AUC ranking, a feature with |ρ| > 0.98 against a higher-ranked feature is merged into it for reporting. Nothing is removed from the feature table.
- **Same-stage AUC.** The single-feature AUC within one stage group. The number of windows in each class is reported beside every value. A value resting on fewer than 10 windows in either class is marked indicative and drawn hollow. The number of sessions behind each class's windows, and the share of the largest one, are reported with the window counts.
- **ε².** Kruskal–Wallis H across stage groups, within one class, divided by (n − 1). Stage groups with fewer than 5 windows are left out of the test.

**Tables**
- **T4 Feature profile.** Every feature: tier, defined share by class, zero share by class, median and interquartile range by class, AUC, higher in, AUC minimum and maximum across the session drops. The top six rows are the paper's Table 4-3; the full table goes to Appendix A.
- **T5 Shortcut audit.** Every flagged feature, what the review found, and what was done. If none is flagged the table is one line saying so.
- **T6 Near-duplicate groups.**
- **T7 Top 20 by stage.** Top 20 features after merging: tier, higher in, AUC over all training windows, same-stage AUC for each stage group with its window and session counts, ε² for the human class and for the AI class. The paper's Table 4-8.
- **T8 Tier means.** Mean AUC over every column of each tier: all training windows against each stage group that has at least 10 windows in both classes, with the window and session counts of each stage group. The paper's Table 4-9.
- **T9 Range check.** Within the human class, single-feature AUC between Original Austin (P001, P003) and AHIR-03 (P004, P006), with P005 (AHIR-01) listed on its own. Within the AI class, AHIR-03 (P002, P011) against Original Austin (P009) and against AHIR-01 (P010), which have one session each. With one or two sessions a side, range and participant cannot be told apart, so the table is read for a pattern (the same columns at the top in both classes would point to the lab build) and no threshold is applied.
- **60-second repeat.** T4 to T8 are produced again for 60-second windows, as tables only.

**Figures**

| ID | Form | Data and rule |
|---|---|---|
| E1 | Two short text excerpts side by side (human, AI): four to six cleaned recorder and audit lines from one discovery-stage training window each, with the placeholders visible. Below: the two feature rows, six columns | Pick windows that hold no credential. Check by eye before use (§10) |
| E5 | Left: for each lab machine, the share of each class's commands that name it. Right: number of sessions that addressed it, by class | Per-command table; a fixed list of the lab's machine names and addresses. Shares, not counts, because the classes differ in size |
| E7 | Left: share of each class's windows that are quiet (no command), hold only commands that started no program (typed inside an interactive client), or hold commands that started programs. Right: share of each class's commands that were typed, pasted, recalled or written as whole lines | Feature table and per-command table. The right panel is input-channel data and is labeled as diagnostic |
| E8 | Left: the 15 programs started in the most training windows, each bar split by stage group. Right: program by stage group heatmap, one block per class; cell is the share of that class's windows in the stage group in which the program ran; programs run by only one class are outlined | Per-command table. Counted by windows in which a program ran, so one loop cannot dominate. Wrapper, validator and collection programs are already removed |
| E9 | Lower-triangle heatmap of Spearman ρ among the top 20 features after merging, values printed in the cells | T4, T6 |
| E10 | Horizontal bars of single-feature AUC, grouped in four tier panels and sorted within each. Bar color: the class in which the feature is higher. Lines at 0.50 and at the 0.95 flag. Whiskers: the session-drop minimum and maximum | T4. Top 20 in the body (replaces the current Figure 4-2); the full list in Appendix A |
| E11 | Small multiples, 3 by 4, for the top 12 features after merging. In each: the two classes side by side, a box for the median and interquartile range, one faint point per window, one larger marker per session median. Symmetric log axis for counts | Feature table, T4. The session markers show whether a difference holds for every session or rests on one |
| E12 | Dumbbell, top 20 features: AUC over all training windows and AUC within the same stage group, one panel for each stage group with at least 10 windows in both classes; each panel's title gives the window and session counts | T7 |

## 7. Pass 3: after the trials
Not EDA, listed so the slots are not forgotten.
- **Model-based importance.** The reference's Figures 4-10 and 4-11 come from a trained model. The direct counterparts are SHAP values from the random forest on held-out-session rows: mean absolute SHAP for every feature, stacked by the stage group of the rows, and a top-20 beeswarm. They count only if written into the trial plan before Freeze 2 (§11, decision 4).
- **Shuffled-label control.** Reported in Section 4.3 of the paper but produced by the trials.

## 8. Where the outputs go in the paper

| Paper location | Now (placeholder) | After the EDA |
|---|---|---|
| Section 3.3 | Four-part method on training rows | Add the two levels of access (counts from all kept windows, feature values from training rows), the undefined-value audit, the session robustness and the tools |
| Section 4.2 Dataset | Table 4-1 | T1 as Table 4-1; E1 |
| Section 4.3 EDA | Tables 4-2 and 4-3; Figures 4-1 and 4-2 | T2, top six of T4, T5 in the text; E2, E3, E4, E6, E7, E8, E11, E10, E9 in that order |
| Section 4.4 Preprocessing and feature selection | Table 4-4 | T3 for the split row; T6 in the text |
| Section 4.8 Stage analysis | Tables 4-8 and 4-9; Figure 4-4 | T7, T8, E12 |
| Appendix A | Feature definitions | Full T4 and the full-list E10 |
| Appendix D | Results by stage | T2 by session, T7 for every stage group, T9, the 60-second tables; E5 if made |

Chapter 4 goes from 4 figures to 12, or 14 with the SHAP pair. The reference's Chapter 4 has 12.

## 9. Figure style
- Match the existing Chapter 4 figures (`make_figs.py`): 6.2 in wide at 300 dpi, text no smaller than 8 pt at printed size.
- **Class:** human blue `#2a78d6`, AI orange `#eb6834` with a diagonal hatch so the classes separate in gray. Humans first, everywhere.
- **Stage groups:** aqua `#1baf7a`, yellow `#eda100`, magenta `#e87ba4`, green `#008300`, in stage order and always labeled on the chart. Checked for color-vision deficiency; three of the four are light against white, which is why the labels are required.
- **Magnitude heatmaps (E3, E8):** one blue ramp, `#cde2fb` to `#0d366b`; light gray for no data.
- **Correlation (E9):** blue to red through gray `#f0efec`, symmetric from −1 to 1.
- **Two measures of one thing (E12):** one hue, two shades, `#86b6ef` and `#1c5cab`.
- No pie or donut charts and no second y-axis. The number of windows is stated on the chart or in the caption. Sessions are labeled as in Table 4-1.

## 10. Checks before handing back
1. **Counts agree.** T1 to T3 equal the step reports and the split file. The class totals of every Pass 2 table equal the training counts in T3.
2. **Training rows only.** The Pass 2 log shows zero rows of any other split and lists every file opened; the test-label file is not among them.
3. **Leak audit on the outputs.** The preprocessing's leak-audit patterns (§6.6 of the design) are run over every file in `reports/eda/`. The count must be zero. The session labels of Table 4-1 (P001 …) match the participant-code pattern; they are counted on their own line and anything else a pattern finds is a hit (E1, §5a).
4. **Credentials by eye.** The leak audit does not look for passwords, because the attack accounts are kept in the data. E1, E5 and E8 and their tables are read by a person before they leave the protected location.
5. **Every number traces.** Each number quoted in the paper is in a CSV under `reports/eda/tables/`.
6. **Rerun matches.** A second run gives the same table hashes.
7. **Figures read in place.** Each figure is checked in the Word template at 5.6 to 6.0 in wide: no overlapping labels, classes identifiable without color.
8. **Handback note.** One page: what was flagged, what was changed and why, and which placeholder statements in the paper no longer hold.

## 11. Decisions (all settled)

| # | Decision | Recommendation |
|---|---|---|
| 1 | What a shortcut flag may change | Run Pass 2 before Freeze 2. A flagged column is reviewed against the recordings. If it records the collection, the feature definition is corrected before Freeze 2 and logged; a fix that needs a cleaning rule is an amendment to Freeze 1 with every session re-run. Nothing is dropped for being strong. The alternative is to run it after Freeze 2 and only report |
| 2 | What "training rows" means | Rows marked `train` in the frozen within-session split, about 70 percent of each session. The main evaluation holds out whole sessions, so Pass 2 sees training rows of sessions that are later held out. That is acceptable because the EDA cannot select or tune (rule 5), and the session-drop range in T4 shows the audit inside every fold. Section 3.3 should say this |
| 3 | Rows for the stage analysis | Training rows are the planned version, written into Freeze 2. A repeat on all windows after scoring is allowed in Appendix D only, labeled post hoc |
| 4 | SHAP after the trials | Add it to the trial plan for the random forest (§7). E10 and E11 stay in Section 4.3 as the model-free versions |
| 5 | Undefined values in the single-feature AUC | AUC on defined rows, with the "is defined" indicator audited separately (§6). The alternative, filling with the training median as logistic regression does, hides how much of a feature's separation is only that the AI has more multi-command windows |
| 6 | How much goes in the body | Everything except E5 and the full-list E10, which go to the appendices |

Decisions 1, 3 and 4 were approved on Nov 12 as F11 of `real_lab3_feature_trial_design.md`. Decisions 2, 5 and 6 were approved as recommended on Nov 13, between 05:51 and 05:57 EST. For decision 2, the rows marked `train` are 582 of the 951 kept windows at 30 s and 324 of 577 at 60 s, about 61 and 56 percent, not about 70.

## 12. Order of work
1. Settle §11. Decisions 1, 3 and 4 are written into the feature and trial document.
2. When the preprocessing runs, confirm the description sidecar and the step-report counts exist (§2).
3. After Freeze 1: Pass 1, then checks 1, 3, 6 and 7.
4. Feature step: feature table and per-command table.
5. Pass 2 on training rows. Review any flag. If a feature is corrected, log it and run Pass 2 again.
6. Freeze 2 records the EDA code and output hashes with the features and the trial plan.
7. Replace the placeholders in Sections 4.2, 4.3 and 4.8 and Appendices A and D, remove their highlight, and update Section 3.3.
8. After the trials: Pass 3.

## 12a. Amendment: Pass 2 after the trials (user, Nov 13, 06:11 EST)
The recommended order was Pass 2 before Freeze 2. The user chose to go on to Freeze 2 and the trials, with Pass 2 afterwards as a report only (F16 of `real_lab3_feature_trial_design.md`).

- **What changes.** Rule 1 and the table of §0: Pass 2 no longer comes before Freeze 2. §6 (shortcut flag) and §11, decision 1: a flagged feature is reported beside the results and is not corrected; an analysis with a corrected feature would be a new protocol. §12, steps 5 and 6: Freeze 2 records the Pass 1 code and outputs only.
- **What does not.** Pass 2 still reads feature values and command text from rows marked `train` only (rule 3, decision 2), still cannot select or tune (rule 5), and its tables and figures are as §6 sets out. T5 is still written, now as a finding made after scoring.
- **For the paper.** Section 3.3 has to say that the feature EDA and the shortcut audit were run after the models were scored.
- **Closed with this:** the user read the five windows of each session in `reports/10_features_review_windows.md` and found no issue.

## 13. Change log
| When (EST) | Change |
|---|---|
| Nov 11 | First draft |
| Nov 13 | P010 and P011 are in; all nine sessions in hand. User (03:05): the stage tables show the number of sessions, and the share of the largest one, beside the window counts (T2, T7, T8, E12, same-stage AUC). T9 reworded for the ranges of the four AI sessions. E6 note extended for P010 and for the operator's own acceptances (preprocessing design A13). Status line brought up to date: decisions 1, 3 and 4 of §11 were approved on Nov 12 as F11 |
| Nov 13, 06:00 | Pass 1 was run (05:12–05:41; `real_lab3_eda_pass1_feature_run.md`). User (between 05:51 and 05:57): the readings E1 to E7 approved (§5a, §10 check 3); decisions 2, 5 and 6 of §11 approved as recommended, so all six are settled. Status brought up to date. Correction: the training rows are about 61 percent of the kept 30-second windows, not about 70 (§11) |
| Nov 13, 07:05 | User (06:11): Pass 2 is run after the trials, as a report only (new §12a; F16 of the feature and trial design). Status brought up to date. This is the text frozen in Freeze 2 |
