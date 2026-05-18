# Praxis 07 Concept: Relationship-Evidence Retrieval For CTI Task Compliance

Generated: 2026-05-17

Status: **defensible narrow positive; mechanism bounded by ablation**

Branch: `experiment/relationship-evidence-cti-compliance`

## Working Title

**Praxis 07: Retrieval-Conditioned CTI Compliance**

Short title: **Retrieval-Conditioned CTI Compliance**

## Thesis

Cyber threat intelligence questions often require answer-bearing ATT&CK facts that are not reliably supplied by a broad CTI role prompt. Retrieval-conditioned ATT&CK evidence improves strict CTI-MCQ compliance without changing model weights. Relationship-level evidence is the strongest tested evidence form, but the final mechanism claim must be bounded because technique-only evidence also improves over vanilla prompting.

## Problem Statement

LLMs are attractive for CTI workflows because analysts need fast answers over large, evolving knowledge bases. The practical failure mode is not only hallucination. It is also incomplete grounding: a model may know the technique name but fail when the answer depends on a mitigation, detection, data-source, or adversary-procedure relation.

The old SEC-LoRD prompt-seeding route exposed this clearly. Broad domain seeding made strict CTI-MCQ compliance worse rather than better. The revised idea is narrower and more defensible:

> Can a frozen LLM answer CTI questions more reliably when the prompt includes question-ranked ATT&CK relationship evidence instead of broad cyber seed text?

## Literature Grounding

| Anchor | Why it matters here |
|---|---|
| Strom et al. (2020), MITRE ATT&CK design philosophy | ATT&CK is an empirically grounded knowledge base for adversary behavior and is widely used across threat intelligence, detection, threat hunting, red teaming, and risk management. |
| MITRE ATT&CK data model relationship types | ATT&CK encodes groups, software, techniques, mitigations, procedures, and detections through explicit STIX relationships, which makes relationship-level retrieval a natural CTI evidence unit. |
| Lewis et al. (2020), retrieval-augmented generation | RAG motivates adding external non-parametric knowledge for knowledge-intensive tasks where parametric memory alone is limited and provenance matters. |
| Alam et al. (2024), CTIBench | CTI-specific LLM evaluation is needed because general benchmarks do not capture practical cyber threat intelligence task behavior. |
| Carlini et al. (2021), training-data extraction | This anchors the boundary: extraction/memorization is a different question from retrieval-conditioned CTI task compliance and should not be claimed here. |

## Claim Boundary

This experiment **does claim**:

- Question-specific ATT&CK retrieval materially improves strict CTI-MCQ answer compliance on a locked, no-label evidence-addressable slice.
- The effect replicates across Llama-3.1-8B and Llama-3.2-3B instruction-tuned models.
- Broad CTI role seeding is not enough; it does not reproduce the relationship-evidence lift.
- Relationship evidence is the best tested condition and beats technique-only evidence in the 8B ablation.

This experiment **does not claim**:

- SEC-LoRD or DS-LoRD extraction works.
- The model is extracting training data.
- The method solves open-ended CTI analysis or campaign attribution.
- The 106-row slice is the whole CTIBench distribution.
- Relationship evidence is the only causal mechanism; technique-only evidence also helps.

## Current Positive Evidence

Primary run: `reports/sec_lord_ds_lord/SEC_LORD_RELATIONSHIP_EVIDENCE_MODEL_GATE_20260517.md`

| Condition | Strict accuracy | Correct | Rows | Invalid |
|---|---:|---:|---:|---:|
| Vanilla strict prompt | `0.642` | `68` | `106` | `0` |
| Relationship-evidence prompt | `0.915` | `97` | `106` | `0` |
| Broad-seed negative control | `0.642` | `68` | `106` | `1` |

Primary delta: `+0.274` relationship evidence over vanilla.

Paired comparison: `33` evidence-only wins vs `4` vanilla-only wins.

Model: `meta-llama/Llama-3.1-8B-Instruct`

ATT&CK snapshot: `enterprise-attack-12.0`

