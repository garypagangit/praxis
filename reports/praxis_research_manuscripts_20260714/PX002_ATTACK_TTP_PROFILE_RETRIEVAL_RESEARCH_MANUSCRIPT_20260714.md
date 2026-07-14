# Few-Shot ATT&CK Group-Profile Retrieval from Observed TTP Sets

Research manuscript draft

Praxis ID: PX-002

Generated: 2026-07-14

Status: Bounded lookup-style positive; supporting result, not a lead defense pillar

## Abstract

Security investigations often begin with partial observations: a small number of tactics, techniques, and procedures rather than a complete campaign narrative. This paper evaluates whether small observed MITRE ATT&CK technique sets can retrieve likely group profiles under a bounded profile-lookup protocol. Using ATT&CK group-technique relationships represented as a group-by-technique matrix, the experiment samples one, three, five, and ten observed techniques from eligible group profiles and ranks candidate groups with random, frequency-prior, overlap-cosine, low-rank SVD, and GraphSAGE-style learned-embedding baselines. At the five-shot operating point, overlap cosine reached top-5 accuracy 0.960 and SVD reached 0.879, compared with random 0.028 and frequency prior 0.041. A later defense audit narrowed the claim: under leave-query-out stress, overlap top-5 collapsed to 0.000 and SVD top-5 fell to 0.299. The result supports analyst triage and candidate-shortlist generation under known-profile lookup, but it does not support actor attribution, CTI prose attribution, or a robust defense mechanism.

## 1. Introduction

MITRE ATT&CK is widely used as a structured vocabulary for adversary behavior. Its group-technique relationships invite a natural retrieval question: if an analyst has observed a handful of techniques, can those techniques retrieve likely group profiles for triage? The attraction of this problem is practical. A correct top-5 shortlist can focus analyst review, but an overclaimed result can become a misleading attribution system.

PX-002 was designed around that tension. The experiment intentionally avoids claiming authorship or campaign attribution. It treats ATT&CK group profiles as curated retrieval targets and asks whether simple baselines can rank the known group profile near the top when a subset of its techniques is observed. The paper also includes negative and boundary tests so the result cannot be mistaken for a graph-neural attribution system.

## 2. Prior Work

ATT&CK provides the data model. Strom et al. describe ATT&CK as a knowledge base of adversary tactics and techniques grounded in real-world observations and intended to support threat modeling and defensive analysis. That design motivates treating group-technique relationships as a graph-like matrix rather than free text alone.

Information-retrieval work on latent semantic analysis motivates the SVD baseline. Deerwester et al. introduced the use of singular value decomposition to uncover latent structure in a term-document matrix. PX-002 adapts that idea to a group-technique matrix: groups play the document role, techniques play the term role, and low-rank structure becomes a simple profile-retrieval baseline.

Graph representation learning motivated the learned-embedding negative gate. Hamilton et al. introduced GraphSAGE as an inductive graph representation learning method based on neighborhood aggregation. Because ATT&CK relationships form a graph, a graph-neural baseline was plausible. PX-002 required that learned graph embeddings beat simple overlap/SVD before any GNN claim could be promoted.

Recent CTI evaluation work, including CTIBench, reinforces the need for task-specific cyber evaluations and conservative interpretation. CTIBench evaluates LLMs on CTI-relevant tasks and highlights reliability concerns in CTI reasoning. PX-002 is narrower: it does not evaluate general LLM CTI reasoning; it evaluates profile retrieval from curated ATT&CK relationships.

## 3. Experimental Design Influences

The experiment setup was directly shaped by four research influences.

First, ATT&CK's design philosophy led to a structured group-technique matrix rather than a report-text corpus. The experiment asks what the curated relationship layer can do by itself.

Second, latent semantic analysis led to the SVD32 baseline. SVD was included because a low-rank matrix method is a strong, explainable midpoint between direct overlap and learned graph modeling.

Third, GraphSAGE led to the learned-embedding pilot. The protocol required GraphSAGE to outperform overlap/SVD before the result could be framed as graph-neural attribution. It did not, which is why the final claim excludes GNN superiority.

Fourth, CTI benchmark concerns led to explicit claim boundaries. The protocol reports top-k lookup metrics, not attribution accuracy, and it includes a leave-query-out stress test to separate profile overlap from stronger generalization.

## 4. Research Questions

RQ1: Can five observed ATT&CK techniques retrieve the correct group profile near the top of a ranked candidate list?

RQ2: Do overlap and SVD exceed random and frequency-prior floors?

RQ3: Does a GraphSAGE-style learned graph baseline outperform simple profile retrieval?

RQ4: Does the result survive noisy-query and leave-query-out stress conditions?

## 5. Data and Methods

PX-002 uses ATT&CK Enterprise group-technique relationships represented as a binary group-by-technique matrix.

| Data item | Count |
|---|---:|
| Groups | 174 |
| Techniques | 697 |
| Group-technique edges | 4546 |
| Eligible groups, degree >= 10 | 121 |
| Queries per shot level | 605 |

For each eligible group, the protocol samples k techniques from the group profile where k is 1, 3, 5, or 10. The sampled techniques become the observed query. All group profiles are ranked by similarity to the query.

Methods:

| Method | Role |
|---|---|
| random_uniform | Chance floor |
| frequency_prior | Non-query baseline favoring high-degree groups |
| overlap_cosine | Direct overlap between observed techniques and candidate profile |
| svd32_graph_embedding | Low-rank matrix baseline |
| graphsage_linkpred | Learned graph baseline retained as negative evidence |

Metrics include top-1, top-5, top-10, mean reciprocal rank, median rank, degree-bucket performance, noisy-query performance, and leave-query-out stress performance.

## 6. Results

