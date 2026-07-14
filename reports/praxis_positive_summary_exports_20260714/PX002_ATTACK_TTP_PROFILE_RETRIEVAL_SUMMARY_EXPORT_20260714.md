# PX-002 Summary Export

## Experiment

Title: Few-Shot ATT&CK Group-Profile Retrieval from Observed TTP Sets

Praxis ID: PX-002

Status: Final bounded lookup-style positive. Supporting artifact only; not a lead defense pillar.

## Executive Summary

PX-002 tested whether a small observed set of MITRE ATT&CK techniques can retrieve the correct ATT&CK group profile near the top of a ranked candidate list. The positive result is real but narrow: if the candidate group profile already contains the observed techniques, direct overlap and SVD retrieval are strong analyst-triage tools. The stronger audit also showed the limit: when query techniques are removed from the candidate profile, simple overlap collapses, so this should not be defended as actor attribution or a major defense result.

## Thesis

ATT&CK group-technique profiles can support useful candidate-group lookup from small observed TTP sets, but the result must be framed as analyst triage rather than actor attribution.

## Objective

Evaluate whether a small observed set of ATT&CK techniques can retrieve likely group profiles under a formal TTP-set profile-retrieval protocol.

## What Was Tested

The experiment built a group-by-technique matrix from MITRE ATT&CK group-technique relationships. For eligible groups with at least 10 techniques, the protocol sampled 1, 3, 5, and 10 observed techniques and ranked candidate group profiles using overlap cosine and SVD baselines. A defense audit added noisy-query and leave-query-out stress settings.

## Key Results

Standard five-shot lookup:

| Method | Top-1 | Top-5 | Top-10 | MRR | Median rank | Queries |
|---|---:|---:|---:|---:|---:|---:|
| Random uniform | 0.005 | 0.028 | 0.053 | 0.033 | 84.0 | 605 |
| Frequency prior | 0.008 | 0.041 | 0.083 | 0.044 | 61.0 | 605 |
| Overlap cosine | 0.721 | 0.960 | 0.992 | 0.824 | 1.0 | 605 |
| SVD32 graph embedding | 0.623 | 0.879 | 0.949 | 0.732 | 1.0 | 605 |

Defense-audit boundary:

| Setting | Method | Top-5 | MRR | Median rank | Queries |
|---|---|---:|---:|---:|---:|
| Standard | Overlap cosine | 0.960 | 0.824 | 1.0 | 605 |
| Standard | SVD32 graph embedding | 0.879 | 0.732 | 1.0 | 605 |
| Noisy query | Overlap cosine | 0.788 | 0.567 | 2.0 | 605 |
| Noisy query | SVD32 graph embedding | 0.577 | 0.389 | 4.0 | 605 |
| Leave-query-out | Overlap cosine | 0.000 | 0.008 | 134.0 | 605 |
| Leave-query-out | SVD32 graph embedding | 0.299 | 0.215 | 16.0 | 605 |

GraphSAGE did not become a learned-GNN positive. Known-profile five-shot GraphSAGE top-5 was 0.060 versus SVD 0.926 and overlap 0.985.

## What It Proves

PX-002 proves that small observed TTP sets can retrieve likely ATT&CK group profiles under a bounded known-profile lookup protocol. It also proves that simple overlap and SVD baselines are strong enough for analyst triage when the task is profile lookup.

## What It Does Not Prove

PX-002 does not prove actor authorship, real-world attacker identification, GNN superiority, CTI prose attribution, or defense-pillar readiness. The leave-query-out stress result is the key boundary: the original win depends heavily on observable profile overlap.

## Defense Use

Use PX-002 as a supporting CTI retrieval utility and as evidence that the Praxis process demoted results after stronger tests. Do not lead a defense with PX-002.

## Evidence Links

- `reports/praxis_final_positive_reports_20260701/PX002_FINAL_REPORT_ATTACK_TTP_PROFILE_RETRIEVAL.md`
- `reports/gnn_attribution_ttp_graph_embeddings/px002_final_manuscript_20260706/PX002_FINAL_MANUSCRIPT_20260706.md`
- `reports/gnn_attribution_ttp_graph_embeddings/px002_final_defense_package_export_20260706/PX002_FINAL_DEFENSE_PACKAGE_EXPORT_20260706.md`
- `reports/gnn_attribution_ttp_graph_embeddings/px002_paper_package_20260706/PX002_CLAIM_BOUNDARY_20260706.md`
- `reports/gnn_attribution_ttp_graph_embeddings/PX002_TTP_RETRIEVAL_DEFENSE_AUDIT_20260630.md`
- `paper/attack_ttp_retrieval/ATTACK_TTP_PROFILE_RETRIEVAL_THESIS_SECTION_20260514.md`
- `scripts/run_attack_ttp_retrieval_closeout.py`
- `scripts/audit_px002_ttp_retrieval_defense.py`

