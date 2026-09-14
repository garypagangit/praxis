# PX-003/PX-034 all-2,500 CTI-MCQ preregistration

Frozen: **2026-07-31T13:36:32Z, before any outcome from the 500-row confirmatory run was inspected**

Status: **FROZEN — DO NOT RETUNE FROM THE 500-ROW OR ALL-2,500 OUTCOMES**

## Question

Does ATT&CK relationship evidence improve strict multiple-choice accuracy across the complete published 2,500-row CTIBench CTI-MCQ artifact, and does the result survive (a) evidence-form ablations, (b) a second model family, (c) current ATT&CK 19.1, and (d) a non-oracle query-only retrieval test?

The study keeps two claims separate:

1. **Source-known verification upper bound.** Retrieval begins from the source technique encoded in the benchmark URL. It is label-free but oracle-provenance-assisted and is not deployable retrieval.
2. **Query-only retrieval.** Retrieval reads only the question and all four displayed answer options. It does not read the answer label, source URL, or source technique.

## Published dataset and fixed strata

- Published artifact: all `2,500` CTIBench CTI-MCQ rows from the authors' [public AI4Sec/cti-bench release](https://huggingface.co/datasets/AI4Sec/cti-bench), local parquet SHA-256 `42f8cb0c1d804945cbdcf890411ca6ede3a1e0222fb91966804fed7dc1a19acb`.
- `attack_technique_eligible`: `1,578` rows whose published source URL points to an ATT&CK technique.
- `non_attack_domain_mismatch`: `922` rows whose source is not an ATT&CK technique (`543` use a CWE domain; `379` use other source families).
- Source-pointer evidence is available for `1,550/1,578` ATT&CK-eligible rows (`98.23%`); the 28 no-evidence eligible rows remain in the intention-to-treat stratum. As designed, none of the 922 mismatch rows has an ATT&CK source pointer.
- Strata are fixed from the published source URL before inference and are independent of the answer label and model output.
- The earlier 500-row table is exactly 20% of CTI-MCQ. It is a pilot/fixed-table confirmation and will never be described as the full dataset.

