# ATT&CK TTP Graph Attribution Baseline

Generated: 2026-05-10

## Decision

Gate result: `PROCEED - ATTRIBUTION SIGNAL PRESENT`

The cheap SVD graph embedding recovers enough held-out group identity from small TTP sets to justify a real GNN baseline.

## Graph

| Metric | Value |
|---|---:|
| Groups | 174 |
| Techniques | 697 |
| Group-technique edges | 4546 |
| Eligible groups, degree >= 10 | 121 |

## Few-Shot Attribution Results

| Method | Shots | Top-1 | Top-5 | Top-10 | MRR | Median rank | Queries |
|---|---:|---:|---:|---:|---:|---:|---:|
| overlap_cosine | 1 | 0.136 | 0.425 | 0.598 | 0.284 | 7.0 | 605 |
| svd32_graph_embedding | 1 | 0.093 | 0.286 | 0.468 | 0.209 | 12.0 | 605 |
| overlap_cosine | 3 | 0.425 | 0.846 | 0.942 | 0.602 | 2.0 | 605 |
| svd32_graph_embedding | 3 | 0.306 | 0.684 | 0.858 | 0.479 | 3.0 | 605 |
| overlap_cosine | 5 | 0.721 | 0.960 | 0.992 | 0.824 | 1.0 | 605 |
| svd32_graph_embedding | 5 | 0.623 | 0.879 | 0.949 | 0.732 | 1.0 | 605 |
| overlap_cosine | 10 | 0.969 | 1.000 | 1.000 | 0.982 | 1.0 | 605 |
| svd32_graph_embedding | 10 | 0.931 | 0.993 | 1.000 | 0.959 | 1.0 | 605 |

## Interpretation

- The overlap baseline is intentionally strong because it scores directly against full ATT&CK group technique profiles.
- The SVD embedding baseline is a cheap stand-in for a graph embedding. If it were flat, a GNN would be hard to justify.
- This evaluates attribution from observed TTP sets, not attribution from raw CTI prose.

## Next Logical Step

Promote this branch to a real graph experiment: create temporal/group-held-out splits, add technique/tactic metadata features, and compare SVD/nearest-neighbor against a small GraphSAGE or relational GCN. Keep document-level APTNotes claims separate until report-to-group labels are available.
