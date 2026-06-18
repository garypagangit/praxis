# EXP01 Full AWS Result

Generated: 2026-06-18T16:40:09.691290+00:00

Status: **RESULTS PRESENT - INTERNAL DEFENSIBILITY REVIEW REQUIRED BEFORE CLAIM PROMOTION**

## Run Scope

- Models: `4` open models
- GSM8K rows sampled: `80`
- MATH-500 strict holdout rows sampled: `80`
- Budgets evaluated: `K=1,2,4,8`
- Strategies evaluated: `single_sample`, `majority_vote`
- Policy selection: GSM8K validation-policy rows only
- Strict holdout: MATH-500 rows were not used for policy selection

## Dataset Access

| Dataset | Visible rows | Sampled rows | Role |
|---|---:|---:|---|
| `gsm8k` | 1319 | 80 | policy_selection_and_in_domain_test |
| `math500` | 500 | 80 | strict_domain_holdout_test |

## Selected Validation Policies

| Model | Strategy | K | Validation accuracy |
|---|---|---:|---:|
| `qwen2p5_7b_instruct` | `majority_vote` | 8 | 0.8250 |
| `qwen2p5_math_7b_instruct` | `majority_vote` | 8 | 0.1750 |
| `deepseek_r1_distill_qwen_7b` | `majority_vote` | 8 | 0.0500 |
| `mistral_7b_instruct_v0p3` | `single_sample` | 1 | 0.0500 |

## Model / Strategy Accuracy Summary

