# PX-035 Thought-Budget Oracle Probe

Generated: 2026-06-30T11:20:20+00:00

Status: **MIXED - ORACLE UPPER BOUND EXISTS; CHEAP ROUTER NOT PROMOTED**

## Claim Boundary

This is a budget-control probe over the existing EXP01 test-time-compute run, not Long-CoT data collection or RLVR training. The deployable probe uses a cheap K=2 majority-vote self-consistency margin, selected on the validation-policy split, to decide whether to spend the full K=8 budget.

## Headline Result

A hindsight thought-budget oracle exists, but the cheap validation-selected margin router is not strong enough to promote PX-035 as a new positive research lane. On the strict MATH-500 holdout, the K=8 baseline accuracy is `0.0906` with mean tokens `2532.5`. The deployable K=2->K=8 router reaches accuracy `0.0906` with mean tokens `2445.1`; retention is `1.0000` and token savings are `0.0345`.

The hindsight oracle upper bound reaches accuracy `0.0969` with mean tokens `351.5`, showing there is budget structure in the frozen generations. The missing piece is a reliable cheap predictor of which rows deserve the long budget.

## EXP01 Budget-Router Scorecard

| Split | Policy | Accuracy | Mean tokens | Retention vs K8 | Token savings vs K8 | Escalation rate |
|---|---|---:|---:|---:|---:|---:|
| Validation policy | `k2` | `0.2062` | `568.9` | `0.7674` | `0.7492` | `0.0000` |
| Validation policy | `router` | `0.2625` | `1965.6` | `0.9767` | `0.1336` | `0.7812` |
| Validation policy | `k8` | `0.2687` | `2268.7` | `1.0000` | `0.0000` | `1.0000` |
| Validation policy | `oracle` | `0.2938` | `378.1` | `1.0930` | `0.8333` | `0.0000` |
| In-domain test | `k2` | `0.1938` | `593.7` | `0.9118` | `0.7498` | `0.0000` |
| In-domain test | `router` | `0.2062` | `2088.1` | `0.9706` | `0.1201` | `0.8125` |
| In-domain test | `k8` | `0.2125` | `2373.0` | `1.0000` | `0.0000` | `1.0000` |
| In-domain test | `oracle` | `0.2437` | `326.5` | `1.1471` | `0.8624` | `0.0000` |
| Strict holdout | `k2` | `0.0594` | `633.4` | `0.6552` | `0.7499` | `0.0000` |
| Strict holdout | `router` | `0.0906` | `2445.1` | `1.0000` | `0.0345` | `0.9406` |
| Strict holdout | `k8` | `0.0906` | `2532.5` | `1.0000` | `0.0000` | `1.0000` |
| Strict holdout | `oracle` | `0.0969` | `351.5` | `1.0690` | `0.8612` | `0.0000` |

## Selected Router Thresholds

| Model | Threshold | Validation K8 acc. | Validation router acc. | Validation router mean tokens | Reason |
|---|---:|---:|---:|---:|---|
| `deepseek_r1_distill_qwen_7b` | `1.001` | `0.0500` | `0.0500` | `2387.8` | min_tokens_retaining_95pct_validation_k8 |
| `mistral_7b_instruct_v0p3` | `0.025` | `0.0250` | `0.0250` | `2035.5` | min_tokens_retaining_95pct_validation_k8 |
| `qwen2p5_7b_instruct` | `0.025` | `0.8250` | `0.8000` | `1235.2` | min_tokens_retaining_95pct_validation_k8 |
| `qwen2p5_math_7b_instruct` | `0.025` | `0.1750` | `0.1750` | `2203.9` | min_tokens_retaining_95pct_validation_k8 |

## CTI Evidence-Budget Cross-Check

The PX-003 CTI ablation shows a separate budget frontier: vanilla prompt accuracy `0.642` at mean prompt tokens `88.5`, technique-only evidence accuracy `0.764` at `177.7` tokens, and relationship evidence accuracy `0.915` at `385.4` tokens.

That cross-check agrees with the EXP01 result: budget tiers matter, but the current evidence is not a standalone Long-CoT/RLVR result. It is a practical budget-control diagnostic that should be merged into EXP01/PX-003 style protocols.

## Decision

- Do not start Long-CoT collection or RLVR training for PX-035.
- Keep PX-035 as a mixed budget-control add-on: useful diagnostics and an oracle upper bound, but no deployable positive yet.
- A future positive would require a cheap predictor that retains at least 95% of K8 strict-holdout accuracy while saving at least 25% tokens across more model families.

## Artifacts

- Raw analysis JSON: [`runs/px035-thought-budget-oracle-20260630/px035_thought_budget_oracle.json`](../../runs/px035-thought-budget-oracle-20260630/px035_thought_budget_oracle.json)
- Per-row router CSV: [`runs/px035-thought-budget-oracle-20260630/px035_budget_router_rows.csv`](../../runs/px035-thought-budget-oracle-20260630/px035_budget_router_rows.csv)
- EXP01 full run: [`runs/frontier-exp01-ttc-transfer-full-20260618/`](../../runs/frontier-exp01-ttc-transfer-full-20260618/)
- CTI ablation cross-check: [`SEC_LORD_RELATIONSHIP_EVIDENCE_ABLATION_GATE_20260517.md`](../relationship_evidence_cti_compliance/SEC_LORD_RELATIONSHIP_EVIDENCE_ABLATION_GATE_20260517.md)