Slice: `106` no-label evidence-addressable CTI-MCQ rows selected from the retrieval support audit, not by model outcomes.

Follow-on gates completed on 2026-05-17:

| Gate | Result | Decision |
|---|---|---|
| Slice audit | Complement vanilla `230/394 = 0.584`; A1/A3/A4 pass | **SOFT PASS**, report adjusted baseline/lift |
| 3B cross-model | Vanilla `0.547`, relationship `0.887`, broad seed `0.575` | **PASS**, effect replicates across Llama instruct capacities |
| 8B ablation | Vanilla `0.642`, relationship `0.915`, technique-only `0.764`, random `0.566`, empty `0.670` | **MIXED**, main effect robust but mechanism unclear |

## Core Research Questions

| ID | Question | Current status |
|---|---|---|
| RQ1 | Does relationship evidence improve strict CTI-MCQ answer compliance over vanilla prompting? | Passed in first cloud GPU gate. |
| RQ2 | Does relationship evidence outperform broad CTI seed prompting? | Passed in first cloud GPU gate. |
| RQ3 | Are gains driven by relationship evidence rather than label leakage? | Slice audit soft pass: no-label/determinism checks pass; complement slice is somewhat harder. |
| RQ4 | Is the relationship neighborhood better than technique-only retrieval? | Yes on 8B (`0.915` vs `0.764`), but technique-only also helps, so mechanism is mixed. |
| RQ5 | Does the effect replicate across another model or a wider evidence-addressable slice? | Replicates on Llama-3.2-3B (`+0.340` over vanilla). |

## Strong Defensible Experiment Shape

The Praxis-ready version should be reframed away from SEC-LoRD extraction and toward retrieval-conditioned CTI compliance:

1. Freeze a CTI-MCQ benchmark slice and an ATT&CK snapshot.
2. Build prompts from three conditions: vanilla, broad seed, and relationship evidence.
3. Add an ablation condition: technique-only evidence.
4. Score strict `Answer: <A|B|C|D>` compliance with invalid-rate accounting.
5. Report paired wins, not just aggregate accuracy.
6. Run one replication model or slice before making the thesis claim final.

## Proposed Contribution

This contribution is small but real: it shows that strict CTI-MCQ compliance improves when prompts include question-specific ATT&CK evidence instead of only broad cyber seed text. Relationship evidence is strongest, but the ablation requires conservative wording: the result is retrieval-conditioned CTI compliance, not proof that relationship facts alone cause the full lift.

## Recommended Next Step

Package the result as a bounded Praxis 07 paper/chapter section using `reports/relationship_evidence_cti_compliance/PRAXIS07_RESULT_SYNTHESIS_20260517.md`. Do not run more rescue gates unless they are pre-registered external-validity or reviewer-requested robustness checks.

## References

- Strom, B. E., Applebaum, A., Miller, D. P., Nickels, K. C., Pennington, A. G., & Thomas, C. B. (2020). *MITRE ATT&CK: Design and Philosophy*. MITRE. https://www.mitre.org/news-insights/publication/mitre-attck-design-and-philosophy
- MITRE ATT&CK Data Model. *Relationship Types*. https://mitre-attack.github.io/attack-data-model/schemas/relationship-types/
- Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Kuttler, H., Lewis, M., Yih, W., Rocktaschel, T., Riedel, S., & Kiela, D. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS. https://arxiv.org/abs/2005.11401
- Alam, M. T., Bhusal, D., Nguyen, L., & Rastogi, N. (2024). *CTIBench: A Benchmark for Evaluating LLMs in Cyber Threat Intelligence*. https://arxiv.org/abs/2406.07599
- Carlini, N., Tramer, F., Wallace, E., Jagielski, M., Herbert-Voss, A., Lee, K., Roberts, A., Brown, T., Song, D., Erlingsson, U., Oprea, A., & Raffel, C. (2021). *Extracting Training Data from Large Language Models*. USENIX Security. https://www.usenix.org/conference/usenixsecurity21/presentation/carlini-extracting
