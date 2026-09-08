# Final Praxis Proposals

Updated: 2026-09-08
Branch: `Final-Praxis-Proposals`

## Purpose

This branch contains the three final Praxis candidates selected for rigorous completion. Historical PX artifacts remain evidence/provenance only; no prior exploratory result is automatically promoted.

> **Common lane:** treat probabilistic agents as untrusted decision makers and test whether deterministic mechanisms can verify actions, consequences, handoffs, or stopping decisions without destroying useful task performance.

## Portfolio Dashboard

| Final Praxis | Working title | Status | Novelty position | Frozen/next gate |
|---|---|---|---|---|
| **Final Praxis 001** | Independent Outcome-State Verification for Agent Task Completion Under Evaluator Disagreement | **GATE 2 FIXTURE PASS / GATE 3 ADAPTER PREP** | Broad final-state evaluation is not novel. Surviving contribution is controlled evaluation-integrity measurement: judge false-success acceptance vs authoritative postcondition truth, including alternate-valid solutions and collateral-state violations. | **Passed:** executable inert harness, 20 task templates, 140/140 fixture validation, deterministic replay hash `fab1d1fc...b68a3ec`. **Frozen scientific design:** 400 primary units (+40 admitted-failure controls if budget permits), paired FSAR analysis, TSAR/APAR/CVMR gates. **Next:** freeze agent/judge model adapters and run an infrastructure-only end-to-end pilot before the 400-unit discovery run. |
| **Final Praxis 002** | Deterministic Trust-Boundary Containment for Multi-Agent Security Workflows | **GO after novelty gate** | Architecture alone is not novel. Contribution must be measured cascade containment across probabilistic-agent handoffs. | Complete closest-work matrix; freeze cascade definitions, baselines, utility budget and kill criteria. |
| **Final Praxis 003** | Safety-Gated Adaptive Investigation Stopping for Agentic Security Triage | **CONDITIONAL GO** | Generic stopping is crowded. Novelty must be security-investigation termination plus preregistered safety decomposition and mechanically enforced review gate. | Calculate calibration/review sample size; freeze policy independently of prior protocol-invalid/descriptive outcomes. |

## Final Praxis 001 — completed gates

- **Gate 0:** PASS WITH RESCOPE.
- **Gate 1:** DESIGN FROZEN.
  - 20 inert task templates across four task families.
  - Seven required state/claim fixture classes per task.
  - 400 primary discovery units: 200 valid-success + 200 invalid-success; optional 40 admitted-failure controls.
  - Frozen promotion contract: paired FSAR reduction, TSAR >= .95, APAR >= .90, collateral improvement in >=3/4 families, primary judge FSAR >= .10, full audit validity.
- **Gate 2:** FIXTURE/VERIFIER PASS.
  - 140/140 fixtures passed.
  - Repeated fixture generation produced identical SHA-256 `fab1d1fc72946935d58db7875744a192996fd7eee08ea3b9d9900de38b68a3ec`.
  - Deterministic replay reproduced stored verifier outcomes.
  - Scientific runner fails closed without fixture gate marker.

## Final Praxis 001 current artifacts

- `final_praxis/001_outcome_state_verification/001_NOVELTY_GATE_20260908.md`
- `final_praxis/001_outcome_state_verification/001_PREREGISTRATION_DRAFT_20260908.md`
- `final_praxis/001_outcome_state_verification/001_FROZEN_TASK_CATALOG_20260908.md`
- `final_praxis/001_outcome_state_verification/001_SAMPLE_SIZE_AND_FROZEN_GATES_20260908.md`
- `final_praxis/001_outcome_state_verification/001_IMPLEMENTATION_SPEC_20260908.md`
- `final_praxis/001_outcome_state_verification/001_GATE2_FIXTURE_DETERMINATION_20260908.md`
- `final_praxis/001_outcome_state_verification/harness/`
- `final_praxis/001_outcome_state_verification/artifacts/fixtures/FIXTURE_GATE_PASS`

## Ranking

1. **Final Praxis 001** — strongest clean-result candidate; infrastructure gate has passed and the next risk is real evaluator/agent behavior, not harness correctness.
2. **Final Praxis 002** — highest flagship upside; novelty gate remains mandatory before build.
3. **Final Praxis 003** — promising only if corrected protocol and anti-leakage controls clear before compute.

## Explicitly Not Promoted

- Historical agent-memory provenance / PX-065-style work.
- Generic adaptive-stopping transfer as a flagship.
- Historical PX-057 numbers as a certified result; they remain descriptive prior evidence only.
- Drift-warning rescue work.

## Common Promotion Contract

1. Novelty Gate.
2. Threat/failure model.
3. Frozen hypotheses.
4. Programmatic ground truth where possible.
5. Strong baselines.
6. Fixture gate.
7. Frozen pilot for infrastructure only.
8. Full preregistered gate.
9. Independent verification.
10. Frozen replication.
11. Honest classification: Positive / Bounded Positive / Mixed / Negative / Protocol Invalid / Blocked.
12. Explicit publication boundary.

Proposal documents are provenance artifacts and must not be silently rewritten to match outcomes.