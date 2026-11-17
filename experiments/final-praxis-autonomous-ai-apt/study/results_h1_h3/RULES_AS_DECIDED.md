# H1 and H3 as restated after scoring: the rules, and what this folder holds

Written 2026-11-14 14:31:07 EST. **These rules were not written before their numbers.** Both hypotheses were restated after the trials were scored on 2026-11-13, and the paired tests in this folder were first computed in the conversation of 2026-11-14 at about 10:20 EST, from the saved predictions. This folder puts those numbers on file so that the paper and the deck can cite a table.

## H1, as on the defense deck uploaded on 2026-11-14 (slide 6)
- **Wording.** Command-content features improve classification of human-operated versus autonomous-AI activity compared with a predefined baseline.
- **Baseline.** The same classifier on the same session folds without the command-content tier and its context columns: the frozen trial `no_command_content` (22 columns) against the frozen trial `main` (40 columns).
- **Rule (deck).** Supported when held-out-session macro-F1 is higher with command content in at least three of the five classifiers.
- **Reported beside the rule.** The paired difference with its 95% interval, its one-sided p and the Holm-adjusted p over the five classifiers, by the frozen bootstrap (2,000 resamples of whole sessions within each class, seed 42, readings T4 and T14).

## H3, as on the deck (slide 7), with the rule the user chose on 2026-11-14 at 10:32 EST
- **Wording.** XGBoost achieves higher held-out-session macro-F1 than logistic regression, random forest, gradient boosting, and histogram gradient boosting.
- **Rule (user, 10:32: "for h3 loosen the rule to 'highest macro-F1'").** Supported when XGBoost has the highest held-out-session macro-F1 of the five classifiers in the main configuration.
- **Reported beside the rule.** XGBoost minus each of the other four: the paired difference with its 95% interval, its one-sided p and the Holm-adjusted p over the four, by the frozen bootstrap. The rule on the deck before 10:32 asked for all four to be above zero after Holm; the table says how many are.

## The hypotheses fixed before scoring
They stay in the frozen design (`reports/freeze2/real_lab3_feature_trial_design.md`, section 9) and their outcomes stay in `results/tables/T_hypotheses.csv`: H1 (command diversity and transition entropy) not supported, H2 (logistic regression against chance) supported, H3 (random forest highest) not supported. `tables/T_original_hypotheses.csv` here is a copy of those outcomes for the paper's table.

Nothing in `results/`, `data/`, `reports/` or the frozen code is written or changed. No model is fitted.
