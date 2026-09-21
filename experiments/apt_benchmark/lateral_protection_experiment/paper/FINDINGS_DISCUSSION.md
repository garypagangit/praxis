# Chapter 5. Discussion and conclusion

## 5.1 Measured improvements and their costs

The experiments produced useful improvements in false alarms, classification, and lateral-flow detection, depending on the intervention and comparator. These gains answer different practical questions. A quieter detector can reduce unnecessary flags while missing more attacks; a more sensitive detector can recover lateral activity while increasing false alarms. The contribution is to measure both sides of these choices under controlled attack fitting labels.

The preceding benign-label experiment provides the clearest classification improvement. With the same 160 attack fitting examples, increasing normal examples from 32 to 1,024 raised the selected tree's macro-F1 from 0.4421 to 0.6543 and reduced normal false positives from 10.04% to 0.40%. Lateral-flow detection declined from 94.24% to 83.06%. More normal training data therefore improved the overall score substantially, but that score concealed a cost to one consequential attack stage. This earlier experiment used the original development test and remains distinct from the subsequent weighting study.

The new experiment demonstrated a way to recover sensitivity. Across all ten primary fitting seeds, balanced LightGBM increased lateral-flow detection from 78.89% to 84.58%, a 5.69-percentage-point gain over natural weighting. Normal FPR increased from 0.378% to 0.611%, approximately 35 additional benign flags per evaluation of 14,965 normal flows. Training emphasis changed the measured balance between detection and false alarms. It did not improve every outcome or prove which balance an organization should accept.

## 5.2 What locked policy selection added

Among the six primary seeds with feasible selected policies, the candidate reduced verification FPR from 0.719% to 0.480% relative to the lateral-sensitive reference: 33.3% fewer false positives. Attack precision increased from 79.78% to 86.03%, and attack F1 increased from 0.8770 to 0.9044. Lateral detection declined from 88.2% to 84.5%, approximately 2.7 additional misses among 72 lateral flows per repeated fit. These are actual improvements in false alarms and alert quality, with an explicit detection cost.

Threshold adjustment explained much of this result. The candidate matched the threshold-only ablation in four of six seeds. Compared with that ablation, its mean FPR was 16.3% lower, while lateral recall was 0.46 percentage points lower. Broader detector selection supplied a limited additional benefit in two supports; it was not necessary for every improvement.

A further matched comparison revealed a favorable aggregate result. The lateral-sensitive reference produced 25.9% fewer false positives than the ordinary source-normal 1% threshold control, while mean lateral detection rose from 87.73% to 88.19%. This exploratory difference is small: both outcomes improved together in only two of six seeds. The reference also used labeled lateral examples for selection, whereas the ordinary threshold used normal selection examples. No confidence interval or claim of superiority across all stages, seeds, or incidents follows from this comparison.

## 5.3 Keeping the original requirement in perspective

The original screen required all ten primary seeds to supply a feasible policy, more than 20% relative false-alarm reduction, less than three percentage points of lateral-recall loss, at least 90% lateral recall, and at most 1% benign FPR. These were study-defined engineering requirements, not universal standards of acceptable cybersecurity performance.

The unchanged screen was INFEASIBLE: six seeds supplied a qualifying selection and four did not. Even within the feasible subset, mean verification lateral recall was below 90% and its loss exceeded three percentage points. That result remains valid, alongside the measured benefits. It does not make the false-alarm reductions disappear, and those reductions do not establish that the original joint requirement was met.

This findings-led emphasis is an interpretation after completion, not a new registered hypothesis. No threshold, model, outcome, or decision rule was changed. Infeasibility applies to the eight final CV-selected detectors and their thresholds in each support; it does not establish that every possible learning procedure is incapable of improvement.

## 5.4 Empirical contribution and literature position

The literature already motivates the interventions. Revell et al. (2026, Section 6.5) discuss increased benign support as a response to benign/attack ambiguity. Singhal and Kumar (2026) combine cost-sensitive learning with validation-selected thresholds under a miss constraint. Consequently, neither adding normal examples nor combining weights and thresholds is a new general algorithm.

The narrower contribution is measured evidence about these choices with attack fitting identities held fixed, normal-label budgets disclosed, stage-sensitive outcomes retained, and a threshold-only comparator available. The study shows why a higher aggregate score should be accompanied by a report of which attack activity becomes less visible. It also distinguishes improvements attributable to a changed operating point from improvements requiring another detector.

This is a defensible applied empirical contribution, subject to the institution's assessment of praxis scope and originality. It does not establish a first method, validated operational benefit, or guaranteed satisfaction of academic requirements. Fewer flow flags suggest a possible workload benefit; analyst time, investigation quality, and organizational losses were not measured.

## 5.5 Transfer and evidence limits

DEDALE illustrates why source improvements require external evaluation. The fixed source seed had no feasible candidate, so only ordinary controls were tested. Argmax detected one of four lateral flows with 7,418 false positives among 100,000 benign groups. Source-normal thresholding detected all four but produced 24,511 false positives. Greater sensitivity therefore had a substantial external false-alarm cost. All four flows belonged to one execution, and a single detected flow might already alert on that execution; these counts are not incident-level recall.

SCVIC was previously examined development data. Ten fitting seeds reuse the same verification flows, and exact-feature deduplication does not establish independent incidents. The candidate means cover six selected supports and cannot represent all ten. “160 attack labels” describes fitting only: selection, verification, and test required additional labels. The external sample and uncertain extractor equivalence further restrict generalization. Neither exact stage naming, actor attribution, early warning, nor reliable missing-log behavior follows from these flow-alert results.

## 5.6 Next study and conclusion

The next study should agree on acceptable missed-activity and false-alarm costs before collecting new outcomes, rather than inherit 90% recall as a standard. It needs independent lateral executions with legitimate remote-administration background, matched label and search budgets, and one locked evaluation. Incident grouping, uncertainty analysis, and eventual analyst-workflow measurement should be specified before confirmation.

The completed work demonstrates substantial false-alarm reductions and recoverable lateral sensitivity through different choices, with measurable costs attached to each. It provides evidence for comparing those choices rather than assuming that the largest overall score offers the best protection. The original joint screen remains unmet, while the positive empirical findings remain useful. Further independent evidence is required to turn a chosen tradeoff into an operational recommendation.
