# Final Praxis Proposals

Updated: 2026-09-08
Branch: `Final-Praxis-Proposals`

## Portfolio Dashboard

| Final Praxis | Working title | Current status | Completed without external compute | Remaining blocker |
|---|---|---|---|---|
| **Final Praxis 001** | Independent Outcome-State Verification for Agent Task Completion Under Evaluator Disagreement | **READY FOR REAL-MODEL PILOT / EXTERNALLY COMPUTE-BLOCKED** | Novelty rescope; frozen preregistration; 20-task catalog; 400-unit design; executable inert harness; **140/140 fixture PASS**; stable fixture SHA-256 `fab1d1fc72946935d58db7875744a192996fd7eee08ea3b9d9900de38b68a3ec`; primary Qwen and Mistral replication plan; fail-closed scientific runner. | Real `Qwen/Qwen2.5-7B-Instruct` inference adapter plus a distinct real judge endpoint; then <=16-unit pilot, 400-unit discovery, independent verification and classification. |
| **Final Praxis 002** | Deterministic Trust-Boundary Containment for Multi-Agent Security Workflows | **NOVELTY PASS WITH NARROW CLAIM / DESIGN FROZEN / BUILD READY** | Closest-work pressure test; stage-attributed cascade novelty sentence; 4 arms; 6 frozen error families; 480-run paired design; CER/utility/propagation-depth gates; implementation specification and deterministic fixture requirement. | Implement 144+ fixture harness, then real multi-agent model execution. Scientific evidence ultimately requires external model compute. |
| **Final Praxis 003** | Safety-Gated Adaptive Investigation Stopping for Agentic Security Triage | **METHODS GATE CONDITIONAL PASS / DESIGN FROZEN / BUILD READY** | Generic-stopping novelty excluded; policy-independence rules; 400-case discovery size; code-enforced STOP/CONTINUE/REVIEW semantics; harm upper-bound gate; prevention/compute/non-inferiority thresholds; implementation specification. | Build 80+ trace fixtures and freeze a 400-case staged-evidence corpus; real eight-round model traces then require external model compute. |

## Final ranking

1. **Final Praxis 001** — nearest to scientific execution and still the cleanest falsifiable candidate.
2. **Final Praxis 002** — strongest flagship upside if stage-attributed cascade behavior exists; design now protects against the final-action-gate-only explanation.
3. **Final Praxis 003** — viable only under the corrected safety protocol; no historical adaptive-stopping result is inherited.

## Scientific truth status

**None of the three Final Praxis experiments currently has a scientific positive/negative result.** Final Praxis 001 has passed its deterministic infrastructure gate; 002 and 003 have passed the design/novelty/methods work needed to justify builds. Real model inference is required before any final scientific classification.

## What has been deliberately prevented

- no synthetic LLM decisions substituted for scientific evidence;
- no historical PX-057 numbers promoted into Final Praxis 003;
- no claim that deterministic final-state evaluation itself is novel in Final Praxis 001;
- no claim that trust-boundary architecture itself is novel in Final Praxis 002;
- no moving promotion thresholds after observing discovery results.

## Execution order when compute is available

1. Final Praxis 001 real-model pilot -> 400-unit discovery -> independent verification -> classify.
2. Final Praxis 002 deterministic fixture harness -> real 480-run paired discovery -> verify -> classify.
3. Final Praxis 003 trace fixture harness + frozen staged corpus -> real 400-case eight-round traces -> verify safety gates -> classify.

## Completion rule

A proposal is scientifically complete only after its frozen real-model discovery and independent verification. Until then its dashboard status must remain `READY`, `BUILD READY`, or `BLOCKED`, never Positive/Negative.