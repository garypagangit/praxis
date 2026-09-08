# Final Praxis Proposals

Updated: 2026-09-08T22:22:26+00:00
Branch: `Final-Praxis-Proposals`

[Live experiment dashboard](final_praxis/index.html) | [Execution and compute plan](final_praxis/execution/20260908/EXECUTION_PLAN.md) | [Frozen execution runbook](FINAL_PRAXIS_EXECUTION_RUNBOOK.md)

## Portfolio dashboard

| Final Praxis | Current status | Evidence | Next action | Report |
|---|---|---|---|---|
| **001 - Outcome-state verification** | Negative - verified complete | 400 cases independently verified. False-success acceptance: judge 7/200 (3.5%) versus state verifier 0/200; 205/400 judge responses violated the frozen schema. Required gap and collateral gates failed. | Completed: report and independent audit available. Schema noncompliance, observation access and template dependence limit the judge comparison. | [Report](final_praxis/001_outcome_state_verification/paper/PRAXIS_REPORT.md) |
| **002 - Cascade containment** | Negative - verified complete | 480 workflows independently verified. Invalid-action escapes: 10/60 ungated versus 0/60 full containment. Clean success 51/60 (85%) missed the frozen 90% floor. | Completed: five-chapter report and independently verified evidence available. Replication and redesign require a new protocol. | [Report](final_praxis/002_cascade_containment/paper/PRAXIS_REPORT.md) |
| **003 - Adaptive investigation stopping** | Negative - verified complete | 400 cases / 3,200 rounds verified. Reviewed stopping accuracy 34.5% versus fixed-long 54.25%; incorrect early endpoints later corrected in 34/400 cases (8.5%); all cases required review. | Completed: report, frozen cloud verification and separate local numerical replay available. Any policy redesign needs a new protocol. | [Report](final_praxis/003_adaptive_investigation_stopping/paper/PRAXIS_REPORT.md) |

## Scientific truth status

3 of 3 experiments have completed independent scientific verification. Local fixture validation is never substituted for real model evidence. A complete negative or mixed result is retained. A missing safety, sample-size, integrity or execution gate prevents scientific promotion.

## Claim discipline

- The studies use transparent inert generated benchmarks; external operational validity remains untested.
- Pre-outcome amendments document protocol repairs and close gaps without changing frozen hypothesis thresholds.
- Raw model outputs, exact model revisions, protocol hashes, paired comparisons and verifier reports support each determination.
- Prior PX-series outcomes are not inherited by these experiments.
- Replication is separate and follows a frozen discovery result.

## Execution sequence

All three builds and prechecks proceed concurrently. Shared Qwen inference executes eligible pilots and discovery workflows; 001 uses a distinct Mistral judge in a separate phase. Each completed experiment receives its own report and dashboard update.
