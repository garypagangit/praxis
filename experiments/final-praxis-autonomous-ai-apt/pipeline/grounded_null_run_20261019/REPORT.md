# Synthetic smoke-test results

Engineering validation only. No H1/H2/H3 claim is established. Intervals are descriptive, unadjusted cluster bootstraps.

Input SHA-256: `0be409d48f7a21512eb0c61b653eb38a8ef91057bcaf45415cbce7763ad871b8`. Seed: 19. Primary selected on validation: **xgboost:full**.

| Candidate (full features) | Known-group F1 | Unseen-group F1 | Human false-AI rate (unseen) |
| --- | --- | --- | --- |
| dummy:full | 0.333 | 0.333 | 0.000 |
| logistic:full | 0.541 | 0.454 | 0.475 |
| decision_tree:full | 0.458 | 0.455 | 0.487 |
| random_forest:full | 0.488 | 0.471 | 0.438 |
| xgboost:full | 0.593 | 0.461 | 0.487 |
| svm:full | 0.464 | 0.481 | 0.550 |
| ft_style_transformer:full | 0.497 | 0.475 | 0.512 |

RQ1: see rq1_features.json for validation-family permutations and retrained ablations.
RQ2: see rq2_transfer.json for full/reduced transfer and importance stability.
RQ3: see rq3_comparison.json and metrics.json for paired candidate comparisons.

Controls are separately labeled in predictions.csv; no binary correctness is assigned to them.
The numerical-token transformer is an FT-style smoke-test implementation, not an exact published FT-Transformer replication.
Model artifacts are not persisted in this version; reproduce from input, seed, source and package manifest.
