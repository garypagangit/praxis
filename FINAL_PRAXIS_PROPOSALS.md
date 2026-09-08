# Final Praxis Proposals

Updated: 2026-09-08
Branch: `Final-Praxis-Proposals`

## Portfolio Dashboard

| Final Praxis | Working title | Status | Scientific position | Next executable gate |
|---|---|---|---|---|
| **Final Praxis 001** | Independent Outcome-State Verification for Agent Task Completion Under Evaluator Disagreement | **GATE 0-2 COMPLETE; GATE 3 DESIGN FROZEN; BLOCKED ON EXTERNAL MODEL COMPUTE** | No scientific result yet. 140/140 inert fixtures passed with deterministic hash `fab1d1fc72946935d58db7875744a192996fd7eee08ea3b9d9900de38b68a3ec`. Discovery is frozen at 400 paired units. Primary agent is `Qwen/Qwen2.5-7B-Instruct`; replication model is `mistralai/Mistral-7B-Instruct-v0.3`. | Bind a real Qwen inference adapter and a distinct real judge adapter, run <=16-unit infrastructure pilot, then execute the frozen 400-unit discovery and independent verification. Synthetic scientific fallback is prohibited. |
| **Final Praxis 002** | Deterministic Trust-Boundary Containment for Multi-Agent Security Workflows | **NOVELTY GATE NEXT** | Architecture alone is not novel; contribution must be measured cascade containment. | Complete closest-work kill/go matrix, then freeze cascade experiment. |
| **Final Praxis 003** | Safety-Gated Adaptive Investigation Stopping for Agentic Security Triage | **CONDITIONAL / METHODS GATE NEXT** | Generic stopping is crowded; only security-specific stopping with corrected preregistered safety protocol is viable. | Freeze calibration/review sample-size and anti-leakage policy before any compute. |

## Final Praxis 001 completed work

- Gate 0: **PASS WITH RESCOPE** — final-state evaluation itself is not the novelty; evaluator-integrity disagreement is.
- Gate 1: **DESIGN FROZEN** — 20 tasks, 140 fixture minimum, 400 primary scientific units, paired FSAR primary endpoint, fixed utility/security gates.
- Gate 2: **PASS** — executable inert harness and deterministic verifier; 140/140 fixtures passed and replay hash is stable.
- Gate 3 design: **FROZEN** — primary/replication models, allocation seed, generation policy, pilot constraints and fail-closed scientific runner committed.

### Important boundary

This environment can edit/read the GitHub repository and run local deterministic code, but it does **not** expose the repository's AWS/cloud credentials or an external LLM inference endpoint. Therefore I cannot truthfully execute the Qwen/judge pilot or 400-unit scientific run from this chat. Final Praxis 001 is **externally compute-blocked**, not complete and not positive/negative.

Key artifacts:
- `final_praxis/001_outcome_state_verification/001_GATE3_MODEL_AND_EXECUTION_FREEZE_20260908.md`
- `final_praxis/001_outcome_state_verification/configs/experiment.json`
- `final_praxis/001_outcome_state_verification/harness/run_scientific.py`
- all Gate 0-2 design, fixture, verifier and audit artifacts in the same folder.

## Portfolio priority while 001 is compute-blocked

1. **Final Praxis 002** — run novelty kill/go and design gates now; no model compute is needed for these steps.
2. **Final Praxis 003** — complete methods/sample-size gate now; no model compute is needed for these steps.
3. Return to **Final Praxis 001** as soon as a real inference adapter/cloud execution path is available.

## Common rule

Never substitute synthetic model decisions for a scientific run merely to mark an experiment complete. Classification remains Positive / Bounded Positive / Mixed / Negative / Protocol Invalid / Blocked based only on frozen real evidence.