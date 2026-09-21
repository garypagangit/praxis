# Review of a findings-led praxis framing

**Editorial and methodology review, September 21, 2026.** This note recommends a presentation of completed evidence. It changes no model, threshold, original hypothesis, protocol, or result. The recommendations were formed after the outcomes were known; they are an empirical synthesis, not newly confirmed prospective hypotheses.

## Recommendation

Lead with the measured improvements and explain their security costs next to them. The paper need not define its entire contribution as a negative feasibility study. The completed record supports an applied study of how benign-label availability, training emphasis, and alert selection change the false-alarm/lateral-detection tradeoff. It does not support saying that the original protection hypothesis passed.

Suggested title: **False-Alarm Reduction and Lateral-Movement Detection with Limited Attack Training Labels**.

Suggested thesis:

> In this development study, additional benign training examples and explicit alert-policy selection produced measurable reductions in false alarms and improvements in classification or alert precision, while stage-specific evaluation revealed the lateral-movement detection costs of those improvements.

Plain-language explanation: **We found ways to make the detector quieter and ways to recover more lateral activity, and measured the price of each choice. The useful finding is the quantified tradeoff, including where a selected policy improved the comparison and where it did not.**

Avoid retaining “while preserving” as an unqualified outcome claim in the title. It can remain the original research ambition, with its results reported separately.

## Positive findings that the evidence supports

| Completed comparison | Measured improvement | Cost and scope that must accompany it |
|---|---|---|
| Prior benign-label expansion: 32 to 1,024 normal fitting labels, same 160 attack labels; ten source fits | CV-selected tree macro-F1 rose **0.4421 to 0.6543**; normal FPR fell **10.04% to 0.40%** | Lateral-flow detection fell **94.24% to 83.06%**. This is the preceding 60-cell experiment on the original development test, not a new 152-cell result or independent confirmation. |
| Current candidate versus reference, same six feasible primary seeds | Verification FPR fell **0.71946% to 0.48001%**, a **33.28% relative reduction**. Mean attack precision rose **79.78% to 86.03%**, and binary attack F1 rose **0.87697 to 0.90436** | Lateral detection fell **88.194% to 84.491%**, a **3.704 percentage-point loss**; overall attack recall also fell. Four other primary seeds had no selected candidate. |
| Current candidate versus threshold-only ablation, same six seeds | FPR fell **0.57356% to 0.48001%**, a **16.31% relative reduction**; attack F1 rose **0.89342 to 0.90436** | Lateral detection fell **84.954% to 84.491%**. Policies were identical in four of six seeds; the mean difference arose in two. This supports a limited additional benefit, not a consistently superior new algorithm. |
| Current candidate versus ordinary argmax, same six seeds | Lateral detection rose **79.167% to 84.491%**, a **5.324 percentage-point improvement** | FPR rose **0.35416% to 0.48001%**; attack precision and F1 decreased. This is a sensitivity/workload choice, not an improvement in every score. |
| Current lateral-sensitive reference versus ordinary source-normal-threshold control, same six seeds | Mean FPR was **0.71946% versus 0.97115%** (25.92% lower), with mean lateral detection **88.194% versus 87.731%** | A favorable descriptive mean comparison within a selected six-seed subset; the policies use different selection information. The 0.463-point recall difference corresponds to one-third of a flow per repeated fit, not strong evidence of incident-level superiority. |

The current comparisons use the same **14,965 benign and 72 lateral verification feature groups** per seed. Decimal counts and rates are means of repeated model evaluations, not additional independent cases. The six-seed roster is 20260922, 20260923, 20260925, 20260927, 20260928, and 20260930.

These values are directly supported by [matched feasible aggregates](../../results/lateral_protection_v1/EVIDENCE.json), [all primary seeds and policy counts](../../results/lateral_protection_v1/REPORT.md), and the [earlier benign-label experiment](../../results/strong_benign_controls_v1/REPORT.md). Exact-stage weighting results in [CELL_METRICS.json](../../results/lateral_protection_v1/CELL_METRICS.json) provide another descriptive result: XGBoost lateral-stage recall rises from **58.75% with natural weights to 69.17% with lateral-times-four weights**, while exact lateral precision falls from **48.96% to 29.63%** and macro-F1 falls from **0.6550 to 0.5731**. Correct stage naming and flagging any attack must remain separate.

## Recommended research questions and contribution

Use these as the organizing questions for the completed synthesis; preserve the exact originally frozen questions and joint hypothesis in Methods.

