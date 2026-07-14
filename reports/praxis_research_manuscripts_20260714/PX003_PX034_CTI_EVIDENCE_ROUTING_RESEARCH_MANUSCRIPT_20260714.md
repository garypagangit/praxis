# Retrieval-Conditioned CTI Compliance with Source-Conflict Routing

Research manuscript draft

Praxis IDs: PX-003 and PX-034

Generated: 2026-07-14

Status: Defense-ready positive

## Abstract

Large language models can answer cyber threat intelligence questions, but model-only responses risk unsupported recall, brittle compliance, and hallucinated reasoning. This paper evaluates whether per-question MITRE ATT&CK relationship evidence improves strict CTI multiple-choice answer compliance and whether a source-conflict router can identify high-confidence evidence cases. On a locked 106-row decisive evidence-addressable slice, relationship-conditioned prompting improved accuracy from 0.642 to 0.915 for Llama-3.1-8B-Instruct, from 0.547 to 0.887 for Llama-3.2-3B-Instruct, and from 0.623 to 0.906 for Qwen2.5-7B-Instruct. Qwen ablations showed relationship evidence beating technique-only evidence, broad seeding, empty evidence, random facts, and vanilla prompting. PX-034 added a source-conflict taxonomy over 500 rows. A full-bucket downstream audit showed relationship evidence improved accuracy from 0.6140 to 0.8220 across all rows, while also narrowing the router claim: the router is evidence-risk stratification, not a hard answerability oracle.

## 1. Introduction

Cyber threat intelligence work often involves answering questions that depend on structured knowledge of adversary behavior. LLMs may possess parametric knowledge about common CTI concepts, but CTI answer quality requires source grounding, provenance, and strict output compliance. PX-003/PX-034 studies a constrained version of this problem: multiple-choice CTI questions whose answer options can be connected to ATT&CK relationship evidence.

The central hypothesis is that per-question relationship evidence improves answer compliance over vanilla prompting and broad seeding. The second hypothesis is that a source-conflict router can identify when evidence is decisive enough for direct answering and when review or abstention is safer.

## 2. Prior Work

MITRE ATT&CK provides the structured source layer. Its group, technique, and relationship records provide a defensible evidence substrate for CTI tasks.

Retrieval-augmented generation motivates conditioning model answers on external evidence rather than relying on parametric memory alone. Lewis et al. showed that combining model parameters with non-parametric retrieval can improve knowledge-intensive tasks and provide an updateable evidence channel.

CTIBench motivates CTI-specific evaluation. Alam et al. argue that general LLM benchmarks do not sufficiently measure applied CTI capability, and they include tasks such as CTI knowledge, ATT&CK technique extraction, and threat actor attribution. PX-003 is narrower than CTIBench: it isolates strict multiple-choice compliance under controlled evidence conditions.

Factuality evaluation work such as FActScore motivates decomposing model output into supportable claims. PX-003 does not use atomic-fact scoring directly, but it inherits the principle that factual answers should be evaluated against reliable evidence rather than judged by fluency.

## 3. Experimental Design Influences

RAG literature shaped the primary intervention: each CTI question receives retrieved ATT&CK relationship evidence rather than broad background context.

ATT&CK's structured design shaped the evidence source. The experiment uses relationship-level evidence because it is more precise than technique names alone.

CTIBench influenced the task framing. The evaluation is cyber-specific, answerable, and measured with strict compliance rather than open-ended narrative grading.

Factuality evaluation influenced the source-conflict router. PX-034 does not merely ask whether an answer sounds plausible; it classifies support patterns into decisive, conflicting high-support, ambiguous multi-source, weak single-source, and unsupported buckets.

## 4. Research Questions

RQ1: Does relationship-conditioned ATT&CK evidence improve strict CTI-MCQ compliance over vanilla prompting?

RQ2: Does the effect replicate across model families?

RQ3: Does relationship evidence outperform weaker controls such as technique-only evidence, broad seeding, empty evidence, and random facts?

RQ4: Can a source-conflict router provide useful evidence-risk stratification?

## 5. Data and Methods

The primary PX-003 evaluation uses a locked 106-row decisive evidence-addressable CTI-MCQ slice. The model must output strict `Answer: <A|B|C|D>` responses. Conditions include vanilla prompting, relationship evidence, technique-only evidence, random facts, empty evidence, and broad seeding.

PX-034 expands analysis to a 500-row source-conflict table. Rows are routed into evidence-support buckets before downstream answer evaluation. The full-bucket Qwen audit tests whether relationship evidence helps beyond the decisive slice.

## 6. Results

Cross-model decisive-slice results:

