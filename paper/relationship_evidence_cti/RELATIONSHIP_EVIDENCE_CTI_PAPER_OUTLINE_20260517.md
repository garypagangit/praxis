# Paper Outline: Retrieval-Conditioned CTI Compliance

Generated: 2026-05-17

Status: **post-gate outline; first LaTeX draft created**

## Candidate Title

Retrieval-Conditioned CTI Compliance: A Protocol-Specific Result

## One-Sentence Claim

On a frozen no-label evidence-addressable CTI-MCQ slice, question-specific ATT&CK retrieval improves strict multiple-choice compliance over vanilla and broad-seed prompting at both 8B and 3B; relationship evidence is the strongest tested retrieval form, but technique-only evidence also helps, so the mechanism claim remains bounded.

## Abstract Skeleton

Large language models are increasingly used for cyber threat intelligence, but CTI questions often require answer-bearing ATT&CK facts that broad role prompts do not reliably supply. We test whether question-specific ATT&CK retrieval improves strict CTI question-answering compliance under a parser that accepts only `Answer: <A|B|C|D>`. Using a frozen 106-row no-label evidence-addressable CTI-MCQ slice and ATT&CK `enterprise-attack-12.0`, relationship evidence improves Llama-3.1-8B strict accuracy from `68/106` to `97/106`, with no invalid-rate regression and `33` evidence-only paired wins versus `4` vanilla-only wins. The effect replicates on Llama-3.2-3B (`0.547` to `0.887`). Ablation shows relationship evidence is strongest (`0.915`) but technique-only evidence also helps (`0.764`), so we position the result as retrieval-conditioned CTI compliance rather than a pure relationship-causality claim or training-data extraction result.

## Paper Structure

1. Introduction

   - CTI workflows need accurate, evidence-grounded answers.
   - Broad cyber role prompting can harm strict compliance.
   - ATT&CK evidence is a natural retrieval unit.
   - Main result: relationship evidence yields the strongest strict-compliance gain, with conservative mechanism scope.

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
   - Ablation: technique-only evidence, random facts, empty evidence.
   - No-label evidence-addressable slice construction.

5. Experimental Design

   - Models: `meta-llama/Llama-3.1-8B-Instruct`, `meta-llama/Llama-3.2-3B-Instruct`.
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
   - Random-facts and empty-evidence negative controls.
   - 3B cross-model replication.
   - Slice audit and complement baseline.

8. Discussion

   - Why retrieved evidence helps.
   - Why relationship-level evidence is strongest but not fully isolated.
   - Why broad seed prompting fails.
   - How this differs from extraction.
   - What this means for CTI assistants and analyst workflows.

9. Limitations

   - Evidence-addressable slice is not the full benchmark distribution.
   - Multiple-choice compliance is narrower than open-ended analysis.
   - ATT&CK snapshot age matters.
   - Requires structured knowledge base availability.

10. Conclusion

   - Retrieval-conditioned ATT&CK evidence is a defensible, measurable CTI prompt intervention.
   - The result is bounded and not an extraction claim.

## Core Tables

| Table | Purpose |
|---|---|
| Table 1 | Literature positioning and claim boundary. |
| Table 2 | Prompt conditions and evidence sources. |
| Table 3 | Main strict scorecard. |
| Table 4 | Paired wins and invalid rates. |
| Table 5 | Ablation and replication results. |

## Core Figures

| Figure | Purpose |
|---|---|
| Figure 1 | ATT&CK relationship neighborhood around a technique. |
| Figure 2 | Experimental pipeline: CTI-MCQ row to relationship retrieval to strict answer. |
| Figure 3 | Paired wins: evidence-only vs vanilla-only. |

## Current Result Text

In the first cloud GPU gate, relationship evidence improved strict accuracy by `+0.274` absolute over vanilla prompting. The relationship-evidence condition answered `97/106` rows correctly with zero invalid outputs. Vanilla answered `68/106` rows correctly with zero invalid outputs. The broad-seed negative control answered `68/106` rows correctly and produced one invalid output. Paired scoring showed `33` relationship-evidence-only wins versus `4` vanilla-only wins.

The slice audit produced a soft pass: label isolation and determinism checks passed, while complement vanilla accuracy was `230/394 = 0.584`, lower than the slice vanilla baseline `0.642`. The result must therefore report the complement baseline and adjusted lift.

The 3B cross-model gate passed: relationship evidence improved from `0.547` vanilla to `0.887`, with broad seed at `0.575` and zero invalids.

The 8B ablation reproduced the main effect and bounded the mechanism: relationship evidence `0.915`, technique-only `0.764`, random facts `0.566`, empty evidence `0.670`, vanilla `0.642`, broad seed `0.642`.

## Strong Claim Version

> Question-specific ATT&CK retrieval, not broad domain seeding, improves strict CTI answer compliance on a locked evidence-addressable CTI-MCQ slice; relationship evidence is the strongest tested retrieval form.

## Conservative Claim Version

> A frozen Llama instruction-tuned model substantially improves strict CTI-MCQ compliance on an evidence-addressable slice when prompted with question-ranked ATT&CK evidence, with the mechanism scoped to this retrieval protocol.

## Next Writing Work

1. Edit `main.tex` for prose density and committee-facing flow.
2. Add one pipeline figure and one example row.
3. Compile `main.tex` and `thesis_chapter.tex` in a TeX-enabled environment.
