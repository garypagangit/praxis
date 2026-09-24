# Complete Results and Interpretation

## Evidence inventory

The completed experiments support an applied measurement contribution: a higher aggregate APT-stage score does not necessarily preserve warnings for a particular attack stage. This result is reported alongside improvements, unsuccessful method comparisons, false-alert costs, and the limits of the source labels. This chapter adds a complete publication inventory to the main paired-results narrative; it introduces no new model fit, inference run, threshold, or favorable-condition selection.

| Completed study | Saved evaluations | Comparison coverage | Evaluation population |
|---|---:|---|---|
| Context selection (PX080) | 105 | Seven arms × five conditions × three fits | 208,094 UNRAVELED flows |
| Evidence acquisition (PX081) | 171 | Six policies × three budgets × three conditions × three fits, plus nine unrestricted references | Same 208,094 flows |
| Temporal composition (PX082) | 18 | Two feature views × three fitting protocols × three fits | Fixed anchor 104,051 flows; random comparison 210,226 flows |
| Secondary technique-policy transfer (PX083) | 294 | Seven arms × 21 views × two datasets | CasinoLimit: 920 targets; CAM-LDS: 4,209 targets |

An evaluation record is one saved arm/condition/seed result, not a new dataset or independent attack. Primary fitting seeds reuse the same events. In the supplement, the 21 views represent 15 condition names: each of three random-loss conditions has three perturbations, and the remaining twelve conditions have one deterministic view. The supplement's underlying classifiers were previously trained on their respective sources; only the two score selectors were fitted on CasinoLimit calibration predictions and applied unchanged to CAM-LDS.

The [complete printable mean tables](COMPLETE_GROUP_TABLES.md) retain all **308 group means**. Machine-readable supplements contain all **588 evaluation records**, **1,764 class-metric records**, and **5,880 confusion cells**, plus **6,732 subgroup records** and **16,344 subgroup-class records** where the original experiments supplied them. Full source JSON preserves fields beyond the normalized tables. The acquisition reference-only arms have no matched acquisition budget and cannot support same-budget superiority claims.

## What the complete acquisition inventory shows

The main clean, budget-three comparison raises mean macro-F1 from 0.7148 to 0.7379, reduces exfiltration warning recall from 85.18% to 76.25%, and increases mean benign false alerts from 111.3 to 122.3. Exact exfiltration recall changes only from 67.29% to 67.18%. A nearly unchanged number of exact-stage errors therefore conceals a consequential change in where those errors go: another attack label or benign. Warning recall denotes a non-benign model prediction; no analyst response was observed.

![Complete acquisition contrasts](figures/fig04_acquisition_complete_tradeoffs.png)

**Figure. Complete acquisition contrasts.** Every condition/budget group is included. Differences are error-focused minus entropy acquisition. Macro-F1 is displayed as score points (raw difference multiplied by 100); recall differences are percentage points. Each comparison uses the same 3,442 exfiltration and 192,193 benign records. Three-fit means describe fitting variation. Simulated costs, delivery delays, missing channels, and wrong-host history do not represent measured collection behavior.

The error-focused policy has higher mean macro-F1 in eight of the nine groups. Exfiltration warning recall is lower in all nine. The wrong-host, budget-three group has both lower F1 and lower warning recall, so it must remain visible rather than being described as an overall success. The observed higher-F1/lower-warning count is 19 of 27 paired fitting-seed comparisons, or 17 of 24 distinct ordered aggregate confusion signatures. These are dependent comparisons, not independent replications. Clean and wrong-host budget-one outcomes repeat because that budget cannot acquire history.

The error-focused policy spends less simulated budget than entropy in every reported group, but its exact-stage weighted error is not consistently lower. Actual collection savings, analyst workload savings, and safer deployments were not measured. This finding supports reporting error destinations and resource use together; it does not establish that the tested policy is a generally better detector.

## Selector controls expose the false-alert tradeoff

The stage-harm selector improves mean movement recall relative to ordinary gating under all five tested conditions. For clean history, movement recall rises from 64.76% to 69.52%, while benign false alerts rise from 85.67 to 109.00. For a five-minute stale snapshot, recall rises from 49.52% to 63.81%, while false alerts rise from 85.00 to 113.33. The stage-harm selector has worse weighted error than ordinary gating in every condition. Its training weights are illustrative research choices, not externally validated harm ratios.

![All context-selection controls](figures/fig05_selector_stage_workload.png)

**Figure. Movement recognition and benign false-alert cost.** All seven arms and all five conditions are shown. The denominator is 35 movement-labeled flows and 192,193 benign flows, with means over three fits. Movement labels denote author-annotated Remote System Discovery on one host pair. Missing, stale, and wrong-host histories are simulated interventions. Every cell shows a three-fit mean; darker shading means a larger value of the quantity in that panel.

The strongest simple control remains informative. Current features plus roles retain 78.10% mean movement recall regardless of the history intervention because the arm does not use history. Under entirely missing history, ordinary context-dropout training achieves 68.57% movement recall, compared with 42.86% for the proposed stage-harm gate. This rules out describing the learned gate as a dominant or reliably protective solution.

