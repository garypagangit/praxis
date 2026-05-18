# SEC-LoRD Relationship-Evidence Ablation Gate — Ready

**Date:** 2026-05-17
**Owner:** Gary Pagan
**Status:** Pre-registered; not yet run. Sequenced after cross-model gate and leakage audit.
**Predecessor:** `SEC_LORD_RELATIONSHIP_EVIDENCE_MODEL_GATE_20260517.md` (8B PASS, +0.274 absolute)
**Successor:** Praxis-grade thesis section, naming locked from ablation result.

## Why this gate exists

The 8B PASS shows that *something* in the relationship-evidence prompt lifts strict CTI-MCQ accuracy. It does not show *what* in that prompt is responsible for the lift. Three competing explanations are all consistent with +0.274 absolute:

- **H_relationship:** ATT&CK *relationship* facts (mitigations, detections, procedure examples, data sources, tactic linkages) carry information that the technique description alone does not, and the model uses that information to answer.
- **H_specificity:** any question-specific ATT&CK content lifts accuracy; relationships are no different from technique descriptions when both are routed to the same question. The "relationship" framing is incidental.
- **H_format:** any structured Evidence block in the prompt — even one filled with irrelevant ATT&CK facts — improves strict-format compliance and pulls accuracy up by reducing parse failures, not by grounding reasoning.

These three hypotheses motivate three new prompt conditions. The naming of the eventual Praxis section depends on which hypothesis survives.

## Conditions

Five arms total. The first two are the same as the 8B PASS run, re-included so this gate is self-contained:

1. **Vanilla** — strict prompt, no domain seed, no Evidence block.
2. **Relationship evidence** — strict prompt with the 8B-PASS Evidence block (1–3 ATT&CK relationship facts), retrieved per-question by the locked ranker.
3. **Technique-only** *(new)* — strict prompt with an Evidence block populated by the ATT&CK technique description and tactic name for the identified technique, but no relationships (no mitigations, no detections, no procedure examples, no data-source links). Same Evidence block formatting; same token budget; differs only in the *content* of the retrieved facts.
4. **Random-facts** *(new)* — strict prompt with an Evidence block populated by ATT&CK relationship facts for a *different* technique selected uniformly at random from the 121-technique-eligible set, conditioned on not being the identified technique for this question. Same formatting, same token budget, same number of facts. This is the negative control.
5. **Empty Evidence block** *(new)* — strict prompt with an Evidence block header but no content (or, equivalently, a short irrelevant filler matched in token length). This isolates "did adding a block header alone change behavior" from "did the block content matter."

Five arms, same 8B model, same 106-row slice, strict parser only.

## Pre-registered hypothesis discrimination

The ablation gate is a discriminator, not a pass/fail gate. The pre-registered interpretations of the result are:

| Outcome | Surviving hypothesis | Thesis claim shape |
|---------|---------------------|-------------------|
| Relationship ≥ vanilla + 0.20 *and* Technique-only within 0.05 of vanilla *and* Random ≤ vanilla *and* Empty ≤ vanilla | H_relationship | "Relationship-level ATT&CK retrieval specifically lifts strict CTI-MCQ accuracy." Praxis title can use the word "relationship." |
| Relationship and Technique-only both ≥ vanilla + 0.15 *and* the two are within 0.05 of each other *and* Random and Empty are near vanilla | H_specificity | "Question-specific ATT&CK retrieval — at any granularity above the technique level — lifts strict CTI-MCQ accuracy." Title becomes "Question-Specific Retrieval for CTI Compliance." Relationship framing is demoted to a within-protocol detail. |
| Random and Empty lift above vanilla by ≥ +0.10 | H_format | "The Evidence-block prompt structure improves strict-format compliance independent of content." The thesis becomes a *prompting* paper, not a retrieval paper. Major reframing. |
| Mixed pattern not matching any of the above | None cleanly | Report descriptively. The Praxis must acknowledge the mechanism is unclear and scope the claim to "under this specific evidence-construction pipeline." |

## Pre-registered gates on the discriminator

To call any of the above a "clean" result, the ablation must satisfy:

