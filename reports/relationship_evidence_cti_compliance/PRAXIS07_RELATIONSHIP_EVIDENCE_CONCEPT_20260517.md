# Praxis 07 Concept: Relationship-Evidence Retrieval For CTI Task Compliance

Generated: 2026-05-17

Status: **new narrow positive experiment branch opened**

Branch: `experiment/relationship-evidence-cti-compliance`

## Working Title

**Praxis 07: Relationship-Aware Retrieval for Cyber Threat Intelligence Question Answering**

Short title: **Relationship-Evidence CTI Compliance**

## Thesis

Cyber threat intelligence questions often ask for the relationship between an observed ATT&CK technique and a mitigation, data source, detection cue, software family, procedure example, or tactic. A language model prompted only with a broad CTI role or short technique facts can miss the answer-bearing relationship. Retrieval that surfaces ATT&CK relationship evidence should improve strict CTI task compliance without changing model weights.

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

- Relationship-level ATT&CK evidence can materially improve strict CTI-MCQ answer compliance for a frozen Llama-3.1-8B model on a frozen, no-label evidence-addressable slice.
- Broad CTI role seeding is not enough; in the current gate it ties vanilla accuracy and produces an invalid response.
- The useful unit of retrieval is not only a technique description, but the relationship neighborhood around a technique.

This experiment **does not claim**:

- SEC-LoRD or DS-LoRD extraction works.
- The model is extracting training data.
- The method solves open-ended CTI analysis or campaign attribution.
- The 106-row slice is the whole CTIBench distribution.
- The result is final until ablations and at least one replication model/slice are run.

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

## Core Research Questions

| ID | Question | Current status |
|---|---|---|
| RQ1 | Does relationship evidence improve strict CTI-MCQ answer compliance over vanilla prompting? | Passed in first cloud GPU gate. |
| RQ2 | Does relationship evidence outperform broad CTI seed prompting? | Passed in first cloud GPU gate. |
| RQ3 | Are gains driven by relationship evidence rather than label leakage? | Partially controlled by no-label slice construction; needs frozen-script audit in write-up. |
| RQ4 | Is the relationship neighborhood better than technique-only retrieval? | Not yet run; this is the most important ablation. |
| RQ5 | Does the effect replicate across another model or a wider evidence-addressable slice? | Not yet run. |

## Strong Defensible Experiment Shape

The Praxis-ready version should be reframed away from SEC-LoRD extraction and toward retrieval-conditioned CTI compliance:

1. Freeze a CTI-MCQ benchmark slice and an ATT&CK snapshot.
2. Build prompts from three conditions: vanilla, broad seed, and relationship evidence.
3. Add an ablation condition: technique-only evidence.
4. Score strict `Answer: <A|B|C|D>` compliance with invalid-rate accounting.
5. Report paired wins, not just aggregate accuracy.
6. Run one replication model or slice before making the thesis claim final.

## Proposed Contribution

This contribution is small but real: it shows that CTI retrieval quality depends on matching the structure of CTI questions. When questions ask about mitigations, detections, procedures, software, or data sources, a technique-name-only retrieval unit is underpowered. The ATT&CK relationship graph gives a better evidence unit and produces a large strict-compliance gain in the first frozen model gate.

## Recommended Next Step

Run a targeted ablation/replication gate:

- Vanilla strict prompt.
- Broad-seed negative control.
- Technique-only retrieval.
- Relationship-evidence retrieval.

Pass threshold for promotion to paper claim:

- Relationship evidence beats vanilla by `>= +0.030`.
- Relationship evidence beats technique-only retrieval by `>= +0.030`.
- Invalid rate is no worse than vanilla.
- Evidence-only paired wins exceed vanilla-only wins.
- The result holds on one additional model or on the diagnostic `130`-row evidence-addressable slice.

## References

- Strom, B. E., Applebaum, A., Miller, D. P., Nickels, K. C., Pennington, A. G., & Thomas, C. B. (2020). *MITRE ATT&CK: Design and Philosophy*. MITRE. https://www.mitre.org/news-insights/publication/mitre-attck-design-and-philosophy
- MITRE ATT&CK Data Model. *Relationship Types*. https://mitre-attack.github.io/attack-data-model/schemas/relationship-types/
- Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Kuttler, H., Lewis, M., Yih, W., Rocktaschel, T., Riedel, S., & Kiela, D. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS. https://arxiv.org/abs/2005.11401
- Alam, M. T., Bhusal, D., Nguyen, L., & Rastogi, N. (2024). *CTIBench: A Benchmark for Evaluating LLMs in Cyber Threat Intelligence*. https://arxiv.org/abs/2406.07599
- Carlini, N., Tramer, F., Wallace, E., Jagielski, M., Herbert-Voss, A., Lee, K., Roberts, A., Brown, T., Song, D., Erlingsson, U., Oprea, A., & Raffel, C. (2021). *Extracting Training Data from Large Language Models*. USENIX Security. https://www.usenix.org/conference/usenixsecurity21/presentation/carlini-extracting
