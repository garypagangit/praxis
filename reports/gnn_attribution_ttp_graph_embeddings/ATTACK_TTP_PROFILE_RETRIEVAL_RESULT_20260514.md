# ATT&CK TTP-Set Profile Retrieval Result

Generated: 2026-05-14

Status: **selected second narrow positive result**

## Bottom Line

The second strongest portfolio result is **few-shot ATT&CK group-profile retrieval from observed TTP sets**.

This is not a claim of authorship attribution from raw CTI prose. It is a profile-retrieval result: given a small set of observed ATT&CK techniques, simple overlap and SVD profile baselines can rank the correct ATT&CK group near the top.

## Thesis Claim

ATT&CK group technique profiles contain enough structure that small observed TTP sets can retrieve likely adversary-group profiles with high top-k accuracy. This supports analyst triage and hypothesis generation, but it does not prove document-level actor attribution.

## Research Questions

| ID | Question | Decision criterion | Result |
|---|---|---|---|
| RQ1 | Can a 5-technique observed TTP set retrieve the correct ATT&CK group profile? | Top-5 at 5 shots `>= 0.80` | Supported: overlap `0.960`, SVD `0.879`. |
| RQ2 | Does the signal exist before 5 shots? | Top-5 at 3 shots above a strong practical floor | Partially supported: overlap `0.846`, SVD `0.684`. |
| RQ3 | Do simple baselines beat the current learned GNN? | GraphSAGE must beat SVD/overlap to justify GNN framing | Not supported: GraphSAGE known-profile 5-shot top-5 `0.060` vs SVD `0.926` and overlap `0.985`. |
| RQ4 | Can this be called CTI prose attribution? | Requires report-to-group labels and document-level split | Not supported. Keep the claim to TTP-set profile retrieval. |

## Data

Source: ATT&CK group-technique profiles represented as a group-by-technique matrix.

| Item | Count |
|---|---:|
| Groups | `174` |
| Techniques | `697` |
| Group-technique edges | `4546` |
| Eligible groups, degree >= 10 | `121` |

## Query Protocol

For each eligible group:

1. Sample `k` techniques from that group's ATT&CK profile, where `k in {1, 3, 5, 10}`.
2. Treat the sampled techniques as an observed TTP set.
3. Rank candidate groups by similarity between the query set and each group profile.
4. Repeat over fixed seeds to produce `605` queries per shot level.

## Methods

| Method | Role |
|---|---|
| `overlap_cosine` | Direct profile-overlap retrieval baseline. This is the strongest simple method. |
| `svd32_graph_embedding` | Low-rank group-technique matrix embedding. This is the selected graph-style baseline. |
| `graphsage_linkpred` | Learned GNN pilot. This failed to beat simple baselines and is not selected. |

## Main Results

| Method | Shots | Top-1 | Top-5 | Top-10 | MRR | Median rank | Queries |
|---|---:|---:|---:|---:|---:|---:|---:|
| overlap_cosine | 1 | `0.136` | `0.425` | `0.598` | `0.284` | `7.0` | `605` |
| svd32_graph_embedding | 1 | `0.093` | `0.286` | `0.468` | `0.209` | `12.0` | `605` |
| overlap_cosine | 3 | `0.425` | `0.846` | `0.942` | `0.602` | `2.0` | `605` |
| svd32_graph_embedding | 3 | `0.306` | `0.684` | `0.858` | `0.479` | `3.0` | `605` |
| overlap_cosine | 5 | `0.721` | `0.960` | `0.992` | `0.824` | `1.0` | `605` |
| svd32_graph_embedding | 5 | `0.623` | `0.879` | `0.949` | `0.732` | `1.0` | `605` |
| overlap_cosine | 10 | `0.969` | `1.000` | `1.000` | `0.982` | `1.0` | `605` |
| svd32_graph_embedding | 10 | `0.931` | `0.993` | `1.000` | `0.959` | `1.0` | `605` |

## Closeout Floor Baselines

The 2026-05-14 closeout added two floor baselines without changing the original query-sampling protocol:

| Method | Shots | Top-1 | Top-5 | Top-10 | MRR | Median rank | Lift over random Top-5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| random_uniform | `5` | `0.005` | `0.028` | `0.053` | `0.033` | `84.0` | `1.0x` |
| frequency_prior | `5` | `0.008` | `0.041` | `0.083` | `0.044` | `61.0` | `1.5x` |
| overlap_cosine | `5` | `0.721` | `0.960` | `0.992` | `0.824` | `1.0` | `34.2x` |
| svd32_graph_embedding | `5` | `0.623` | `0.879` | `0.949` | `0.732` | `1.0` | `31.3x` |

Closeout report: `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_CLOSEOUT_20260514.md`.

## GNN Gate Result

The learned GraphSAGE pilot does **not** justify a GNN attribution claim.

| Mode | Method | Shots | Top-5 | Median rank |
|---|---|---:|---:|---:|
| known_profile | overlap_cosine_train | 5 | `0.985` | `1.0` |
| known_profile | svd32_train_graph | 5 | `0.926` | `1.0` |
| known_profile | graphsage_linkpred | 5 | `0.060` | `60.0` |
| held_edge | graphsage_linkpred | 5 | `0.073` | `34.0` |

Decision: preserve the simple profile-retrieval result. Do not pitch the result as a GNN win.

## Interpretation

The high 5-shot top-5 accuracy means ATT&CK group profiles have enough structure for useful triage from partial observed technique sets. The overlap baseline is intentionally strong because it directly compares observed techniques to group profiles. The SVD baseline shows that a compact group-technique embedding also preserves enough retrieval signal.

The result is useful because it is simple and bounded. An analyst can use it to generate candidate group hypotheses from observed techniques. It does not prove that a report, campaign, or intrusion was authored by a specific group.

## Allowed Claims

| Claim | Status |
|---|---|
| Five observed ATT&CK techniques can retrieve correct group profiles with high top-5 accuracy | Allowed |
| SVD group-technique embeddings preserve useful retrieval signal | Allowed |
| The result supports analyst triage and hypothesis generation | Allowed |
| GraphSAGE improves over simple baselines | Not allowed |
| CTI prose attribution is solved | Not allowed |
| Authorship attribution is proven | Not allowed |

## Threats To Validity

- ATT&CK profiles are curated and incomplete.
- Group technique profiles overlap.
- High-degree groups are easier to retrieve.
- Observed TTP sets in real incidents can be noisy or missing key techniques.
- The protocol samples from ATT&CK profiles rather than extracting techniques from full reports.
- The result evaluates profile retrieval, not causal attribution or authorship.

## Paper-Style Result Structure

Working title:

> Few-Shot ATT&CK Group-Profile Retrieval from Observed TTP Sets

Recommended structure:

1. Motivation: analyst triage from partial observed techniques.
2. Problem: rank candidate ATT&CK group profiles from a small TTP set.
3. Data: ATT&CK group-technique matrix.
4. Protocol: few-shot query construction over eligible groups.
5. Baselines: random/frequency if added, overlap cosine, SVD embedding.
6. Results: top-k and MRR across shots.
7. Negative GNN gate: GraphSAGE does not beat cheap baselines.
8. Scope: profile retrieval, not prose attribution.
9. Threats and next steps.

## Next Work

1. Convert this report and the closeout report into a short thesis/paper subsection.
2. Add a small figure or table showing example query techniques to top candidates.
3. Add held-edge split as a stress test, but keep the main claim on known-profile retrieval.
4. Optional: add historical ATT&CK release drift only if release snapshots are available.
