# Final Praxis Proposals

Updated: 2026-09-08
Branch: `Final-Praxis-Proposals`

## Purpose

This branch contains the three final Praxis candidates selected for rigorous completion. They are deliberately separated from the historical PX numbering. Historical PX artifacts remain evidence and provenance only; no prior exploratory result is automatically promoted into these final experiments.

The common research lane is:

> **Treat probabilistic agents as untrusted decision makers and test whether deterministic mechanisms can verify actions, consequences, handoffs, or stopping decisions without destroying useful task performance.**

## Portfolio Dashboard

| Final Praxis | Working title | Status | Novelty position | Primary scientific question | Biggest risk | Immediate gate |
|---|---|---|---|---|---|---|
| **Final Praxis 001** | Independent Outcome-State Verification for Agent Task Completion Under Evaluator Disagreement | **GATE 0 PASS WITH RESCOPE / Gate 1 design active** | Generic final-state evaluation is already established by τ-bench/AppWorld, and deterministic reward-hack measurement is crowded by 2026 work. The remaining contribution is a controlled judge-vs-postcondition disagreement study covering false/incomplete completion, collateral damage, and legitimate alternate paths. | Can machine-checkable postconditions reduce false-success acceptance relative to judge-based evaluation without rejecting valid alternate completions? | Novelty collapses if the work becomes only another state-based benchmark or reward-hacking testbed. | Build and validate 20+ task templates / 140+ inert fixtures, run prospective sample-size calculation, then freeze scientific thresholds before natural model generation. |
| **Final Praxis 002** | Deterministic Trust-Boundary Containment for Multi-Agent Security Workflows | **GO after novelty gate** | Architecture alone is not novel. Candidate contribution is a measured cascade-containment experiment: whether deterministic checks between probabilistic agents stop upstream errors from becoming downstream actions. | Do deterministic inter-agent gates reduce cascade escape rate without unacceptable utility loss? | Current agent-security literature is crowded; novelty fails if experiment only restates least-privilege or prompt-injection defenses. | Complete closest-work matrix, then freeze cascade definitions, injection/error fixtures, baselines, and utility budget. |
| **Final Praxis 003** | Safety-Gated Adaptive Investigation Stopping for Agentic Security Triage | **CONDITIONAL GO** | Generic adaptive stopping is crowded (including REFRAIN, ACL 2026). Novelty must be security-investigation termination plus a preregistered safety decomposition and mechanically enforced review gate. | Can a frozen stopping policy prevent correct-to-wrong investigation degradation while reducing investigation cost under a valid safety protocol? | The earlier stopping line cannot be treated as a certified positive; policy selection may leak from prior descriptive runs. | Calculate required calibration/review sample size, freeze policy independently of prior invalid run outcomes, and mechanically enforce review/harm gate before compute. |

## Final Praxis 001 Gate 0 Finding

**PASS WITH RESCOPE.** The broad idea "verify final state deterministically" is not novel enough. Final Praxis 001 is now frozen around **evaluation integrity under judge/postcondition disagreement**. The experiment must directly measure false-success acceptance, legitimate-success preservation, alternate-valid-path acceptance, collateral-state misses, and paired evaluator disagreement.

Current Final Praxis 001 artifacts:

- `final_praxis/001_outcome_state_verification/001_NOVELTY_GATE_20260908.md`
- `final_praxis/001_outcome_state_verification/001_PREREGISTRATION_DRAFT_20260908.md`
- `final_praxis/001_outcome_state_verification/001_TASK_TAXONOMY_AND_FIXTURE_PLAN_20260908.md`

## Current Ranking

1. **Final Praxis 001** — best probability of a clean, falsifiable result after the Gate 0 rescope.
2. **Final Praxis 002** — highest flagship upside, but requires the strongest novelty discipline and largest build.
3. **Final Praxis 003** — promising mechanism, but only if the corrected protocol and anti-leakage controls are satisfied before execution.

## Explicitly Not Promoted

- Historical agent-memory provenance / PX-065-style work is not a flagship candidate. The 2026 literature has crowded the original contribution.
- Generic adaptive-stopping transfer is not a flagship claim. REFRAIN and related stopping work cover the broad mechanism.
- Historical PX-057 numerical results are **descriptive prior evidence only** for this branch. They are not a certified Final Praxis result and must not be displayed as such.
- Drift-warning rescue work is not part of this branch.

## Common Promotion Contract

Every Final Praxis experiment must follow the same sequence:

1. **Novelty Gate** — identify the closest 2024-2026 work and write the exact difference in one sentence. If the difference is architectural wording only, stop.
2. **Threat/Failure Model** — specify what can go wrong, what the attacker/error source controls, and what is out of scope.
3. **Frozen Hypotheses** — write H1/H2/etc. before any non-fixture evaluation.
4. **Ground Truth** — prefer programmatic/environmental truth over LLM judgment whenever possible.
5. **Strong Baselines** — include the cheapest credible alternative and the strongest directly comparable baseline.
6. **Fixture Gate** — prove parsers, metrics, postconditions, and adjudication logic on inert synthetic fixtures only.
7. **Pilot** — use a small frozen sample to detect broken infrastructure, not to retune scientific thresholds.
8. **Full Gate** — execute exactly the preregistered design.
9. **Independent Verification** — hash datasets/configs, verify denominators, check exclusions, and independently recompute primary metrics.
10. **Replication** — second model/domain only after the discovery gate is frozen; do not rewrite the discovery result.
11. **Classification** — Positive / Bounded Positive / Mixed / Negative / Protocol Invalid / Blocked. Never smooth a miss into a pass.
12. **Publication Boundary** — state exactly what the experiment does *not* prove.

## Required Metrics Across the Branch

All three experiments should report denominators, confidence intervals where meaningful, and both security and utility. At minimum, record:

- failure/escape or false-success rate;
- legitimate task success / clean utility;
- intervention/review rate;
- model and seed breakdown;
- cost/latency/token overhead when applicable;
- exact excluded cases and exclusion reason;
- pre-registered promotion and kill thresholds.

## Branch Layout

- `final_praxis/001_outcome_state_verification/`
- `final_praxis/002_cascade_containment/`
- `final_praxis/003_adaptive_investigation_stopping/`

Each experiment folder contains an experiment charter and an execution checklist. Results must be added later as new artifacts; proposal documents should not be silently rewritten to match outcomes.
