# Reducing False Alarms While Preserving Lateral-Movement Detection

**A praxis proposal for network intrusion detection with scarce attack labels**

Final proposal draft | September 21, 2026

**Research status:** The motivating experiments are complete and audited. The protection procedure and confirmation study described here are proposed; their effectiveness and novelty have not been demonstrated.

## Executive summary

Security teams need fewer unnecessary alerts without making it easier for an attacker to move between systems. Our completed development experiments exposed this tradeoff: adding normal training examples was accompanied by substantially fewer false alarms and lower lateral-movement detection. The question is therefore not simply whether a model's overall score can improve. It is whether an improvement remains acceptable when this dangerous attack stage is explicitly protected.

**Problem statement and impact:** Because lateral movement can resemble legitimate administration, reducing false alarms through training-data balancing can change which attacks are missed, creating a need to evaluate analyst workload and lateral-detection loss together (Smiliotopoulos & Kambourakis, 2026).

**Thesis to be tested:** Selecting a detector's training emphasis and alert threshold under an explicit lateral-detection constraint can reduce benign-flow alerts while keeping lateral-movement detection within a prespecified acceptable loss, when attack labels are scarce.

**Primary research question:** Can a constrained selection procedure reduce false alarms relative to strong conventional controls while maintaining useful lateral-movement detection on independently held-out attack executions?

**Proposed solution in plain language:** Teach the detector about normal traffic, but do not accept a quieter configuration merely because its overall score improves. Check how much lateral activity it misses, select only configurations meeting both requirements, and test the locked choice on new data. If no configuration meets the requirements, report that result and do not authorize alert suppression.

## What the existing evidence shows

| Audited development measure | Fewer normal examples | More normal examples |
|---|---:|---:|
| Total fitting labels | 192 | 1,184 |
| Six-class macro-F1 | 0.4421 | 0.6543 |
| Normal-flow false-alarm rate | 10.04% | 0.40% |
| Lateral flows detected as any attack | 94.24% | 83.06% |

These are means across ten fits on the same SCVIC development cases. The proposed contribution is a controlled applied study and reproducible selection procedure, not a claim that adding normal data or constrained classification is new.

<!-- PAGE BREAK -->

## 1. Completed preliminary evidence

The completed study evaluated five model families on a deduplicated development split of the SCVIC author training data. It used 73 predictors and six source labels. The test partition contains 30,787 flows, including 144 lateral-movement flows, 15 initial-compromise flows, and 106 exfiltration flows. The official author holdout was unavailable. Repeated fitting seeds reused these same test cases.

The stronger tree comparison held the same 160 attack fitting examples constant while increasing normal examples from 32 to 1,024. XGBoost or LightGBM was selected through fitting-data cross-validation, not test performance. The mean macro-F1 improvement was accompanied by an 11.18-percentage-point loss in detecting lateral flows as any attack. Exact lateral-stage recall also declined, from 69.79% to 63.33%.

| Completed test | Audited result | Implication for this proposal |
|---|---|---|
| Equal 192-label comparison | TabICL macro-F1 0.5444; stronger selected tree 0.4421 | Keep a strong foundation-model comparison where budgets match. |
| Secondary foundation model | TabPFN macro-F1 0.5408 | A model leaderboard alone is insufficient. |
| Additional normal labels | False alarms 10.04% to 0.40%; lateral detection 94.24% to 83.06% | Study the tradeoff directly. |
| Added tree rescue checker | No rare-stage gain over its TabICL-only ablation | Do not reuse the failed checker as an established solution. |
| Sandworm, primary rule | TabICL attack recall 44.32%; normal FPR 28.21% | Source performance did not establish reliable transfer. |
| Sandworm, source-calibrated rule | Recall 3.78%; normal FPR 2.20% | A quieter threshold can conceal missed attacks. |

The Sandworm target contains 2,091 unique flows, including 37 attack flows, from one capture. It is an already inspected binary-transfer challenge, not fresh lateral-stage confirmation. The completed uncertainty-set experiment also failed its per-stage coverage requirement.

## 2. Definitions that prevent an inflated claim

**Lateral-activity detection** means that a true lateral flow raises any attack alert. **Lateral-stage identification** means assigning the correct lateral label. The primary proposal protects detection; stage identification remains a separate reported outcome. An alert routed for review is not proof that an analyst resolved an incident.

