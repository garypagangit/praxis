# Few-Shot ATT&CK Group-Profile Retrieval From Observed TTP Sets

Generated: 2026-05-14

Status: **paper outline for portfolio result #2**

## Working Abstract

Analysts often observe only a small number of ATT&CK techniques early in an investigation. This study evaluates whether those partial observed TTP sets can retrieve likely ATT&CK group profiles. Using ATT&CK group-technique relationships, we construct few-shot queries by sampling `1`, `3`, `5`, and `10` techniques from eligible group profiles and ranking all candidate groups. Simple overlap and SVD group-technique embedding baselines perform strongly: at 5 shots, overlap cosine reaches top-5 accuracy `0.960`, while SVD reaches `0.879`, both with median rank `1.0` over `605` queries. A GraphSAGE pilot fails to beat these simple baselines, so the selected claim is profile retrieval, not learned GNN attribution. The result supports analyst triage and hypothesis generation from observed TTP sets, but does not prove CTI prose attribution or actor authorship.

## Contribution

This result contributes a narrow evaluation protocol for ATT&CK group-profile retrieval from small observed TTP sets. It is valuable precisely because it does not overclaim: it separates profile retrieval from prose attribution and shows that simple baselines are already strong.

## Research Questions

| ID | Question | Evidence |
|---|---|---|
| RQ1 | Can small observed TTP sets retrieve the correct ATT&CK group profile? | Yes at 5 shots: overlap top-5 `0.960`, SVD top-5 `0.879`. |
| RQ2 | How many techniques are needed for useful retrieval? | One shot is weak; three shots are useful for overlap; five shots are strong for both overlap and SVD. |
| RQ3 | Does a learned GNN improve this result? | No. Current GraphSAGE is much worse than overlap/SVD. |
| RQ4 | Does this support CTI prose attribution? | No. Report-to-group labels are missing. |

## Main Result Table

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

## Thesis Placement

This should follow Praxis 06 as a second narrow positive:

1. Praxis 06: selective TTA recovers rare-stage behavior under source-file shift.
2. Result #2: ATT&CK profile retrieval supports analyst triage from partial TTP observations.

Both are bounded cybersecurity findings. Neither depends on overstating a failed GNN or LLM attribution claim.

## Next Additions Before Final Chapter

- Random and frequency-prior baselines. **Done 2026-05-14.**
- Degree-bucket robustness. **Done 2026-05-14.**
- Example retrieval table. **Done 2026-05-14.**
- Held-edge stress-test appendix.
- Clean claim guard: profile retrieval only.

Closeout report: `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_CLOSEOUT_20260514.md`.

At 5 shots, overlap top-5 is `0.960` and SVD top-5 is `0.879`, compared with random `0.028` and frequency-prior `0.041`. The remaining work is paper conversion, not rescuing the result.