| Model | Vanilla accuracy | Relationship-evidence accuracy | Delta |
|---|---:|---:|---:|
| Llama-3.1-8B-Instruct | 0.642 | 0.915 | +0.274 |
| Llama-3.2-3B-Instruct | 0.547 | 0.887 | +0.340 |
| Qwen2.5-7B-Instruct | 0.623 | 0.906 | +0.283 |

Qwen2.5-7B ablation results:

| Condition | Accuracy |
|---|---:|
| Relationship evidence | 0.906 |
| Technique-only evidence | 0.726 |
| Broad seed | 0.660 |
| Vanilla | 0.623 |
| Empty evidence | 0.594 |
| Random facts | 0.462 |

Source-conflict buckets:

| Bucket | Rows |
|---|---:|
| Decisive | 106 |
| Conflicting high-support | 179 |
| Ambiguous multi-source | 28 |
| Weak single-source | 37 |
| Unsupported | 150 |

Full-bucket downstream Qwen audit:

| Bucket | Vanilla accuracy | Relationship-evidence accuracy | Delta |
|---|---:|---:|---:|
| Ambiguous multi-source | 0.5357 | 0.7143 | +0.1786 |
| Conflicting high-support | 0.5307 | 0.8101 | +0.2793 |
| Decisive | 0.6226 | 0.9057 | +0.2830 |
| Unsupported | 0.6933 | 0.7733 | +0.0800 |
| Weak single-source | 0.7297 | 0.9189 | +0.1892 |
| Full 500-row table | 0.6140 | 0.8220 | +0.2080 |

## 7. Discussion

PX-003 supports a strong retrieval-conditioned CTI compliance claim. Relationship evidence improves accuracy across three model settings and beats multiple evidence controls. The Qwen replication is especially important because it shows the effect is not Llama-only.

PX-034 is useful but narrower than originally hoped. It identifies high-confidence decisive rows and organizes source-support risk, but the full-bucket audit shows that non-decisive buckets can still answer well when forced to choose. Therefore, the router should be described as risk stratification and review routing, not as proof that non-decisive rows are unanswerable.

## 8. Threats to Validity

The task uses multiple-choice questions, not open-ended analyst reports. The evidence source is ATT&CK relationship data, so the result depends on the quality and coverage of ATT&CK curation. The router buckets are useful for evidence characterization, but downstream answerability is model- and prompt-dependent. Finally, relationship evidence helps most when the evidence is relevant and correctly joined to the question.

## 9. Conclusion

PX-003/PX-034 demonstrates that per-question ATT&CK relationship evidence can substantially improve strict CTI answer compliance. The best defended claim is not that the model understands CTI generally; it is that relationship-grounded retrieval produces measurable gains and that source-conflict routing provides a conservative evidence-risk layer.

## Repository Artifacts

- `reports/relationship_evidence_cti_compliance/PX003_QWEN25_7B_DEFENSE_REPLICATION_20260630.md`
- `reports/relationship_evidence_cti_compliance/PX034_CTI_SOURCE_CONFLICT_GATE_20260630.md`
- `reports/relationship_evidence_cti_compliance/full_bucket_downstream_qwen_20260705/PX003_PX034_FULL_BUCKET_DOWNSTREAM_ACCURACY_AUDIT.md`
- `reports/relationship_evidence_cti_compliance/PRAXIS07_RESULT_SYNTHESIS_20260517.md`
- `scripts/build_sec_lord_relationship_evidence_gate.py`
- `scripts/analyze_cti_source_conflict_gate.py`
- `scripts/analyze_cti_bucket_downstream_accuracy.py`
- `cloud_jobs/sec_lord_relationship_evidence_20260517/run_sec_lord_relationship_evidence_cloud.py`

## References

Alam, M. T., Bhusal, D., Nguyen, L., & Rastogi, N. (2024). CTIBench: A benchmark for evaluating LLMs in cyber threat intelligence. arXiv. https://arxiv.org/abs/2406.07599

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Kuttler, H., Lewis, M., Yih, W., Rocktaschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. Advances in Neural Information Processing Systems, 33. https://arxiv.org/abs/2005.11401

Min, S., Krishna, K., Lyu, X., Lewis, M., Yih, W., Koh, P. W., Iyyer, M., Zettlemoyer, L., & Hajishirzi, H. (2023). FActScore: Fine-grained atomic evaluation of factual precision in long form text generation. Proceedings of EMNLP 2023. https://aclanthology.org/2023.emnlp-main.741/

Qwen Team. (2024). Qwen2.5 technical report. arXiv. https://arxiv.org/abs/2412.15115

Strom, B. E., Applebaum, A., Miller, D. P., Nickels, K. C., Pennington, A. G., & Thomas, C. B. (2020). MITRE ATT&CK: Design and philosophy. The MITRE Corporation. https://www.mitre.org/news-insights/publication/mitre-attck-design-and-philosophy

