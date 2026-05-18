# SEC-LoRD Relationship-Evidence Cross-Model Gate (3B) — Ready

**Date:** 2026-05-17
**Owner:** Gary Pagan
**Status:** Pre-registered; not yet run.
**Predecessor:** `SEC_LORD_RELATIONSHIP_EVIDENCE_MODEL_GATE_20260517.md` (8B PASS, +0.274 absolute)
**Successor (conditional):** ablation gate, then leakage audit, then thesis section.

## Why this gate exists

The 2026-05-17 8B run produced a clean PASS for relationship-evidence retrieval on the 106-row evidence-addressable slice. One model is not cross-model evidence. Before any Praxis-style claim is admissible, the result must be checked on a second instruction-tuned model from the same family at a different capacity.

Two outcomes are both useful, and both are pre-registered as acceptable findings:

- **PASS at 3B:** relationship-evidence retrieval generalizes across model scale within the Llama instruction-tuned family. Claim shape: "retrieval-augmented prompting lifts CTI-MCQ strict accuracy across Llama-3.x instruct models on the evidence-addressable slice."
- **FAIL at 3B with a clean capacity-emergence pattern:** the lift is capacity-dependent. Claim shape: "retrieval-augmented prompting lift on relationship-evidence requires model capacity sufficient to ground the retrieved facts; effect emerges between 3B and 8B."

A FAIL with neither pattern (e.g., 3B vanilla is also at 0.642 but evidence does not help, with no degradation either) is treated as a soft fail and routes to "investigate retrieval-conditioning mechanism" rather than "claim generalizes."

## Model under test

- `meta-llama/Llama-3.2-3B-Instruct`
- Same chat-template handling and same strict parser as the 8B run.
- Same temperature, top-p, and max-token settings as the 8B run. Document the exact values in the result artifact.

## Dataset and slice

- Same CTI-MCQ benchmark as the 8B run.
- Same 106-row evidence-addressable slice, selected by the same label-free retrieval-ranking criterion. **Do not re-select.** The slice must be byte-identical to the 8B run.
- Slice manifest must be recorded with a hash in the result artifact.

## Conditions

Three arms, same as the 8B run:

1. **Vanilla** — strict prompt, no domain seed, no evidence block.
2. **Broad seed** — strict prompt prepended with the same "cyber threat intelligence expert" broad-seed text used in the 8B run.
3. **Relationship evidence** — strict prompt with the same Evidence block (1–3 ATT&CK relationship facts) used in the 8B run, retrieved per-question by the same ranker.

Strict parser only. Format: `Answer: <A|B|C|D>`. No prose credit. Invalid responses counted but not converted.

## Pre-registered gates

The 3B run passes the cross-model gate iff all of the following hold on the 106-row slice:

| Gate | Threshold | Direction |
|------|-----------|-----------|
| G1 — Relationship strict accuracy | ≥ vanilla + 0.030 | absolute |
| G2 — Relationship invalid rate | ≤ vanilla invalid rate | absolute |
| G3 — Evidence-only paired wins | > vanilla-only paired wins | count |
| G4 — Broad-seed strict accuracy | ≤ vanilla + 0.030 | absolute (negative control must not silently pass) |

G1 is the headline. G2 prevents accuracy lift from being achieved by emitting more parsable garbage. G3 ensures the gain is per-question robust, not driven by a few easy items. G4 is the matched-rate negative control that already worked at 8B and must continue to work at 3B.

## Pre-registered failure-mode interpretations

- **Clean capacity-emergence:** G1 fails (relationship ≤ vanilla + 0.030); G2 and G4 hold; vanilla 3B substantially below vanilla 8B; 3B vanilla and 3B relationship are within 0.05 of each other. Conclusion: 3B is not capable enough to act on retrieved relationship facts. The 8B claim narrows to "instruction-tuned ≥ 8B."
- **Clean cross-model PASS:** G1, G2, G3, G4 all hold. Conclusion: effect generalizes within the Llama instruction-tuned family at the 3B–8B band. Move to ablation gate.
- **Ambiguous:** G1 holds but G2 or G3 fails. Conclusion: the lift is partly explained by format compliance or by a small number of high-impact items. Investigate before any further claim.
- **Negative control breaks:** G4 fails (broad seed lifts 3B). Conclusion: the 3B model is differently sensitive to broad seeding than the 8B model. This kills the cross-model generalization claim until understood and is treated as a hard stop.

## Required result artifacts

The result writeup must record, at minimum:

- Model string, exact decoding params, exact prompt strings for all three arms.
- Slice manifest hash; row count; per-row option counts.
- Per-arm: strict-accuracy count and rate, invalid-rate count and rate, mean output token length.
- Paired comparison table: 4 cells (relationship correct × vanilla correct).
- Gate evaluation: PASS/FAIL on each of G1–G4 with the actual numbers.
- The same `SEC_LORD_RELATIONSHIP_EVIDENCE_MODEL_GATE_*.json` shape used at 8B, with a `model_id` field.

Filename convention: `SEC_LORD_RELATIONSHIP_EVIDENCE_CROSS_MODEL_GATE_3B_<DATE>.md` and matching `.json`.

## Cloud-run handoff

This is one cloud run on the same g5.xlarge GPU runner used for the 8B run. Expected wall-clock under 15 minutes including instance start/stop.

Run via SSM through the SSO profile (`praxis-build`), same pattern as the 8B run. Re-use the existing runner script; only the model id and output paths change.

Stop the GPU instance immediately on completion. Commit and push the result artifact. Do not promote any claim before the leakage audit gate passes.

## Out of scope for this gate

- Other model families (Mistral, Qwen, DeepSeek). Defer to a later gate if the within-family cross-model check passes.
- Quantization sensitivity. The 8B run was bf16; the 3B run must also be bf16.
- Slice redesign or expansion. The 106-row slice is the locked unit of evaluation for this gate.
- Ablation across evidence types. That is the next gate.

## Stop conditions

Halt and write up as null result if any of:

- Vanilla 3B strict accuracy is below 0.40 on the 106-row slice. (Suggests the model is too weak to ground a comparison and the slice is invalidated for 3B.)
- Invalid rate above 0.20 in any arm. (Suggests format compliance is broken; the strict parser is not measuring what it should.)
- Reproducibility check on a fixed seed shows > 0.02 accuracy drift between two back-to-back runs in the vanilla arm. (Suggests decoding is non-deterministic at a level that swamps the gate.)