## Ranking metrics and operating decisions answer different questions

The supplements retain per-class average precision and ROC-AUC wherever the original source reported them. They are not reconstructed from hard labels or replaced with approximations. The normalized CSV uses blank fields when a metric was unavailable; source JSON preserves original null values. A class can have strong ranking performance while precision or its selected operating decision remains problematic.

For a concrete existing result, the clean current-plus-roles fit with seed 20260924 identifies 26 of 35 movement-labeled flows. Its movement ROC-AUC is 0.998918, average precision is 0.210308, precision is 0.184397, and recall is 0.742857. The 141 movement predictions include 26 correct labels. This is an actual aggregate from the saved evaluation, not a fabricated example or a production alert rate. Reporting ROC-AUC alone would not describe that operating-point burden. No new ROC curves are inferred from the aggregate tables.

## Temporal controls and sensitivity

The controlled current-feature comparison raises macro-F1 by 0.0632 when the fitting pool can include later-period non-anchor observations. It retains the same 104,051 evaluation rows, fixed architecture, and matched class-specific fitting counts. This is a measured effect of changed training composition and temporal access; it does not isolate time from the diversity or dependence of the additional observations. The conventional random arm evaluates 210,226 different rows and is reported separately.

With past-only fitting, adding history increases macro-F1 from 0.7365 to 0.7582 and reduces mean benign false alerts from 24.0 to 14.3, while losing an average of seven exfiltration warnings among 1,722 exfiltration-labeled anchor rows. The warning loss is 0.41 percentage points. This favorable score/workload comparison still contains a smaller stage-specific cost; the uncertainty and denominator belong beside both directions.

![Fitting-seed influence](figures/fig06_fitting_seed_influence.png)

**Figure. Fitting-seed influence on the clean budget-three acquisition comparison.** The three-fit mean and every leave-one-fit-out mean use fixed saved predictions. Excluding seed 8101 reduces mean warning loss from 8.93 to 0.36 percentage points and additional missed warnings from 307.33 to 12.50. The qualitative mean direction remains, but the original effect magnitude is not stable across fits. These ranges are finite sensitivity summaries, not confidence intervals or refits.

The complete sensitivity audit retains 180 single-capture omissions and 36 seed-omission means. All nine group means exhibiting higher F1 and lower warning recall retain that direction after every specified single-capture and single-seed omission. Individual seed behavior is less uniform: clean budget-three reversals occur in ten of fifteen seed/capture-omission combinations. Current-feature and history-feature mixed-minus-past F1 remain positive in all fifteen omission combinations each; chronological history-minus-current F1 is positive in fourteen of fifteen. Removing a capture changes the evaluated population, not the fitted model. Neither deletion exercise supplies an independent campaign.

## Secondary technique-policy transfer

The secondary study targets **T1105, Ingress Tool Transfer**. It is not a replication of lateral-movement recognition or exfiltration warnings. Negative examples have other author technique labels, so their flags cannot be called benign false alarms. CasinoLimit onset proxies and CAM-LDS labeled interval proxies also represent different target units; results are not pooled across them.

![Secondary policy transfer across all conditions](figures/fig08_secondary_policy_transfer.png)

**Figure. Secondary transfer under all fifteen condition names.** Values are target-cost gate minus current expert in percentage points. A positive recall difference and a negative other-label flag difference are favorable in their respective columns; colors indicate the numerical sign, not a common benefit direction. Random-loss conditions average three perturbations of the same events. Other conditions use one deterministic view.

On clean CasinoLimit data, the current expert and ordinary gate both achieve F1 0.7368, recall 82.35%, and seven other-label flags. The target-cost gate and context expert achieve F1 0.5957 with the same recall and sixteen flags. On clean CAM-LDS, the current expert achieves F1 0.0495, recall 87%, and 3,329 other-label flags; the target-cost gate/context expert achieves F1 0.0534, recall 88%, and 3,108 flags. High target recall therefore coexists with poor discrimination against other technique labels.

A saved post-result diagnostic found only eleven nonzero expert-error comparisons among 1,494 CasinoLimit calibration rows. The target-cost selector's hard decisions match the context expert in every one of the 21 views on each source; different probability vectors do not establish a different operational decision. The ordinary selector matches the current expert in all CasinoLimit views and nine CAM-LDS views. These findings do not support a new adaptive advantage. Original native thresholds are preserved separately; they were not used to tune the transferred policies.

## Interpretation and reproducibility boundary

The observations establish a completed measurement result: under the tested changes, a better aggregate classification score can accompany fewer attack labels for exfiltration-labeled records, and useful history gains can have a warning cost. The practical proposal is to report exact-stage recognition, warning retention, benign workload, denominators, and protocol support together before accepting a model update. That proposed practice benefit is an inference; the experiment did not measure better human decisions or fewer successful attacks.

The publication build independently checks confusion totals, source precision/recall/F1, and four-class macro-F1, while preserving score-derived metrics and all source hashes. It produces no new fitting results. Source labels, the previously examined single campaign, sparse movement support, retrospective warning analysis, and shared events constrain generalization. The secondary technique task broadens the diagnostic context but does not remove those primary-study limits.
