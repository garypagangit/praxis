# PX-002 Final Defense Package Export

Generated: 2026-07-06

Praxis ID: `PX-002`

Status: **PACKAGE_READY - BOUNDED LOOKUP-STYLE POSITIVE ONLY**

## Thesis

Small observed MITRE ATT&CK technique sets can retrieve likely ATT&CK group profiles under a known-profile lookup protocol, supporting analyst triage and hypothesis generation without claiming actor authorship or CTI prose attribution.

## Final Determination

PX-002 is packaged and ready for portfolio use as a bounded CTI retrieval result.

Supported claim:

> On the measured ATT&CK group-technique profile matrix, five observed techniques sampled from known group profiles can retrieve the correct group profile with high top-5 accuracy under a standard profile-lookup protocol: overlap top-5 `0.960` and SVD top-5 `0.879`, compared with random `0.028` and frequency prior `0.041`.

Defense boundary:

> PX-002 should not be used as a major defense pillar. A defense audit found that leave-query-out stress collapses direct overlap retrieval and weakens SVD, so the result is profile lookup utility rather than robust attribution or a general defense mechanism.

## Current Evidence State

| Layer | Status | Main result |
|---|---|---|
| Protocol | `PROFILE_RETRIEVAL_PROTOCOL_READY` | ATT&CK group-technique profiles; `174` groups; `697` techniques; `4546` edges; `121` eligible groups with degree `>= 10`. |
| Standard lookup closeout | `BOUNDED_LOOKUP_POSITIVE` | Five-shot overlap top-5 `0.960`; SVD top-5 `0.879`; random `0.028`; frequency prior `0.041`; median rank `1.0`; `605` queries. |
| Degree-bucket analysis | `SENSITIVITY_DOCUMENTED` | Five-shot overlap and SVD remain above random/frequency floors across low-, mid-, and high-degree buckets. |
| GraphSAGE pilot | `NEGATIVE_GNN_GATE` | GraphSAGE known-profile five-shot top-5 `0.060` vs SVD `0.926` and overlap `0.985`; do not claim GNN superiority. |
| Defense audit | `BOUNDARY_DEMOTION` | Noisy-query top-5 remains useful but reduced; leave-query-out overlap top-5 `0.000` and SVD top-5 `0.299`; do not claim defense-pillar readiness. |

## What This Proves

1. ATT&CK group-technique profiles support useful five-shot profile lookup under the standard known-profile protocol.
2. Simple overlap and SVD baselines beat random and frequency-prior floors by large margins.
3. Three to five observed TTPs are the practical starting point for useful retrieval.
4. The current GraphSAGE path is not worth defending as a positive result.
5. The correct portfolio framing is analyst-triage lookup, not final attribution.

## What This Does Not Prove

- It does not prove actor authorship.
- It does not attribute raw CTI prose.
- It does not identify real-world attackers.
- It does not prove a deployed security defense.
- It does not prove GNN superiority.
- It does not survive leave-query-out stress as a strong generalization claim.

## Read-First Links

- Final manuscript: `reports/gnn_attribution_ttp_graph_embeddings/px002_final_manuscript_20260706/PX002_FINAL_MANUSCRIPT_20260706.md`
- Paper package: `reports/gnn_attribution_ttp_graph_embeddings/px002_paper_package_20260706/PX002_PRAXIS_PAPER_PACKAGE_20260706.md`
- Claim boundary: `reports/gnn_attribution_ttp_graph_embeddings/px002_paper_package_20260706/PX002_CLAIM_BOUNDARY_20260706.md`
- Original result: `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_PROFILE_RETRIEVAL_RESULT_20260514.md`
- Closeout: `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_CLOSEOUT_20260514.md`
- Defense audit: `reports/gnn_attribution_ttp_graph_embeddings/PX002_TTP_RETRIEVAL_DEFENSE_AUDIT_20260630.md`
- Thesis section: `paper/attack_ttp_retrieval/ATTACK_TTP_PROFILE_RETRIEVAL_THESIS_SECTION_20260514.md`

## Result Artifacts

| Artifact | Purpose |
|---|---|
| `runs/attack-ttp-profile-retrieval-closeout-20260514/retrieval_closeout_summary.csv` | Standard lookup summary by method and shot count. |
| `runs/attack-ttp-profile-retrieval-closeout-20260514/retrieval_degree_buckets.csv` | Five-shot degree-bucket sensitivity table. |
| `runs/attack-ttp-profile-retrieval-closeout-20260514/retrieval_examples_five_shot.csv` | Example query-to-candidate retrieval rows. |
| `runs/attack-ttp-profile-retrieval-closeout-20260514/retrieval_closeout_payload.json` | Machine-readable closeout payload. |
| `runs/px002-ttp-retrieval-defense-audit-20260630/summary.csv` | Defense-audit summary for standard, noisy-query, and leave-query-out settings. |
| `runs/px002-ttp-retrieval-defense-audit-20260630/records.csv` | Row-level defense-audit records. |
| `runs/px002-ttp-retrieval-defense-audit-20260630/payload.json` | Machine-readable defense-audit payload. |

## Appendix A: Supporting Code

| Component | Path | Description |
|---|---|---|
| Main closeout runner | `scripts/run_attack_ttp_retrieval_closeout.py` | Loads ATT&CK group-technique data, builds random/frequency/overlap/SVD rankings, writes closeout tables, degree buckets, examples, and report. |
| Defense audit runner | `scripts/audit_px002_ttp_retrieval_defense.py` | Recomputes standard, noisy-query, and leave-query-out settings to decide whether the result can be promoted beyond lookup utility. |
| Baseline graph runner | `scripts/run_attack_ttp_graph_embedding_baseline.py` | Shared loader and rank-metric utilities for ATT&CK group-technique baselines. |
| GraphSAGE pilot runner | `scripts/run_attack_ttp_graphsage_pilot.py` | Failed learned-GNN comparison retained as negative boundary evidence. |

## Verification

The closeout and defense-audit scripts were rerun locally on 2026-07-06. They reproduced the package status:

- Closeout status: `closed_out_bounded_positive`.
- Defense audit status: `BOUNDED LOOKUP-STYLE POSITIVE ONLY`.

## Defense Use

Use PX-002 as a compact supporting result in the portfolio. Lead with the five-shot profile lookup result, immediately show the defense-audit boundary, and state that the result is useful for candidate narrowing rather than attribution finality.
