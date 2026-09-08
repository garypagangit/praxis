# Final Praxis 001 — Preregistration Draft

Date: 2026-09-08
Status: **DRAFT — freeze before non-fixture model runs**

## Title

**Independent Outcome-State Verification for Agent Task Completion Under Evaluator Disagreement**

## Research question

When an agent claims that a tool-mediated task is complete, how often does a judge-based evaluator accept success when the environment does not satisfy the intended postconditions, and can a machine-checkable postcondition verifier reduce that false-success acceptance without rejecting legitimate alternate solutions?

## Primary hypotheses

### H1 — False-success reduction

An independent postcondition verifier will produce a lower false-success acceptance rate than the primary judge baseline on controlled incomplete and falsely claimed completion states.

### H2 — Legitimate-success preservation

The postcondition verifier will preserve a high acceptance rate on legitimate successful executions, including alternate valid solution paths that do not match a canonical trajectory.

### H3 — Collateral-state sensitivity

The postcondition verifier will detect task executions that satisfy the requested goal while violating preregistered collateral-state invariants more reliably than the primary judge baseline.

### H4 — Evaluator disagreement concentration

Judge/verifier disagreements will concentrate in predefined failure families rather than occurring uniformly across clean successful tasks.

## Experimental unit

One experimental unit is one frozen task instance plus one resulting environment state and one agent completion claim.

The same resulting state can be evaluated by multiple evaluator arms, but statistical reporting must account for paired evaluation of identical units.

## Evaluator arms

1. **Independent deterministic postcondition verifier** — primary treatment.
2. **LLM-as-judge baseline** — receives the task request, agent-visible interaction transcript, and final textual completion claim, but not hidden verifier code or expected postcondition implementation.
3. **Trajectory/rubric judge baseline** — optional stronger learned-evaluator arm if source and cost are frozen before execution.
4. **Claim-only heuristic baseline** — cheap negative control if useful; must not replace the LLM judge.

## State families

Every task template must support at least these frozen outcome families:

- **Clean success** — all goal postconditions true; all collateral invariants true.
- **Alternate valid success** — all goal postconditions and invariants true via a non-canonical action sequence or equivalent state.
- **Incomplete completion** — at least one required postcondition false while the agent claims completion.
- **False-success claim** — no sufficient goal completion, but the textual claim reports success.
- **Partial success** — some but not all required postconditions true.
- **Collateral-damage completion** — primary goal postconditions true but one or more protected invariants false.
- **Benign failure / admitted failure** — goal not achieved and the agent correctly reports non-completion.

No evaluator receives a label naming the family.

## Task taxonomy

Discovery version should include at least four machine-checkable task families with different state structures:

1. **File/workspace state** — create/update/rename structured files with exact semantic invariants.
2. **Record/database state** — manipulate inert customer/project/ticket records in a local deterministic store.
3. **Configuration state** — modify an inert service configuration with required and forbidden fields.
4. **Multi-object workflow state** — complete a sequence whose success depends on consistency across two or more state objects.

A fifth family may be added only before fixture freeze.

## Postcondition design rules

Each task must define:

- required goal predicates;
- protected invariants / forbidden side effects;
- equivalence rules that admit legitimate alternate solutions;
- a deterministic verification function;
- a human-readable oracle description used only for independent audit;
- fixture cases that prove each predicate can both pass and fail.

Postconditions must evaluate **state**, not exact trajectory, unless trajectory is itself part of the task requirement.

## Primary outcomes

### Security / integrity

- **False-Success Acceptance Rate (FSAR)** = false/incomplete/collateral-invalid units labeled successful / all such units.
- **Collateral Violation Miss Rate (CVMR)** = collateral-invalid units accepted as success / all collateral-invalid units.

### Utility

- **True-Success Acceptance Rate (TSAR)** = valid successful units accepted / all valid successful units.
- **Alternate-Path Acceptance Rate (APAR)** = alternate-valid successes accepted / all alternate-valid successes.

### Diagnostic

- evaluator disagreement rate;
- disagreement by failure family;
- judge confidence/calibration if exposed;
- evaluation latency and cost;
- per-model and per-task-family results.

## Promotion gate — provisional, must be frozen before pilot

The experiment may be promoted as a bounded positive only if all of the following hold on the frozen discovery set:

1. Postcondition verifier FSAR is at least **20 percentage points lower** than the primary judge baseline OR shows at least **50% relative reduction**, with the paired confidence interval excluding no improvement.
2. Postcondition verifier TSAR is **>= 0.95** on clean + alternate-valid successes.
3. APAR is **>= 0.90** so the verifier is not merely enforcing one canonical path.
4. CVMR is lower than the primary judge baseline and the direction is consistent across at least three task families.
5. Fixture, dataset/config hash, denominator, and exclusion audits pass.

Thresholds are provisional until fixture analysis verifies they are measurable and not structurally guaranteed. Once frozen, they cannot move after scientific outcomes are inspected.

## Kill criteria

Classify as Negative/Mixed rather than rescue if any of the following occurs:

- judge FSAR is already near zero, leaving no meaningful evaluator-integrity gap;
- postcondition verification rejects substantial legitimate alternate successes (APAR below frozen floor);
- gains are driven entirely by one trivial task family;
- postconditions leak the canonical solution path rather than verify outcome state;
- verifier logic requires subjective LLM adjudication for primary ground truth;
- the final novelty audit finds direct prior overlap meeting the Gate 0 kill definition.

## Model plan

Discovery should use at least two agent models if affordable, but the scientific unit is evaluator disagreement over frozen states. The first model must be frozen before generation. A second model is preferred for robustness and cannot be used to retune thresholds.

The judge model should not be identical to the agent model for the primary comparison unless a separate same-model judge arm is explicitly preregistered.

## Sample construction

Before natural model generation, build a balanced fixture corpus spanning every task family × state family combination. Fixture cases are infrastructure tests and cannot count as scientific evidence.

The discovery corpus should contain enough units per failure family to estimate FSAR with useful uncertainty. Final n will be set by a prospective power/precision calculation before model execution.

## Anti-leakage controls

- Freeze task/postcondition definitions before natural agent generation.
- Do not show verifier code, hidden expected-state metadata, or family labels to the agent or judge.
- Separate fixture generation from discovery generation.
- Hash task definitions, verifier implementation, model settings, and evaluation prompts.
- No threshold tuning on discovery results.
- Any manually excluded unit must have a preregistered exclusion category and be reported.

## Required independent verification

A separate verification script or reviewer must recompute:

- family counts;
- postcondition labels;
- judge labels;
- FSAR/TSAR/APAR/CVMR;
- paired confidence intervals;
- exclusions and denominators;
- configuration and artifact hashes.

## Permitted positive claim

If the promotion gate passes, the strongest allowed claim is:

> On the frozen task families and evaluator conditions tested, independent machine-checkable environmental postconditions reduced false acceptance of claimed agent task completion relative to judge-based evaluation while preserving legitimate clean and alternate-path task success.

## Claim boundary

The experiment will not establish universal superiority of deterministic evaluation, universal reward-hacking prevention, or applicability to tasks without machine-checkable outcome semantics.
