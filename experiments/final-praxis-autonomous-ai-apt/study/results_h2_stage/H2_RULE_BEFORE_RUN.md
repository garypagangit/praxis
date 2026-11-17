# H2 (ATT&CK stage groups): decision rule, written before the per-stage chance baseline was computed

Written 2026-11-14 09:10:16 EST, before any per-stage chance baseline, p-value or interval existed.

## What was already known when this was written
- The held-out macro-F1 by stage group of the scored trials (`results/tables/T_by_stage_group.csv`, 2026-11-13) had been seen, and so had the stage tables of EDA Pass 2.
- This H2 is therefore **post hoc**: it was written after the scoring, on the advisor's feedback that the frozen H1 and H2 were too similar. The frozen design (`reports/freeze2/real_lab3_feature_trial_design.md`) keeps the H2 that was set before scoring (logistic regression against the chance baseline).
- Not known when this was written: how the 126 relabelings of the chance baseline score within a stage group. The frozen run kept one confusion count per relabeling, over all windows.

## Wording (proposed by Claude and accepted by the user on 2026-11-14, 09:06 EST)
- **RQ2.** Does the separation of human from autonomous-AI operators hold within each ATT&CK stage group of the intrusion?
- **H2.** Human and autonomous-AI operators are distinguished above chance within each ATT&CK stage group that both classes worked (discovery, execution, lateral movement and collection).

## Rule
1. **Predictions.** Held-out sessions, main configuration (30 s windows, 40 columns), the five classifiers, thresholds unchanged. The stage group is joined to the predictions after scoring and never enters a model (frozen design section 7.5, reading T13).
2. **Stage groups under the rule.** Those in which the true labeling has at least 10 windows of each class, which is the frozen line for "indicative" (section 7.5): stages 1-4, stage 5 and stage 7. Stage 6 has 3 AI windows; it is reported as indicative and is outside the rule.
3. **Statistic.** Macro-F1 within the stage group.
4. **Reference.** The frozen chance baseline (section 8, control 2; reading T9): every way of calling 4 of the 9 sessions AI (126), each run through section 7.1 in full by the frozen trial code, unchanged. For each relabeling the macro-F1 within the stage group is computed against that relabeling's classes. p is the share of the 126 whose value is at least the true labeling's, the true labeling included. The smallest possible p is 1/126 (0.008).
5. **Decision.** A classifier meets the rule when p is 0.05 or below in all three stage groups. **H2 is supported when at least three of the five classifiers meet it.** No adjustment is made across the three stage groups, because the rule needs all three.
6. **Reported beside the rule, not part of it.** The same test without command content; 95% percentile intervals of the stage-group macro-F1 from 2,000 resamples of whole sessions within each class (seed 42, the draws of reading T14); the share of windows called AI by session within each stage group; stage 6.
7. **The run is void unless** (a) the rerun's confusion counts over all windows equal `results/tables/T_chance_all_labelings.csv` for every relabeling, classifier and configuration; (b) every fit hash equals the plumbing log's; (c) the true labeling's stage-group values equal `results/tables/T_by_stage_group.csv`; (d) every file of Freeze 1 that is opened and every file of Freeze 2 is unchanged before and after.
8. **The outcome is reported whichever way it falls.** Nothing in `results/`, `data/`, `reports/` or the frozen code is written or changed. New code goes to `code/h2_stage/`, new outputs to `results_h2_stage/`.
