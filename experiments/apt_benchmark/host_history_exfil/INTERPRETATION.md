# What host roles and earlier activity actually improved

## Answer in plain language

**The model became better at ranking flows carrying the author's exfiltration-stage label, and it raised fewer false alarms on normal traffic. It did not become a consistently better movement-and-exfiltration classifier.** Adding roles and correctly linked earlier activity increased exfiltration average precision (AP) from **0.6363 to 0.8823**, while ordinary four-class decisions reduced normal false attacks from **157.33 to 47.00 per fit**, a **70.13% reduction** over the same 192,193 benign test flows.

The cost was substantial: movement flows recognized as any attack fell from **69.52% to 40.95%**. That is an average of **24.33 to 14.33 out of the same 35 movement flows**, or ten fewer recognized per fit. The model also assigned **zero of 1,101 exfiltration flows in the new department-to-private-services context to the exfiltration class**, under the ordinary largest-score decision, in every fit and every arm.

This is a useful positive result about **ranking information**, accompanied by a clear limitation in stage decisions under a change of destination role. It is not evidence that the requested movement-versus-theft problem has been solved.

## Numerical checks and comparable decisions

This note independently recomputed **all 3,084 numerical means** in [EVIDENCE.json](../results/host_history_exfil_v1/EVIDENCE.json) from the three seed records in [SUMMARY.json](../results/host_history_exfil_v1/SUMMARY.json). Every mean matches within `1e-12` absolute/relative tolerance, and the evidence's source-summary SHA-256 matches the actual summary. It did not rerun models or reuse the report's aggregation function. This check verifies summary arithmetic; independent prediction-level audit and source-label validity are separate questions.

The separate published [prediction audit](../results/host_history_exfil_v1/AUDIT.json) records `PASS`. That verifies saved-output calculations and associated checks; it does not independently verify successful movement or theft.

These are means of three fits on the same cases, not three independent test populations. The following table uses the largest of four class scores, consistently across methods:

| Method | Exfil AP | Exfil F1 | Exfil exact-stage recall | Movement any-attack recall | Normal flows called any attack |
|---|---:|---:|---:|---:|---:|
| Current flow | 0.6363 | 0.7561 | 67.53% | 69.52% | 157.33 |
| Flow + roles | 0.6782 | 0.7558 | 67.50% | 70.48% | 149.00 |
| Flow + earlier activity | 0.7300 | 0.7639 | 67.19% | 37.14% | 43.33 |
| Flow + roles + earlier activity | 0.8823 | 0.7641 | 67.17% | 40.95% | 47.00 |
| Flow + roles + wrong-host history | 0.6629 | 0.7548 | 67.52% | 69.52% | 142.67 |
| Roles alone | 0.0133 | 0.0000 | 0.00% | 0.00% | 0.00 |

AP describes how effectively a score ranks positive examples above negatives across decision thresholds. It is not the percentage of correctly labeled flows. Here its **+0.2460** improvement is much larger than the exact-stage F1 gain, **0.7561 to 0.7641**. Exfiltration recall slightly decreases, **67.53% to 67.17%**, while precision improves, **85.90% to 88.61%**. Four-class macro-F1 barely changes, **0.755153 to 0.755248**. Report these together rather than equating the AP gain with better final stage identification.

The normal false-attack rate decreases from **0.08186% to 0.02445%**. The movement loss is therefore not a denominator artifact: fewer normal flows are flagged, and more movement flows are dismissed as benign. Movement F1 also falls, **0.2861 to 0.2754**, despite higher movement precision. Reporting F1 alone would obscure the larger recall loss.

## What the controls tell us

Roles added to the current flow improve pooled exfiltration AP modestly, **0.6363 to 0.6782**, but do not improve exfiltration F1. Roles alone predict every test row as benign under the four-class decision. Coarse asset roles therefore do not solve the task by themselves.

Earlier activity added to the current flow improves AP to **0.7300**. Combining roles with correctly linked history raises AP to **0.8823**, compared with **0.6629** when the history belongs to a different, previously observed host. This supports the narrower interpretation that useful information exists in correctly linked temporal context in this dataset. It does not establish a causal attack explanation: repeated hosts, scripts, timings and environment-specific behavior remain possible sources of that information.

The aggregate gain is not uniform. Within the department-to-private-services subset, exfiltration AP is **0.5786** for flow-only, **0.8695** with roles, and **0.7876** with roles plus history. Thus adding history improves the pooled ranking while reducing ranking quality relative to roles alone in this important shifted context. The wrong-host control reaches **0.8132** there, also above the correctly linked combined arm. The shared-role result prevents a claim that history consistently resolves same-role stage ambiguity.

## The new-role failure is specific and important

The fitting data contain no exfiltration example from department to private services. That stratum contains **1,576 benign, 35 movement, and 1,101 exfiltration flows** in testing. The calibration subset contains neither movement nor exfiltration from this role pair. It cannot teach the model how to place a decision boundary for these target stages in that context.

With roles plus history, the largest-score decision labels an average **1,091 of those 1,101 exfiltration flows benign and ten as movement**; none are labeled exfiltration. With flow-only, all 1,101 are labeled benign. The zero exact-stage recall is not proof that the exfiltration score contains no information, but it is a direct failure of the ordinary decision rule on a new destination-role context.

The exfiltration-versus-movement ranking diagnostic is especially easy to overread: exfiltration is **96.92%** of the two-stage subset. A constant score already has AP equal to that prevalence. Combined-context pairwise AP of **0.9725** is only slightly above that reference; it must not be presented as 97% stage-classification accuracy.

## Fixed threshold comparisons reveal a usable score and its costs

