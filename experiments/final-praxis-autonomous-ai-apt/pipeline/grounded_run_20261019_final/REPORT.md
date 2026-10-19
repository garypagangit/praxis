# Synthetic smoke-test results

Engineering validation only. No H1/H2/H3 claim is established. Intervals are descriptive, unadjusted cluster bootstraps.

Input SHA-256: `206a261f6ec27eca702807f99cb4d94b23816958e49f66c30fe35b6c25d7d6c5`. Seed: 19. Primary selected on validation: **logistic:full**.

| Candidate (full features) | Known-group F1 | Unseen-group F1 | Human false-AI rate (unseen) |
| --- | --- | --- | --- |
| dummy:full | 0.333 | 0.333 | 0.000 |
| logistic:full | 0.708 | 0.512 | 0.487 |
| decision_tree:full | 0.601 | 0.411 | 0.350 |
| random_forest:full | 0.646 | 0.543 | 0.487 |
| xgboost:full | 0.687 | 0.524 | 0.512 |
| svm:full | 0.604 | 0.500 | 0.487 |
| ft_style_transformer:full | 0.728 | 0.542 | 0.400 |

RQ1: see rq1_features.json for validation-family permutations and retrained ablations.
RQ2: see rq2_transfer.json for full/reduced transfer and importance stability.
RQ3: see rq3_comparison.json and metrics.json for paired candidate comparisons.

Controls are separately labeled in predictions.csv; no binary correctness is assigned to them.
The numerical-token transformer is an FT-style smoke-test implementation, not an exact published FT-Transformer replication.
Model artifacts are not persisted in this version; reproduce from input, seed, source and package manifest.
