# CTI: the next three author actions

**Internal AI-assisted checklist and source-navigation aid. Not submitted academic prose.** Start with the completed evidence and the author's own understanding before investing in another router. This checklist adds no experiments, analysis results, literature conclusions or academic approval.

The [CTI development guide](https://github.com/garypagangit/praxis/blob/9240d9c9239a04a2d261faf562ca7f3cb34fc926/final_praxis/cti_development_20260914/INTERNAL_RESEARCH_GUIDE.md) and [evidence index](https://github.com/garypagangit/praxis/blob/9240d9c9239a04a2d261faf562ca7f3cb34fc926/final_praxis/cti_development_20260914/EVIDENCE_INDEX.json) are published on the separate CTI development branch. The [completed paper/evidence package](../papers/20260914/01_cti/README.md) is available in this checkout. Its frozen terminal states are `PASS_SOURCE_KNOWN_ONLY`, `FAIL_ROUTER_CONFIRMATION` for PX068, and no completed scientific result for PX071. See [the exact status record](../papers/20260914/01_cti/evidence/STUDY_STATUS.json).

## 1. Make the closest-prior comparison independently

Read these primary sources and record the author's own comparison notes with page, section or table references:

- [CTIBench paper](https://arxiv.org/abs/2406.07599) and [public dataset](https://huggingface.co/datasets/AI4Sec/cti-bench).
- [Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401).
- [TechniqueRAG](https://aclanthology.org/2025.findings-acl.1076/).
- [Beyond RAG for CTI](https://arxiv.org/abs/2604.11419).
- [AthenaBench paper](https://arxiv.org/abs/2511.01144) and [pinned source repository](https://github.com/Athena-Software-Group/athenabench/tree/39d3a74eaf84b93e21dde0a4b60ddd4f08620eaf).

For each closest prior, answer independently: What practical problem is measured? What information does retrieval receive? What comparison would distinguish the CTI study from ordinary retrieval? Are incompatible-evidence harm and routing failure evaluated? What independent data units and confirmation conditions support the claimed difference?

**Completion artifact:** an author-created comparison table identifying an exact supported contribution and any unresolved overlap. Leave uncertain entries unresolved; do not treat this checklist, a previous AI-written manuscript or a search result as the literature answer. A reproducible result does not automatically establish doctoral originality.

## 2. Understand the evidence and executable outcome

Use the [package reading/reproduction instructions](https://github.com/garypagangit/praxis/blob/cdf59507b588972b9a0f6879daa1184eadcf08e6/final_praxis/papers/20260914/01_cti/README.md) to trace one eligible comparison and one mismatch comparison from saved observations to their reported counts. The [evidence index](https://github.com/garypagangit/praxis/blob/9240d9c9239a04a2d261faf562ca7f3cb34fc926/final_praxis/cti_development_20260914/EVIDENCE_INDEX.json) supplies exact JSON pointers and hashes; [FULL_2500_ANALYSIS.json](../papers/20260914/01_cti/evidence/FULL_2500_ANALYSIS.json) contains both strata and both models.

Inspect these exact implementations:

- [Question-based evidence builder](../papers/20260914/01_cti/frozen/builders/build_px003_query_only_prompts.py): `rank_query_only_evidence`, including the question and all displayed options.
- [Reproduction driver](../papers/20260914/01_cti/reproduce.py): `frozen_parser`, `validate_cti` and `validate_derived`; then follow the extracted parser in the [frozen inference source](../papers/20260914/01_cti/frozen/inference/run_sec_lord_relationship_evidence_cloud.py).
- [Primary gates](../papers/20260914/01_cti/frozen/scripts/analyze_px003_full_2500.py): `evaluate_gates`; [external gates](../papers/20260914/01_cti/frozen/scripts/analyze_px068_source_router.py): `router_gate`, `evaluate_model_gates` and `portfolio_status`.

**Completion artifact:** the author's own explanation of input access, option-parser correctness, invalid-output treatment, question-level pairing and each failed gate, with links to the relevant code. Account for 2,500 question units, including 1,578 eligible and 922 mismatch items, rather than calling 40,000 response records independent samples. Explain the source-known access advantage, prior exposure of 500 items, and the public Athena package's derived-indicator limitation.

The [completed full reproduction receipt](../papers/20260914/01_cti/evidence/reproduced_full/REPRODUCTION_RECEIPT.json) already records regeneration of all 156 intervals. Understanding what it checks is the immediate task; repeating paid inference is unnecessary. Technical PASS does not validate benchmark labels, model reproducibility, novelty or academic eligibility.

## 3. Resolve applied-Praxis fit before a new router experiment

Use the author's independent comparison and code explanation to discuss the completed study's scope with the appropriate advisor or committee. The decision to resolve is whether this bounded empirical contribution satisfies the program's original applied-contribution requirement, or whether a separately qualified process contribution is necessary. See the [official D.Eng. guidance](https://online.engineering.gwu.edu/sites/g/files/zaxdzs5816/files/2025-10/deng-student-guidelinesOct6_2025.pdf) and the guide's section on institutional fit.

Bring the complete outcome, including the [failed external PX068 analysis](../papers/20260914/01_cti/evidence/PX068_ANALYSIS.json) and [terminal audit](../papers/20260914/01_cti/evidence/PX068_TERMINAL_AUDIT.json). Do not describe the router as a successful defense or use unfinished PX071 as confirmation. Any future router would need its own prior-art comparison, qualified output contract, fresh confirmation data, matched controls and frozen criteria; the existing failed data cannot become fresh confirmation by relabeling it.

**Completion artifact:** a record of the actual scope decision and any specific remaining research requirement. No such decision or approval is asserted here. A proposed extension remains unrun; there is no automatic reason to launch it.

The [official doctoral policy page](https://online.engineering.gwu.edu/policies-procedures-doctoral) links the [AI policy](https://gwu.box.com/s/ickb578cz7d75089n2j5c1y9c6gb0z2v). The [existing retrieval record](https://github.com/garypagangit/praxis/blob/9240d9c9239a04a2d261faf562ca7f3cb34fc926/final_praxis/cti_development_20260914/REQUIREMENTS_SOURCES.json) documents its September 14, 2026 review and unspecified effective date. No applicable written exception was located. Preserve AI provenance; human editing alone is not a demonstrated remedy for restrictions on AI-written or AI-edited submitted work. The author must verify any applicable written authorization and follow the rules governing source identification, code assistance and attribution. This aid supplies navigation and preparation questions, not literature answers or submission-ready writing.
