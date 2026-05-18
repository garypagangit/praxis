# Paper Outline: Relationship-Evidence Retrieval For CTI Task Compliance

Generated: 2026-05-17

Status: **outline draft**

## Candidate Title

Relationship-Aware Retrieval Improves Cyber Threat Intelligence Task Compliance

## One-Sentence Claim

On a frozen no-label evidence-addressable CTI-MCQ slice, a frozen Llama-3.1-8B model improves from `0.642` strict accuracy under vanilla prompting to `0.915` when prompted with ATT&CK relationship evidence, while broad CTI seed prompting does not improve over vanilla.

## Abstract Skeleton

Large language models are increasingly used for cyber threat intelligence, but CTI questions often depend on structured relationships between techniques, mitigations, detections, data sources, software, groups, and procedure examples. We test whether retrieving relationship-level evidence from MITRE ATT&CK improves strict CTI question-answering compliance. Using a frozen CTI-MCQ slice and ATT&CK `enterprise-attack-12.0`, we compare vanilla prompting, broad CTI seed prompting, and relationship-evidence prompting on a frozen Llama-3.1-8B model. Relationship evidence improves strict accuracy from `68/106` to `97/106`, with no invalid-rate regression and `33` evidence-only paired wins versus `4` vanilla-only wins. We position the result as retrieval-conditioned CTI task compliance, not training-data extraction, and define ablations needed to separate relationship evidence from simpler technique-only retrieval.

## Paper Structure

1. Introduction

   - CTI workflows need accurate, evidence-grounded answers.
   - Broad cyber role prompting can harm strict compliance.
   - ATT&CK relationship structure is a natural retrieval unit.
   - Main result: relationship evidence yields a large strict-compliance gain.

2. Background

   - MITRE ATT&CK as an empirically grounded CTI knowledge base.
   - ATT&CK STIX relationships: procedures, software usage, mitigations, detections/data sources, subtechniques, tactics.
   - RAG as external knowledge access for knowledge-intensive tasks.
   - CTIBench as CTI-specific LLM evaluation.
   - Boundary from extraction/memorization literature.

3. Problem Formulation

   - Task: multiple-choice CTI answer compliance.
   - Inputs: question, options, optional evidence.
   - Output: exact `Answer: <A|B|C|D>`.
   - Success: strict parsed answer, invalids count as failures.

4. Method

   - ATT&CK snapshot and evidence index.
   - Question-ranked relationship retrieval.
   - Prompt conditions: vanilla, broad seed, relationship evidence.
   - Planned ablation: technique-only evidence.
   - No-label evidence-addressable slice construction.

5. Experimental Design

   - Model: `meta-llama/Llama-3.1-8B-Instruct`.
   - Slice: `106` CTI-MCQ rows.
   - Frozen prompts and decoding.
   - Metrics: strict accuracy, invalid rate, paired wins.
   - Pass/fail gates.

6. Results

   - Main scorecard table.
   - Paired win table.
   - Invalid-rate table.
   - Examples where relationship evidence supplies the answer-bearing field.

7. Ablations And Robustness

   - Technique-only retrieval vs relationship evidence.
   - Diagnostic `130`-row slice.
   - Second model or smaller model replication.
   - Evidence-family dropout: no procedures, no mitigations, no detection/data source evidence.

8. Discussion

   - Why relationship-level evidence helps.
   - Why broad seed prompting fails.
   - How this differs from extraction.
   - What this means for CTI assistants and analyst workflows.

9. Limitations

   - Evidence-addressable slice is not the full benchmark distribution.
   - Multiple-choice compliance is narrower than open-ended analysis.
   - ATT&CK snapshot age matters.
   - Requires structured knowledge base availability.

10. Conclusion

   - Relationship-aware retrieval is a defensible, measurable CTI prompt intervention.
   - The next step is ablation and replication, not an extraction claim.

## Core Tables

| Table | Purpose |
|---|---|
| Table 1 | Literature positioning and claim boundary. |
| Table 2 | Prompt conditions and evidence sources. |
| Table 3 | Main strict scorecard. |
| Table 4 | Paired wins and invalid rates. |
| Table 5 | Ablation/replication results when run. |

## Core Figures

| Figure | Purpose |
|---|---|
| Figure 1 | ATT&CK relationship neighborhood around a technique. |
| Figure 2 | Experimental pipeline: CTI-MCQ row to relationship retrieval to strict answer. |
| Figure 3 | Paired wins: evidence-only vs vanilla-only. |

## Current Result Text

In the first cloud GPU gate, relationship evidence improved strict accuracy by `+0.274` absolute over vanilla prompting. The relationship-evidence condition answered `97/106` rows correctly with zero invalid outputs. Vanilla answered `68/106` rows correctly with zero invalid outputs. The broad-seed negative control answered `68/106` rows correctly and produced one invalid output. Paired scoring showed `33` relationship-evidence-only wins versus `4` vanilla-only wins.

## Strong Claim Version

After the ablation gate passes:

> Relationship-aware retrieval, not broad domain seeding, improves strict CTI answer compliance because CTI questions often ask about relationships encoded in ATT&CK rather than technique descriptions alone.

## Conservative Claim Version

Before the ablation gate:

> A frozen Llama-3.1-8B model substantially improves strict CTI-MCQ compliance on an evidence-addressable slice when prompted with question-ranked ATT&CK relationship evidence.

## Next Writing Work

1. Implement and run technique-only ablation.
2. Add a second-model or diagnostic-slice replication.
3. Convert this outline into a thesis-neutral LaTeX section only after the ablation table exists.
