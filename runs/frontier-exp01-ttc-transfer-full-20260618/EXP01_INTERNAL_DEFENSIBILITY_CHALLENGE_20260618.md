# EXP01 Internal Defensibility Challenge

Generated: 2026-06-18T16:40:09.691927+00:00

## Defense Verdict

Verdict: **PROVISIONAL / DO NOT OVERCLAIM**

The experiment now has results and proper split discipline. It is defensible as a first-pass open-model TTC transfer matrix if the report keeps the exact limitations visible. It is not yet a complete Praxis-level paper claim because verifier-based best-of-N, sequential refinement, and multi-seed decoding were deferred.

## Challenge Questions

| Challenge | Answer |
|---|---|
| Is the transfer matrix complete for the configured model set? | `True` (32 rows). |
| Is there a strict holdout not used for policy selection? | `True`. |
| Are off-diagonal transfer rows present? | `True`; mean off-diagonal retention `1.4515`. |
| Are diagonal target-optimal controls present? | `True`. |
| Were final test/holdout rows used for policy selection? | No; policy selection is defined on GSM8K validation-policy rows. |
| Did the run test H1 fully? | No. H1 requires verifier/scorer best-of-N; this first run tests majority-vote transfer only. |
| Did the run test H3 fully? | No. Sequential refinement was deferred. |
| Did Optuna tune only the predictor? | Predictor status `COMPLETE`, leave-one-target-family R2 `-14.9408`; no prompt/budget rescue path is implemented. |
| Is answer scoring fully semantic? | No. It is strict normalized exact-answer scoring. This is conservative but may undercount equivalent math expressions. |
| Is the result ready for a defense slide? | Yes, as preliminary full-run evidence with limitations. Not yet as final dissertation claim. |

## Required Before Praxis Promotion

1. Add a verifier/scorer-based best-of-N condition.
2. Add sequential self-refinement or explicitly drop H3.
3. Add at least one more decoding seed or justify bootstrap-over-problems only.
4. Manually audit exact-answer scoring on a random sample and report agreement.
5. Expand or replace strict math scoring with a symbolic/math verifier if exact matching undercounts too heavily.
