# Praxis 07 Result Synthesis

Generated: 2026-05-17

Status: **DEFENSIBLE NARROW POSITIVE**

## Thesis

Retrieval-conditioned ATT&CK evidence improves strict CTI multiple-choice task compliance on a locked, label-free evidence-addressable CTI-MCQ slice. Relationship-level evidence is the strongest tested evidence form, but the mechanism is not pure relationship causality because technique-only evidence also improves performance.

## Problem Statement

LLM-based CTI systems often receive broad cyber-security prompts or broad domain seed text, but broad seeding can hurt strict task compliance and does not guarantee that the model grounds its answer in the specific ATT&CK facts needed for a question. Praxis 07 tests whether per-question ATT&CK evidence retrieval improves strict answer compliance under a parser that accepts only `Answer: <A|B|C|D>`.

## Locked Evaluation Unit

- Benchmark: CTIBench CTI-MCQ scaffold
- Retrieval corpus: MITRE ATT&CK `enterprise-attack-12.0`
- Slice: `106` evidence-addressable rows selected by a label-free relationship-support criterion
- Slice ID hash: `3bd1a6a809abf95063860b60e288bac2248ab655da55f79b0cdbc91671601091`
- Complement rows: `394`
- Parser: strict one-line answer parser; invalids are counted, not dropped

## Result Chain

| Gate | Result | Decision |
|---|---|---|
| Old broad-seed SEC-LoRD audit | Negative: 3B vanilla `0.276` vs seed `0.090`; 8B vanilla `0.466` vs seed `0.284` | Do not claim broad prompt seeding works |
| 8B relationship-evidence model gate | PASS: vanilla `0.642`, relationship `0.915`, broad seed `0.642`; lift `+0.274` | New narrow positive |
| Slice audit | SOFT PASS: A1/A3/A4 pass; complement vanilla `0.584` | Report adjusted baseline/lift |
| 3B cross-model gate | PASS: vanilla `0.547`, relationship `0.887`, broad seed `0.575`; lift `+0.340` | Effect replicates within Llama instruct family |
| 8B ablation | MIXED: relationship `0.915`, technique-only `0.764`, random `0.566`, empty `0.670`, vanilla `0.642` | Main effect robust; mechanism unclear |

## Claim Boundary

Strong claim:

- On a locked evidence-addressable CTI-MCQ slice, per-question ATT&CK retrieval substantially improves strict multiple-choice compliance over vanilla prompting and broad seed prompting.

Careful mechanism claim:

- Relationship-level evidence is the best tested retrieval condition and outperforms technique-only evidence by `+0.151` at 8B.

Required caveat:

- Technique-only evidence also improves over vanilla by `+0.123`, so the evidence does not support a pure "relationships alone" mechanism.

Do not claim:

- SEC-LoRD/DS-LoRD extraction success.
- Open-ended CTI reasoning improvement.
- General benchmark-wide improvement without the evidence-addressable slice boundary.
- Label-dependent prompt construction.

## Literature Anchors

- MITRE ATT&CK design philosophy: ATT&CK represents adversary behavior as structured techniques and related operational knowledge.
- MITRE ATT&CK STIX relationship model: evidence is not only technique names; it includes relationships to mitigations, detections, data sources, procedures, tactics, and groups.
- Retrieval-augmented generation: question-specific evidence can ground model outputs better than broad parametric recall.
- CTIBench: CTI-MCQ provides a strict task-compliance setting where answer parsing and invalid responses matter.
- LLM extraction boundary: this is not an extraction experiment; it is a retrieval-conditioned compliance experiment.

## Recommended Paper Shape

Title:

> Retrieval-Conditioned CTI Compliance: A Protocol-Specific Result

Core contribution:

1. A label-free evidence-addressable CTI-MCQ slice construction protocol over ATT&CK relationship support.
2. A strict parser evaluation showing large gains over vanilla and broad seed prompting at 8B and 3B.
3. A slice audit showing the result is usable with adjusted baseline reporting.
4. An ablation showing relationship evidence is strongest, but the safest mechanism claim is retrieval-conditioned evidence rather than relationship causality alone.

## Next Action

Convert this into the Praxis 07 paper/chapter section. Do not run more rescue gates unless the next gate is a pre-registered external replication or reviewer-requested robustness check.
