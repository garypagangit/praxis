# Few-Shot ATT&CK Group-Profile Retrieval

Generated: 2026-05-14

Status: **draft thesis section for selected result #2**

## Claim

Small observed ATT&CK TTP sets can retrieve likely ATT&CK group profiles with high top-k accuracy under a bounded profile-retrieval protocol. The selected claim is **profile retrieval for analyst triage**, not prose attribution, authorship attribution, or a GNN representation claim.

## Motivation

Early investigations often contain only a partial set of observed techniques. A defender may know that several ATT&CK techniques appeared in a campaign, but may not yet have reliable prose reports, malware-family labels, infrastructure clusters, or campaign outcome labels. This makes full CTI attribution premature. A narrower and more defensible question is whether a small observed TTP set can retrieve known ATT&CK group profiles that share similar technique structure.

This distinction matters for the dissertation portfolio. Earlier graph-neural attempts did not beat simple baselines, so the selected result is not "GraphSAGE for attribution." The positive result is that a carefully scoped retrieval protocol is already useful with simple overlap and low-rank group-technique embeddings.

## Data And Protocol

The experiment uses ATT&CK group-technique relationships. For each eligible group, the protocol samples query techniques from that group's known profile and ranks all candidate groups. Each query is evaluated at `1`, `3`, `5`, and `10` observed techniques.

The protocol reports:

- Top-1, top-5, and top-10 retrieval accuracy.
- Mean reciprocal rank.
- Median rank.
- Random and frequency-prior baselines.
- Degree-bucket analysis to check whether the result is only a high-degree-profile artifact.

## Methods

| Method | Role |
|---|---|
| Random ranking | Chance floor |
| Frequency prior | Non-query baseline that prefers common/high-degree groups |
| Overlap cosine | Direct TTP-set similarity baseline |
| SVD32 group-technique embedding | Low-rank profile retrieval baseline |
| GraphSAGE pilot | Negative learned-embedding comparison |

The GraphSAGE result is retained as a boundary condition. It is not promoted because it underperforms the simple baselines.

## Main Result

| Method | Shots | Top-1 | Top-5 | Top-10 | MRR | Median rank |
|---|---:|---:|---:|---:|---:|---:|
| overlap_cosine | 1 | `0.136` | `0.425` | `0.598` | `0.284` | `7.0` |
| svd32_graph_embedding | 1 | `0.093` | `0.286` | `0.468` | `0.209` | `12.0` |
| overlap_cosine | 3 | `0.425` | `0.846` | `0.942` | `0.602` | `2.0` |
| svd32_graph_embedding | 3 | `0.306` | `0.684` | `0.858` | `0.479` | `3.0` |
| overlap_cosine | 5 | `0.721` | `0.960` | `0.992` | `0.824` | `1.0` |
| svd32_graph_embedding | 5 | `0.623` | `0.879` | `0.949` | `0.732` | `1.0` |
| overlap_cosine | 10 | `0.969` | `1.000` | `1.000` | `0.982` | `1.0` |
| svd32_graph_embedding | 10 | `0.931` | `0.993` | `1.000` | `0.959` | `1.0` |

At five observed techniques, overlap retrieval reaches top-5 accuracy `0.960` and SVD reaches `0.879`, compared with random `0.028` and frequency-prior `0.041`. Median rank is `1.0`.

## Interpretation

The result supports a practical analyst-triage workflow: given a small observed set of TTPs, retrieve a short list of plausible ATT&CK group profiles for comparison. This is useful because it narrows analyst attention without claiming actor authorship.

The result also says something methodological: for this ATT&CK profile-retrieval task, simple set/linear baselines are stronger than the current learned graph embedding pilot. That is a positive scientific outcome because it prevents an overbuilt GNN claim and identifies the simpler method that actually clears the gate.

## Claim Guard

| Not Allowed | Reason |
|---|---|
| "This attributes campaigns to actors" | No dated report-to-group or campaign outcome labels are used. |
| "GraphSAGE improves APT attribution" | GraphSAGE underperformed overlap and SVD. |
| "This identifies real attackers" | ATT&CK group profiles are knowledge-base abstractions, not identity proof. |
| "Top-5 retrieval is a final attribution decision" | It is a triage shortlist. |

## Thesis Placement

This should follow Praxis 06 as the second positive result:

1. Praxis 06 shows a safety-gated adaptation pattern for streaming APT stage detection under source-file shift.
2. This section shows a bounded retrieval protocol for ATT&CK group-profile triage from small TTP sets.

Together, the two selected results form a coherent dissertation story around **bounded, auditable cybersecurity ML claims** rather than broad claims that the negative experiments do not support.

## Artifact Trail

- Protocol: `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_PROTOCOL_20260513.md`
- Baseline refresh: `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_BASELINE_REFRESH_20260513.md`
- Closeout: `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_CLOSEOUT_20260514.md`
- Paper outline: `paper/attack_ttp_retrieval/ATTACK_TTP_PROFILE_RETRIEVAL_PAPER_OUTLINE_20260514.md`
