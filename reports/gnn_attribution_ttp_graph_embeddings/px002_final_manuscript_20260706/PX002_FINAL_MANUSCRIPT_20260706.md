# PX-002 Final Manuscript

Generated: 2026-07-06

Praxis ID: `PX-002`

Status: **FINAL BOUNDED LOOKUP-STYLE POSITIVE - NOT A DEFENSE PILLAR**

## Title

Few-Shot ATT&CK Group-Profile Retrieval from Observed TTP Sets

## Abstract

Security analysts often observe only a small number of MITRE ATT&CK techniques early in an investigation. PX-002 evaluates whether those partial observed TTP sets can retrieve likely ATT&CK group profiles under a formal profile-retrieval protocol. Using ATT&CK group-technique relationships, the experiment samples `1`, `3`, `5`, and `10` techniques from eligible group profiles and ranks candidate groups with direct overlap and low-rank SVD profile baselines. At the practical five-shot operating point, overlap cosine reaches top-5 accuracy `0.960` and SVD reaches `0.879`, compared with random `0.028` and frequency-prior `0.041`; median rank is `1.0`.

The result is useful but narrow. A later defense audit shows that the direct-overlap claim collapses under a leave-query-out anti-tautology stress test, where overlap top-5 becomes `0.000` and SVD top-5 becomes `0.299`. PX-002 is therefore packaged as a bounded lookup-style positive for analyst triage and hypothesis generation, not as actor authorship attribution, CTI prose attribution, or a major Praxis defense pillar.

## Research Question

Can a small observed set of ATT&CK techniques retrieve the correct ATT&CK group profile near the top of a ranked candidate list?

## Praxis Thesis

ATT&CK group technique profiles contain enough curated structure that small observed TTP sets can retrieve likely group profiles under a bounded lookup protocol. The result supports analyst triage and hypothesis generation. It does not prove that a report, intrusion, or campaign was authored by a specific threat actor.

## Data

PX-002 uses ATT&CK group-technique relationships represented as a group-by-technique matrix.

| Item | Count |
|---|---:|
| Groups | `174` |
| Techniques | `697` |
| Group-technique edges | `4546` |
| Eligible groups, degree >= 10 | `121` |
| Queries per shot level | `605` |

## Protocol

For each eligible group:

1. Sample `k` techniques from the group's ATT&CK profile, where `k in {1, 3, 5, 10}`.
2. Treat the sampled techniques as an observed TTP set.
3. Rank all candidate group profiles by similarity to the observed set.
4. Repeat across fixed seeds and report top-k accuracy, MRR, and median rank.

The final package uses the rerun verification completed on 2026-07-06, which reproduced the existing closeout and defense-audit status.

## Methods

| Method | Role |
|---|---|
| `random_uniform` | Chance floor. |
| `frequency_prior` | Non-query baseline that ranks high-degree/common group profiles. |
| `overlap_cosine` | Direct observed-technique-to-profile overlap baseline. |
| `svd32_graph_embedding` | Low-rank embedding of the group-technique matrix. |
| `graphsage_linkpred` | Failed learned-GNN pilot retained as negative boundary evidence. |

## Main Result

At five observed techniques, the lookup task is strong under the standard known-profile protocol.

| Method | Shots | Top-1 | Top-5 | Top-10 | MRR | Median rank | Queries |
|---|---:|---:|---:|---:|---:|---:|---:|
| random_uniform | `5` | `0.005` | `0.028` | `0.053` | `0.033` | `84.0` | `605` |
| frequency_prior | `5` | `0.008` | `0.041` | `0.083` | `0.044` | `61.0` | `605` |
| overlap_cosine | `5` | `0.721` | `0.960` | `0.992` | `0.824` | `1.0` | `605` |
| svd32_graph_embedding | `5` | `0.623` | `0.879` | `0.949` | `0.732` | `1.0` | `605` |

The full shot sweep shows weak one-shot retrieval, usable three-shot overlap retrieval, and strong five-shot retrieval for both overlap and SVD.

| Method | Shots | Top-1 | Top-5 | Top-10 | MRR | Median rank |
|---|---:|---:|---:|---:|---:|---:|
| overlap_cosine | `1` | `0.136` | `0.425` | `0.598` | `0.284` | `7.0` |
| svd32_graph_embedding | `1` | `0.093` | `0.286` | `0.468` | `0.209` | `12.0` |
| overlap_cosine | `3` | `0.425` | `0.846` | `0.942` | `0.602` | `2.0` |
| svd32_graph_embedding | `3` | `0.306` | `0.684` | `0.858` | `0.479` | `3.0` |
| overlap_cosine | `5` | `0.721` | `0.960` | `0.992` | `0.824` | `1.0` |
| svd32_graph_embedding | `5` | `0.623` | `0.879` | `0.949` | `0.732` | `1.0` |
| overlap_cosine | `10` | `0.969` | `1.000` | `1.000` | `0.982` | `1.0` |
| svd32_graph_embedding | `10` | `0.931` | `0.993` | `1.000` | `0.959` | `1.0` |