At five observed techniques, profile lookup is strong under the known-profile protocol.

| Method | Top-1 | Top-5 | Top-10 | MRR | Median rank | Queries |
|---|---:|---:|---:|---:|---:|---:|
| random_uniform | 0.005 | 0.028 | 0.053 | 0.033 | 84.0 | 605 |
| frequency_prior | 0.008 | 0.041 | 0.083 | 0.044 | 61.0 | 605 |
| overlap_cosine | 0.721 | 0.960 | 0.992 | 0.824 | 1.0 | 605 |
| svd32_graph_embedding | 0.623 | 0.879 | 0.949 | 0.732 | 1.0 | 605 |

The shot sweep shows that one observed technique is insufficient, three techniques are useful, and five techniques are the practical operating point.

| Method | Shots | Top-5 | MRR | Median rank |
|---|---:|---:|---:|---:|
| overlap_cosine | 1 | 0.425 | 0.284 | 7.0 |
| svd32_graph_embedding | 1 | 0.286 | 0.209 | 12.0 |
| overlap_cosine | 3 | 0.846 | 0.602 | 2.0 |
| svd32_graph_embedding | 3 | 0.684 | 0.479 | 3.0 |
| overlap_cosine | 5 | 0.960 | 0.824 | 1.0 |
| svd32_graph_embedding | 5 | 0.879 | 0.732 | 1.0 |
| overlap_cosine | 10 | 1.000 | 0.982 | 1.0 |
| svd32_graph_embedding | 10 | 0.993 | 0.959 | 1.0 |

The learned GraphSAGE pilot failed to outperform simple baselines.

| Mode | Method | Shots | Top-5 | Median rank |
|---|---|---:|---:|---:|
| known_profile | overlap_cosine_train | 5 | 0.985 | 1.0 |
| known_profile | svd32_train_graph | 5 | 0.926 | 1.0 |
| known_profile | graphsage_linkpred | 5 | 0.060 | 60.0 |
| held_edge | graphsage_linkpred | 5 | 0.073 | 34.0 |

The defense audit narrowed the claim.

| Setting | Method | Top-5 | MRR | Median rank | Queries |
|---|---|---:|---:|---:|---:|
| standard | overlap_cosine | 0.960 | 0.824 | 1.0 | 605 |
| standard | svd32_graph_embedding | 0.879 | 0.732 | 1.0 | 605 |
| noisy_query | overlap_cosine | 0.788 | 0.567 | 2.0 | 605 |
| noisy_query | svd32_graph_embedding | 0.577 | 0.389 | 4.0 | 605 |
| leave_query_out | overlap_cosine | 0.000 | 0.008 | 134.0 | 605 |
| leave_query_out | svd32_graph_embedding | 0.299 | 0.215 | 16.0 | 605 |

## 7. Discussion

PX-002 is useful because it establishes a bounded retrieval operating point. With five observed techniques sampled from known profiles, overlap and SVD retrieve the correct group profile far above random and frequency-prior floors. This can help an analyst generate candidate groups for further review.

The boundary result is just as important. Leave-query-out stress shows that the strongest result depends on direct profile overlap. The experiment should not be reframed as attribution, authorship, or hidden-edge discovery. The GraphSAGE negative result also prevents a misleading graph-neural claim.

## 8. Threats to Validity

The main internal validity risk is tautology: sampled query techniques come from the same group profiles used for retrieval. The defense audit makes this visible rather than hiding it. The main external validity risk is that curated ATT&CK profiles are not equivalent to noisy incident reports. A real-world analyst may have partial, uncertain, or incorrectly extracted techniques. Finally, ATT&CK itself changes over time, so temporal release splits would be needed before making drift or future-profile claims.

## 9. Conclusion

PX-002 supports a bounded analyst-triage claim: small observed ATT&CK technique sets can retrieve likely group profiles under a known-profile lookup protocol. It should be used as candidate-shortlist evidence and as an example of disciplined claim narrowing. It should not be defended as actor attribution, CTI prose attribution, or a graph-neural defense result.

## Repository Artifacts

- `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_PROTOCOL_20260513.md`
- `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_PROFILE_RETRIEVAL_RESULT_20260514.md`
- `reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_RETRIEVAL_CLOSEOUT_20260514.md`
- `reports/gnn_attribution_ttp_graph_embeddings/PX002_TTP_RETRIEVAL_DEFENSE_AUDIT_20260630.md`
- `scripts/run_attack_ttp_retrieval_closeout.py`
- `scripts/run_attack_ttp_graph_embedding_baseline.py`
- `scripts/run_attack_ttp_graphsage_pilot.py`
- `scripts/audit_px002_ttp_retrieval_defense.py`

## References

Alam, M. T., Bhusal, D., Nguyen, L., & Rastogi, N. (2024). CTIBench: A benchmark for evaluating LLMs in cyber threat intelligence. arXiv. https://arxiv.org/abs/2406.07599

Deerwester, S., Dumais, S. T., Furnas, G. W., Landauer, T. K., & Harshman, R. (1990). Indexing by latent semantic analysis. Journal of the American Society for Information Science, 41(6), 391-407. https://doi.org/10.1002/(SICI)1097-4571(199009)41:6%3C391::AID-ASI1%3E3.0.CO;2-9

Hamilton, W. L., Ying, R., & Leskovec, J. (2017). Inductive representation learning on large graphs. Advances in Neural Information Processing Systems, 30. https://arxiv.org/abs/1706.02216

Strom, B. E., Applebaum, A., Miller, D. P., Nickels, K. C., Pennington, A. G., & Thomas, C. B. (2020). MITRE ATT&CK: Design and philosophy. The MITRE Corporation. https://www.mitre.org/news-insights/publication/mitre-attck-design-and-philosophy