The experiment already specified calibration-based exfiltration thresholds before fitting. This note reports them without selecting a new winning threshold. F1-maximizing calibration thresholds give no improvement from combined context: test exfiltration F1 is **0.7653** for flow-only and **0.7632** for roles plus history. The calibration period contains no movement flows.

The separate, predeclared non-exfiltration calibration-tail points expose the ranking gain at other operating choices. Each cell below shows **flow-only / roles plus history**. False exfiltration alerts include benign flows and other attack stages, not just normal traffic.

| Nominal calibration tail | Exfil precision | Exfil recall | False exfiltration labels | Movement wrongly labeled exfiltration, out of 35 |
|---|---:|---:|---:|---:|
| 0.1% | 84.61 / 86.58% | 67.53 / 67.41% | 422.67 / 360.00 | 0.00 / 0.00 |
| 0.5% | 74.40 / 75.57% | 67.55 / 74.48% | 805.33 / 827.67 | 0.00 / 8.00 |
| 1% | 67.11 / 63.63% | 67.56 / 90.46% | 1148.33 / 1774.00 | 0.00 / 17.33 |
| 2% | 57.31 / 48.90% | 67.57 / 92.58% | 1738.33 / 3328.67 | 0.00 / 24.67 |

At the 0.5% point, combined context improves both exfiltration precision and recall, but labels eight movement flows as exfiltration on average. At the 1% point, exfiltration recall rises from **67.56% to 90.46%**, accompanied by **1,148.33 to 1,774.00 false exfiltration labels** and **17.33 of 35 movement flows assigned the wrong stage**. The combined arm's 1,774 false labels comprise **816 benign, 940.67 other-stage and 17.33 movement flows**. That is useful sensitivity at a measurable cost, not a protected movement detector.

These percentages describe the calibration selection rule. They are not guarantees that later normal false alarms equal the nominal percentage, and the comparisons are not at equal achieved test false-alert counts. The improved detection at lower exfiltration thresholds must not be confused with preserving correct movement labels or with the ordinary four-class decision.

## What the source labels actually establish

The primary outcome is **author-defined campaign stage**, not independently verified successful movement or data transfer. Every IT-sensor movement example uses one directed host pair and Activity `Remote System Discovery`. The author exfiltration stage includes 88 IT-sensor flows annotated `Unsecured Credentials`, as well as transfer-related activities. The four label fields were excluded from predictors and the malformed CSV layout was corrected without inventing labels; neither measure independently validates the underlying security meaning.

Other important limits are one previously exposed emulated APT campaign, only 27 movement fitting flows and 35 later movement flows, no movement calibration examples, no target-stage calibration coverage in the shifted role pair, one fixed model configuration, and full-flow statistics available only after completion. This is not an untouched cross-campaign confirmation, adversary attribution, proof of stage progression, or measured early warning. Three fitting supports do not supply independent attack-level confidence intervals.

## A concrete next experiment

The next question should be: **Can context improve identification of event-verified exfiltration after the destination role changes, while retaining movement recognition under a declared analyst workload?** The current scores make this worth testing; they do not establish a working solution or a new algorithm.

1. **Collect verified outcomes in an isolated testbed.** Use marked dummy files with sender/receiver manifests for transfers, remote-execution or authenticated-session evidence for movement, and timestamped host/network observations. Record successful, failed and preparatory actions separately. Include benign administration, backups and legitimate large transfers matched to the attack traffic.
2. **Vary roles independently of the target.** Include movement, exfiltration and benign activity for the same relevant role pairs. Hold out complete executions and new hosts. Prespecify both a covered-role test and a deliberately unseen-role test; do not let a single role pair or attack schedule determine the label. Reserve movement examples and relevant role contexts for calibration where a coverage claim is intended.
3. **Test a context-support-aware decision rule as a new hypothesis.** Maintain separate movement and exfiltration scores and record whether the fitting/calibration data support that role context. In unsupported contexts, allow an explicitly budgeted ?suspicious, stage uncertain? review outcome instead of silently treating a weak class score as benign. Compare with unchanged flow-only, combined-context and ordinary multiclass decisions. This review option consumes workload and must count as such; it is not a successful stage label by definition.
4. **Set acceptable costs before the new evaluation.** Choose movement misses, stage-confusion costs, benign false alerts and review capacity with the intended analyst workflow. Freeze the decision rule and thresholds on fitting/calibration executions. Report exact stage identification, any-attack detection, unresolved reviews and actual event-level transfer/movement outcomes separately. Evaluate the declared operating curve rather than searching the final test set for a flattering threshold.

This follow-up would test whether the ranking information can be converted into decisions that survive role changes. The current defensible contribution is identifying both the useful context signal and the failure that a stronger decision rule and better ground truth must address.

## Evidence bindings

- Source/protocol freeze: `b6e9e8d`, as recorded in the published report.
- SUMMARY SHA-256: `7a4ff8f0df6c9301277edae92d5a9ac516276c10f45b53557caf31b1fdbb6f70`.
- EVIDENCE SHA-256: `96ddf38aa805a462cfc167b67ea60212ab498c6ace4ba7894df4dd9f978b47bf`.
- Protocol SHA-256 in source receipt: `db58c390a4ae3a8cbc70469e60e19d694c349b20b400efc761932fac8ce78e4a`.
- Seeds: `20260922`, `20260923`, `20260924`; six matched arms; 18 completed fits.
- Further scope: [frozen design](DESIGN.md), [data inventory](DATA_INVENTORY.md), [source review](DATASET_LITERATURE.md), and [full result tables](../results/host_history_exfil_v1/REPORT.md).
