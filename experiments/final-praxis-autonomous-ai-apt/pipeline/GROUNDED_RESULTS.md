# Grounded synthetic results ? 19 October 2026

880 synthetic rows; 22 model/feature combinations in each of two runs. Both saved runs passed verification of hashes, labels, partitions, all 66 metric records and 10,912 predictions per run. Eleven tests passed. Dataset generation seed 20261019; model-run seed 19.

These are engineering results on a statistically anchored simulation, not empirical findings about autonomous AI APTs. Macro-F1 ranges from 0 to 1; higher is better. Reduced features retain command/host proxies and network proxies, removing timing and tool features.

| Model | Seen groups, full | Unseen groups, full | Unseen groups, reduced | Unseen shuffled-label control, full |
| --- | ---: | ---: | ---: | ---: |
| logistic | 0.708 | 0.512 | 0.574 | 0.454 |
| decision_tree | 0.601 | 0.411 | 0.544 | 0.455 |
| random_forest | 0.646 | 0.543 | 0.570 | 0.471 |
| xgboost | 0.687 | 0.524 | 0.525 | 0.461 |
| svm | 0.604 | 0.500 | 0.567 | 0.481 |
| ft_style_transformer | 0.728 | 0.542 | 0.567 | 0.475 |
| dummy | 0.333 | 0.333 | 0.333 | 0.333 |

## RQ1: Which feature families matter?

For the random-forest reference, permuting validation timing reduced macro-F1 by 0.071, host/command proxies by 0.068, tool proxies by 0.048 and network proxies by 0.023. These are family-level findings within this generated sample, not individual real-world attribute discoveries. A nonzero network importance can arise despite no designed network class signal; finite-sample correlations and model interactions are not causal evidence.

## RQ2: Do the learned attributes transfer?

Full logistic regression was selected on validation before test scoring. Its macro-F1 fell from 0.708 on seen groups to 0.512 on unseen groups. Removing timing/tools gave 0.574 on unseen groups; reduced random forest scored 0.570. The dataset intentionally shifts the synthetic AI timing assumption in unseen groups. This result exercises the shortcut/generalization checks; it does not measure actual model-family transfer.

The selected full logistic model labels 90% of scripted controls and 15% of benign controls as AI. This exposes sensitivity to scripted behavior in this scenario. Controls are neither assigned human/AI ground truth nor included in binary accuracy.

## RQ3: Which model works best?

Among full-feature candidates, random forest has the highest observed unseen score (0.543), narrowly above the FT-style transformer (0.542). Logistic regression with reduced features has the highest observed reduced score (0.574). These are descriptive test rankings, not a replacement for the preselected primary. Every learned full-feature candidate's paired descriptive interval versus the primary includes zero. There is no established winner.

The learned full-feature shuffled-label controls score 0.454?0.481 on unseen groups; the constant dummy scores 0.333 macro-F1 (balanced accuracy 0.5). One group-label permutation is only a diagnostic, not a permutation significance test. More seeds and real matched data are required for scientific conclusions.

## Evidence

- [Dataset definitions, source limitations and reproduction](GROUNDED_DATASET.md)
- [Synthetic run](grounded_run_20261019_final/REPORT.md), [all metrics and intervals](grounded_run_20261019_final/metrics.json)
- [RQ1 feature ablations](grounded_run_20261019_final/rq1_features.json), [RQ2 transfer](grounded_run_20261019_final/rq2_transfer.json), [RQ3 paired comparisons](grounded_run_20261019_final/rq3_comparison.json)
- [Shuffled-label run](grounded_null_run_20261019/REPORT.md)

Final study requirements remain: qualified target-side features, genuinely matched human/AI collection, repeated grouped validation, fair final tuning budgets, exact transformer qualification, frozen hypothesis margins and independent reproduction. No H1/H2/H3 decision is made here.