A flow-level false-alarm rate measures flagged normal flows, not analyst hours or alerts per host-day. For example, a 1% rate implies 1,000 flagged flows per 100,000 normal flows before aggregation. This is an arithmetic illustration, not a measured workload reduction.

Evidence: [final audited results](https://github.com/garypagangit/praxis/blob/apt-benchmark/experiments/apt_benchmark/results/tabular_followup_decision_v1/REPORT.md) and [complete benign-control tradeoffs](https://github.com/garypagangit/praxis/blob/apt-benchmark/experiments/apt_benchmark/results/strong_benign_controls_v1/REPORT.md).

<!-- PAGE BREAK -->

## 3. Literature foundation and proposed contribution

**Primary application paper.** Smiliotopoulos and Kambourakis (2026) examine 13 models, imbalanced and resampled LMD-2023 Sysmon data, and lateral-movement false-positive/false-negative tradeoffs. This directly precedes the broad topic of balancing data to protect lateral movement. Its publisher abstract and bibliographic record were verified; the complete subscription methods were not available in this review. We therefore cannot claim that it omits a particular control or split without obtaining the full article.

**Primary methodological foundation.** Tian and Feng (2025) connect multiclass Neyman-Pearson classification to cost-sensitive learning and address class-specific error constraints and feasibility. Tong et al. (2018) establish related binary error-control methods. The present proposal borrows the principle of prioritizing particular mistakes; it does not introduce new error-control mathematics.

**Closest normal-data allocation precedent.** Revell et al. (2026, Section 6.5) explicitly propose allocating more support examples to benign traffic. Increasing normal examples is therefore prior art. The proposed study must test when that allocation helps, when it hurts lateral detection, and what labels it actually requires.

**Other relevant controls.** García et al. (2025) already compare tabular foundation models and conventional intrusion detectors. Angelopoulos et al. (2025) address selecting predictive configurations under risk requirements; searching many thresholds does not create free statistical validity. Bilot et al. (2026) describe host-centered lateral-movement graph detection in an author manuscript marked accepted at ACSAC 2026; final proceedings metadata was not verified. This is relevant alternative architecture research, not evidence for this proposal's results.

## 4. The gap this study will try to fill

The candidate applied gap is a controlled answer to the following question: **When scarce attack examples are held fixed, how do additional distinct normal examples and changed class emphasis affect lateral detection, and can a selection procedure retain a useful false-alarm benefit on new executions?**

Three elements must be evaluated together:

1. **Matched resources:** the same attack examples, normal examples, tuning access, and label accounting for competing methods.
2. **Separated mechanisms:** controls that distinguish more varied normal behavior from simply giving the normal class more training weight.
3. **Independent protection evidence:** false-alarm reduction and lateral noninferiority assessed jointly on untouched, meaningfully grouped data.

The intended contribution is an operational selection-and-rejection procedure plus evidence about this tradeoff. If an established constrained method implements the same rule, it will be evaluated under its existing name. A duplicated method will not be presented as a new algorithm. If the literature already answers the same question under comparable controls, the work must be positioned as replication rather than methodological novelty.

<!-- PAGE BREAK -->

## 5. Proposed method

### Primary comparison: hold the label budget fixed

Use the same 160 attack and 1,024 normal fitting examples in every primary arm: 1,184 unique fitting labels. Start with XGBoost and LightGBM. Use fitting-only cross-validation to tune each family within identical declared search budgets. Select the primary model family through development data before independent verification. No final-test outcome may select a model, weight, or threshold.

Compare ordinary class proportions, equal total weight per class, and equal class mass with lateral multipliers of 1, 2, and 4. These are established weighting operations. Normalizing total weights keeps a change in class emphasis distinct from a change in the overall loss scale. Hyperparameter candidates, seeds, normalization, and ties will be specified in the prospective protocol before execution.

For each eligible configuration, compute the attack score as **1 minus the probability of NormalTraffic**. Flag a flow only when this score is strictly above its fixed threshold. The proposed procedure chooses the lowest normal false-alarm rate among configurations satisfying the declared lateral-detection constraints. It uses a single detector and threshold; it does not depend on the failed rescue ensemble.

### Selection and verification

1. **Fit:** learn model parameters from the fitting partition only.
2. **Select:** use a separate development partition to choose weights, model configuration, reference comparator, and alert threshold.
3. **Lock:** record the complete choice, preprocessing, prediction rule, label ledger, and artifact hashes.
4. **Verify once:** evaluate that locked choice on separate verification data. A failure rejects the choice; it cannot trigger retuning on those data.
5. **Confirm:** evaluate the frozen procedure on the qualified independent dataset or new executions. Publish every prespecified outcome.

The existing SCVIC split is already exposed. Further evaluations on it are exploratory, even when new code is frozen. Repartitioning already inspected examples does not create independent confirmation.

### Secondary allocation and mechanism study

Keep the same attack examples and form nested, outcome-independent normal supports of 32, 128, 512, and 1,024 examples. Total fitting sizes are 192, 288, 672, and 1,184. At each size, compare ordinary class proportions with equal class mass, threshold-only adjustment, and constrained selection. All families compared at a size receive the same rows.

A small-support reweighting control changes normal-class mass without introducing new distinct examples. A large-support equal-class-mass control expands normal coverage without increasing its total class weight. These controls test possible explanations for the original tradeoff; neither mechanism is already established by the preliminary results.

TabICL is a secondary matched-budget comparator, including the abundant-normal setting if resources permit. Unsupported sample weights will not be simulated silently. Selecting a smaller support after inspecting a larger labeled pool does not reduce the actual label-acquisition cost.

<!-- PAGE BREAK -->

## 6. Data and baseline plan

**Development: SCVIC.** Retain the author training-data provenance, deduplication, fixed feature schema, source labels, and prior results. Use it to check implementation and characterize tradeoffs. The already inspected test set cannot certify the new lateral hypothesis. Existing normal calibration labels and all stage labels inspected during selection must be counted separately from fitting labels.

**Preferred fresh transfer candidate: DEDALE.** The authors provide labeled Zeek flows and CICFlowMeter archives, but a labeled CICFlowMeter join is not yet verified. Their first two weeks contain only benign traffic; the final two weeks contain attacks. This split cannot supply supervised lateral training from the first period (Lanvin & Majorczyk, 2026). Qualify access, license, features, lateral labels, attack-related exclusions, background exposure, and campaign overlap before modeling.

Preserving that split requires an external attack-training source and compatible features. Source-only transfer is separate from a variant using target-benign calibration, whose labels must be charged. Within-dataset procedure replication instead needs a justified attack-containing training partition and untouched executions; it changes the author benchmark and must be labeled accordingly. Neither route is ready or confirmed. Freeze the qualified route before examining model outcomes.

**Local secondary option: Unraveled.** It can support additional development because author-matching files and lateral labels are locally available. Prior GML experiments already used its files; it is not an untouched confirmation set. LMD-2023 is a relevant Sysmon alternative, but its modality and rule-derived labels require a separate task definition. Neither is silently pooled with network flows.

If these artifacts cannot support confirmation, obtain an unused author holdout or generate new executions with the documented RESCOUSSE testbed and realistic benign administration. Keep separate execution groups for fitting, selection, verification, and confirmation. Until data and group adequacy are verified, the study remains developmental. More seeds do not substitute for new executions.

### Required baseline families

| Comparator | Purpose |
|---|---|
| Strong macro-F1-selected tree, ordinary argmax | Preserve a conventional reference. |
| Same tree, threshold-only adjustment | Test whether a simpler operating point solves the problem. |
| Class-balanced and lateral-weighted trees | Prevent claiming established weighting as a new contribution. |
| Established constrained/NP procedure | Compare against the actual methodological precedent. |
| Matched-budget TabICL | Assess whether the effect depends on model family. |

Select the reference on development data: among controls with lateral recall at least 90% and FPR at most 1%, maximize lateral recall, then minimize FPR, then apply a fixed model order. If none qualifies, report infeasibility. The candidate minimizes FPR subject to the locked reference's lateral constraint. Report all controls. Collapse equivalent constrained methods into one arm. If threshold adjustment alone explains the benefit, report no added value from the more complex training procedure.

For a new taxonomy, allocate the 160 attack fitting labels across qualified native attack groups using a prospective, outcome-independent rule shared by all arms; SCVIC's five-by-32 allocation cannot be assumed. Preserve the binary alert endpoint and report native stage scores separately. **Procedure replication** with new fitting labels is not zero-target-label model transfer. If the required label budget or grouping is unavailable, do not claim a matched confirmation.

<!-- PAGE BREAK -->

## 7. Research questions, hypotheses, and success criteria

**RQ1: What changes when normal examples increase?** The secondary hypothesis is that added normal coverage and changed class emphasis have distinguishable effects on false alarms and lateral misses. The mechanism controls in Section 5 address this; the existing result alone does not prove a cause.

**RQ2: Can the protection procedure improve a useful operating point?** The primary hypothesis is that the locked procedure reduces false alarms while meeting both relative and absolute lateral-detection requirements on independent confirmation data.

**RQ3: Does the benefit replicate?** A positive development result must be tested on qualified new executions or a separately prepared dataset. Cross-network transfer and target-calibrated adaptation are reported as different conditions, not combined into a single generalization claim.

Let **F** denote mean benign false-alarm rate and **R** mean detection of lateral flows as any attack. Compute each rate within an eligible incident or campaign, then average with equal group weights. Use the same paired eligible groups for candidate and reference. Report pooled flow counts separately. The primary claim requires every condition below.

| Proposed confirmation requirement | One-sided 95% bound |
|---|---|
| At least 20% relative false-alarm reduction | Upper bound of F(candidate) - 0.8 x F(reference) below 0 |
| Lateral recall loss less than 3 percentage points | Lower bound of R(candidate) - R(reference) above -0.03 |
| Useful absolute lateral detection | Lower bound of R(candidate) at least 0.90 |
| Normal-flow false-alarm budget | Upper bound of F(candidate) at most 0.01 |

These are proposed engineering targets, not industry standards, proven safe limits, or criteria applied retrospectively to the completed experiments. The 3-point margin permits some harm; it is not a zero-loss claim. If the reference has effectively no false alarms, the reduction endpoint may be infeasible. That fact must be addressed before confirmation, not by changing a failed endpoint afterward.

### Statistical feasibility and reporting

Freeze a paired incident/campaign interval procedure and its adequacy checks before confirmation. Do not bootstrap dependent flows as independent observations. Seeds measure training variability; they do not multiply the number of incidents. All four conditions form one joint claim; selectively reporting a passing condition is not success.

The current 144 lateral test flows are inadequate evidence of independent protection. An illustrative independent-pair calculation assuming zero true paired recall difference, a 3-point margin, 80% power, and 5%, 10%, or 20% discordance requires approximately 344, 687, or 1,374 lateral observations. These are planning examples, not achieved power; clustering can increase requirements. Use development-estimated variability and qualified group counts to plan the actual confirmation sample.

Report precision, recall, F1, ROC-AUC, average precision, false-alert counts, all attack-stage detection rates, correct-stage scores, label costs, runtime, and memory. Insufficient support for another stage must be disclosed; the method does not guarantee protection of every stage.

<!-- PAGE BREAK -->

## 8. Execution plan and decision rules

### Milestone 1: qualify the evidence and freeze the study

Acquire and inspect only the metadata and artifacts needed to establish the independent data role. Verify execution grouping, normal exposure, lateral labels, and feature timing. Build a split manifest, label ledger, duplicate audit, and uncertainty/power plan. Then version and freeze the finite search space, primary comparator rule, weighting details, interval method, success thresholds, exclusion rules, and evaluation script before new confirmation outcomes are inspected.

This document is a final proposal draft, not a completed registration. The study cannot claim confirmation until data adequacy and these analysis details are resolved and recorded prospectively.

### Milestone 2: run the controlled development study

Start with CPU tree models and test all prespecified weighting, threshold, and normal-support controls. Fit only on authorized dataset copies. Add matched-budget TabICL runs after the pipeline and label accounting are verified. GPU compute may accelerate compatible foundation-model inference; it does not improve the validity of a split or create independent evidence. AWS requires a fresh authentication session before use, and mixed CPU/GPU timings will not support a speed claim.

### Milestone 3: lock, verify, and confirm

Retain all candidates and negative outcomes in the development record. Lock one choice and one primary reference before independent verification. Do not search again on a failed verification or confirmation set. Preserve per-group predictions privately and publish aggregate results, configuration hashes, provenance, and reproducibility instructions without redistributing restricted source data.

### Milestone 4: write the final empirical praxis

Report a positive conclusion only if every primary confirmation condition passes. Use **INFEASIBLE** when no configuration satisfies development requirements, **INSUFFICIENT EVIDENCE** when data cannot resolve the claim, and **NEGATIVE** when an adequately tested locked comparison fails. A failed algorithmic claim may still support a useful applied account of the labeling and detection tradeoff; it must retain the failed outcome.

## 9. Industry value, deliverables, and limits

If confirmed, the practical output is a selection policy that helps a security team decide when extra normal training data genuinely reduces unnecessary alerts without an unacceptable lateral-detection loss. Deliverables include the qualified benchmark, explicit label-cost ledger, reusable selection code, all-stage scorecards, feasibility report, and final evidence-linked paper. No analyst-time savings will be claimed without measuring review workload.

The proposed system does not authorize autonomous suppression in production. An infeasible or unverified policy remains in shadow evaluation; an existing independently validated process is retained where available. The study does not establish actor attribution, before-impact warning, resilience to missing logs, or universal protection under distribution shift.

**Praxis position:** This is a defensible, literature-grounded applied research proposal with a measured motivating problem. Its empirical contribution can be established only by the proposed controls and independent evidence. A novel algorithm and a successful protection method remain unproven.

<!-- PAGE BREAK -->

## References

Angelopoulos, A. N., Bates, S., Candès, E. J., Jordan, M. I., & Lei, L. (2025). Learn then test: Calibrating predictive algorithms to achieve risk control. *The Annals of Applied Statistics, 19*(2), 1641-1662. https://doi.org/10.1214/24-AOAS1998

Bilot, T., Zouaoui, A., Al Agha, K., El Madhoun, N., & Pasquier, T. (2026). *LARES: Host-centered lateral movement detection via inductive graph reasoning* [Accepted conference paper, author preprint]. 42nd IEEE Annual Computer Security Applications Conference. https://tfjmp.org/publications/2026-acsac.pdf

García, P., de Curtò, J., de Zarzà, I., Cano, J. C., & Calafate, C. T. (2025). Foundation models for cybersecurity: A comprehensive multi-modal evaluation of TabPFN and TabICL for tabular intrusion detection. *Electronics, 14*(19), Article 3792. https://doi.org/10.3390/electronics14193792

Lanvin, M., & Majorczyk, F. (2026). Get out of DEDALE with RESCOUSSE: A new dataset and testbed for evaluating the detection of APT attacks among network and system logs. In *Computer security. ESORICS 2025 international workshops* (Lecture Notes in Computer Science, Vol. 16232, pp. 3-23). Springer. https://doi.org/10.1007/978-3-032-16092-8_1

Revell, L., Kang, H., Seo, J. T., & Kim, D. D. (2026). Systematic evaluation of few-shot learning for unseen IoT network attack detection. *Computer Modeling in Engineering & Sciences, 147*(1), Article 45. https://doi.org/10.32604/cmes.2026.078467

Smiliotopoulos, C., & Kambourakis, G. (2026). Machine learning for lateral movement detection using Sysmon logs: An empirical comparison of imbalanced and resampled data. *International Journal of Information Security, 25*, Article 38. https://doi.org/10.1007/s10207-025-01182-1

Tian, Y., & Feng, Y. (2025). Neyman-Pearson multi-class classification via cost-sensitive learning. *Journal of the American Statistical Association, 120*(550), 1164-1177. https://doi.org/10.1080/01621459.2024.2402567

Tong, X., Feng, Y., & Li, J. J. (2018). Neyman-Pearson classification algorithms and NP receiver operating characteristics. *Science Advances, 4*(2), Article eaao1659. https://doi.org/10.1126/sciadv.aao1659

### Research evidence and verification record

Praxis experiment repository. (2026, September 21). *Final praxis decision: Rare-stage protection and limited-label APT recognition* [Audited development report, commit 9dd2b81]. https://github.com/garypagangit/praxis/blob/9dd2b81276c86fc7591a90fa85eb879f831e798c/experiments/apt_benchmark/results/tabular_followup_decision_v1/REPORT.md

The companion literature, methodology, and data-plan notes retain the search boundaries, exact preliminary metrics, source references, and design objections. Peer-reviewed papers, accepted author manuscripts, and untested proposed work are identified separately. The literature check is bounded and does not prove absence of a similar study.