## Degree-Bucket Check

The five-shot result is not only a high-degree-profile artifact. In the closeout analysis, overlap top-5 remains above `0.887` in all degree buckets and SVD top-5 remains above `0.831` in all degree buckets.

| Method | Degree bucket | Top-5 | MRR | Median rank | Median degree | Queries |
|---|---|---:|---:|---:|---:|---:|
| overlap_cosine | high-degree | `0.887` | `0.644` | `2.0` | `57.0` | `195` |
| overlap_cosine | low-degree | `0.995` | `0.953` | `1.0` | `14.0` | `205` |
| overlap_cosine | mid-degree | `0.995` | `0.866` | `1.0` | `29.0` | `205` |
| svd32_graph_embedding | high-degree | `0.831` | `0.659` | `1.0` | `57.0` | `195` |
| svd32_graph_embedding | low-degree | `0.951` | `0.866` | `1.0` | `14.0` | `205` |
| svd32_graph_embedding | mid-degree | `0.854` | `0.667` | `1.0` | `29.0` | `205` |

## Negative Boundary: GraphSAGE

The learned GraphSAGE pilot does not justify a GNN attribution claim.

| Mode | Method | Shots | Top-5 | Median rank |
|---|---|---:|---:|---:|
| known_profile | overlap_cosine_train | `5` | `0.985` | `1.0` |
| known_profile | svd32_train_graph | `5` | `0.926` | `1.0` |
| known_profile | graphsage_linkpred | `5` | `0.060` | `60.0` |
| held_edge | graphsage_linkpred | `5` | `0.073` | `34.0` |

This is a useful negative result. It prevents the work from being presented as "GNN attribution" when simple profile retrieval is the supported mechanism.

## Defense Audit Boundary

The 2026-06-30 PX-002 defense audit tested whether the profile-retrieval positive survives harsher conditions.

| Setting | Method | Shots | Top-5 | MRR | Median rank | Queries |
|---|---|---:|---:|---:|---:|---:|
| standard | overlap_cosine | `5` | `0.960` | `0.824` | `1.0` | `605` |
| standard | svd32_graph_embedding | `5` | `0.879` | `0.732` | `1.0` | `605` |
| noisy_query | overlap_cosine | `5` | `0.788` | `0.567` | `2.0` | `605` |
| noisy_query | svd32_graph_embedding | `5` | `0.577` | `0.389` | `4.0` | `605` |
| leave_query_out | overlap_cosine | `5` | `0.000` | `0.008` | `134.0` | `605` |
| leave_query_out | svd32_graph_embedding | `5` | `0.299` | `0.215` | `16.0` | `605` |

The defense audit demotes PX-002 from a major defense pillar. The standard and noisy-query results still support bounded lookup utility, but the leave-query-out result blocks any claim that the method generalizes beyond known-profile overlap without stronger representation learning or temporal profile splits.

## Final Determination

PX-002 is package-ready as a bounded Praxis portfolio result:

> Given five observed ATT&CK techniques sampled from known group profiles, simple overlap and SVD profile-retrieval baselines can rank the correct ATT&CK group profile near the top of the candidate list. This supports analyst triage and hypothesis generation, but it does not prove CTI prose attribution, actor authorship, or a robust defense mechanism.

## What This Proves

1. ATT&CK group-technique profiles contain enough structure for strong five-shot profile lookup under the standard known-profile protocol.
2. Simple overlap and low-rank SVD baselines outperform random and frequency-prior floors by large margins.
3. The useful operating point starts around three to five observed TTPs, not one.
4. The current GraphSAGE pilot should not be promoted because it performs far below simple baselines.
5. The method has bounded analyst-triage value, not attribution-finality value.

## What This Does Not Prove

- It does not prove actor authorship.
- It does not attribute CTI prose reports to groups.
- It does not identify real-world attackers.
- It does not prove a deployed security defense.
- It does not prove that GraphSAGE or GNN embeddings improve ATT&CK attribution.
- It does not survive the leave-query-out anti-tautology stress as a strong generalization claim.

## Artifact Trail

- Protocol: `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_PROTOCOL_20260513.md`
- Baseline refresh: `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_BASELINE_REFRESH_20260513.md`
- Main result: `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_PROFILE_RETRIEVAL_RESULT_20260514.md`
- Closeout: `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_CLOSEOUT_20260514.md`
- Defense audit: `reports/gnn_attribution_ttp_graph_embeddings/PX002_TTP_RETRIEVAL_DEFENSE_AUDIT_20260630.md`
- Thesis section: `paper/attack_ttp_retrieval/ATTACK_TTP_PROFILE_RETRIEVAL_THESIS_SECTION_20260514.md`
- Runner: `scripts/run_attack_ttp_retrieval_closeout.py`
- Defense-audit runner: `scripts/audit_px002_ttp_retrieval_defense.py`
