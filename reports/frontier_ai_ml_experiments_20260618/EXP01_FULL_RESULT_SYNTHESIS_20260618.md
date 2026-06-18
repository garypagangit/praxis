# EXP01 Full Result Synthesis

Date: 2026-06-18

Experiment: `frontier-exp01-ttc-transfer`

Status: **PRELIMINARY FULL RESULT PRESENT - PROVISIONAL / DO NOT OVERCLAIM**

## Run Summary

The first full EXP01 AWS run evaluated cross-model transferability of test-time compute policies on public GSM8K and MATH-500 rows. Policy selection used GSM8K validation-policy rows only. Final evaluation used a GSM8K in-domain test split plus a strict MATH-500 holdout that was not used for policy selection.

| Item | Value |
|---|---:|
| Open models | `4` |
| Public benchmark rows | `160` |
| Validation-policy rows | `40` |
| In-domain test rows | `40` |
| Strict MATH-500 holdout rows | `80` |
| Strategies | `single_sample`, `majority_vote` |
| Budgets | `K=1,2,4,8` |
| Score rows | `2,560` |
| Transfer rows | `32` |

Primary artifacts:

- `runs/frontier-exp01-ttc-transfer-full-20260618/EXP01_FULL_AWS_RESULT_20260618.md`
- `runs/frontier-exp01-ttc-transfer-full-20260618/EXP01_INTERNAL_DEFENSIBILITY_CHALLENGE_20260618.md`
- `runs/frontier-exp01-ttc-transfer-full-20260618/accuracy_summary.csv`
- `runs/frontier-exp01-ttc-transfer-full-20260618/transfer_retention.csv`
- `runs/frontier-exp01-ttc-transfer-full-20260618/predictor_analysis.json`

## Key Results

The strongest model was `qwen2p5_7b_instruct`. Its validation-selected policy was `majority_vote K=8`, with validation accuracy `0.8250`, in-domain test accuracy `0.7250`, and strict MATH-500 holdout accuracy `0.2250`.

The other configured models were much weaker under strict normalized exact-answer scoring:

| Model | Selected policy | Validation acc | In-domain test acc | Strict holdout acc |
|---|---|---:|---:|---:|
| `qwen2p5_7b_instruct` | `majority_vote K=8` | `0.8250` | `0.7250` | `0.2250` |
| `qwen2p5_math_7b_instruct` | `majority_vote K=8` | `0.1750` | `0.0500` | `0.0625` |
| `deepseek_r1_distill_qwen_7b` | `majority_vote K=8` | `0.0500` | `0.0000` | `0.0000` |
| `mistral_7b_instruct_v0p3` | `single_sample K=1` | `0.0500` | `0.0250` | `0.0375` |

Mean off-diagonal retention among non-null rows was `1.5920` in-domain and `1.3111` on strict holdout. Several high retention values are artifacts of weak target-optimal denominators, so this should be interpreted as evidence that transfer can be measured, not as evidence that transferred policies are broadly strong.

The feature-engineered Optuna predictor completed with best leave-one-target-family R2 `-14.9408`, using `{'n_estimators': 130, 'max_depth': 5, 'min_samples_leaf': 4}`. This is a negative RQ3 result for the tested features and small model-family set.

## RQ / Hypothesis Readout

| Item | Preliminary readout |
|---|---|
| RQ1 | Partially answered. The off-diagonal matrix is complete, but performance is dominated by Qwen2.5-7B and weak target denominators. |
| RQ2 | Not fully answered. Only majority voting and single-sample were tested; verifier best-of-N and sequential refinement are still missing. |
| RQ3 | Negative in this run. The feature-engineered predictor failed leave-one-target-family generalization. |
| H1 | Not tested. Verifier/scorer best-of-N was deferred. |
| H2 | Not supported yet. Predictor generalization was strongly negative. |
| H3 | Not tested. Sequential refinement was deferred. |

## Defense Position

Defensible claim: the EXP01 harness now supports strict split discipline, frozen generation logs, exact-answer scoring, source-policy selection, target-optimal controls, and transfer-retention computation across four open models.

Do not claim: that TTC strategies broadly transfer, that verifier-based best-of-N is better than majority voting, that sequential refinement transfers poorly, or that the current feature set predicts degradation.

## Required Promotion Work

1. Add verifier/scorer best-of-N.
2. Add sequential self-refinement or formally drop H3.
3. Manually audit exact-answer scoring and report agreement.
4. Add bootstrap confidence intervals for accuracy and retention.
5. Expand model-family diversity if RQ3 remains important.
