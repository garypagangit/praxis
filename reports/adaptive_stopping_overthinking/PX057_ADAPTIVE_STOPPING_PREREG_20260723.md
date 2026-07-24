# PX-057 Adaptive Stopping to Prevent LLM Overthinking

Date: 2026-07-23
Status: pre-registered; Gate 0 harness implementation active; no scientific result yet.

## Literature basis

The source paper, *When More Thinking Hurts: Overthinking in LLM Test-Time Compute Scaling*, reports that increasing reasoning compute can eventually reduce answer quality on some tasks. Its stated limitation is concentration on mathematical and scientific reasoning, leaving transfer to other domains unresolved.

## Claim to test

A precommitted stopping policy based on answer stability and uncertainty can stop reasoning before harmful correct-to-wrong changes, reduce consumed reasoning steps, and preserve final-answer accuracy relative to a fixed long-compute policy.

## Constructs

- **Overthinking event:** a trace contains a correct answer at an eligible earlier step but the fixed-budget final answer is incorrect.
- **Adaptive stop:** the first step at which the normalized answer is unchanged for `patience` consecutive steps and confidence clears the frozen threshold.
- **Prevented overthinking:** the adaptive stop is correct on a trace whose fixed-budget final answer is incorrect.
- **Early-stop harm:** the adaptive stop is incorrect on a trace whose fixed-budget final answer is correct.
- **Compute saving:** one minus adaptive steps divided by fixed-budget steps.

## Research questions and frozen gates

| ID | Hypothesis | Pass | Fail |
|---|---|---|---|
| H1 | Adaptive stopping preserves task accuracy while saving compute. | Accuracy is no worse than fixed-long by more than 1 percentage point, and mean step saving is at least 20%. | Either condition fails. |
| H2 | Adaptive stopping prevents harmful overthinking. | At least 25% of observable overthinking events are prevented, with a bootstrap 95% CI reported. | Prevention rate below 25%. |
| H3 | Stopping does not introduce excessive new errors. | Early-stop harm is at most 2% of all evaluated traces. | Harm exceeds 2%. |
| H4 | The policy transfers beyond its tuning domain. | On a frozen held-out domain, H1 and H3 still pass without threshold changes. | Either gate fails. |

## Arms

1. `fixed_short`: answer at a precommitted small reasoning budget.
2. `fixed_long`: answer at the maximum budget; primary baseline.
3. `answer_stability`: stop after repeated normalized answers; cheap control.
4. `stability_plus_confidence`: primary adaptive policy.
5. `oracle_best_step`: descriptive upper bound only, never a deployable comparator.

## Data plan

Phase A uses public mathematical reasoning benchmarks with stepwise answer snapshots. Phase B adds a frozen coding or scientific-QA domain. Prompts, models, decoding settings, maximum steps, normalization rules, and answer scorers must be frozen before generation.

Gold labels remain scoring-only. Policy thresholds are selected on validation traces and applied once to test traces. No prompt or threshold changes are allowed after test inspection.

## Required controls

- Equal maximum token and wall-clock budgets.
- Exact-answer scorer manually checked on a random sample.
- Fixed-short and fixed-long baselines.
- Answer-only stability control without confidence.
- Per-model and per-domain results; no pooling that hides failures.
- Trace completeness audit and missing-step exclusions reported.

## Negative-result interpretations

- If H1 fails, stopping signals do not preserve quality at the required savings.
- If H2 fails, overthinking may be too rare or insufficiently predictable for this policy.
- If H3 fails, stability/confidence creates premature commitment.
- If H4 fails, the signal is domain-specific and should be reported as such.

## Gate sequence

1. Gate 0: controlled fixtures validate parsing, normalization, stopping, and metrics.
2. Gate 1: small real-model trace pilot verifies that answer snapshots and scorers are usable.
3. Gate 2: frozen validation/test experiment evaluates H1-H3.
4. Gate 3: frozen-domain transfer evaluates H4.

## Current artifact paths

- Config: `configs/px057_adaptive_stopping_gate0_20260723.json`
- Harness: `scripts/run_px057_adaptive_stopping_gate.py`
- Tests: `tests/test_px057_adaptive_stopping.py`
- Gate 0 output: `reports/adaptive_stopping_overthinking/gate0_20260723/`
