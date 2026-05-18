# SEC-LoRD Relationship-Evidence Follow-On Sequence — Index

**Date:** 2026-05-17
**Owner:** Gary Pagan
**Status:** Three follow-on gate docs pre-registered; runs not yet executed.

## Why this index exists

The 2026-05-17 8B PASS for relationship-evidence retrieval is a clean prospective result, but the headline number (+0.274 absolute) is not Praxis-defensible on a single model under a single condition with one slice. Three follow-on gates close that gap. This document sequences them, names the pre-conditions for each, and states which outcomes route to which thesis claim.

The three gates are independent artifacts but dependent in execution order.

## The three gates

1. **Cross-model gate (3B):** does the lift hold on `Llama-3.2-3B-Instruct`?
   File: `SEC_LORD_RELATIONSHIP_EVIDENCE_CROSS_MODEL_GATE_3B_READY_20260517.md`

2. **Leakage audit:** is the 106-row slice independent of `expected_output`, and is the slice not systematically easier than the complement?
   File: `SEC_LORD_RELATIONSHIP_EVIDENCE_SLICE_AUDIT_READY_20260517.md`

3. **Ablation gate:** is the lift driven by relationship content, by any question-specific content, or by prompt structure?
   File: `SEC_LORD_RELATIONSHIP_EVIDENCE_ABLATION_GATE_READY_20260517.md`

## Run order

The three gates have different costs and different unblocking patterns. Run in this order:

| Order | Gate | Why this slot |
|-------|------|---------------|
| 1 | Leakage audit (A1, A3, A4 local-only) | Cheapest. If A1 or A4 fails, the 8B PASS itself is methodologically suspect and the other two gates are wasted budget. |
| 2 | Leakage audit (A2 cloud run on complement) | One cloud run, ~30 min wall-clock. If A2 hard-fails, the headline number must be reframed before any further work. |
| 3 | Cross-model gate (3B) | One cloud run, ~15 min wall-clock. Cheap relative to its information value. Either outcome (clean PASS or clean capacity-emergence) is publishable. |
| 4 | Ablation gate | Most informative but only useful once the slice methodology is defended (gates 1–2) and the cross-model picture is known (gate 3). Three new arms on the 8B + 106-row slice, ~30 min wall-clock. |

Total budget: roughly 75 minutes of GPU wall-clock across two to three cloud runs, plus local-only audit work. Well inside what the existing `praxis-build` SSO + g5.xlarge runner can absorb in a single session.

## Pre-conditions for each gate

| Gate | Must hold before running |
|------|--------------------------|
| Leakage A1, A3, A4 | None. Run first. |
| Leakage A2 | A1, A3, A4 all PASS. |
| Cross-model 3B | Full leakage audit PASS or SOFT PASS. (A FAIL routes to slice redesign, not to running on a second model.) |
| Ablation | Full leakage audit PASS or SOFT PASS, AND cross-model gate produced either a clean PASS or a clean capacity-emergence FAIL. |

## Outcome routing

The three gates together fork the Praxis section into one of several shapes. Each terminal outcome is a defensible thesis section; none requires another full experiment cycle.

| Leakage | Cross-model 3B | Ablation | Resulting Praxis claim |
|---------|---------|----------|---------------------|
| PASS | PASS | H_relationship | **"Relationship-Evidence Retrieval for CTI Multiple-Choice Compliance"** — strongest claim. Cross-model generalization within Llama-3.x instruct, mechanism isolated to relationship content. |
| PASS | PASS | H_specificity | **"Question-Specific ATT&CK Retrieval for CTI Multiple-Choice Compliance"** — strong claim, relationship framing demoted to within-protocol detail. |
| PASS | PASS | H_format | **"Structured Prompt Scaffolding for Strict-Format CTI Compliance"** — major reframing; thesis becomes a prompting paper, not a retrieval paper. Still defensible. |
| PASS | capacity-emergence FAIL | any | **"Capacity-Dependent Retrieval Lift in Strict-Format CTI Compliance"** — narrow but interesting finding. Claim is bounded to ≥ 8B Llama instruct. |
| SOFT PASS | any | any | All headline numbers report the *adjusted* lift (relationship − complement vanilla), and the section explicitly documents the slice-difficulty correction. The contribution still stands; the framing becomes more conservative. |
| FAIL (A1 or A4) | n/a | n/a | Slice methodology is broken. Redo the 8B PASS run on a no-label-confirmed pipeline before any further follow-on work. |
| FAIL (A2 hard) | n/a | n/a | Slice is materially easier than the complement. Either redesign the slice criterion or reframe the entire contribution as protocol-conditional on the specific slicing rule. |

## What is *not* in this sequence

- LoRD-style extraction. Permanently demoted to "motivation / related work" in the thesis. Not running.
- Cross-task generalization (other CTI benchmarks, other security MCQ sets). Defer until committee feedback on the drafted section.
- Other model families (Mistral, Qwen, DeepSeek). Defer; the within-family Llama 3B–8B check is sufficient for the Praxis claim. Cross-family is an external-validity question for a later paper.
- Quantization sensitivity, latency analysis, deployment economics. Out of scope for this Praxis chapter.
- Any work that tries to rescue broad-seeded prompting. The 8B PASS run already closed that path at the same accuracy as vanilla (0.642 / 0.642). It stays closed.

## Stop conditions for the sequence as a whole

- Two consecutive cloud runs fail reproducibility (e.g., 8B vanilla in the ablation gate differs from 8B vanilla in the cross-model gate by more than 0.03). Halt and investigate decoding determinism before continuing.
- Any audit step surfaces label contamination in the retrieval pipeline. Halt everything, fix, and re-run the 8B PASS gate before any follow-on work.
- Cumulative GPU spend exceeds 4 hours wall-clock without producing any of the four terminal outcomes above. Stop and report what was learned; do not keep running variants in search of a positive.

## Handoff to the coding agent

Each of the three gate docs is self-contained and matches the format of `SEC_LORD_RELATIONSHIP_EVIDENCE_CLOUD_GATE_READY_20260517.md`. The coding agent should pick up the next-in-order gate from this index, follow the same SSM-via-SSO pattern used for the 8B PASS run, write the result artifact in the format specified by that gate's "Required result artifacts" section, commit, push, stop the GPU instance, and report PASS/FAIL with the specific gate-evaluation numbers.

No claim — in any artifact, dashboard, or thesis section — should be promoted past "8B PASS, cross-model unknown, mechanism unknown" until all three gates have produced terminal outcomes.
