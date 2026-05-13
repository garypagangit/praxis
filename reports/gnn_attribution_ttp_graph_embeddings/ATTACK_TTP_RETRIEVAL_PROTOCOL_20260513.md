# ATT&CK TTP-Set Retrieval Protocol

Generated: 2026-05-13

Status: **selected next narrow protocol**

This protocol reframes the attribution branch honestly. The result is not "CTI prose attribution." It is **few-shot ATT&CK group-profile retrieval from observed TTP sets**.

## Research Question

Given a small set of observed ATT&CK techniques, can a simple retrieval model rank the correct ATT&CK group profile near the top?

## Thesis Claim

ATT&CK group technique profiles contain enough structure that small observed TTP sets can retrieve likely adversary groups with high top-k accuracy. This supports analyst triage and hypothesis generation, but it does not prove authorship attribution from raw prose reports.

## Current Evidence

From `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_BASELINE_20260510.md`:

| Method | Shots | Top-1 | Top-5 | Top-10 | MRR | Median rank | Queries |
|---|---:|---:|---:|---:|---:|---:|---:|
| overlap_cosine | 5 | `0.721` | `0.960` | `0.992` | `0.824` | `1.0` | `605` |
| svd32_graph_embedding | 5 | `0.623` | `0.879` | `0.949` | `0.732` | `1.0` | `605` |

From `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_GRAPHSAGE_PILOT_20260510.md`:

| Mode | Method | Shots | Top-5 | Median rank |
|---|---|---:|---:|---:|
| known_profile | graphsage_linkpred | 5 | `0.060` | `60.0` |
| known_profile | svd32_train_graph | 5 | `0.926` | `1.0` |
| known_profile | overlap_cosine_train | 5 | `0.985` | `1.0` |
| held_edge | graphsage_linkpred | 5 | `0.073` | `34.0` |

Decision: keep overlap/SVD retrieval. Do not claim GraphSAGE yet.

## Data

Primary data:

- ATT&CK groups.
- ATT&CK techniques.
- Group-technique edges.

Current graph:

| Item | Count |
|---|---:|
| Groups | `174` |
| Techniques | `697` |
| Group-technique edges | `4546` |
| Eligible groups, degree >= 10 | `121` |

Eligibility:

- Include only groups with at least `10` known techniques for the main few-shot evaluation.
- Preserve all group-technique edges for profile retrieval unless running the held-edge ablation.

## Query Construction

For each eligible group:

1. Sample `k` techniques from that group's profile, where `k in {1, 3, 5, 10}`.
2. Treat the sampled set as the observed TTP set.
3. Rank all candidate groups by score against the query set.
4. Repeat enough times to produce at least `500` total queries for stable estimates.

Randomness:

- Use fixed seeds.
- Record query group, sampled techniques, candidate ranks, and scores.
- Do not tune methods on final query outputs.

## Splits

### Main Known-Profile Retrieval

Purpose: analyst-style retrieval when candidate group profiles are known.

- Query: sampled observed TTPs from a group.
- Candidate profiles: complete ATT&CK group profiles.
- Claim allowed: retrieval from partial observed TTP sets.

### Held-Edge Ablation

Purpose: test whether methods generalize to hidden group-technique associations.

- Hold out a percentage of group-technique edges.
- Query from held-out or mixed edges.
- Candidate profiles are built from training edges only.
- Claim allowed: limited link/generalization stress test.

### Optional Future Temporal Split

Purpose: evaluate profile drift across ATT&CK releases.

- Train candidate profiles on an older ATT&CK release.
- Query using techniques added in a later release.
- Claim allowed only if release snapshots are archived.

## Methods

Minimum baselines:

| Method | Description |
|---|---|
| random_rank | Random candidate order; sanity floor. |
| frequency_prior | Rank groups by profile degree/frequency; popularity baseline. |
| overlap_cosine | Cosine/Jaccard-style direct overlap with group profiles. |
| svd32_graph_embedding | Low-rank embedding of group-technique matrix. |

Optional learned baselines:

| Method | Allowed only if |
|---|---|
| GraphSAGE | It includes meaningful technique/tactic/node metadata or a better graph objective. |
| R-GCN | Relations beyond group-technique edges exist and are frozen before evaluation. |
| Text+TTP hybrid | Report-to-group labels exist; otherwise keep prose separate. |

## Metrics

Primary:

- Top-5 accuracy at 5 shots.

Secondary:

- Top-1 accuracy.
- Top-10 accuracy.
- Mean reciprocal rank.
- Median rank.
- Per-group degree-bucket performance.

Required tables:

1. Main few-shot table by method and shot count.
2. Degree-bucket robustness table.
3. Held-edge ablation table.
4. Example retrievals with query TTPs and top candidates.

## Selection Gates

| Gate | Threshold | Decision |
|---|---:|---|
| Main SVD/overlap retrieval | Top-5 at 5 shots >= `0.80` | Current result passes. |
| Median rank | <= `3` at 5 shots | Current result passes. |
| Learned GNN promotion | GNN top-5 beats SVD by >= `0.03` absolute at 5 shots | Current GraphSAGE fails. |
| Prose attribution claim | Report-to-group labels plus document-level split | Not available. |

## Threats To Validity

- ATT&CK group profiles are analyst-curated and incomplete.
- Groups can share techniques; retrieval is not proof of authorship.
- High-degree groups are easier to retrieve.
- Technique observations may be noisy or missing.
- The protocol evaluates profile matching, not natural-language extraction.

## Next Implementation Steps

1. Freeze the ATT&CK version and write a group-technique manifest.
2. Generate query sets for `1, 3, 5, 10` shots using fixed seeds.
3. Re-run overlap, frequency, random, and SVD baselines.
4. Add held-edge split.
5. Write a short paper-style report around profile retrieval only.

## Stop Rule

If SVD/overlap remains strong but learned GNN remains weak, publish the simple method. Do not keep adding GNN complexity just to make the title sound more advanced.
