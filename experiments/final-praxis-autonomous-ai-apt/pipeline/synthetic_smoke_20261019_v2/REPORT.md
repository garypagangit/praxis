# Synthetic smoke-test results

Engineering validation only. No H1/H2/H3 claim is established. Intervals are descriptive, unadjusted cluster bootstraps.

Input SHA-256: `f5435c78ff13b252a136a869442af8a20079918fb7725140e4818cb53535fbe1`. Seed: 19. Primary selected on validation: **logistic:full**.

| Candidate (full features) | Known-group F1 | Unseen-group F1 | Human false-AI rate (unseen) |
| --- | --- | --- | --- |
| dummy:full | 0.333 | 0.333 | 0.000 |
| logistic:full | 0.917 | 0.363 | 0.036 |
| decision_tree:full | 0.937 | 0.374 | 0.214 |
| random_forest:full | 0.958 | 0.371 | 0.071 |
| xgboost:full | 0.958 | 0.393 | 0.107 |
| svm:full | 0.937 | 0.358 | 0.054 |
| ft_style_transformer:full | 0.917 | 0.344 | 0.036 |

RQ1: see rq1_features.json for validation-family permutations and retrained ablations.
RQ2: see rq2_transfer.json for full/reduced transfer and importance stability.
RQ3: see rq3_comparison.json and metrics.json for paired candidate comparisons.

Controls are separately labeled in predictions.csv; no binary correctness is assigned to them.
The numerical-token transformer is an FT-style smoke-test implementation, not an exact published FT-Transformer replication.
Model artifacts are not persisted in this version; reproduce from input, seed, source and package manifest.
