# CTI: closest-prior comparison

Primary sources checked September 17, 2026. This is a targeted contribution review, not an exhaustive novelty certification. The manuscript and experiment are complete within their stated scope; author and advisor originality judgment remains pending.

## Closest comparisons

| Primary source and exact locator | Established work that overlaps | Present study's bounded distinction | Consequence |
|---|---|---|---|
| [TechniqueRAG, ACL 2025](https://aclanthology.org/2025.findings-acl.1076.pdf), Sections 3.1–3.4, printed pp. 20915–20917 | Technique annotation uses retrieved examples, LLM reranking, and generator fine-tuning. | Fixed-model multiple-choice answering separates published-source access from question-and-options access, with explicit mismatch gates. | CTI retrieval is established. Task and design differences support a narrow empirical comparison; no head-to-head performance claim is available. |
| [Beyond RAG for CTI, v1](https://arxiv.org/html/2604.11419v1), Section 4.1.2 and Tables 11–14; Section 4.2 | Four retrieval architectures exhibit question-type-dependent benefit and harm, with hallucination and abstention analysis. | The present treatment uses deterministic evidence selection, paired option-label outcomes, source compatibility strata, and a failed external source-router test. | Generic “retrieval helps and hurts” and graph-grounding contributions overlap directly. The specific access-controlled experiment must supply any additional knowledge. |
| [Evidence-Grounded Retrieval / Ahlert, v1](https://arxiv.org/html/2609.08790v1), Sections II-A–II-D and Table I; submitted September 8, 2026 | Hybrid semantic/graph/entity retrieval preserves provenance and grounds hunt leads in a defender's environment. | The current study measures fixed-choice answer changes under source access and mismatch; it does not generate or validate hunt leads. | Provenance-aware CTI assistance is established. Do not present the failed router as equivalent to Ahlert's task or as a superior solution. |

These are comparisons of documented tasks and designs, not claims that the other papers prove the present result or test identical interventions. No rival implementation was executed during this closure.

## Foundations and benchmark lineage

- [RAG, Lewis et al. (2020)](https://arxiv.org/abs/2005.11401): external retrieval as generator context is the methodological foundation.
- [CTIBench, Alam et al. (2024), v3](https://arxiv.org/abs/2406.07599v3): supplies the original benchmark; the present work uses its released labels rather than creating a new dataset.
- [AthenaBench, Alam et al. (2025/2026), v2](https://arxiv.org/abs/2511.01144v2): explicitly extends CTIBench. PX-068 is external-item testing within a related benchmark lineage, not independent benchmark-producer replication.

## Contribution proposed for human review

The specific candidate contribution is an auditable paired estimate of how evidence form and source access affect fixed-model CTI answers, combined with a registered mismatch failure and an unsuccessful external applicability intervention. Its value is the concrete evidence and decision boundary. It does not introduce retrieval, source provenance, graph reasoning, or a successful protective router.

The reviewer must decide whether that added empirical information is sufficiently distinct and useful for the intended Praxis. A different dataset, two model families, a significant result, or extensive verification cannot settle that judgment alone. Any required extension must identify the missing practical capability before selecting new models or commissioning experiments.

## Review provenance

The links above were opened through primary publisher/arXiv sources on September 17. TechniqueRAG's full PDF methods, Beyond RAG's results tables, and Ahlert's methods were inspected. No secondary summaries supply the comparison. The exact URLs and reviewed locators also appear in [EVIDENCE.json](EVIDENCE.json). This update does not change the historical experiment protocol or outcomes.
