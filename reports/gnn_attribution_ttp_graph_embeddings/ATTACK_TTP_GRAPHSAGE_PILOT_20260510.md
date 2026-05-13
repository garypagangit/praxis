# ATT&CK TTP GraphSAGE Pilot

Generated: 2026-05-10

## Decision

Gate result: `WEAK - GRAPHSAGE DOES NOT BEAT CHEAP BASELINES`

The learned graph encoder does not justify replacing the simpler SVD/overlap baselines yet.

## Graph And Split

| Metric | Value |
|---|---:|
| Groups | 174 |
| Techniques | 697 |
| Full group-technique edges | 4546 |
| Train group-technique edges | 3692 |
| Held-out group-technique edges | 854 |
| Eligible groups, degree >= 10 | 121 |
| GraphSAGE final train loss | 0.4810 |

## Results

| Mode | Method | Shots | Top-1 | Top-5 | Top-10 | MRR | Median rank | Queries |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| held_edge | graphsage_linkpred | 1 | 0.015 | 0.043 | 0.099 | 0.051 | 58.0 | 605 |
| held_edge | overlap_cosine_train | 1 | 0.002 | 0.010 | 0.013 | 0.019 | 99.0 | 605 |
| held_edge | svd32_train_graph | 1 | 0.002 | 0.007 | 0.028 | 0.022 | 86.0 | 605 |
| held_edge | graphsage_linkpred | 3 | 0.017 | 0.074 | 0.126 | 0.064 | 49.0 | 525 |
| held_edge | overlap_cosine_train | 3 | 0.000 | 0.000 | 0.000 | 0.010 | 119.0 | 525 |
| held_edge | svd32_train_graph | 3 | 0.000 | 0.000 | 0.002 | 0.013 | 104.0 | 525 |
| held_edge | graphsage_linkpred | 5 | 0.014 | 0.073 | 0.170 | 0.072 | 34.0 | 370 |
| held_edge | overlap_cosine_train | 5 | 0.000 | 0.000 | 0.000 | 0.009 | 124.0 | 370 |
| held_edge | svd32_train_graph | 5 | 0.000 | 0.000 | 0.003 | 0.010 | 115.0 | 370 |
| known_profile | graphsage_linkpred | 1 | 0.018 | 0.061 | 0.116 | 0.060 | 56.0 | 605 |
| known_profile | overlap_cosine_train | 1 | 0.137 | 0.458 | 0.638 | 0.291 | 6.0 | 605 |
| known_profile | svd32_train_graph | 1 | 0.101 | 0.342 | 0.517 | 0.230 | 10.0 | 605 |
| known_profile | graphsage_linkpred | 3 | 0.015 | 0.060 | 0.109 | 0.058 | 58.0 | 605 |
| known_profile | overlap_cosine_train | 3 | 0.517 | 0.902 | 0.969 | 0.679 | 1.0 | 605 |
| known_profile | svd32_train_graph | 3 | 0.362 | 0.737 | 0.881 | 0.527 | 2.0 | 605 |
| known_profile | graphsage_linkpred | 5 | 0.012 | 0.060 | 0.104 | 0.052 | 60.0 | 605 |
| known_profile | overlap_cosine_train | 5 | 0.808 | 0.985 | 0.997 | 0.883 | 1.0 | 605 |
| known_profile | svd32_train_graph | 5 | 0.671 | 0.926 | 0.977 | 0.781 | 1.0 | 605 |

## Interpretation

- `known_profile` asks whether a partial observed TTP set can retrieve the known ATT&CK group profile.
- `held_edge` hides some group-technique edges during training and asks whether the embedding generalizes to withheld TTP associations.
- This is still ATT&CK-profile attribution, not raw CTI prose attribution.

## Next Logical Step

Do not spend more GPU/engineering here until metadata features or a better split objective are defined.
