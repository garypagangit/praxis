# Retrospective paired reanalysis of stage recognition and attack warnings

## Status and scope

This plan is frozen **after the original PX081/PX082 experiments and selected warning-recall observations were examined**, but before computing this complete reanalysis. It is retrospective, not a preregistration of the original experiments or an independent confirmation. No model is fitted, selected, tuned or recalibrated. Existing probability vectors retain their native argmax decision rule, including first-column tie breaking. All specified comparisons are reported, regardless of direction.

The analysis addresses a measurement question: can a higher macro-F1 coexist with more true attack events being classified as benign? It does not claim that the underlying metrics are new, that a causal mechanism has been identified, or that the best deployment system has been established.

## Fixed inputs and comparisons

Use the unchanged prepared UNRAVELED source and original private probability archives, validating their hashes against the original PX081 artifact manifest and PX082 completion receipt. The source SHA256 is `b2a491474e722f4dabcd4c419c83a4a6b49f08dfc3bc059aa42ef2aaa4c3de14`.

1. **PX081:** candidate harm policy minus baseline entropy policy, all clean/delayed_unavailable/wrong_host_history conditions, budgets 1/2/3, seeds 8101/8102/8103: 27 comparisons. Both policies use the same 208,094 later-test rows in every comparison. Availability, delays and wrong-host context are simulated interventions, not measured collection conditions.
2. **PX082:** candidate time_mixed_anchor minus baseline past_only_anchor for each current/current_history view; plus chronological candidate current_history minus baseline current on past_only_anchor. All seeds 20260923/20260924/20260925: nine comparisons. All use the same 104,051-row later anchor. Exclude conventional_random because it evaluates different rows. Deliberate future training is a protocol diagnostic, not a deployment-valid model improvement.

Native labels are explicitly 0 Benign, 1 OtherAttackStage, 2 LateralMovement, 3 DataExfiltration, as in these source experiments. This does not impose a universal stage mapping on other datasets. The movement annotation in this sensor is author Remote System Discovery progress on one host pair; it does not independently verify successful lateral movement. Completed-flow features and author progress labels do not support early warning, exfiltration forecasting, or confirmed theft claims.

## Identity qualification

Match PX081 evaluation truth, capture and event hashes to the exact source split=2 order. Match every PX082 saved test index, truth and capture vector to the frozen common anchor and prepared source. Require finite normalized four-column probabilities, unique original event hashes, identical ordered rows/truth/groups in each comparison, and no missing or duplicate requested archive. Real source capture IDs are groups; event hashes are row identities, never independent groups. Raw predictions, literal endpoints and event IDs remain private.

## Metrics

Use the frozen D1 native-label metric library, with its hash bound in FREEZE.json. For every attack stage report support, exact-stage recall, stage F1, warning recall, attack-to-benign count (lost warning), and wrong-attack-stage count. Warning recall is the fraction of the true stage receiving any nonbenign prediction. Exact recognition, wrong attack stage and benign prediction must partition the stage support. Also report fixed-four-class macro-F1, benign false-alert count/rate, and total missed-warning/wrong-stage counts. All deltas are candidate minus baseline; higher missed-warning/false-alert counts are unfavorable.

Every per-seed table contains both method points and paired deltas. Flag macro-F1-up/warning-down and the reverse directional pattern without a significance or magnitude gate. Aggregate tables show arithmetic means across exactly three seeds and counts of seedwise sign reversals. **Do not pool repeated seed rows, compute a confidence interval for their mean, or count seeds as independent datasets.**

## Paired capture resampling

Generate exactly 2,000 five-capture draws with replacement using NumPy default_rng seed 20260923. Construct one row-bound D1 plan for each evaluation cohort; reuse that plan for every comparison and seed on the cohort. Both cohorts must have the same ordered capture IDs and identical capture draws; publish the capture-only draw digest and the two row-bound plan digests. Repeated draws repeat whole captures, preserving their observed unequal row counts. Both methods always receive identical repetitions.

Report 95% percentile intervals of paired differences: macro-F1, false-alert rate/count, all stage recall/F1/warning differences, and missed-warning/wrong-stage count differences. Quantiles use NumPy linear interpolation. For a draw without a required true stage, stage rates/F1 are null; fixed-schema macro-F1 is null if any declared true class is absent. Report valid and undefined replicate counts and label affected intervals support-conditional. Counts remain defined even when stage support is zero; count intervals therefore include zero-support draws. These conventions differ from PX082's original 1,000-draw, seed-specific macro-F1 bootstrap, which inserted zeros for absent classes. Preserve the original results unchanged.

There are only **five capture fragments from one previously examined campaign**. Intervals are descriptive sensitivity to resampling these fragments, conditional on observed support where specified; they do not estimate uncertainty across independent campaigns or guarantee coverage. No multiplicity-adjusted confirmatory tests or p-values are claimed. Publish all 36 comparisons and all three attack stages to prevent selective reporting.

## Recomputability checks and outputs

Before computation, freeze this plan, executable code, synthetic tests, original input hashes and metric-library hash in Git through the parent agent. After authorization to execute the frozen analysis, verify exact source bytes against that commit, verify all original input hashes, and evaluate. An arithmetic audit independently forms per-capture confusion matrices, applies the shared capture multiplicities, recomputes paired points and percentile intervals without calling the D1 metric functions, and checks all three-seed means. This is code/arithmetic verification, not a human audit of author labels.

Public outputs: complete paired JSON; stage-level per-seed CSV; complete three-seed means JSON/CSV; capture-level confusion sufficient statistics; capture draw plan; a plain-language report; input/source/output hash and arithmetic-audit receipts. Private probabilities are read only and are never copied into the public repository. The report will distinguish observed sign disagreements from generalization, novelty and deployment claims.