The CTIBench paper states: “Our final dataset consists of 2500 questions, out of which, 1578 questions are collected from MITRE.” This directly confirms both the full row count and the ATT&CK-eligible stratum. [Primary paper](https://openreview.net/pdf?id=iJAOpsXo2I)

No-kidding discrepancy note: the same paragraph prints source-family subtotals `1,578 + 750 + 40 + 32`, which sum to `2,400`, not `2,500`. We therefore do **not** use those prose subtotals for finer stratification. The preregistered binary strata come from an executable audit of all 2,500 released row URLs and reconcile exactly: `1,578 + 922 = 2,500`.

## Frozen knowledge source and prompt inputs

- Combined Enterprise, Mobile, and ICS ATT&CK 19.1 STIX bundle SHA-256: `bca81a8d69218ace1f7b5c706c605d22ad77d64425375b3d7804fdaf87c2ded9`.
- Source-pointer all-six-condition prompt table SHA-256: `c52550f1a7c690ffdd7700bfb46a6a8f7cef48cb4f22edac7b2cc21ac0627d12`.
- Query-only vanilla/relationship prompt table SHA-256: `75d87d944cc2bcbe623ba3248a55a7c7e859111b08a52a7f06d42223f7f594c8`.
- Source-pointer builder SHA-256: `5a825420ec6d30af986e1282626ac0101c42ab2c3f753b2e6d1ccaaaac3d6754`.
- Query-only builder SHA-256: `658e60eb38a661c07a6e0bbcc248f5fbb510547d69b7c909fbd0966c00b372db`.
- Inference runner SHA-256: `cd94f3da527c0e35ce2c408b2d03865d62cb195c608656eb11a08ccc187178f9`.

MITRE describes the source as: “ATT&CK is knowledge base of adversarial techniques based on real-world observations.” This supports the behavioral knowledge-source choice; it does not predict a model-accuracy gain. [MITRE ATT&CK](https://attack.mitre.org/resources/)

## Models and inference

| Model | Immutable revision |
|---|---|
| `Qwen/Qwen2.5-7B-Instruct` | `a09a35458c702b33eeacc393d103063234e8bc28` |
| `meta-llama/Llama-3.1-8B-Instruct` | `0e9e39f249a16976918f6564b8830bc894c89659` |

- Greedy decoding (`do_sample=False`), float16, maximum 4,096 input tokens, maximum 8 new tokens, batch size 2.
- Strict output parser accepts exactly `A`, `B`, `C`, or `D`; invalid outputs are failures and remain in every denominator.
- Each inference shard uses the same pinned runner, inputs, model revision, parser, and decoding settings. Sharding changes scheduling only.

## Registered conditions

For both models, the source-pointer table runs every condition over all 2,500 rows:

- `vanilla`
- `relationship_evidence`
- `technique_only_evidence`
- `random_facts`
- `empty_evidence`
- `broad_seed`

For both models, the query-only table runs `vanilla` and `relationship_evidence` over all 2,500 rows.

The source-pointer mechanism is interpretable only in the 1,578 ATT&CK-technique-eligible rows. All 2,500 are still run as a fixed intention-to-treat stress test; the 922 mismatch rows cannot be silently removed or used to imply that source pointers exist outside ATT&CK.

## Leakage and version checks

- Query-only construction is rerun after permuting every `expected_output`; the prompt hash must remain unchanged for every row.
- The exact candidate index was regression-tested against the original exhaustive 500-row builder and produced the identical byte-level prompt SHA-256 `2d3cbb0d5f76d26a7f81477ae42d13983edde6d128799288d7004900a2824e81`.
- The answer label is not a retrieval input.
- Source-technique top-1/top-6 recovery and verbatim correct-option phrase presence are mandatory diagnostics, not hidden successes.
- Frozen query-only diagnostics: in the 1,578 ATT&CK-eligible rows, source-technique recovery is `813/1,578` top-1 and `1,105/1,578` top-6, while the correct displayed option phrase appears verbatim in retrieved evidence for `785/1,578`. In the 922 mismatch rows, correct-option phrase presence is `94/922`. All of these are disclosure diagnostics; none is a retrieval input.
- Exact model revisions, STIX version/hash, prompt hashes, runner hash, package freeze, GPU type/driver, and every shard command are retained.
- Duplicate or missing `(id, condition)` pairs stop analysis until corrected without changing the protocol.

## Estimands and statistics

- Condition accuracy with 95% Wilson intervals.
- Row-paired accuracy differences with deterministic 20,000-replicate paired-bootstrap 95% intervals.
- Two-sided exact McNemar tests.
- Holm adjustment over the five source-pointer treatment/control contrasts within each model.
- Holm adjustment across the two models for the query-only primary contrast.
- Results are reported for the complete 2,500-row intention-to-treat table and separately for both fixed strata.

## Frozen decision rules

### Gate A — source-known main effect, ATT&CK-eligible stratum

For **each model**, relationship evidence versus vanilla must have delta at least `+0.05`, paired 95% interval lower bound above zero, and Holm-adjusted exact McNemar `p < .05`.

### Gate B — relationship specificity, ATT&CK-eligible stratum

For **each model**, relationship evidence versus technique-only must have delta at least `+0.03`, paired 95% interval lower bound above zero, and Holm-adjusted exact McNemar `p < .05`. If Gate A passes and Gate B fails, the allowable claim is retrieval-conditioned/source-known verification, not relationship-specific causality.

### Gate C — negative controls, ATT&CK-eligible stratum

For each model, relationship evidence must have a paired interval lower bound above zero versus random facts, empty evidence, and broad seed. Every negative-control failure is reported.

### Gate D — query-only deployability, ATT&CK-eligible stratum

For **each model**, query-only relationship evidence versus vanilla must have delta at least `+0.03`, paired 95% interval lower bound above zero, and the Holm-adjusted exact McNemar test across the two model tests must have `p < .05`.

### Gate E — non-ATT&CK mismatch safety

For each model on the 922-row mismatch stratum, the paired 95% interval lower bound for query-only relationship evidence minus vanilla must be greater than `-0.05`. This is a non-inferiority safety gate, not evidence that ATT&CK retrieval helps non-ATT&CK questions.

### Invalid-output safety

Relationship-evidence invalid rate may not exceed vanilla by more than `0.03` absolute in either stratum.

No universal full-dataset claim is allowed merely because the pooled 2,500-row effect is positive. The mechanism claim follows the prespecified stratum gates.

## Literature relationship and exact titles

| Exact publication title | What it supports | What remains for this experiment |
|---|---|---|
| **CTIBench: A Benchmark for Evaluating LLMs in Cyber Threat Intelligence** | Direct provenance for CTI-MCQ, its 2,500 rows, and its source-family composition. | It did not test this evidence treatment or ablation family. |
| **MITRE ATT&CK: Design and Philosophy** | ATT&CK is a curated, maintained behavioral knowledge source. | It did not claim prompt injection of ATT&CK facts improves LLM accuracy. |
| **Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks** | General foundation for conditioning a generator on retrieved non-parametric memory. The paper describes RAG as models “which combine pre-trained parametric and non-parametric memory for language generation.” | It is not CTI-specific and does not establish the present effect. |
| **TechniqueRAG: Retrieval Augmented Generation for Adversarial Technique Annotation in Cyber Threat Intelligence Text** | Closest peer-reviewed CTI retrieval precedent; it combines retrievers, reranking, and generation for ATT&CK annotation. | The present study tests strict CTI-MCQ answering, source-known versus query-only provenance, and six evidence-form controls. |

TechniqueRAG reports: “Experiments on multiple security benchmarks demonstrate that TechniqueRAG achieves state-of-the-art performance.” This justifies CTI retrieval as a serious empirical direction, but it is not proof of the PX-003/PX-034 result. [ACL Anthology](https://aclanthology.org/2025.findings-acl.1076/)

## Verified APA references

Alam, M. T., Bhusal, D., Nguyen, L., & Rastogi, N. (2024). CTIBench: A benchmark for evaluating LLMs in cyber threat intelligence. *Advances in Neural Information Processing Systems, 37*, 50805–50825. https://doi.org/10.52202/079017-1607. [NeurIPS proceedings record](https://proceedings.neurips.cc/paper_files/paper/2024/hash/5acd3c628aa1819fbf07c39ef73e7285-Abstract-Datasets_and_Benchmarks_Track.html)

Lekssays, A., Shukla, U., Sencar, H. T., & Parvez, M. R. (2025). TechniqueRAG: Retrieval augmented generation for adversarial technique annotation in cyber threat intelligence text. In *Findings of the Association for Computational Linguistics: ACL 2025* (pp. 20913–20926). Association for Computational Linguistics. https://doi.org/10.18653/v1/2025.findings-acl.1076

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. In *Advances in Neural Information Processing Systems* (Vol. 33). https://proceedings.neurips.cc/paper/2020/hash/6b493230-Abstract.html

Strom, B. E., Applebaum, A., Miller, D. P., Nickels, K. C., Pennington, A. G., & Thomas, C. B. (2020). *MITRE ATT&CK: Design and philosophy* (MP180360R1). The MITRE Corporation. https://www.mitre.org/news-insights/publication/mitre-attck-design-and-philosophy

## Stop and reporting rules

- No prompt, threshold, evidence count, retrieval rule, parser, model, stratum, or decision threshold changes after freeze.
- A technical failure may be retried unchanged and must remain in the execution ledger.
- All failed gates and all 922 mismatch rows remain visible in the final Praxis report.
- The source-pointer cell is always labeled an oracle-provenance/source-known upper bound.
- The final novelty claim cannot be “first CTI RAG.” The defensible contribution is a preregistered paired mechanism ablation that separates source-known verification, query-only retrieval, versioned evidence, mismatch safety, and model-family replication.
