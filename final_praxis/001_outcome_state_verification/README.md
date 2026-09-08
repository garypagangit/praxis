# Final Praxis 001

## Deterministic Outcome-State Verification for Agent Task Completion

**Status:** GO / preregistration required  
**Priority:** 1  
**Historical lineage:** conceptually extends PX-050 verification from action validity to action consequence; replaces the blocked TRACE dependency of the PX-063 direction.

## Research Question

Can deterministic verification of frozen environmental postconditions reduce false acceptance of agent-claimed task success compared with judge-based evaluation, while preserving legitimate task completion?

## Candidate Contribution

The contribution is **not** that deterministic checks are generally useful. The candidate contribution is a controlled empirical comparison between:

1. an agent's claimed success;
2. an LLM/judge-based success assessment; and
3. independent deterministic verification of the actual post-task environment state.

The publication-safe unit of novelty is **measured false-success acceptance under outcome verification**, with explicit security/utility tradeoffs.

## Hypotheses to Freeze Before Model Runs

- **H1 — False-success reduction:** deterministic outcome verification produces a materially lower false-success acceptance rate than the frozen judge baseline.
- **H2 — Utility preservation:** deterministic verification does not reduce valid completed-task acceptance beyond a preregistered utility budget.
- **H3 — Judge disagreement:** a non-trivial subset of judge-approved successes fail deterministic postconditions, demonstrating that textual plausibility and environmental success are separable.
- **H4 — Cross-model robustness (replication only):** H1-H3 retain direction on a second model without changing the discovery thresholds.

## Experimental Structure

Construct an inert, sandboxed task suite where success is externally measurable. Each task must have:

- a natural-language objective;
- an allowed action interface;
- an initial state;
- one or more valid solution paths;
- a machine-checkable postcondition;
- explicitly defined partial-success and invalid-success states;
- an agent-generated completion claim.

Example task classes should emphasize harmless software/workflow state changes such as file creation, structured data transformation, repository metadata edits in a sandbox, or simulated service configuration. Do not use real destructive effects.

## Arms

- **A0:** agent self-report only.
- **A1:** frozen LLM/judge evaluates transcript + claimed completion.
- **A2:** deterministic postcondition verifier evaluates final state.
- **A3 (optional):** judge + deterministic verifier with a review state for disagreement.

## Primary Metrics

- false-success acceptance rate;
- true-success acceptance rate;
- false-reject rate;
- verifier/judge disagreement rate;
- task completion utility;
- review rate;
- latency/cost overhead;
- per-task-family and per-model breakdown.

## Critical Controls

- Postconditions are frozen before model execution.
- The agent must not see verifier implementation details beyond the task specification.
- The judge prompt/model/version are frozen.
- At least one cheap non-LLM baseline is included where applicable.
- Partial completion is explicitly encoded so the verifier does not manufacture a binary ground truth from ambiguous tasks.
- Fixtures must include true success, false claimed success, partial success, and malformed state.

## Novelty Gate

Before preregistration is locked, build a closest-work table covering reward-hacking/task-completion benchmarks, judge gaming, environment-based agent evaluation, and deterministic agent guardrails. Final Praxis 001 survives only if the exact empirical comparison and outcome-state framing are not already directly evaluated at comparable scope.

## Kill Criteria

Stop or downgrade if any of the following is true:

- the closest literature already performs the same deterministic postcondition-vs-judge experiment;
- postconditions cannot be defined without subjective adjudication for a large fraction of tasks;
- deterministic verification rejects legitimate alternate solution paths at an unacceptable rate;
- the judge baseline is so weak or artificial that beating it is scientifically uninteresting;
- the task suite is too trivial to create meaningful judge/verifier disagreement.

## Promotion Boundary

A positive result may support a claim about **the tested task families, models, verifier definitions, and sandbox**. It must not be generalized into a claim that deterministic verification solves reward hacking or guarantees safe autonomous agents.
