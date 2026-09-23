# Retrospective capture and fitting-seed sensitivity audit

## Evidentiary status

This is a bounded retrospective robustness audit of previously exposed results. Prior reanalysis already showed fitting-seed heterogeneity and repeated conditions. Freeze this plan, executable code, synthetic tests and input hashes before computing the new sensitivity outputs. No models, thresholds, loss weights, observations or datasets are fitted or selected. This is not independent confirmation, a prospective test, or a search for a favorable subset.

Read only the public sufficient statistics and paired results in `measurement_praxis/evidence/paired_reanalysis/`. The original private probability and row-identity audits remain separate; this audit never opens private data. Report every specified omission, including nulls and contrary directions. Preserve all original files unchanged.

## Fixed comparison inventory and quantities

Include all 36 original pairs: 27 PX081 harm-minus-entropy comparisons (three conditions by three budgets by three fitting seeds) and nine PX082 pairs (current mixed-minus-past, history mixed-minus-past, and chronological history-minus-current, each at three seeds). Retain the original baseline/candidate orientation.

For each side and difference, compute fixed-four-class macro-F1, DataExfiltration warning recall (any nonbenign prediction among the true exfiltration-labeled events), LateralMovement exact-stage recall, benign false-alert rate, exfiltration-to-benign count and benign false-alert count. Macro-F1 is null if any of the four true classes is absent. Each rate is null when its denominator is absent; counts remain defined at zero support. No silent class dropping or absent-class zero F1 is permitted. Preserve the prepared experiment's four-class meanings; these are not a universal author taxonomy. The movement target describes Remote System Discovery progress on one host pair, not independently verified successful lateral movement.

Define the directional flag `f1_up_exfil_warning_down` when candidate-minus-baseline macro-F1 is greater than 1e-12 and exfiltration warning difference less than -1e-12. Define the reverse combination and a combined sign-disagreement flag as well. If a required value is null the flag is null, not false. The tolerance prevents floating-point artifacts and is not a practical-significance gate.

## A. Exhaustive leave-one-capture-out calculation

For each of all 36 pairs, omit each of the same five source captures (6, 7, 8, 9, 10) in turn: **180 paired omission results**. Sum the remaining capture confusion matrices before calculating metrics. Both methods omit precisely the same capture. Record the retained row counts and support for all four classes alongside both methods, paired differences and direction flags.

This is a perturbation of the evaluation population while predictions stay fixed. It does not refit models, remove the omitted capture from any original fitting history, estimate generalization to an unseen capture, or create independent campaigns. Remaining capture sizes keep their observed event weights. Report each omitted capture's exact identity; do not choose the most favorable omission.

For concise presentation, also average the three seed-specific paired point estimates separately for each of the five capture omissions in each of the 12 experiment groups. Never pool repeated seed rows. Report the full-data group difference, the minimum/maximum among the five mean omission differences, and counts of defined favorable/unfavorable/unchanged directions. The complete seed-specific 180 rows remain available.

## B. Exhaustive leave-one-fitting-seed-out calculation

For each of the 12 condition/budget/contrast groups, omit each of its three seeds: **36 seed-omission summaries**. Average the two remaining seed-specific metrics and paired differences arithmetically; do not add their confusion matrices or pool their flows. Include the three-seed point mean as a reference. If any retained seed lacks support for a required metric, its mean remains null; do not silently remove that seed.

Report all three omissions and their range. Highlight clean budget-three heterogeneity using the same predeclared metrics and count changes as every other group. No confidence interval, p-value, seed-independence claim or new significance gate is attached to these leave-one-out ranges. They are finite observed sensitivity ranges, not statistical confidence bounds.

## C. Aggregate-equivalent comparison inventory

For all 27 PX081 pairs, hash a canonical ordered payload containing class order, capture order, baseline per-capture 4 x 4 confusion counts, and candidate per-capture confusion counts. Condition, budget and fitting-seed names are not part of the signature, so repeated sufficient statistics can be identified. Baseline and candidate remain ordered; an inverse contrast is not equivalent. Include every equivalence class, member comparison ID, class size, and its direction flags.

Report the original comparison-count statement (previously 19 of 27 macro-F1-up/exfil-warning-down pairs) next to the number of aggregate-equivalent signature classes showing that direction. Do not call the class count an independent replication count, deduplicate away contrary results, or claim equal confusion matrices prove identical row-level predictions. Different predictions can have the same confusion counts; all classes still share a campaign and many rows/models. Equivalence of the sufficient statistics supports only equivalence for the metrics and capture-resampling arithmetic computed from them.

## Verification and outputs

Before evaluation, verify the new source bytes against the parent-provided Git freeze commit and verify every public input hash against the recorded manifest. Check the complete contrast inventory and same capture-stage support marginals. Recompute full-population points and compare them to the previous paired tables; check all 12 prior means. Use direct confusion formulas for the audit and independently cross-check each full/omitted calculation with the previously published standalone public verifier, whose code hash is bound as an input. Synthetic tests cover undefined classes, sign directions, capture weighting, distinct confusion-equivalent predictions, ordered signatures and arithmetic seed means versus pooled-F1 differences.

Public outputs will include complete paired capture omissions JSON/CSV, seed omissions JSON/CSV, compact group summaries, all aggregate-equivalence classes, a plain-language report, source/input/output SHA256 receipts and arithmetic-audit status. No private probabilities are exported. New files stay entirely under `submission_readiness/sensitivity/`; no original experiment, reanalysis or manuscript is edited by this task.