1. **Benign training data:** With attack fitting identities held fixed, how do additional normal examples change false alarms, overall classification, and detection of each attack stage?
2. **Training emphasis:** At matched fitting budgets, what lateral-detection or exact-stage sensitivity is gained by weighting, and what happens to precision, other stages, and false alarms?
3. **Operating choice:** What verified false-alarm and precision improvements remain after selection is locked, and how much comes from threshold adjustment versus choosing another trained detector?
4. **Transfer:** Which source operating properties persist in the available external flow stress, and what evidence limits a claim of broader protection?

The completed contribution can be described as **an auditable comparison that makes the cost of false-alarm reduction visible under controlled attack fitting labels**. It supplies a practical decision framework: disclose normal-label budgets; assess both alerting and exact stage identification; compare locked operating policies on matching supports; retain unavailable policies; and test transfer before assuming that source calibration carries over. Describe this as the study's evaluation protocol and evidence, not an invented methodology with proven novelty.

This can be a legitimate empirical or applied praxis contribution if the program accepts original applied evidence, careful adaptation, and evaluation of an industry problem. It is not currently a validated novel algorithm or an independently confirmed deployment improvement. Whether it meets a particular institution's contribution requirement still depends on that institution's criteria; software completion cannot establish that judgment.

## Handling the original 90% requirement

The 90% lateral-recall floor, 1% FPR ceiling, recall-loss margin, and all-ten-seed prerequisite were **study-defined engineering requirements**, not universal industry standards. They are one prespecified assessment of the method, not a rule that makes every measured benefit worthless.

Keep a compact, prominent results subsection: **“Outcome of the original development requirement.”** It must report **INFEASIBLE, six feasible seeds out of ten**, all secondary infeasibility counts, and the recall cost among feasible seeds. Explain that this conclusion applies to the eight final CV-selected detectors and their observed thresholds per seed. It does not prove that every threshold, model, or lateral-detection approach fails. Conversely, removing or loosening the original criterion after seeing outcomes would not create a new confirmed success.

Suggested abstract order: practical problem; fixed-label design and 152 completed models; measured positive changes with paired recall costs; six-of-ten selection availability and original requirement; external-transfer limit; applied contribution. The abstract and conclusion should lead with what was learned, with the requirement outcome stated once clearly rather than repeated as the entire thesis.

## Minimum disclosures and pitfalls

- Keep the **preceding benign-label study** and **current weighting/selection experiment** separate by fit counts, partitions, and source receipts. A useful combined narrative is not permission to relabel them as one prospective experiment.
- Put **six feasible seeds** beside every candidate mean. Never compare a six-seed candidate with ten-seed ordinary means as a paired improvement. Keep four unavailable policies visible; unavailable is neither zero performance nor a successful policy.
- Preserve the threshold-only result, other-stage costs, and modest effect sizes. A headline relative FPR reduction should include absolute rates and the paired recall change.
- State that SCVIC is **previously examined development data**; repeated fitting seeds and exact-feature deduplication do not produce independent attacks. No significance or population confidence claim follows from these means.
- Describe **160 attack fitting labels**, not 160 total labels. Selection uses 426 attack labels, verification 427, and the original descriptive test 858; supports came from a larger known-label pool.
- DEDALE tested **ordinary controls only**, because the fixed source candidate was unavailable. The 1/4-to-4/4 lateral improvement cost **7,418-to-24,511 false positives per 100,000 benign groups**. All four flows represent one execution; one detected flow could already alert on that execution. No candidate-transfer success or deployment precision claim is supported.
- Do not equate lower flow flags with measured analyst-time savings, exact stage labels with actor attribution, or completed-flow classification with early warning. Those outcomes were not measured.
- Existing literature already covers class weighting, benign support, and constrained thresholds. This editorial review performed no new literature search and supplies no “first” or novelty guarantee. Retain the manuscript's documented prior-art boundaries.
- State that this is a **findings-led interpretation after completion**. Frozen code, results, original decision rules, and audits remain unchanged.

## Suggested concluding paragraph

> The completed experiments demonstrate substantial false-alarm reductions and improved classification or alert precision, while also showing how those gains can conceal lateral activity. Locked operating-policy comparisons quantify alternatives: among six feasible source supports, the candidate reduced false alarms by 33.28% and improved attack F1, at a 3.70-percentage-point lateral-detection cost. The original ten-support protection requirement was not met, and the external stress did not validate a constrained candidate. The praxis therefore contributes measured guidance on label budgets, training emphasis, and operating choices, together with clear evidence of where independent validation remains necessary.