| Model | Strategy | K | Split role | Rows | Accuracy | Mean entropy | Mean margin |
|---|---|---:|---|---:|---:|---:|---:|
| `deepseek_r1_distill_qwen_7b` | `majority_vote` | 2 | `test_in_domain` | 40 | 0.0000 | 0.6931 | 0.0000 |
| `deepseek_r1_distill_qwen_7b` | `majority_vote` | 2 | `validation_policy_selection` | 40 | 0.0250 | 0.6758 | 0.0250 |
| `deepseek_r1_distill_qwen_7b` | `majority_vote` | 2 | `strict_domain_holdout_test` | 80 | 0.0000 | 0.6931 | 0.0000 |
| `deepseek_r1_distill_qwen_7b` | `majority_vote` | 4 | `test_in_domain` | 40 | 0.0000 | 1.3863 | 0.0000 |
| `deepseek_r1_distill_qwen_7b` | `majority_vote` | 4 | `validation_policy_selection` | 40 | 0.0250 | 1.3570 | 0.0187 |
| `deepseek_r1_distill_qwen_7b` | `majority_vote` | 4 | `strict_domain_holdout_test` | 80 | 0.0000 | 1.3820 | 0.0031 |
| `deepseek_r1_distill_qwen_7b` | `majority_vote` | 8 | `test_in_domain` | 40 | 0.0000 | 2.0708 | 0.0063 |
| `deepseek_r1_distill_qwen_7b` | `majority_vote` | 8 | `validation_policy_selection` | 40 | 0.0500 | 2.0258 | 0.0219 |
| `deepseek_r1_distill_qwen_7b` | `majority_vote` | 8 | `strict_domain_holdout_test` | 80 | 0.0000 | 2.0548 | 0.0078 |
| `deepseek_r1_distill_qwen_7b` | `single_sample` | 1 | `test_in_domain` | 40 | 0.0000 | 0.0000 | 1.0000 |
| `deepseek_r1_distill_qwen_7b` | `single_sample` | 1 | `validation_policy_selection` | 40 | 0.0250 | 0.0000 | 1.0000 |
| `deepseek_r1_distill_qwen_7b` | `single_sample` | 1 | `strict_domain_holdout_test` | 80 | 0.0000 | 0.0000 | 1.0000 |
| `mistral_7b_instruct_v0p3` | `majority_vote` | 2 | `test_in_domain` | 40 | 0.1000 | 0.5892 | 0.1500 |
| `mistral_7b_instruct_v0p3` | `majority_vote` | 2 | `validation_policy_selection` | 40 | 0.0000 | 0.6065 | 0.1250 |
| `mistral_7b_instruct_v0p3` | `majority_vote` | 2 | `strict_domain_holdout_test` | 80 | 0.0375 | 0.6672 | 0.0375 |
| `mistral_7b_instruct_v0p3` | `majority_vote` | 4 | `test_in_domain` | 40 | 0.1250 | 1.1685 | 0.1500 |
| `mistral_7b_instruct_v0p3` | `majority_vote` | 4 | `validation_policy_selection` | 40 | 0.0250 | 1.1368 | 0.1625 |
| `mistral_7b_instruct_v0p3` | `majority_vote` | 4 | `strict_domain_holdout_test` | 80 | 0.0375 | 1.3050 | 0.0563 |
| `mistral_7b_instruct_v0p3` | `majority_vote` | 8 | `test_in_domain` | 40 | 0.0750 | 1.6452 | 0.1661 |
| `mistral_7b_instruct_v0p3` | `majority_vote` | 8 | `validation_policy_selection` | 40 | 0.0250 | 1.5433 | 0.2188 |
| `mistral_7b_instruct_v0p3` | `majority_vote` | 8 | `strict_domain_holdout_test` | 80 | 0.0750 | 1.9091 | 0.0797 |
| `mistral_7b_instruct_v0p3` | `single_sample` | 1 | `test_in_domain` | 40 | 0.0250 | 0.0000 | 1.0000 |
| `mistral_7b_instruct_v0p3` | `single_sample` | 1 | `validation_policy_selection` | 40 | 0.0500 | 0.0000 | 1.0000 |
| `mistral_7b_instruct_v0p3` | `single_sample` | 1 | `strict_domain_holdout_test` | 80 | 0.0375 | 0.0000 | 1.0000 |
| `qwen2p5_7b_instruct` | `majority_vote` | 2 | `test_in_domain` | 40 | 0.6000 | 0.3119 | 0.5500 |
| `qwen2p5_7b_instruct` | `majority_vote` | 2 | `validation_policy_selection` | 40 | 0.6750 | 0.2773 | 0.6000 |
| `qwen2p5_7b_instruct` | `majority_vote` | 2 | `strict_domain_holdout_test` | 80 | 0.1625 | 0.5805 | 0.1625 |
| `qwen2p5_7b_instruct` | `majority_vote` | 4 | `test_in_domain` | 40 | 0.6750 | 0.5890 | 0.5312 |
| `qwen2p5_7b_instruct` | `majority_vote` | 4 | `validation_policy_selection` | 40 | 0.7000 | 0.4981 | 0.6188 |
| `qwen2p5_7b_instruct` | `majority_vote` | 4 | `strict_domain_holdout_test` | 80 | 0.1875 | 1.1604 | 0.1531 |
| `qwen2p5_7b_instruct` | `majority_vote` | 8 | `test_in_domain` | 40 | 0.7250 | 0.8475 | 0.5344 |
| `qwen2p5_7b_instruct` | `majority_vote` | 8 | `validation_policy_selection` | 40 | 0.8250 | 0.6483 | 0.6312 |
| `qwen2p5_7b_instruct` | `majority_vote` | 8 | `strict_domain_holdout_test` | 80 | 0.2250 | 1.7227 | 0.1672 |
| `qwen2p5_7b_instruct` | `single_sample` | 1 | `test_in_domain` | 40 | 0.6000 | 0.0000 | 1.0000 |
| `qwen2p5_7b_instruct` | `single_sample` | 1 | `validation_policy_selection` | 40 | 0.6500 | 0.0000 | 1.0000 |
| `qwen2p5_7b_instruct` | `single_sample` | 1 | `strict_domain_holdout_test` | 80 | 0.2250 | 0.0000 | 1.0000 |
| `qwen2p5_math_7b_instruct` | `majority_vote` | 2 | `test_in_domain` | 40 | 0.0750 | 0.6585 | 0.0500 |
| `qwen2p5_math_7b_instruct` | `majority_vote` | 2 | `validation_policy_selection` | 40 | 0.1250 | 0.5892 | 0.1500 |
| `qwen2p5_math_7b_instruct` | `majority_vote` | 2 | `strict_domain_holdout_test` | 80 | 0.0375 | 0.6672 | 0.0375 |
| `qwen2p5_math_7b_instruct` | `majority_vote` | 4 | `test_in_domain` | 40 | 0.0750 | 1.2964 | 0.0625 |
| `qwen2p5_math_7b_instruct` | `majority_vote` | 4 | `validation_policy_selection` | 40 | 0.1250 | 1.2357 | 0.1062 |
| `qwen2p5_math_7b_instruct` | `majority_vote` | 4 | `strict_domain_holdout_test` | 80 | 0.0375 | 1.2877 | 0.0625 |
| `qwen2p5_math_7b_instruct` | `majority_vote` | 8 | `test_in_domain` | 40 | 0.0500 | 1.8882 | 0.0906 |
| `qwen2p5_math_7b_instruct` | `majority_vote` | 8 | `validation_policy_selection` | 40 | 0.1750 | 1.7949 | 0.1375 |
| `qwen2p5_math_7b_instruct` | `majority_vote` | 8 | `strict_domain_holdout_test` | 80 | 0.0625 | 1.8797 | 0.0938 |
| `qwen2p5_math_7b_instruct` | `single_sample` | 1 | `test_in_domain` | 40 | 0.0250 | 0.0000 | 1.0000 |
| `qwen2p5_math_7b_instruct` | `single_sample` | 1 | `validation_policy_selection` | 40 | 0.1000 | 0.0000 | 1.0000 |
| `qwen2p5_math_7b_instruct` | `single_sample` | 1 | `strict_domain_holdout_test` | 80 | 0.0500 | 0.0000 | 1.0000 |

