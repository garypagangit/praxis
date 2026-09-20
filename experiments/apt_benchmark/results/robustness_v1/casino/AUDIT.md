# Independent robustness result audit

**PASS** for saved-result computation and frozen calibration. This is an AI/code audit, not human label review or validation of novelty.

Dataset: **casino**. 3,758,674 context/source events; 8,240 eligible targets; 920 fixed test targets. Verified 204 condition/model results at both operating points, pooled and per run.

## Checks

- Streamed source hash, source manifest, original pre-fit code hashes, saved models, target roster and all used aggregate cache matrix/mask/row hashes verified.
- Labels derived independently from eligible source-bound metadata; all prediction rows preserve their order and target denominator.
- Confusion counts, precision/recall/F1, continuous-score ROC-AUC/AP, observation coverage and hidden-positive counts independently recomputed.
- Saved models were loaded only after byte verification for calibration-only inference. Strict sorted-negative thresholds and calibration confusion counts reproduced exactly. No fitting, test inference or tuning.

## Target support

| Target | Status | Test positives | Test negatives | Verified result rows |
|---|---|---:|---:|---:|
| T1068 | COMPLETE | 14 | 906 | 68 |
| T1548 | COMPLETE | 39 | 881 | 68 |
| T1105 | COMPLETE | 17 | 903 | 68 |

## Interpretation limits

- Fixed0.5 and separately frozen calibration thresholds are different operating points; an advantage at one is not an advantage at every flag budget.
- An empirical calibration flag budget does not establish reliable population or operational false-alarm control under shift.
- Positive source events, runs and corruption seeds can be correlated; no independent campaign count or confidence claim.
- Runs without positive target labels have no evaluated positive-class capability; numerical F1=0 follows the upstream convention only.
- Completely unobserved targets remain in the denominator with score0/no alarm; their evaluator-known roster is not a deployment trigger.
- AIT singleton deletion often removes whole events. Casino negatives are other source-annotated techniques, not verified benign activity.
- Synthetic deterministic delays use source event clocks, not measured collection times; full recovery after the delay is expected by construction.
- The feature cache was separately qualified against Replay; this audit binds its artifacts but does not independently reimplement all feature semantics.
- This audit validates reported computation, not novel mechanism, larger-model need, or broad robustness/generalization.

The pre-fit receipt binds source bytes but does not attest a Git commit or independent timestamp. Audit-time Git comparison and filesystem chronology are reported explicitly in [AUDIT.json](AUDIT.json), alongside all recomputed results, source hashes, calibration checks and delay-control equality checks.