| Gate | Threshold |
|------|-----------|
| AB1 — Relationship vs Vanilla | within 0.04 absolute of the 8B PASS lift (+0.274). |
| AB2 — Random vs Vanilla | ≤ vanilla + 0.05 (random must not silently lift). |
| AB3 — Empty vs Vanilla | ≤ vanilla + 0.05 (empty must not silently lift). |
| AB4 — Invalid rate in all five arms | ≤ relationship invalid rate + 0.03. |

AB1 ensures the original PASS reproduces. AB2 and AB3 ensure the negative controls behave as negative controls. AB4 ensures any accuracy difference between arms is not explained by differing parse-failure rates.

If AB1 fails the original 8B PASS does not reproduce and the entire result chain is in question — stop and investigate before drawing any ablation conclusion.

## Required result artifacts

`SEC_LORD_RELATIONSHIP_EVIDENCE_ABLATION_GATE_<DATE>.md` must record:

- Per-arm: strict-accuracy count and rate, invalid-rate count and rate, mean output token length, mean Evidence-block token length.
- Pairwise paired-win matrix (5×5) of strict-correct.
- Gate evaluation: AB1–AB4 with actual numbers.
- Hypothesis verdict: H_relationship / H_specificity / H_format / unclear, with the specific row of the discrimination table that justifies the verdict.
- Recommended Praxis section title based on the verdict.

Filename and JSON conventions match the 8B PASS run.

## Cloud-run handoff

This gate adds three new arms (technique-only, random-facts, empty) on the existing 106-row slice and 8B model. Re-running vanilla and relationship as in-run controls is mandatory to confirm AB1.

Expected wall-clock under 30 minutes total on the g5.xlarge runner. Run via SSM through the SSO profile (`praxis-build`), same pattern as the 8B PASS run.

Random-facts arm requires a per-question random technique draw. Pin the random seed and record it in the result artifact so the run is reproducible.

## Sequencing

This gate runs *after* the cross-model gate and the leakage audit. Rationale:

- If the cross-model gate produces a clean PASS, this ablation explains *what* generalizes.
- If the cross-model gate fails with capacity-emergence, this ablation is run at 8B only and produces the same hypothesis discrimination.
- If the leakage audit fails A2 hard (slice is materially easier than complement), this ablation is rebuilt on a redesigned slice before being run.

The ablation is the most informative of the three follow-on runs but the least useful to run early; it depends on the prior two passing.

## Out of scope for this gate

- Cross-model ablation. If the cross-model gate passes cleanly and this ablation isolates H_relationship at 8B, a 3B-side ablation could follow as a robustness addendum, but it is not in scope here.
- Cross-task generalization (other CTI benchmarks, other security MCQ sets). Defer until the Praxis section is drafted and committee feedback identifies external-validity priorities.
- Cost/latency analysis of the Evidence block. The ablation is about *what is responsible for the lift*, not about deployment economics.

## Stop conditions

- AB1 fails: original PASS does not reproduce. Halt, investigate retrieval-pipeline reproducibility, do not interpret AB2–AB4 until AB1 holds.
- Random-facts or empty arm produces invalid rate above 0.20: prompt template is breaking format compliance in those arms specifically. Adjust the empty-block formatting (e.g., use a short benign filler), pin the change, re-run.
- Mean Evidence-block token length differs across arms by more than 30%: token-budget imbalance confounds the comparison. Re-balance lengths and re-run before drawing conclusions.

## Naming decision flow (post-ablation)

The Praxis section title is locked by the ablation verdict:

- **H_relationship survives →** *Relationship-Evidence Retrieval for CTI Multiple-Choice Compliance*
- **H_specificity survives →** *Question-Specific ATT&CK Retrieval for CTI Multiple-Choice Compliance*
- **H_format survives →** *Structured Prompt Scaffolding for Strict-Format CTI Compliance* (and the thesis becomes a prompting paper, not a retrieval paper)
- **Unclear →** *Retrieval-Conditioned CTI Compliance: A Protocol-Specific Result* (most conservative naming; defers mechanism claim)

No section title is committed to before this gate runs.
