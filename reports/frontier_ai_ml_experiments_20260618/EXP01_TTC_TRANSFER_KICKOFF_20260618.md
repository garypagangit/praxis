# EXP01 Kickoff - Cross-Model Transferability of Test-Time Compute Strategies

Date: 2026-06-18

Source brief: `C:\Users\garyp\Downloads\AI_ML_Praxis_Experiment_Templates.docx`.

## One-Sentence Goal

Measure whether test-time compute strategies selected on one model remain effective when transferred to other models, then fit a lightweight predictor of transfer degradation.

## Claim Boundary

This experiment is not a claim that more inference compute always helps. It is a map of where a TTC policy transfers, where it fails, and which cheap signals predict failure.

## Stage A - Harness Smoke

**Purpose:** prove that the measurement system works before spending GPU time.

**Scope:**

- Datasets: 50 total problems from GSM8K and/or MATH-500.
- Models: two low-cost model adapters. Acceptable initial choices are one local small model plus one API/local adapter, or two local small open models if available.
- Strategies: greedy/single-sample `K=1`, majority voting with `K={2,4}`, and a placeholder best-of-N scorer if an open verifier is not ready.
- Required logs: problem id, problem text hash, model, strategy, budget K, raw samples, selected answer, normalized answer, gold answer, correctness, token/cost proxy, seed.

**Pass criteria:**

- Exact-answer scorer agrees with a manual spot check on at least `95%` of smoke rows.
- Every run emits JSONL logs with the required fields.
- Retention can be computed as `target_acc(source_optimal_policy) / target_acc(target_optimal_policy)` from disjoint dev/test rows.
- The harness can rerun with fixed seeds and produce stable row counts.

**Fail criteria:**

- Answer extraction is too brittle to score math results.
- The run cannot separate dev tuning from final test evaluation.
- Token/cost logging is missing or inconsistent.

## Stage B - Minimal Transfer Matrix

**Scope:**

- Datasets: 200-500 problems, split dev/test.
- Models: at least three families or family/scale variants if available.
- Strategies: majority voting, best-of-N with verifier/scorer, sequential refinement only after the first two strategies are stable.
- Budgets: `K={1,2,4,8,16}` initially; expand only if the curve has not saturated.

**Decision metric:**

- Off-diagonal retention with bootstrap confidence intervals.
- Mean retention by strategy.
- Retention versus cheap feature distances: base accuracy, answer entropy, model scale, and source-target entropy divergence.

## Stage C - Formal Gate

**Promotion target:**

- Full transfer matrix over the selected model set.
- Predictor evaluated with strict model-family holdout.
- AIME or HumanEval held out as an out-of-distribution domain check.

**Pass target:**

- Predictor `R^2 >= 0.60` on held-out families, or a clear negative result showing transfer is unpredictable under the tested signals.
- Strategy ranking has confidence intervals narrow enough to support or reject H1/H3.

## Initial Work Items

1. Create the formal Praxis protocol: `reports/frontier_ai_ml_experiments_20260618/PRAXIS_EXP01_TTC_TRANSFER_PROTOCOL_20260618.md`.
2. Run the split-readiness gate with `scripts/run_frontier_exp01_ttc_split_gate.py`.
3. Implement normalized answer extraction for GSM8K/MATH-style answers in the model-generation harness.
4. Implement JSONL generation logging using the fixed required field list in `configs/frontier_exp01_ttc_smoke_20260618.json`.
5. Run the `K=1` baseline first.
6. Add majority voting.
7. Compute the first retention table on the smoke set.

## Compute Notes

Use AWS only after Stage A passes locally. The working AWS CLI profile is `praxis-build`; plain default AWS credentials are not configured.

Suggested cloud guardrail before any GPU run:

```powershell
aws sts get-caller-identity --profile praxis-build
```

## Current State After First AWS Run

The split-readiness gate passed on 2026-06-18 with 50 sampled rows, separated validation/test/strict-holdout roles, scoring-only labels, and zero model calls.

The first full preliminary AWS run is now complete under `runs/frontier-exp01-ttc-transfer-full-20260618/`. It evaluated four open 7B-class models on 160 public benchmark rows, wrote 2,560 score rows, and produced a 32-row transfer matrix. The internal defense verdict is **PROVISIONAL / DO NOT OVERCLAIM**.

Immediate next work is the promotion gate:

1. Add verifier/scorer best-of-N to test H1 directly.
2. Add sequential self-refinement or formally drop H3.
3. Manually audit exact-answer scoring on a random sample.
4. Add bootstrap confidence intervals for accuracy and retention.
5. Keep the negative predictor result visible: leave-one-target-family R2 was `-14.9408`.