## Transfer Retention Matrix Rows

| Source | Target | Eval role | Source policy | Target optimum | Source-on-target acc | Target-opt acc | Retention |
|---|---|---|---|---|---:|---:|---:|
| `qwen2p5_7b_instruct` | `qwen2p5_7b_instruct` | `test_in_domain` | `majority_vote K=8` | `majority_vote K=8` | 0.7250 | 0.7250 | 1.0000 |
| `qwen2p5_7b_instruct` | `qwen2p5_7b_instruct` | `strict_domain_holdout_test` | `majority_vote K=8` | `majority_vote K=8` | 0.2250 | 0.2250 | 1.0000 |
| `qwen2p5_7b_instruct` | `qwen2p5_math_7b_instruct` | `test_in_domain` | `majority_vote K=8` | `majority_vote K=8` | 0.0500 | 0.0500 | 1.0000 |
| `qwen2p5_7b_instruct` | `qwen2p5_math_7b_instruct` | `strict_domain_holdout_test` | `majority_vote K=8` | `majority_vote K=8` | 0.0625 | 0.0625 | 1.0000 |
| `qwen2p5_7b_instruct` | `deepseek_r1_distill_qwen_7b` | `test_in_domain` | `majority_vote K=8` | `majority_vote K=8` | 0.0000 | 0.0000 |  |
| `qwen2p5_7b_instruct` | `deepseek_r1_distill_qwen_7b` | `strict_domain_holdout_test` | `majority_vote K=8` | `majority_vote K=8` | 0.0000 | 0.0000 |  |
| `qwen2p5_7b_instruct` | `mistral_7b_instruct_v0p3` | `test_in_domain` | `majority_vote K=8` | `single_sample K=1` | 0.0750 | 0.0250 | 3.0000 |
| `qwen2p5_7b_instruct` | `mistral_7b_instruct_v0p3` | `strict_domain_holdout_test` | `majority_vote K=8` | `single_sample K=1` | 0.0750 | 0.0375 | 2.0000 |
| `qwen2p5_math_7b_instruct` | `qwen2p5_7b_instruct` | `test_in_domain` | `majority_vote K=8` | `majority_vote K=8` | 0.7250 | 0.7250 | 1.0000 |
| `qwen2p5_math_7b_instruct` | `qwen2p5_7b_instruct` | `strict_domain_holdout_test` | `majority_vote K=8` | `majority_vote K=8` | 0.2250 | 0.2250 | 1.0000 |
| `qwen2p5_math_7b_instruct` | `qwen2p5_math_7b_instruct` | `test_in_domain` | `majority_vote K=8` | `majority_vote K=8` | 0.0500 | 0.0500 | 1.0000 |
| `qwen2p5_math_7b_instruct` | `qwen2p5_math_7b_instruct` | `strict_domain_holdout_test` | `majority_vote K=8` | `majority_vote K=8` | 0.0625 | 0.0625 | 1.0000 |
| `qwen2p5_math_7b_instruct` | `deepseek_r1_distill_qwen_7b` | `test_in_domain` | `majority_vote K=8` | `majority_vote K=8` | 0.0000 | 0.0000 |  |
| `qwen2p5_math_7b_instruct` | `deepseek_r1_distill_qwen_7b` | `strict_domain_holdout_test` | `majority_vote K=8` | `majority_vote K=8` | 0.0000 | 0.0000 |  |
| `qwen2p5_math_7b_instruct` | `mistral_7b_instruct_v0p3` | `test_in_domain` | `majority_vote K=8` | `single_sample K=1` | 0.0750 | 0.0250 | 3.0000 |
| `qwen2p5_math_7b_instruct` | `mistral_7b_instruct_v0p3` | `strict_domain_holdout_test` | `majority_vote K=8` | `single_sample K=1` | 0.0750 | 0.0375 | 2.0000 |
| `deepseek_r1_distill_qwen_7b` | `qwen2p5_7b_instruct` | `test_in_domain` | `majority_vote K=8` | `majority_vote K=8` | 0.7250 | 0.7250 | 1.0000 |
| `deepseek_r1_distill_qwen_7b` | `qwen2p5_7b_instruct` | `strict_domain_holdout_test` | `majority_vote K=8` | `majority_vote K=8` | 0.2250 | 0.2250 | 1.0000 |
| `deepseek_r1_distill_qwen_7b` | `qwen2p5_math_7b_instruct` | `test_in_domain` | `majority_vote K=8` | `majority_vote K=8` | 0.0500 | 0.0500 | 1.0000 |
| `deepseek_r1_distill_qwen_7b` | `qwen2p5_math_7b_instruct` | `strict_domain_holdout_test` | `majority_vote K=8` | `majority_vote K=8` | 0.0625 | 0.0625 | 1.0000 |
| `deepseek_r1_distill_qwen_7b` | `deepseek_r1_distill_qwen_7b` | `test_in_domain` | `majority_vote K=8` | `majority_vote K=8` | 0.0000 | 0.0000 |  |
| `deepseek_r1_distill_qwen_7b` | `deepseek_r1_distill_qwen_7b` | `strict_domain_holdout_test` | `majority_vote K=8` | `majority_vote K=8` | 0.0000 | 0.0000 |  |
| `deepseek_r1_distill_qwen_7b` | `mistral_7b_instruct_v0p3` | `test_in_domain` | `majority_vote K=8` | `single_sample K=1` | 0.0750 | 0.0250 | 3.0000 |
| `deepseek_r1_distill_qwen_7b` | `mistral_7b_instruct_v0p3` | `strict_domain_holdout_test` | `majority_vote K=8` | `single_sample K=1` | 0.0750 | 0.0375 | 2.0000 |
| `mistral_7b_instruct_v0p3` | `qwen2p5_7b_instruct` | `test_in_domain` | `single_sample K=1` | `majority_vote K=8` | 0.6000 | 0.7250 | 0.8276 |
| `mistral_7b_instruct_v0p3` | `qwen2p5_7b_instruct` | `strict_domain_holdout_test` | `single_sample K=1` | `majority_vote K=8` | 0.2250 | 0.2250 | 1.0000 |
| `mistral_7b_instruct_v0p3` | `qwen2p5_math_7b_instruct` | `test_in_domain` | `single_sample K=1` | `majority_vote K=8` | 0.0250 | 0.0500 | 0.5000 |
| `mistral_7b_instruct_v0p3` | `qwen2p5_math_7b_instruct` | `strict_domain_holdout_test` | `single_sample K=1` | `majority_vote K=8` | 0.0500 | 0.0625 | 0.8000 |
| `mistral_7b_instruct_v0p3` | `deepseek_r1_distill_qwen_7b` | `test_in_domain` | `single_sample K=1` | `majority_vote K=8` | 0.0000 | 0.0000 |  |
| `mistral_7b_instruct_v0p3` | `deepseek_r1_distill_qwen_7b` | `strict_domain_holdout_test` | `single_sample K=1` | `majority_vote K=8` | 0.0000 | 0.0000 |  |
| `mistral_7b_instruct_v0p3` | `mistral_7b_instruct_v0p3` | `test_in_domain` | `single_sample K=1` | `single_sample K=1` | 0.0250 | 0.0250 | 1.0000 |
| `mistral_7b_instruct_v0p3` | `mistral_7b_instruct_v0p3` | `strict_domain_holdout_test` | `single_sample K=1` | `single_sample K=1` | 0.0375 | 0.0375 | 1.0000 |

## Predictor / Feature Engineering

Predictor status: `COMPLETE`.

Best leave-one-target-family R2: `-14.9408`.
Best Optuna parameters: `{'n_estimators': 130, 'max_depth': 5, 'min_samples_leaf': 4}`.
Interpretation: the feature-engineered transfer predictor did not generalize across held-out target model families.

Feature engineering used model-family metadata, source/target base validation accuracy, base-accuracy gap, strategy id, budget, and evaluation role. Optuna was limited to transfer-predictor hyperparameters and did not tune prompts, budgets, or final holdout behavior.

## Claim Boundary

This run can support a first-pass transferability analysis only. It does not yet support claims about verifier-based best-of-N or sequential refinement because those strategy classes were intentionally deferred until exact-answer scoring and majority-vote logging were stable.
