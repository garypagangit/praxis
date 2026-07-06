# PX-002 Praxis Paper Package

Generated: 2026-07-06

Praxis ID: `PX-002`

Status: **PACKAGE_READY - BOUNDED LOOKUP-STYLE POSITIVE**

## Paper Title

Few-Shot ATT&CK Group-Profile Retrieval from Observed TTP Sets

## One-Sentence Contribution

PX-002 defines and evaluates a bounded ATT&CK TTP-set profile-retrieval protocol showing that simple overlap and SVD baselines can retrieve likely group profiles from five observed techniques, while a defense audit prevents the result from being overclaimed as attribution or a robust defense.

## Thesis

Small observed ATT&CK technique sets can support useful group-profile lookup under a known-profile protocol, but this utility should be framed as analyst triage and hypothesis generation rather than actor authorship or CTI prose attribution.

## Final Claim

Given five observed ATT&CK techniques sampled from known group profiles, direct overlap and SVD group-technique baselines retrieve the correct ATT&CK group profile with high top-5 accuracy. The result is bounded by the fact that leave-query-out stress substantially weakens or collapses the same retrieval signal.

## Main Evidence

| Evidence layer | Result |
|---|---|
| Standard five-shot lookup | Overlap top-5 `0.960`; SVD top-5 `0.879`; random top-5 `0.028`; frequency-prior top-5 `0.041`; `605` queries. |
| Degree-bucket closeout | Overlap top-5 at least `0.887`; SVD top-5 at least `0.831` across low-, mid-, and high-degree groups. |
| GraphSAGE negative gate | GraphSAGE known-profile five-shot top-5 `0.060`, far below overlap/SVD. |
| Noisy-query audit | 40% noisy observed TTPs: overlap top-5 `0.788`; SVD top-5 `0.577`. |
| Leave-query-out audit | Removing query techniques from the target candidate profile: overlap top-5 `0.000`; SVD top-5 `0.299`. |

## Recommended Manuscript Structure

1. Motivation: early investigations often have partial observed TTPs.
2. Scope: profile retrieval is narrower than actor attribution.
3. Data: ATT&CK group-technique matrix.
4. Protocol: sample observed TTP sets from eligible group profiles.
5. Baselines: random, frequency prior, overlap, SVD, GraphSAGE pilot.
6. Results: five-shot lookup, all-shot sweep, degree-bucket check.
7. Boundary audit: noisy query and leave-query-out tests.
8. Claim guard: analyst triage only.
9. Portfolio placement: supporting CTI retrieval result, not a lead defense pillar.

## Read-First Links

- Final manuscript: `reports/gnn_attribution_ttp_graph_embeddings/px002_final_manuscript_20260706/PX002_FINAL_MANUSCRIPT_20260706.md`
- Claim boundary: `reports/gnn_attribution_ttp_graph_embeddings/px002_paper_package_20260706/PX002_CLAIM_BOUNDARY_20260706.md`
- Final defense export: `reports/gnn_attribution_ttp_graph_embeddings/px002_final_defense_package_export_20260706/PX002_FINAL_DEFENSE_PACKAGE_EXPORT_20260706.md`
- Main result: `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_PROFILE_RETRIEVAL_RESULT_20260514.md`
- Closeout: `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_CLOSEOUT_20260514.md`
- Defense audit: `reports/gnn_attribution_ttp_graph_embeddings/PX002_TTP_RETRIEVAL_DEFENSE_AUDIT_20260630.md`

## Appendix Pointers

| Component | Path | Purpose |
|---|---|---|
| Main closeout runner | `scripts/run_attack_ttp_retrieval_closeout.py` | Rebuilds standard lookup summaries, degree buckets, examples, and report. |
| Defense audit runner | `scripts/audit_px002_ttp_retrieval_defense.py` | Tests standard, leave-query-out, and noisy-query variants. |
| Baseline runner | `scripts/run_attack_ttp_graph_embedding_baseline.py` | Builds group-technique baselines used by the retrieval branch. |
| GraphSAGE pilot | `scripts/run_attack_ttp_graphsage_pilot.py` | Retained as negative learned-GNN boundary evidence. |

## Portfolio Use

Use PX-002 as a support result in the defense portfolio. It strengthens the narrative that Praxis keeps useful bounded positives while rejecting overclaims. It should follow PX-001/PX-003/PX-050/PX-054, not lead the defense.
