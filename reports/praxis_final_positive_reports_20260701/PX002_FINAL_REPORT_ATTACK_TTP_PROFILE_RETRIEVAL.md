# PX-002 Final Praxis Report

## Project

**Title:** Few-Shot ATT&CK Group-Profile Retrieval from Observed TTP Sets

**Praxis ID:** PX-002

**Status:** **FINAL BOUNDED LOOKUP-STYLE POSITIVE - NOT A DEFENSE PILLAR**

## Praxis Summary

**Praxis thesis:** ATT&CK group-technique profiles can support useful candidate-group lookup from small observed TTP sets, but the result must be framed as analyst triage rather than actor attribution.

**Objective:** Evaluate whether a small observed set of ATT&CK techniques can retrieve the correct ATT&CK group profile near the top of a ranked candidate list.

**Research question:** Can five observed ATT&CK techniques retrieve likely group profiles under a formal TTP-set profile-retrieval protocol?

**Hypothesis:** Direct overlap and low-rank SVD baselines will rank the correct group profile substantially above random and frequency-prior floors under the standard known-profile lookup protocol.

## Method

PX-002 builds a group-by-technique matrix from MITRE ATT&CK group-technique relationships. For each eligible group with at least `10` techniques, the protocol samples `1`, `3`, `5`, and `10` observed techniques and ranks all candidate group profiles.

The evaluation reports top-1, top-5, top-10, MRR, median rank, floor baselines, degree-bucket sensitivity, and a later defense audit with noisy-query and leave-query-out stress settings.

## Results

Standard five-shot profile lookup:

| Method | Top-1 | Top-5 | Top-10 | MRR | Median rank | Queries |
|---|---:|---:|---:|---:|---:|---:|
| random_uniform | `0.005` | `0.028` | `0.053` | `0.033` | `84.0` | `605` |
| frequency_prior | `0.008` | `0.041` | `0.083` | `0.044` | `61.0` | `605` |
| overlap_cosine | `0.721` | `0.960` | `0.992` | `0.824` | `1.0` | `605` |
| svd32_graph_embedding | `0.623` | `0.879` | `0.949` | `0.732` | `1.0` | `605` |

Defense-audit boundary:

| Setting | Method | Top-5 | MRR | Median rank | Queries |
|---|---|---:|---:|---:|---:|
| standard | overlap_cosine | `0.960` | `0.824` | `1.0` | `605` |
| standard | svd32_graph_embedding | `0.879` | `0.732` | `1.0` | `605` |
| noisy_query | overlap_cosine | `0.788` | `0.567` | `2.0` | `605` |
| noisy_query | svd32_graph_embedding | `0.577` | `0.389` | `4.0` | `605` |
| leave_query_out | overlap_cosine | `0.000` | `0.008` | `134.0` | `605` |
| leave_query_out | svd32_graph_embedding | `0.299` | `0.215` | `16.0` | `605` |

GraphSAGE failed as a learned-GNN positive: known-profile five-shot GraphSAGE top-5 was `0.060` versus SVD `0.926` and overlap `0.985`.

## What It Proves

PX-002 proves that small observed TTP sets can retrieve likely ATT&CK group profiles under a bounded known-profile lookup protocol, and that simple overlap/SVD baselines are strong enough to be useful for analyst triage.

## Claim Boundary

Allowed claim:

> On the measured ATT&CK group-technique matrix, five observed techniques sampled from known group profiles retrieved the correct group profile with top-5 accuracy `0.960` using overlap and `0.879` using SVD, compared with random `0.028` and frequency-prior `0.041`.

Do not claim actor authorship, CTI prose attribution, real-world attacker identification, GNN superiority, or major defense-pillar readiness.

## Evidence Links

- `reports/gnn_attribution_ttp_graph_embeddings/px002_final_manuscript_20260706/PX002_FINAL_MANUSCRIPT_20260706.md`
- `reports/gnn_attribution_ttp_graph_embeddings/px002_final_defense_package_export_20260706/PX002_FINAL_DEFENSE_PACKAGE_EXPORT_20260706.md`
- `reports/gnn_attribution_ttp_graph_embeddings/px002_paper_package_20260706/PX002_CLAIM_BOUNDARY_20260706.md`
- `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_PROFILE_RETRIEVAL_RESULT_20260514.md`
- `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_CLOSEOUT_20260514.md`
- `reports/gnn_attribution_ttp_graph_embeddings/PX002_TTP_RETRIEVAL_DEFENSE_AUDIT_20260630.md`
- `paper/attack_ttp_retrieval/ATTACK_TTP_PROFILE_RETRIEVAL_THESIS_SECTION_20260514.md`
- `scripts/run_attack_ttp_retrieval_closeout.py`
- `scripts/audit_px002_ttp_retrieval_defense.py`

## Appendix A: Transportable Project Code

The full project runners use the local MITRE ATT&CK STIX export and write full CSV/JSON reports. This portable appendix shows the core profile-retrieval idea with a small local matrix so the method travels with the report.

```python
#!/usr/bin/env python3
"""
PX-002 portable ATT&CK TTP-set profile retrieval demo.

Purpose:
    Demonstrate the core bounded lookup method used in PX-002.

What this code does:
    1. Creates a tiny group-by-technique profile matrix.
    2. Treats a few observed techniques as a query.
    3. Ranks candidate group profiles by overlap cosine.
    4. Reports whether the true group appears in the top-k shortlist.

The full project runner uses MITRE ATT&CK STIX data, fixed seeds, random and
frequency floors, SVD embeddings, degree buckets, and defense-audit variants.
This appendix keeps the concept transparent and dependency-free.
"""

from __future__ import annotations

from math import sqrt


GROUP_PROFILES = {
    "APT-Alpha": {"T1059", "T1105", "T1027", "T1055", "T1082"},
    "APT-Beta": {"T1566.001", "T1204.002", "T1059", "T1102", "T1027"},
    "APT-Gamma": {"T1003", "T1087", "T1021.001", "T1055", "T1105"},
    "APT-Delta": {"T1110", "T1078", "T1087", "T1059", "T1047"},
}


def overlap_cosine(query: set[str], profile: set[str]) -> float:
    """Score a query against a candidate profile using binary cosine overlap."""

    if not query or not profile:
        return 0.0
    overlap = len(query & profile)
    return overlap / (sqrt(len(query)) * sqrt(len(profile)))


def rank_profiles(query: set[str]) -> list[tuple[str, float]]:
    """Return candidate group profiles ranked from most to least similar."""

    scores = [
        (group, overlap_cosine(query, profile))
        for group, profile in GROUP_PROFILES.items()
    ]
    return sorted(scores, key=lambda item: item[1], reverse=True)


def top_k_hit(ranked: list[tuple[str, float]], true_group: str, k: int = 3) -> bool:
    """Check whether the true group appears in the top-k candidate shortlist."""

    return true_group in [group for group, _score in ranked[:k]]


def main() -> None:
    # A realistic PX-002 query is a small observed ATT&CK technique set.
    query = {"T1059", "T1105", "T1027"}
    true_group = "APT-Alpha"

    ranked = rank_profiles(query)

    print("PX-002 portable profile retrieval demo")
    print("Observed TTPs:", ", ".join(sorted(query)))
    print("Ranked candidate profiles:")
    for rank, (group, score) in enumerate(ranked, start=1):
        print(f"{rank}. {group}: {score:.3f}")

    print("top-3 hit:", top_k_hit(ranked, true_group, k=3))


if __name__ == "__main__":
    main()
```
