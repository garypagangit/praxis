# Improving APT Alert Efficiency: Measured Gains and Lateral-Movement Tradeoffs

## An empirical praxis on benign training coverage, alert policies, and attack-stage visibility

**Completed findings synthesis - September 21, 2026.** The measured improvements and their detection costs are reported together. Original models, thresholds, data splits, and scientific receipts are unchanged.

**Evidence scope:** Previously examined SCVIC development data; 152 completed final models in the new experiment; a qualified DEDALE stress test of ordinary controls. This revised emphasis was developed after the results were known. The original investigator-chosen joint screen remains INFEASIBLE.

## Abstract

Security detectors need to reduce unnecessary alerts without obscuring the attack behaviors that matter. This praxis measures how benign fitting coverage, training weights, and alert thresholds change that tradeoff in APT-labeled network flows. An earlier ten-seed SCVIC comparison increased benign fitting examples from 32 to 1,024 while retaining the same 160 attack fitting examples within each seed. Mean false-positive rate fell from 10.04% to 0.40%, a 96.02% relative reduction, and six-class macro-F1 increased from 0.4421 to 0.6543; lateral-flow detection also declined from 94.24% to 83.06%. The subsequent experiment completed 152 final models across 19 support groups. On the same six primary supports with selected policies, the low-false-alarm candidate reduced false positives by 33.3% and increased binary attack F1 from 0.8770 to 0.9044, while lateral detection changed from 88.19% to 84.49%. A further exploratory matched-subset comparison found 25.9% fewer false positives and a 0.46-percentage-point higher mean lateral recall for the lateral-sensitive reference, selected using lateral-labeled data, than for the ordinary source-normal threshold; this small gain was not consistent across seeds or all stages. Four primary supports supplied no qualifying policy, so the original self-imposed 90%-recall/1%-false-positive joint screen remained unmet. DEDALE evaluated ordinary controls only on four lateral flows from one execution. The contribution is reproducible evidence linking false-alarm gains to stage-specific costs under explicit label budgets. It partially addresses a literature-motivated empirical question about richer benign support; it does not establish a new algorithm, guaranteed preservation, or deployment utility.

**Keywords:** intrusion detection; lateral movement; benign training data; false alarms; class weighting; alert thresholds; empirical evaluation

## Executive explanation

**There are positive findings.** The experiment is more informative than a single pass/fail label. More examples of normal traffic produced substantially fewer false alarms and a better overall classification score. Changing how the fitted models were used also produced favorable comparisons. Those improvements came with different detection costs, which are part of the result.

| Question | Measured benefit | Companion finding |
| --- | --- | --- |
| What did more benign examples achieve? | 96.02% fewer false positives; macro-F1 0.4421 to 0.6543. | Ten earlier paired fitting seeds; lateral detection 94.24% to 83.06%; 992 additional benign labels per fit. |
| What did the low-false-alarm candidate achieve? | 33.3% fewer false positives; attack F1 0.8770 to 0.9044. | Same six selected supports; lateral detection 88.19% to 84.49%. |
| Was there any paired improvement in both false alarms and lateral detection? | The lateral-sensitive reference had 25.9% fewer false positives and mean lateral recall 0.46 percentage points higher than the source-normal threshold. | Exploratory six-support comparison; only two supports improved both measures, and some other stages declined. |

The 90% detection floor was selected for this study. It was not a literature-established safety boundary or a requirement from an organization. The other numerical screen values were also investigator choices. Keeping their original outcome preserves the research record; it does not erase improvements in the observed measurements.

The practical contribution is a way to report what a quieter detector buys and what it gives up. The paper connects this evidence to published calls for richer benign support, reports the fitting and selection information used by each comparison, and identifies which conclusions still need independent attack executions. No reduction in analyst hours or successful new protection algorithm was measured.

# Chapter 1. Problem, purpose, and contribution

## 1.1 The practical problem in ordinary language

A security detector should help people find an attack in a large amount of ordinary activity. A false alarm sends harmless activity for review. A missed attack leaves harmful activity unflagged. Both matter, and improving one score does not necessarily improve both outcomes.

Lateral movement is an attacker's movement from one system or account to another after gaining access. Some of this activity resembles legitimate remote administration. A detector can therefore become better at recognizing ordinary traffic while also becoming less willing to alert on lateral activity. Recent research directly studies how imbalance and resampling affect this detection problem (Smiliotopoulos & Kambourakis, 2026).

The practical question is how much benefit a change produces, what detection it costs, and whether a simpler alternative provides the same benefit. This study measures those quantities in recorded network flows. It does not measure analyst time or claim that each flagged flow creates a separate investigation.

## 1.2 Problem statement and importance

**When attack fitting examples are limited, improving a detector's recognition of normal traffic can reduce false alarms while changing detection of important attack stages, so model evaluation must expose both effects before an overall improvement is treated as operationally useful (Revell et al., 2026; Smiliotopoulos & Kambourakis, 2026).**

The potential benefit for organizations is better information for choosing training data and alert settings: fewer unnecessary flags, explicit visibility into missed lateral activity, and clear accounting of the labels needed. These are decision benefits suggested by the measurements, not demonstrated financial savings, improved analyst performance, or prevented breaches. A controlled alert-review study provides motivation for examining human consequences, but its task and error measures differ from this flow experiment (Layman & Roden, 2023).

## 1.3 Thesis supported by the actual findings

**Additional benign fitting examples and explicit comparisons of training weights and alert policies can improve false-alarm and classification measures in the tested APT flow setting; reporting the accompanying attack-stage changes makes those improvements interpretable.**

This thesis concerns measured component improvements and their costs. It does not mean that every setting improves every metric. The evidence includes a large earlier benign-support gain, a smaller conditional policy gain, and training-weight comparisons that improve lateral detection while raising false alarms. The same records also show an unmet joint engineering target and limited transfer of source settings.

## 1.4 Research questions for this synthesis

The following questions organize this revised, post-result synthesis. They do not replace the hypothesis frozen before the model runs.

1. With the attack fitting examples held fixed within each seed, what changes in false alarms, overall classification, and lateral-flow detection when more benign examples are supplied?
2. On identical fitting rows, how do ordinary class balancing and additional lateral weighting change the false-alarm/detection tradeoff across all ten primary fitting seeds?
3. Among supports where a policy was selected, what benefit and cost remain when the candidate is compared with the same reference, a threshold-only alternative, and ordinary controls on the same seeds?
4. How stable are those findings across fitting supports, other attack stages, and the qualified external flow sample?

The original prospective question was narrower: could one declared selection process satisfy all of its chosen false-alarm and lateral-protection requirements? Its recorded answer remains INFEASIBLE. That answer and the favorable component measurements describe different aspects of the same completed evidence.

## 1.5 The critical empirical gap

The gap addressed here is **evidence connecting the benefit of additional benign fitting data to its cost at individual attack stages, while separating changes in training emphasis from changes in the alert threshold**. Revell et al. (2026, Section 6.5) provide an explicit future-work anchor by proposing larger benign support. Our study tests the related data-allocation idea with supervised trees and fixed attack fitting identities, rather than reproducing their episodic meta-learning architectures.

The distinction matters because a practitioner needs more than a statement that a total score increased. The useful evidence is the paired change: how many harmless flows are no longer flagged, how many lateral flows remain visible, whether other stages lose detection, and whether threshold adjustment explains the gain. Chapter 2 situates this bounded empirical contribution against work that already uses class weighting, constrained thresholds, and abundant benign information.

This is a literature-linked application and evaluation contribution. The bounded review does not establish that no one has studied this combination before. The methods are established; the contribution lies in the controlled comparisons, actual stage costs, reproducible evidence, and limits of their applicability.

## 1.6 What the study includes

The evidence has three distinct parts: an earlier ten-seed benign-support comparison, the completed 152-model weighting and policy experiment, and a DEDALE controls-only external stress test. They use different evaluation roles and must not be pooled into one result. The first two use previously examined SCVIC source data. DEDALE provides a separate environment but only four lateral flow groups from one execution.

The revised paper leads with measured gains. The previous screen-oriented manuscript, original protocol, predictions, and audits remain preserved. No new fitting, threshold selection, or success rule was introduced for this rewrite. Additional paired comparisons highlighted after the results were known are explicitly descriptive. Independent incident-level validation and a new learning algorithm are not claimed.


# Chapter 2. Literature and the empirical gap

## 2.1 Review approach and limits

The review was refreshed on September 21, 2026. The supporting review prioritized primary journal records, official publication pages, author manuscripts, and institutional copies, emphasizing 2024–2026 literature. Earlier methodological work was retained where it established the error-control framework. This is a bounded review supporting a specific empirical design, not a systematic review or proof that no similar procedure exists. The current [gap review](FINDINGS_LITERATURE_GAP.md) documents additional checks. The [earlier literature research note](../../lateral_protection_praxis/LITERATURE_REVIEW.md) records the search boundaries and publication-status checks.

The scope of the review limits the claims that can be made. The publisher metadata and abstract of the closest lateral-movement resampling study were inspected, but its full methods were not inspected in this bounded review. This manuscript therefore does not assert that its authors omitted a particular split, comparator, or selection rule. Such an omission would require full-text verification.

## 2.2 Lateral detection and imbalanced training data

Smiliotopoulos and Kambourakis (2026) compare 13 learning approaches for lateral-movement detection using LMD-2023 Sysmon data, including imbalanced and resampled conditions. This is direct application prior art for studying how training balance affects detection errors. The present flow-based study has a different data representation and declared operating objective, but those differences alone do not demonstrate originality. [Publisher record](https://doi.org/10.1007/s10207-025-01182-1).

Revell et al. (2026) evaluate few-shot learning for network attacks and explicitly identify increased benign support as a possible response to benign/attack ambiguity. Therefore, adding more normal examples is already a literature-supported suggestion. Our work can test its consequences under fixed attack identities and lateral constraints; it cannot claim to originate that suggestion. [Article, especially Section 6.5](https://www.techscience.com/CMES/v147n1/67129/html).

Debelie et al. (2026) investigate GAN-based minority augmentation through controlled ablations on tactic-versus-benign tasks in UWF-ZeekData22. Their study provides further precedent for tactic-sensitive imbalance experiments. The present design begins with weights and unique benign supports, so a result need not depend on generating synthetic attack records. [Primary article](https://doi.org/10.3390/electronics15061291).

## 2.3 Error-constrained classification

Neyman–Pearson classification treats selected error rates as constraints while optimizing another objective. Tong et al. (2018) develop classification procedures and NP receiver-operating characteristics in the binary setting. Tian and Feng (2025) extend a multiclass approach through cost-sensitive learning and address feasibility. These works establish that asymmetric error priorities and constrained optimization are not novel concepts introduced by this praxis. [Tong et al.](https://doi.org/10.1126/sciadv.aao1659); [Tian and Feng](https://doi.org/10.1080/01621459.2024.2402567).

The implemented development policy is an empirical finite search over fitted detectors and their observed selection thresholds. It does not implement or reproduce a population guarantee from those papers. In particular, a 1% empirical false-positive rate on selection data is not a certified 1% deployment rate. Dependence among network flows, searching among candidate settings, and distribution changes all matter to interpretation.

Learn then test provides a framework for calibrating predictive procedures against risk requirements using hypothesis testing (Angelopoulos et al., 2025). Its relevance is the separation between selecting a plausible operating rule and obtaining valid evidence about its risk. Our development verification reports point estimates; it does not borrow the framework's inferential guarantees. A formal comparison or certification procedure would require its own specified assumptions, sampling units, and analysis. [Published article](https://doi.org/10.1214/24-AOAS1998).

There is also direct cybersecurity overlap. Singhal and Kumar (2026) combine a cost-sensitive random forest with validation-selected thresholds for binary ARP spoofing detection on CICIoMT2024. Their method chooses an F1-maximizing threshold subject to a false-negative-rate limit of 0.5%, with test data reserved for evaluation. This already combines weights, operating-point selection, and an explicit miss constraint. Our stage-specific reference comparison, fixed attack supports, nested benign budgets, and threshold-only ablation define a different empirical question; they do not establish a new general constrained-detection method. Their claimed operational safety is not adopted as a guarantee for our setting. [Primary full text, Sections 3.6.2–3.6.4](https://www.frontiersin.org/journals/big-data/articles/10.3389/fdata.2026.1878242/full).

## 2.4 Model novelty and contextual detection

García et al. (2025) already evaluate TabPFN and TabICL for tabular intrusion detection. Applying one of these foundation models to an IDS, or comparing it with boosted trees, is therefore prior art. The earlier foundation-model experiments provide context, but the new primary experiment is restricted to trees with explicit sample weights. It makes no tree-versus-foundation claim at unequal normal-label budgets. [Primary article](https://doi.org/10.3390/electronics14193792).

Bilot et al. (2026) present LARES, a host-centered graph approach to lateral movement, including temporal and unseen-host settings. The available author version states conference acceptance; final proceedings metadata was not verified in this review. This work illustrates a distinct source of information: relationships and host context. If flow-only selection proves insufficient, a contextual extension would need comparison with such methods rather than being described as unprecedented. [Author manuscript](https://tfjmp.org/publications/2026-acsac.pdf).

ULTIMATE uses multi-agent deep reinforcement learning with false-positive penalties and adaptive thresholds for enterprise intrusion detection (Saidane et al., 2026). Its published abstract supplies another direct precedent for false-alarm-oriented optimization. The full experimental procedure was not inspected here, so no claim is made that it omits our controls or validates lateral protection. Switching to reinforcement learning would not, by itself, resolve the novelty question. [Publisher abstract](https://www.sciencedirect.com/science/article/pii/S2590005626002195).

Bae et al. (2026) already combine large benign audit-log pretraining with few-shot attack learning in DUPIN. Its publication is verified in the official USENIX Security 2026 proceedings. Li et al. (2026) use potential entity relations for few-shot APT recognition in APMP. An earlier author preprint also applies class-weighted XGBoost to lateral movement (Kushwaha et al., 2022). These sources further limit broad novelty claims. Their provenance/entity representations and information budgets differ from our supervised flow study; none was a head-to-head baseline in this experiment. [DUPIN proceedings](https://www.usenix.org/conference/usenixsecurity26/presentation/bae); [APMP primary paper](https://doi.org/10.1186/s42400-026-00592-5); [earlier weighting preprint](https://doi.org/10.48550/arXiv.2208.13524).

## 2.5 Data and evidence quality

SCVIC-APT-2021 is associated with a peer-reviewed network APT benchmark paper (Liu et al., 2022). This study uses a prepared local copy of its author training data; it does not use the author's separate test artifact. Dataset publication and our local split qualification are different claims. The qualification receipts document what was actually available and how it was prepared. [Dataset paper](https://doi.org/10.1109/LNET.2022.3185553); [local qualification](../../tabular_batch/E0_DATASET_GATE.md).

DEDALE and RESCOUSSE provide a recent dataset/testbed direction for evaluating APT activity across network and system logs (Lanvin & Majorczyk, 2026). DEDALE was qualified for the limited controls-only stress reported in Chapter 4. Its author-provided labeled CICFlowMeter tables supported a documented feature adapter; the resulting four lateral rows remained one execution, and extractor equivalence was not established. [Published chapter](https://doi.org/10.1007/978-3-032-16092-8_1); [author documentation](https://dedale.inria.fr/download.html).

## 2.6 The gap this praxis partially addresses

The relevant empirical question is how much false-alarm improvement richer benign fitting data produces, which attack stages change alongside it, and how much of a later policy gain can be achieved by moving the same detector's threshold. The scope here is fixed attack fitting identities, nested benign supports, identical-row weighting, and locked verification. This is an applied extension of established ideas, not a claim that these topics have never been studied.

| Literature connection | Question addressed in this study | Boundary |
| --- | --- | --- |
| Revell et al. propose larger benign support. | Measure benign-support gains together with lateral and other-stage costs. | Supervised trees on SCVIC; not a replication of their meta-learners. |
| Smiliotopoulos and Kambourakis examine lateral imbalance and both error types. | Report every declared weighting arm on the same rows and fitting seeds. | Different representation; no unverified omission is attributed to their full methods. |
| Singhal and Kumar combine weights and constrained thresholds. | Compare a selected policy with its threshold-only alternative under matched information. | Established components; no new risk guarantee. |
| DUPIN uses abundant benign information with few attack labels. | Account explicitly for the smaller supervised fitting budget and all additional label access. | No claim to originate the abundant-benign idea or outperform DUPIN. |

The gap is critical to the decision being made: a larger overall score is insufficient to explain whether a rare attack step became less visible. The completed evidence provides that missing account for this tested setting. It does not establish a field-wide absence of such evaluations. The present contribution is supported by the actual comparisons, while broader originality remains bounded by the review and the institution's requirements.

# Chapter 3. Research methodology

## 3.0 Original design and later synthesis

The original design was fixed before the new model fits. This paper's emphasis on measured gains is a later descriptive synthesis. It preserves all selected and infeasible supports and all original requirements. No evaluation label was used to revise a model or threshold for this paper. Favorable additional contrasts are not presented as newly successful prespecified hypotheses.

The earlier benign-support comparison uses the original development test, whereas the new main policy comparisons use the verification half of the old calibration partition. Rates from these roles are not pooled. The complete prepared data were previously exposed in research, so neither role supplies untouched confirmation.

## 3.1 Design and completed execution

The governing [protocol](../protocol.json) and [executable specification](../specification.py) were frozen before the new model fits. The completed study remained `exposed_source_development`. All 19 registered groups completed: ten primary groups with 1,024 normal fitting examples, plus three seeds at each of three smaller normal budgets. Two families and four weighting schemes produced 152 final models after 4,788 inner-CV fits. The source freeze revision was `95d949276d754e6155b789b60779414ed88afcbd`. The independent source and external audits passed; their scientific outcomes are reported separately in Chapter 4.

## 3.2 Data provenance and preparation

The prepared SCVIC artifact contains 153,919 unique, nonconflicting feature rows and 73 predictors. Its source CSV contained 259,120 rows. Preparation excluded identifiers, IP addresses, ports, timestamps, labels, and four Idle statistics; removed 105,199 duplicate rows; and excluded one conflicting-label feature group containing two rows. Nonfinite predictor values became missing values before model-specific imputation. The exact preparation and hashes appear in the [qualification record](../../tabular_batch/E0_DATASET_GATE.md) and [preparation receipt](../../tabular_batch/SCVIC_PREPARATION.json).

The original deterministic partitions are stratified by class and grouped by exact predictor fingerprint. That construction prevents exact predictor duplicates from crossing partitions. It does not establish independence between incidents, hosts, time periods, or related flows. The author's separate test file has not been qualified in this study. The source artifact hash in the protocol binds the new experiment to the same prepared data as the preliminary work.

## 3.3 Fitting, selection, verification, and test roles

The old fit pool supplied fitting examples. The old calibration partition is divided into selection and verification halves, within each class, using a fixed SHA-256 ranking of its feature fingerprint and a declared tag. The first floor-half becomes selection; the remainder becomes verification. This split is fixed across all seeds. The original development test is retained for descriptive reporting only.

| Class | Available fit pool | Selection | Verification | Original development test |
|---|---:|---:|---:|---:|
| DataExfiltration | 316 | 52 | 53 | 106 |
| InitialCompromise | 43 | 7 | 7 | 15 |
| LateralMovement | 432 | 72 | 72 | 144 |
| NormalTraffic | 89,787 | 14,964 | 14,965 | 29,929 |
| Pivoting | 1,273 | 212 | 212 | 425 |
| Recon. | 499 | 83 | 83 | 168 |
| **Total** | **92,350** | **15,390** | **15,392** | **30,787** |

The table was checked against the prepared labels and deterministic partition rule; it contains no new model outcomes. Both halves originate from data already used in earlier work. They separate the new selection computation from its verification calculation, but they are not newly collected or untouched confirmatory samples. The new question itself arose after inspection of source results.

Each fit uses 32 examples from every attack stage: 160 attack labels in total. The original 32-per-class supports are retained. Additional normal examples come from a deterministic, seed-specific ordering of unused normal fit-pool rows. Smaller budgets are nested prefixes of the same expansion. Within a seed, model families and weighting schemes use identical fitting rows; no verification or test outcome selects those rows.

| Normal fitting budget | Attack fitting labels | Total fitting labels | Prespecified seeds | Role |
|---|---:|---:|---|---|
| 1,024 | 160 | 1,184 | 20260921–20260930 | Primary development comparison |
| 32 | 160 | 192 | 20260921–20260923 | Secondary budget control |
| 128 | 160 | 288 | 20260921–20260923 | Secondary budget control |
| 512 | 160 | 672 | 20260921–20260923 | Secondary budget control |

Cross-validation labels are reused fitting labels. The 15,390 selection labels, 15,392 verification labels, and 30,787 descriptive-test labels are additional information resources. These contain 426, 427, and 858 attack labels, respectively. Thus, “scarce attack labels” describes the fitting support here; it does not mean the whole procedure has access to only 160 labeled attacks. The available labeled fit pool and all prior exposure are disclosed. Using a small support selected from a larger labeled pool is not proof that the entire study required only that many acquired labels.

## 3.4 Models, preprocessing, and fitting-only tuning

The two families are XGBoost and LightGBM, using CPU execution with four threads per worker. Their grids contain 12 and nine configurations, respectively. The first nine original LightGBM configurations exclude embedded `class_weight` settings, because explicit sample weights now define the treatment. Exact parameter grids are bound through the protocol and its source-hashed backend rather than inferred from final performance. The family searches are bounded and differ in size; this study does not claim an exhaustive or equal-cost architecture contest.

For each model, weighting scheme, support, and seed, three-fold stratified cross-validation uses shuffle with that seed. Every training fold fits its own median imputer; entirely missing training features are retained under the declared empty-feature handling. The validation fold does not influence imputer statistics or training weights. Validation macro-F1 is unweighted across all six declared classes, with predictions from the maximum probability column. The candidate with the highest mean fold score wins; an exact tie chooses the first configuration in the frozen grid.

The chosen configuration is refitted on the full selected support with freshly computed support-only weights and imputation. Threshold selection receives predictions only after this fit. It does not feed verification outcomes back into model tuning. Predicted class-column order, finite probabilities, input identity, and output hashes are validated by the implementation. [Weighted fitting backend](../backend.py); [execution code](../run.py).

## 3.5 Training-weight treatments

Let a fitting fold contain `n` observations across `K = 6` classes; let `n_k` be the number in class `k`. Weights are calculated only from that fold's training labels, then normalized to have mean one.

| Scheme | Weight before final mean-one normalization | Purpose |
|---|---|---|
| Natural | `1` | Preserve observed fitting proportions |
| Balanced | `n / (K × n_k)` | Equal relative class mass |
| Lateral ×2 | Balanced weight, multiplied by two for lateral examples | Increase lateral training emphasis |
| Lateral ×4 | Balanced weight, multiplied by four for lateral examples | Stronger fixed lateral emphasis |

These are established sample-weighting operations. No new objective function is claimed. Missing fitting classes or invalid weights are rejected rather than silently changing the class set.

At 1,024 normal examples, natural training gives normal traffic 1,024/1,184 of the total weight. Balanced training gives each class one-sixth of the total weight. Across budgets, balanced weighting holds the **relative** class mass fixed; its absolute summed mass is `n/6` and changes with support size. Consequently, a budget comparison also changes sample count, weight distribution, regularization behavior, and possibly the CV-selected configuration. It can clarify the observed tradeoff, but cannot by itself prove that benign diversity is the sole causal mechanism.

## 3.6 Selection-only alert policy

For all threshold policies, the attack score is `s(x) = 1 − p(NormalTraffic | x)`. A flow is alerted when `s(x) > t`. Equal scores receive the same decision. The finite threshold frontier includes a below-range all-alert sentinel and every distinct observed selection score; verification labels do not define its candidates.

Selection considers the eight fitted family/weighting combinations in fixed model and scheme order. It selects three named policies:

1. **Reference:** Among detector/threshold pairs with selection lateral recall at least 90% and selection normal FPR no more than 1%, maximize lateral true positives. Break ties by fewer normal false positives, frozen cell order, and the largest threshold.
2. **Candidate:** Minimize normal false positives subject to the same 1% FPR limit and lateral recall of at least `max(90%, reference recall − 3 percentage points)`. Break ties by more lateral true positives, frozen cell order, and the largest threshold.
3. **Threshold-only ablation:** Apply the candidate's objective and constraints to the already selected reference detector alone. This isolates whether searching another detector adds value beyond moving the reference operating point.

All three use the same permitted fitting and selection information. Balanced and lateral-weighted detectors are available to the reference as well as to the candidate. If no reference is feasible, the group remains `INFEASIBLE`; it is not removed from the primary denominator. The reference and candidate may legitimately be identical.

Two ordinary controls are also locked: the fitting-CV-best natural-weight tree using its argmax prediction, and the same tree using a selection-normal-only empirical 1% threshold. An argmax attack decision need not equal a threshold of 0.5 on `1 − pNormal` in a six-class model. The empirical 1% control is not presented as an NP confidence certificate. [Selection and metric implementation](../selection.py).

## 3.7 Locking and verification

All eight fits and selection predictions for a group are completed before its selection lock is written. The lock records the chosen model identities, thresholds, selection counts, and fitting receipts. Verification and descriptive-test predictions are then evaluated against that lock. A failed verification result cannot trigger a new choice from the same data.

Every group preserves per-cell argmax classification and alert outcomes, in addition to the selected policies. This prevents the chosen policy from becoming the only visible result. The runner preserves input, code, environment, model, prediction, and selection-lock hashes. It rejects incompatible reuse or silent replacement of incomplete cells. An independent audit recomputed the rosters, policy choices, and saved metrics before results entered the manuscript. Such an audit establishes implementation consistency, not scientific effectiveness or independent ground truth.

## 3.8 Endpoints and development decision rule

The primary lateral endpoint counts any attack alert on a true `LateralMovement` flow. Exact-stage recall requires the predicted class to be `LateralMovement`; it is reported separately. Normal FPR is the number of alerted normal flows divided by all normal flows in the partition. Attack precision is the fraction of alerts that correspond to any labeled attack; recall is the fraction of attacks alerted. F1 combines the corresponding precision and recall. Macro-F1 averages class-specific F1 values. ROC-AUC and average precision summarize ranking, not protection at the selected threshold.

For each primary seed, calculate paired candidate and reference verification rates. Let `F_C` and `F_R` be their mean normal FPRs across the ten seeds, and `R_C` and `R_R` their mean lateral recalls. The development screen requires all of the following:

| Requirement | Exact criterion |
|---|---|
| Complete feasible primary comparison | All ten registered primary seeds have selected policies |
| Relative reduction in normal false alarms | `F_C < 0.8 × F_R` |
| Lateral loss below three percentage points | `R_C − R_R > −0.03` |
| Absolute lateral detection floor | `R_C ≥ 0.90` |
| Absolute normal false-alarm limit | `F_C ≤ 0.01` |

The 90% recall floor, 1% false-positive ceiling, 20% reduction target, three-point loss margin, and requirement for ten feasible supports were investigator-selected development requirements. No cited paper or documented stakeholder process establishes these exact values as universally acceptable. They were chosen to make the test demanding and explicit. Their original result is retained even though this synthesis asks what component improvements occurred.

The two improvement inequalities are strict. A reduction of exactly 20% or a recall loss of exactly three percentage points does not satisfy those criteria. If the reference has zero false alarms, the strict relative reduction cannot pass; the endpoint is not changed afterward. Exact count arithmetic governs boundary decisions.

`DEVELOPMENT_PROMISING` requires every guard; otherwise a complete feasible comparison is `DEVELOPMENT_NEGATIVE`. Missing groups remain `INCOMPLETE`, and infeasible seeds are retained as `INFEASIBLE`. Secondary budget summaries do not replace a failed primary result or select a new preferred budget. No confidence interval or significance claim was inferred from ten fitting seeds on common rows.

The 72 lateral verification flows give a per-seed recall resolution of approximately 1.39 percentage points. Three additional misses change a seed's rate by approximately 4.17 points. Averaging seeds smooths the numerical mean but does not create more independent attacks. Worst-seed FPR and lateral recall, individual-seed counts, all other stage recalls, and ordinary-control outcomes must accompany the aggregate decision.

## 3.9 Completed DEDALE qualification and external stress

The [DEDALE qualification](../dedale/QUALIFICATION.md) acquired named members of the author's CICFlowMeter archive and verified member CRC32 and SHA-256 values. The entire archive's advertised checksum was not independently verified. The acquired author tables already contained attack labels, steps, tactics, and techniques, so no inferred Zeek-to-CICFlowMeter label join was required. Author category 2, attack-related but not inherently malicious, remained distinct from confirmed benign traffic.

The acquired subset contained four lateral flows on day 17, linked by the author's labeling procedure to one PrintNightmare execution and two substeps. The [preparation protocol](../dedale/PREPARATION_PROTOCOL.json) retained every eligible lateral feature group and selected at most 100,000 unique benign groups by a fixed hash rule. Exact source overlap and conflicting labels were excluded; none occurred in this stress preparation. Other attack stages were excluded by its fixed scope. The prepared sample contained 100,004 groups, including all four lateral groups.

All 73 source predictors were mapped in order, with documented renames for Protocol and Flow Duration. The target implementation's duration unit was verified, but the exact source extractor revision/settings remain unknown. Matching names and units therefore support a transparent stress test, not proof of identical extraction. No target-derived preprocessing, fitting, calibration, or threshold choice occurred.

The external protocol fixed source budget 1,024 and seed 20260921 before target inference. That source selection was infeasible. The prespecified policy roster consequently contained only the source-locked natural argmax control and its source-normal 1% threshold; no candidate or fallback was invented. Chapter 4 reports both controls regardless of their performance. Four flows from one execution cannot confirm a three-point incident-level protection margin.

## 3.10 Reproducibility, rights, and practical safeguards

The final empirical package identifies the source-freeze revision, protocol and data hashes, full software versions, complete cell roster, selection locks, prediction hashes, and independent audit. Private flow records and model probabilities remain in their authorized storage; public reports use permitted aggregates and provenance. A software-test pass is reported separately from the experiment's scientific decision.

No automatic production suppression or analyst outcome is part of this study. Flow-level results may inform shadow evaluation after independent validation. A 1% FPR corresponds arithmetically to 1,000 flagged flows per 100,000 benign flows, before aggregation; it is not necessarily an acceptable workload. Claims about saved analyst time would require measured alert grouping and human investigation, which this experiment does not perform.

# Chapter 4. Actual findings

## 4.1 More benign fitting data improved false alarms and overall classification

This earlier comparison averages all ten fitting seeds on the same original development test: 29,929 benign and 144 lateral flows, within 30,787 total flows. Attack fitting identities remained fixed within each seed. It is the motivating result, not an outcome newly produced by the 152-model experiment (Praxis experiment repository, 2026).

| Measure | 32 benign + 160 attack labels | 1,024 benign + same 160 attack labels |
| --- | --- | --- |
| Mean benign false-positive rate | 10.036% | 0.400% |
| Mean benign flags / 29,929 | 3003.8 | 119.6 |
| Six-class macro-F1 | 0.4421 | 0.6543 |
| All-attack detection | 98.40% | 95.70% |
| Lateral flows detected as any attack | 94.24% | 83.06% |
| Lateral flows assigned correct stage | 69.79% | 63.33% |

The positive gain was a 96.02% relative false-positive reduction and a 0.2122 increase in macro-F1. The lateral cost was 11.18 percentage points, or approximately 16.1 fewer detected lateral flows per repeated-fit mean. More benign coverage, changed class proportions, support size, and model selection changed together; the experiment does not isolate a causal diversity effect. [Audited earlier comparison](../../results/strong_benign_controls_v1/SUMMARY.json).

## 4.2 Policy improvements on the same six selected supports

All five rows below use exactly the same six fitting seeds: 20260922, 20260923, 20260925, 20260927, 20260928, 20260930. Each is evaluated on 14,965 benign flows and 72 lateral flows within the same 15,392-row verification partition. The other four primary supports had no selected constrained policy and remain visible in Section 4.6. These are conditional descriptive comparisons.

| Policy | Mean benign flags | Benign FPR | Mean lateral flags | Lateral recall |
| --- | --- | --- | --- | --- |
| Ordinary natural tree | 53.0 | 0.354% | 57.0 | 79.167% |
| Source-normal 1% threshold | 145.3 | 0.971% | 63.2 | 87.731% |
| Lateral-sensitive reference | 107.7 | 0.719% | 63.5 | 88.194% |
| Threshold-only alternative | 85.8 | 0.574% | 61.2 | 84.954% |
| Low-false-alarm candidate | 71.8 | 0.480% | 60.8 | 84.491% |

| Policy | Attack precision | Attack recall | Attack F1 | Attack ROC-AUC | Attack AP |
| --- | --- | --- | --- | --- | --- |
| Ordinary natural tree | 88.74% | 95.67% | 0.9202 | 0.9981 | 0.9671 |
| Source-normal 1% threshold | 74.20% | 97.74% | 0.8435 | 0.9981 | 0.9671 |
| Lateral-sensitive reference | 79.78% | 97.58% | 0.8770 | 0.9982 | 0.9743 |
| Threshold-only alternative | 83.55% | 96.57% | 0.8934 | 0.9982 | 0.9743 |
| Low-false-alarm candidate | 86.03% | 95.98% | 0.9044 | 0.9982 | 0.9732 |

**Candidate versus lateral-sensitive reference.** False alarms declined 33.28% and attack F1 increased from 0.8770 to 0.9044. Alert precision increased from 79.78% to 86.03%. Lateral recall declined from 88.19% to 84.49%, a 3.70-point loss. On the fixed verification sample, the mean reduction was 35.8 benign flags with 2.67 fewer lateral flags. These counts describe flows, not analyst cases or unique incidents.

**Candidate versus ordinary natural tree.** Lateral recall increased from 79.17% to 84.49%, a 5.32-point gain. False-positive rate increased from 0.354% to 0.480%. This comparison shows why a method can be better at one operational objective and worse at another. It is not the same reference comparison as the preceding paragraph.

**Exploratory reference versus source-normal threshold.** The lateral-sensitive reference had 25.92% fewer false positives and mean lateral recall 0.463 points higher. False positives improved in five seeds and worsened in one; lateral detection improved in two, tied in one, and worsened in three. Only two seeds improved both. Exfiltration, pivoting, and reconnaissance mean detection declined slightly, and all-attack recall declined from 97.736% to 97.580%. This is a small, selected-subset gain in two averages, not consistent superiority or statistically confirmed lateral improvement. The reference used labeled lateral examples during policy selection, whereas the ordinary threshold used only selection-normal labels. This comparison does not isolate algorithm quality from that extra selection information.

The independent arithmetic review records every contrast and its stage costs in [FINDINGS_ACTUALS.json](FINDINGS_ACTUALS.json). The expanded interpretation is post-result. No confidence interval or statistical significance is inferred from repeated fitting on the same verification observations.

## 4.3 Training emphasis improved lateral detection at different false-alarm costs

The following table includes every declared model/weight combination and all ten primary seeds, regardless of policy feasibility. Each row uses 1,024 benign and the same 160 attack fitting examples within a seed. These are the classifiers' ordinary maximum-probability decisions; they do not use the selected candidate thresholds.

| Model / weights | Benign FPR | Lateral alert recall | Six-class macro-F1 | Exact lateral-stage recall |
| --- | --- | --- | --- | --- |
| xgboost/natural | 0.303% | 76.81% | 0.6550 | 58.75% |
| xgboost/balanced | 0.931% | 85.14% | 0.5961 | 65.28% |
| xgboost/lateral2 | 1.143% | 86.67% | 0.5842 | 66.81% |
| xgboost/lateral4 | 1.286% | 87.92% | 0.5731 | 69.17% |
| lightgbm/natural | 0.378% | 78.89% | 0.6395 | 61.53% |
| lightgbm/balanced | 0.611% | 84.58% | 0.6123 | 63.61% |
| lightgbm/lateral2 | 0.768% | 83.89% | 0.6072 | 64.72% |
| lightgbm/lateral4 | 0.815% | 84.72% | 0.5986 | 64.44% |

Balanced LightGBM increased lateral alert recall from 78.89% to 84.58%, with FPR increasing from 0.378% to 0.611% and macro-F1 decreasing from 0.6395 to 0.6123. XGBoost with fourfold lateral emphasis increased lateral alert recall from 76.81% to 87.92%, with FPR increasing from 0.303% to 1.286%. These favorable lateral changes are descriptive contrasts within the full reported family; the paper does not select one after evaluation and certify it as the best deployment model. Exact-stage recall is lower than any-attack alert recall because assigning the correct stage is a harder, different task. Appendix E retains all classes and ranking metrics.

## 4.4 What the threshold-only comparison adds

Among 6 feasible primary seeds, the candidate was identical to the threshold-only ablation in **4**. Identity means the saved policy choice, threshold, and selection counts match. This is not an extra success criterion, and a different detector does not itself establish an improvement.

| Seed | Reference detector | Candidate detector | Identical ablation? | Candidate minus ablation FP | Candidate minus ablation lateral TP |
| --- | --- | --- | --- | --- | --- |
| 20260922 | lightgbm/lateral4 | lightgbm/lateral4 | Yes | 0 | 0 |
| 20260923 | lightgbm/balanced | lightgbm/balanced | Yes | 0 | 0 |
| 20260925 | lightgbm/lateral2 | lightgbm/balanced | No | -59 | 0 |
| 20260927 | lightgbm/balanced | lightgbm/lateral4 | No | -25 | -2 |
| 20260928 | xgboost/natural | xgboost/natural | Yes | 0 | 0 |
| 20260930 | xgboost/balanced | xgboost/balanced | Yes | 0 | 0 |

Whenever a reference existed, it was itself an eligible candidate and threshold-only option. Therefore selection FPR satisfied candidate ≤ threshold-only ≤ reference by construction. A selection-side reduction is an optimization consequence; the locked verification counts above determine whether it persisted. No policy was changed after observing those counts.

Across the same six supports, the candidate had 16.31% fewer false positives than threshold-only, with mean lateral recall 0.463 points lower. Four identical choices mean the extra detector search added nothing in those four supports. The remaining difference is informative, but it does not establish a broadly superior learning method.

## 4.5 Detection at every attack stage

All policies below use the same six selected supports. Each entry is the percentage of true stage-labeled flows that raised any attack alert. Denominators are 53 exfiltration, seven initial-compromise, 72 lateral, 212 pivoting, and 83 reconnaissance flows per seed. The very small initial-compromise group limits interpretation.

| Policy | Exfiltration | Initial | Lateral | Pivoting | Recon. |
| --- | --- | --- | --- | --- | --- |
| Ordinary natural tree | 99.37% | 100.00% | 79.17% | 99.14% | 98.39% |
| Source-normal 1% threshold | 100.00% | 100.00% | 87.73% | 99.69% | 99.80% |
| Lateral-sensitive reference | 99.37% | 100.00% | 88.19% | 99.61% | 99.20% |
| Threshold-only alternative | 98.11% | 100.00% | 84.95% | 99.37% | 98.19% |
| Low-false-alarm candidate | 98.11% | 95.24% | 84.49% | 98.82% | 97.39% |

## 4.6 What the original engineering screen found

All **152 final model cells and 19 registered groups completed**. The independent source consistency audit passed. The recorded joint engineering-screen decision was **INFEASIBLE**: only 6 of ten primary fitting seeds produced a feasible reference policy. The all-ten-feasible prerequisite was therefore unmet. A passing software or artifact audit is not a passing scientific hypothesis.

Here, independent audit means a separately implemented software and calculation check. It was not human review, external peer review, independent relabeling, or a model refit.

Infeasible primary seeds were: **20260921, 20260924, 20260926, 20260929**. In each, no threshold on any of the eight final CV-selected family/weighting detectors simultaneously met the selection requirements of at least 90% lateral recall and at most 1% benign FPR. This statement does not cover discarded CV hyperparameter models, other learning algorithms, or every possible detector.

The 90% requirement and the other numerical limits were investigator-chosen. A result below 90% is not automatically useless, just as a result above it is not automatically safe. This study has no stakeholder utility calculation establishing either conclusion. The positive metric changes and the unmet original requirement are both retained.

Counts below are on the same verification partition: 14,965 benign flows and 72 lateral flows. Unselected policies have no verification result; their values are not zero.

| Seed | Selection status | Reference FP / lateral TP | Candidate FP / lateral TP | Same as threshold-only? |
| --- | --- | --- | --- | --- |
| 20260921 | INFEASIBLE | Not selected | Not selected | No candidate |
| 20260922 | SELECTED | 140 / 59 | 140 / 59 | Yes |
| 20260923 | SELECTED | 131 / 67 | 97 / 67 | Yes |
| 20260924 | INFEASIBLE | Not selected | Not selected | No candidate |
| 20260925 | SELECTED | 139 / 62 | 63 / 60 | No |
| 20260926 | INFEASIBLE | Not selected | Not selected | No candidate |
| 20260927 | SELECTED | 73 / 67 | 9 / 60 | No |
| 20260928 | SELECTED | 105 / 62 | 105 / 62 | Yes |
| 20260929 | INFEASIBLE | Not selected | Not selected | No candidate |
| 20260930 | SELECTED | 58 / 64 | 17 / 57 | Yes |

![Each of ten primary fitting seeds on the same exposed verification partition: 14,965 unique benign feature groups and 72 lateral groups. Natural argmax and source-normal threshold controls appear for every seed; a missing candidate diamond means source selection was infeasible. Dashed lines mark 1% benign FPR and 90% lateral recall. No confidence intervals are implied.](figures/primary_seeds.png)

### Selection-only description of the attainable operating points

After completing the frozen experiment, saved selection probabilities were examined to describe the attainable tradeoff within the eight final fitted detectors per seed. All tied score cutoffs were retained. No new policy, threshold, model fit, or success gate resulted. These are selection-data descriptions, not held-out performance estimates.

| Seed | Locked status | Maximum selection lateral recall at ≤1% FPR | Minimum selection FPR at ≥90% lateral recall |
| --- | --- | --- | --- |
| 20260921 | INFEASIBLE | 88.889% | 1.457% |
| 20260922 | SELECTED | 90.278% | 0.962% |
| 20260923 | SELECTED | 98.611% | 0.194% |
| 20260924 | INFEASIBLE | 88.889% | 1.624% |
| 20260925 | SELECTED | 94.444% | 0.421% |
| 20260926 | INFEASIBLE | 87.500% | 2.406% |
| 20260927 | SELECTED | 95.833% | 0.033% |
| 20260928 | SELECTED | 90.278% | 0.735% |
| 20260929 | INFEASIBLE | 84.722% | 1.611% |
| 20260930 | SELECTED | 95.833% | 0.047% |

The limits apply only to the saved CV-selected model/weighting cells, not to every hyperparameter configuration considered during fitting or to all possible solutions.

## 4.7 Secondary budgets and exposed test

| Normal fitting labels | Total fitting labels | Feasible / registered seeds | Declared secondary decision |
| --- | --- | --- | --- |
| 32 | 192 | 0/3 | INFEASIBLE |
| 128 | 288 | 1/3 | INFEASIBLE |
| 512 | 672 | 1/3 | INFEASIBLE |

![Argmax classifier tradeoffs at normal fitting budgets 32, 128, 512, and 1,024, always averaging the same first three seeds. Separate XGBoost and LightGBM panels show natural, balanced, lateral2, and lateral4 weighting; larger circles mark budget 32, squares mark 1,024, and the connected intermediate points mark 128 and 512 in order. All points use the same exposed verification sample, with 14,965 unique benign groups and 72 lateral groups per seed. These are individual classifiers, not selected constrained candidates; no confidence intervals are shown.](figures/budget_tradeoff.png)

All three secondary budgets retained infeasible supports under their declared screens. This does not negate the individual false-alarm or detection changes; it bounds reliability under the chosen joint rule. Appendix F provides the detailed secondary-policy results and the original exposed-test outcomes, with their separate seed counts. They are not used to choose a better-looking primary result.

## 4.8 DEDALE external stress

The fixed source seed was 20260921, at 1024 normal fitting examples. Its source selection was **INFEASIBLE**. Accordingly, no candidate, reference, or threshold-only candidate was available for external testing. The prespecified fallback was to evaluate the two already locked natural-tree controls without target fitting, calibration, or threshold selection.

The target consisted of 100,000 deterministically sampled unique benign feature groups and all four lateral groups from one documented PrintNightmare execution on DEDALE day 17. All four lateral groups came from the same execution; they are not four independent attacks. Other attack stages were excluded by the frozen stress scope.

| Source-locked control | Benign false alerts | Benign FPR | Lateral detected | Lateral recall | Sample attack F1 |
| --- | --- | --- | --- | --- | --- |
| Natural tree, argmax | 7,418/100,000 | 7.418% | 1/4 | 25.000% | 0.0003 |
| Natural tree, source-normal 1% threshold | 24,511/100,000 | 24.511% | 4/4 | 100.000% | 0.0003 |

| Source-locked control | Sample attack precision | Binary ROC-AUC | Sample average precision |
| --- | --- | --- | --- |
| Natural tree, argmax | 0.013% | 0.8698 | 0.0002 |
| Natural tree, source-normal 1% threshold | 0.016% | 0.8698 | 0.0002 |

![DEDALE controls-only external stress for fixed source seed 20260921: false benign alerts among 100,000 sampled unique normal groups and lateral detections among four unique lateral flows. All four lateral flows belong to one execution. The source candidate was infeasible and is absent; no confidence intervals or incident-level recall estimates are shown.](figures/external_stress.png)

The source-normal 1% label names its source calibration rule; it is not a 1% target guarantee. In a multiclass model it also need not be a stricter decision rule than argmax. The larger alert count on DEDALE must therefore be reported rather than described as successful suppression. Precision, F1, and average precision describe this deliberately selected sample; they are not deployment-prevalence estimates. Detecting one of four flows does not mean the entire incident was missed; a single flow could alert on that execution. Even four-of-four detections cannot establish protection across independent executions or a three-point noninferiority margin.

The external consistency audit passed. That audit reconstructs saved counts and provenance; it does not independently replay the attack, adjudicate the author's labels, or prove matching feature-extractor settings. This completed stress test supplies no external validation of a constrained candidate, because no such candidate was selected for the fixed source seed.

Complete numerical aggregates and provenance are available in [EVIDENCE.json](../../results/lateral_protection_v1/EVIDENCE.json), [SUMMARY.json](../../results/lateral_protection_v1/SUMMARY.json), [CELL_METRICS.json](../../results/lateral_protection_v1/CELL_METRICS.json), [source audit](../../results/lateral_protection_v1/AUDIT.json), and [external audit](../../results/lateral_protection_v1/EXTERNAL_AUDIT.json).

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


# References

Angelopoulos, A. N., Bates, S., Candès, E. J., Jordan, M. I., & Lei, L. (2025). Learn then test: Calibrating predictive algorithms to achieve risk control. *The Annals of Applied Statistics, 19*(2), 1641–1662. https://doi.org/10.1214/24-AOAS1998

Bae, C., Ding, H., Ma, S., & Zhang, X. (2026). DUPIN: Attack learning is still needed! Demonstrating few-shot after unsupervised pretraining is a nimble forensics learner. In *35th USENIX Security Symposium (USENIX Security 26)* (pp. 2287-2306). USENIX Association. https://www.usenix.org/conference/usenixsecurity26/presentation/bae

Bilot, T., Zouaoui, A., Al Agha, K., El Madhoun, N., & Pasquier, T. (2026). *LARES: Host-centered lateral movement detection via inductive graph reasoning* [Accepted conference paper, author preprint]. 42nd IEEE Annual Computer Security Applications Conference. https://tfjmp.org/publications/2026-acsac.pdf

Debelie, A., Bagui, S. S., Bagui, S. C., & Mink, D. (2026). A systematic ablation study of GAN-based minority augmentation for intrusion detection on UWF-ZeekData22. *Electronics, 15*(6), Article 1291. https://doi.org/10.3390/electronics15061291

García, P., de Curtò, J., de Zarzà, I., Cano, J. C., & Calafate, C. T. (2025). Foundation models for cybersecurity: A comprehensive multi-modal evaluation of TabPFN and TabICL for tabular intrusion detection. *Electronics, 14*(19), Article 3792. https://doi.org/10.3390/electronics14193792

Kushwaha, D., Nandakumar, D., Kakkar, A., Gupta, S., Choi, K., Redino, C., Rahman, A., Chandramohan, S. S., Bowen, E., Weeks, M., Shaha, A., & Nehila, J. (2022). *Lateral movement detection using user behavioral analysis* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2208.13524

Lanvin, M., & Majorczyk, F. (2026). Get out of DEDALE with RESCOUSSE: A new dataset and testbed for evaluating the detection of APT attacks among network and system logs. In R. Laborde, J. Garcia-Alfaro, G. Blanc, P.-F. Gimenez, H. Kalutarage, N. Yanai, A. Shukla, S. Pirbhulal, J. Posegga, & K.-Y. Lam (Eds.), *Computer security. ESORICS 2025 international workshops* (Lecture Notes in Computer Science, Vol. 16232, pp. 3–23). Springer. https://doi.org/10.1007/978-3-032-16092-8_1

Layman, L., & Roden, W. (2023). *A controlled experiment on the impact of intrusion detection false alarm rate on analyst performance* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2307.07023

Li, J., Li, T., Zhang, R., Wan, Z., & Yang, Z. (2026). Apmp: APT attack detection in few-shot scenarios based on entity potential relations. *Cybersecurity, 9*, Article 172. https://doi.org/10.1186/s42400-026-00592-5

Liu, J., Shen, Y., Simsek, M., Kantarci, B., Mouftah, H. T., Bagheri, M., & Djukic, P. (2022). A new realistic benchmark for advanced persistent threats in network traffic. *IEEE Networking Letters, 4*(3), 162–166. https://doi.org/10.1109/LNET.2022.3185553

Praxis experiment repository. (2026, September 21). *Final praxis decision: Rare-stage protection and limited-label APT recognition* [Audited development report; commit 9dd2b81276c86fc7591a90fa85eb879f831e798c]. https://github.com/garypagangit/praxis/blob/9dd2b81276c86fc7591a90fa85eb879f831e798c/experiments/apt_benchmark/results/tabular_followup_decision_v1/REPORT.md

Revell, L., Kang, H., Seo, J. T., & Kim, D. D. (2026). Systematic evaluation of few-shot learning for unseen IoT network attack detection. *Computer Modeling in Engineering & Sciences, 147*(1), Article 45. https://doi.org/10.32604/cmes.2026.078467

Saidane, S., Telch, F., Shahin, K., Gkonis, P., & Granelli, F. (2026). ULTIMATE: A multi-agent deep reinforcement learning framework for false-positive optimized enterprise intrusion detection. *Array, 30*, Article 100896. https://doi.org/10.1016/j.array.2026.100896

Singhal, S., & Kumar, K. A. (2026). A cost-sensitive random forest framework for ARP spoofing detection in Internet of Medical Things networks. *Frontiers in Big Data, 9*, Article 1878242. https://doi.org/10.3389/fdata.2026.1878242

Smiliotopoulos, C., & Kambourakis, G. (2026). Machine learning for lateral movement detection using Sysmon logs: An empirical comparison of imbalanced and resampled data. *International Journal of Information Security, 25*, Article 38. https://doi.org/10.1007/s10207-025-01182-1

Tian, Y., & Feng, Y. (2025). Neyman–Pearson multi-class classification via cost-sensitive learning. *Journal of the American Statistical Association, 120*(550), 1164–1177. https://doi.org/10.1080/01621459.2024.2402567

Tong, X., Feng, Y., & Li, J. J. (2018). Neyman–Pearson classification algorithms and NP receiver operating characteristics. *Science Advances, 4*(2), Article eaao1659. https://doi.org/10.1126/sciadv.aao1659

## Reference verification and publication status

The journal issue years and DOI metadata were checked against primary records. LARES is cited as an accepted-paper author version because final proceedings details were not verified. Layman and Roden and Kushwaha et al. are labeled as preprints. DUPIN is verified in the official 2026 USENIX proceedings; APMP is verified through the journal publisher. The bounded Sysmon review used abstract/metadata, and ULTIMATE's overlap was assessed from its publisher abstract; no omission in their full methods is inferred. The local repository report is audited project evidence, not a peer-reviewed publication.

# Appendix A. Software and execution accounting

The recorded validation receipt reports **40 passing software tests** in 20.254 seconds, recorded at 2026-09-21T18:55:13.314864+00:00. These synthetic and artifact-tampering checks test software behavior; they do not demonstrate model effectiveness, independent attack truth, or a human audit. The assembler verifies that the referenced test-source hashes still match the receipt.

| Package | Recorded version |
| --- | --- |
| lightgbm | 4.6.0 |
| numpy | 2.2.6 |
| pandas | 2.3.3 |
| python | 3.11.9 |
| scikit-learn | 1.7.2 |
| scipy | 1.15.3 |
| tabicl | 2.2.0 |
| tabpfn | 9.0.0 |
| torch | 2.5.1+cpu |
| xgboost | 2.1.4 |

The sum of per-cell fit-and-tuning elapsed times was **4,316.6 seconds**. The two workers could overlap, so this is neither CPU-core seconds nor the total batch wall time. Inference latency was not benchmarked. Foundation packages present in the environment do not imply that a foundation model was fitted in this tree experiment.

# Appendix B. Full label ledger

| Normal fitting budget | Attack fitting labels per fit | Total fitting labels per fit |
| --- | --- | --- |
| 32 | 160 | 192 |
| 128 | 160 | 288 |
| 512 | 160 | 672 |
| 1024 | 160 | 1184 |

| Partition | All labels | Normal labels | Attack labels | Lateral labels |
| --- | --- | --- | --- | --- |
| Selection | 15390 | 14964 | 426 | 72 |
| Verification | 15392 | 14965 | 427 | 72 |
| Test | 30787 | 29929 | 858 | 144 |

There were 10,746 unique fitting rows across the registered groups. The available labeled fit pool contained 92,350 rows, within 153,919 prepared labeled rows. Supports overlap across seeds and budgets; adding per-fit counts would overstate unique labels. Conversely, reporting only one support's count would understate label access used for stratification, selection, and assessment. No low acquisition-cost claim follows from the allocated fitting budget.

# Appendix C. Evidence and provenance

| Binding | Value |
| --- | --- |
| Source freeze Git revision | 95d949276d754e6155b789b60779414ed88afcbd |
| Source execution binding | 8c03ddb57d72de601bd55fe652f134a58fadaa2d6a5258edd3dda2fe93ad5a0e |
| Source protocol SHA-256 | f20d9a96c693081896ca5057b207d635b82912eeccc5da073143f059a5257a5e |
| Software validation SHA-256 | 7f063a6d7a5f4289e33d548cd5ad3077f3acf28103fc643dfbe2b7ba322e7861 |
| Optional frontier diagnostics SHA-256 | b2ef07683adbfad6df73cd3416e7ea72725803146d8d8d5eb884f02f9f9ab5be |

| Published artifact | SHA-256 |
| --- | --- |
| [EVIDENCE.json](../../results/lateral_protection_v1/EVIDENCE.json) | 3bf80c0317d58c382afcbb8b6023ea47141584e28732d226aa9b60998a52fbd5 |
| [SUMMARY.json](../../results/lateral_protection_v1/SUMMARY.json) | c8b09fa71b26f60262adf4c0bbe539375364dd97d453b328ea04f09964930f2b |
| [CELL_METRICS.json](../../results/lateral_protection_v1/CELL_METRICS.json) | 6b3d8d98b4eee9717c3967d1cf190f3484b651bafc0ea76f7853f9539aa7ff89 |
| [AUDIT.json](../../results/lateral_protection_v1/AUDIT.json) | 9ca5dc2b73a0c58a81d909632f002c1a0ba58998f48c47b1d3a336b7baa40374 |
| [EXTERNAL_RESULT.json](../../results/lateral_protection_v1/EXTERNAL_RESULT.json) | ce37313fe015dcc5743332b320af1032404cde64c5f9e10d00918dcd4f60805d |
| [EXTERNAL_AUDIT.json](../../results/lateral_protection_v1/EXTERNAL_AUDIT.json) | 68b0df150fad76512a4f5624f4462f77e023e902a6993f06f5ab7f7443281d7c |
| [PUBLICATION.json](../../results/lateral_protection_v1/PUBLICATION.json) | 846fd927696de24dee9e4dfdd9d5f3841b7b228c81b3ad2c2268d52fb7d49253 |

The source audit independently reconstructs support/partition rosters, fold-weight and imputer metadata, threshold/tie choices, saved prediction metrics, and exact decision arithmetic. It does not retrain the models or recompute unsaved inner-fold predictions. Receipt order documents the execution path, not independent human blindness. The external audit checks saved target predictions and source/target bindings; it does not replay the attack or rebuild author labels from raw evidence. The optional posthoc frontier description, when included, binds the complete source audit and does not modify the frozen experiment.

# Appendix D. Next study with justified operational requirements

Future work should use independent lateral executions and realistic legitimate remote-administration background. Split complete executions or campaigns, rather than correlated flows, into development and confirmation groups. Give each comparator the same label and search information; include ordinary natural and balanced trees, threshold-only selection, and an appropriately implemented established constrained procedure.

Before examining new confirmation outcomes, determine the intended review capacity and relative consequences of missed activity with the intended users. Choose and justify any recall floor, false-alert budget, or allowable loss from that use case. The earlier 90%/1%/three-point/20% values need not be reused, but changing them creates a new question and cannot alter the original recorded outcome. Publish descriptive operating curves and the selected requirement, including the number of independent units supporting each estimate.

Plan uncertainty estimates and sample size around independent incidents, paired errors, and temporal or network variation. A very small lateral sample cannot support a precise protection claim. Measure actual grouped analyst alerts and investigation time if the eventual claim concerns workload. A new flow-level score alone does not provide those observations.

# Appendix E. Exact-stage classification for every primary final cell

All entries below average ten argmax classifiers on the common verification partition. Precision/recall/F1 concern the named exact class; AUC and AP are one-versus-rest. They are different from the alert-policy detection metrics in Chapter 4. All weighting cells remain visible, including those that did not yield a feasible policy. Confusion matrices are retained in the linked CELL_METRICS artifact.

## xgboost/natural

| Class | Exact precision | Exact recall | Exact F1 | OvR AUC | OvR AP |
| --- | --- | --- | --- | --- | --- |
| DataExfiltration | 39.865% | 67.925% | 0.5009 | 0.9950 | 0.4872 |
| InitialCompromise | 28.913% | 94.286% | 0.4338 | 0.9998 | 0.8392 |
| LateralMovement | 48.957% | 58.750% | 0.5313 | 0.9843 | 0.5617 |
| NormalTraffic | 99.861% | 99.697% | 0.9978 | 0.9983 | 0.9999 |
| Pivoting | 85.726% | 65.377% | 0.7416 | 0.9972 | 0.8572 |
| Recon. | 72.116% | 73.373% | 0.7250 | 0.9972 | 0.7815 |

## xgboost/balanced

| Class | Exact precision | Exact recall | Exact F1 | OvR AUC | OvR AP |
| --- | --- | --- | --- | --- | --- |
| DataExfiltration | 37.375% | 67.925% | 0.4807 | 0.9900 | 0.4744 |
| InitialCompromise | 12.283% | 94.286% | 0.2147 | 0.9994 | 0.8385 |
| LateralMovement | 37.637% | 65.278% | 0.4686 | 0.9555 | 0.5485 |
| NormalTraffic | 99.917% | 99.069% | 0.9949 | 0.9980 | 0.9999 |
| Pivoting | 82.320% | 66.368% | 0.7342 | 0.9932 | 0.8182 |
| Recon. | 66.013% | 71.205% | 0.6833 | 0.9922 | 0.7431 |

## xgboost/lateral2

| Class | Exact precision | Exact recall | Exact F1 | OvR AUC | OvR AP |
| --- | --- | --- | --- | --- | --- |
| DataExfiltration | 36.487% | 67.170% | 0.4708 | 0.9885 | 0.4727 |
| InitialCompromise | 12.463% | 90.000% | 0.2147 | 0.9992 | 0.8243 |
| LateralMovement | 32.747% | 66.806% | 0.4273 | 0.9534 | 0.5328 |
| NormalTraffic | 99.927% | 98.857% | 0.9939 | 0.9980 | 0.9999 |
| Pivoting | 79.897% | 65.283% | 0.7171 | 0.9925 | 0.8080 |
| Recon. | 65.515% | 71.566% | 0.6811 | 0.9894 | 0.7395 |

## xgboost/lateral4

| Class | Exact precision | Exact recall | Exact F1 | OvR AUC | OvR AP |
| --- | --- | --- | --- | --- | --- |
| DataExfiltration | 36.499% | 67.170% | 0.4710 | 0.9889 | 0.4810 |
| InitialCompromise | 11.601% | 92.857% | 0.2039 | 0.9991 | 0.8182 |
| LateralMovement | 29.625% | 69.167% | 0.4100 | 0.9568 | 0.5448 |
| NormalTraffic | 99.933% | 98.714% | 0.9932 | 0.9979 | 0.9999 |
| Pivoting | 80.925% | 64.057% | 0.7141 | 0.9923 | 0.8091 |
| Recon. | 61.956% | 70.241% | 0.6463 | 0.9894 | 0.7255 |

## lightgbm/natural

| Class | Exact precision | Exact recall | Exact F1 | OvR AUC | OvR AP |
| --- | --- | --- | --- | --- | --- |
| DataExfiltration | 38.784% | 67.358% | 0.4904 | 0.9935 | 0.4838 |
| InitialCompromise | 23.832% | 95.714% | 0.3757 | 0.9997 | 0.8072 |
| LateralMovement | 45.612% | 61.528% | 0.5214 | 0.9739 | 0.5512 |
| NormalTraffic | 99.873% | 99.622% | 0.9975 | 0.9976 | 0.9999 |
| Pivoting | 86.618% | 65.425% | 0.7446 | 0.9956 | 0.8546 |
| Recon. | 71.907% | 70.482% | 0.7074 | 0.9955 | 0.7739 |

## lightgbm/balanced

| Class | Exact precision | Exact recall | Exact F1 | OvR AUC | OvR AP |
| --- | --- | --- | --- | --- | --- |
| DataExfiltration | 38.304% | 68.302% | 0.4891 | 0.9887 | 0.4906 |
| InitialCompromise | 14.304% | 91.429% | 0.2450 | 0.9994 | 0.7941 |
| LateralMovement | 44.479% | 63.611% | 0.5210 | 0.9508 | 0.5537 |
| NormalTraffic | 99.909% | 99.389% | 0.9965 | 0.9969 | 0.9999 |
| Pivoting | 85.240% | 65.991% | 0.7435 | 0.9911 | 0.8223 |
| Recon. | 64.970% | 71.566% | 0.6789 | 0.9931 | 0.7465 |

## lightgbm/lateral2

| Class | Exact precision | Exact recall | Exact F1 | OvR AUC | OvR AP |
| --- | --- | --- | --- | --- | --- |
| DataExfiltration | 39.530% | 69.623% | 0.5018 | 0.9872 | 0.4779 |
| InitialCompromise | 15.082% | 90.000% | 0.2574 | 0.9993 | 0.8048 |
| LateralMovement | 38.423% | 64.722% | 0.4745 | 0.9518 | 0.5430 |
| NormalTraffic | 99.911% | 99.232% | 0.9957 | 0.9972 | 0.9999 |
| Pivoting | 84.262% | 66.321% | 0.7419 | 0.9900 | 0.8163 |
| Recon. | 64.351% | 71.205% | 0.6718 | 0.9897 | 0.7294 |

## lightgbm/lateral4

| Class | Exact precision | Exact recall | Exact F1 | OvR AUC | OvR AP |
| --- | --- | --- | --- | --- | --- |
| DataExfiltration | 37.675% | 68.491% | 0.4835 | 0.9878 | 0.5002 |
| InitialCompromise | 14.860% | 88.571% | 0.2470 | 0.9991 | 0.8000 |
| LateralMovement | 36.422% | 64.444% | 0.4586 | 0.9531 | 0.5449 |
| NormalTraffic | 99.914% | 99.185% | 0.9955 | 0.9974 | 0.9999 |
| Pivoting | 85.207% | 63.821% | 0.7296 | 0.9911 | 0.8106 |
| Recon. | 65.650% | 70.602% | 0.6771 | 0.9895 | 0.7403 |

# Appendix F. Supplementary secondary and exposed-test outcomes

These tables retain all secondary supports and their original outcomes. Different row seed counts identify different comparison populations; only matching seeds support a paired contrast.

## F.1 32 normal fitting examples

| Seed | Selection status | Reference FP / lateral TP | Candidate FP / lateral TP | Same as threshold-only? |
| --- | --- | --- | --- | --- |
| 20260921 | INFEASIBLE | Not selected | Not selected | No candidate |
| 20260922 | INFEASIBLE | Not selected | Not selected | No candidate |
| 20260923 | INFEASIBLE | Not selected | Not selected | No candidate |

| Policy | Seeds | Mean benign FP | Benign FPR | Mean lateral detected | Lateral recall |
| --- | --- | --- | --- | --- | --- |
| Natural tree, argmax | 3 | 1496.3 | 9.999% | 67.3 | 93.519% |
| Natural tree, source-normal 1% threshold | 3 | 143.7 | 0.960% | 47.3 | 65.741% |

- Natural tree, argmax: seeds 20260921, 20260922, 20260923.
- Natural tree, source-normal 1% threshold: seeds 20260921, 20260922, 20260923.

## F.2 128 normal fitting examples

| Seed | Selection status | Reference FP / lateral TP | Candidate FP / lateral TP | Same as threshold-only? |
| --- | --- | --- | --- | --- |
| 20260921 | INFEASIBLE | Not selected | Not selected | No candidate |
| 20260922 | INFEASIBLE | Not selected | Not selected | No candidate |
| 20260923 | SELECTED | 151 / 66 | 100 / 62 | No |

| Policy | Seeds | Mean benign FP | Benign FPR | Mean lateral detected | Lateral recall |
| --- | --- | --- | --- | --- | --- |
| Constrained candidate | 1 | 100.0 | 0.668% | 62.0 | 86.111% |
| Natural tree, argmax | 3 | 483.0 | 3.228% | 63.0 | 87.500% |
| Natural tree, source-normal 1% threshold | 3 | 155.7 | 1.040% | 58.7 | 81.481% |
| Lateral-sensitive reference | 1 | 151.0 | 1.009% | 66.0 | 91.667% |
| Threshold-only ablation | 1 | 144.0 | 0.962% | 65.0 | 90.278% |

- Constrained candidate: seeds 20260923.
- Natural tree, argmax: seeds 20260921, 20260922, 20260923.
- Natural tree, source-normal 1% threshold: seeds 20260921, 20260922, 20260923.
- Lateral-sensitive reference: seeds 20260923.
- Threshold-only ablation: seeds 20260923.

## F.3 512 normal fitting examples

| Seed | Selection status | Reference FP / lateral TP | Candidate FP / lateral TP | Same as threshold-only? |
| --- | --- | --- | --- | --- |
| 20260921 | INFEASIBLE | Not selected | Not selected | No candidate |
| 20260922 | INFEASIBLE | Not selected | Not selected | No candidate |
| 20260923 | SELECTED | 111 / 64 | 82 / 64 | No |

| Policy | Seeds | Mean benign FP | Benign FPR | Mean lateral detected | Lateral recall |
| --- | --- | --- | --- | --- | --- |
| Constrained candidate | 1 | 82.0 | 0.548% | 64.0 | 88.889% |
| Natural tree, argmax | 3 | 71.0 | 0.474% | 58.7 | 81.481% |
| Natural tree, source-normal 1% threshold | 3 | 146.3 | 0.978% | 61.7 | 85.648% |
| Lateral-sensitive reference | 1 | 111.0 | 0.742% | 64.0 | 88.889% |
| Threshold-only ablation | 1 | 94.0 | 0.628% | 63.0 | 87.500% |

- Constrained candidate: seeds 20260923.
- Natural tree, argmax: seeds 20260921, 20260922, 20260923.
- Natural tree, source-normal 1% threshold: seeds 20260921, 20260922, 20260923.
- Lateral-sensitive reference: seeds 20260923.
- Threshold-only ablation: seeds 20260923.

These budgets used only the first three registered seeds and nested supports. Their screens are secondary development descriptions; no favorable budget was promoted to replace the failed primary requirement.

## F.4 Six-class ranking and classification

The following means include all ten primary fits for every family/weighting cell, regardless of policy feasibility. They describe each classifier's argmax output. Macro-F1 includes normal traffic; a larger value is not proof that the alert policy meets the lateral constraint. Appendix E reports every class separately.

| Model / weights | Fits | Six-class macro-F1 | Macro OvR AUC | Macro OvR AP | Exact lateral-stage recall |
| --- | --- | --- | --- | --- | --- |
| xgboost/natural | 10 | 0.6550 | 0.9953 | 0.7545 | 58.750% |
| xgboost/balanced | 10 | 0.5961 | 0.9881 | 0.7371 | 65.278% |
| xgboost/lateral2 | 10 | 0.5842 | 0.9868 | 0.7295 | 66.806% |
| xgboost/lateral4 | 10 | 0.5731 | 0.9874 | 0.7298 | 69.167% |
| lightgbm/natural | 10 | 0.6395 | 0.9926 | 0.7451 | 61.528% |
| lightgbm/balanced | 10 | 0.6123 | 0.9867 | 0.7345 | 63.611% |
| lightgbm/lateral2 | 10 | 0.6072 | 0.9859 | 0.7286 | 64.722% |
| lightgbm/lateral4 | 10 | 0.5986 | 0.9864 | 0.7327 | 64.444% |

## F.5 Original exposed test

The same locked choices were also evaluated on the original 30,787-row development test. It includes 29,929 benign and 144 lateral flows. These descriptive outcomes neither select thresholds nor rescue the verification gate, and this split is not the author's independent test artifact.

| Policy | Seeds | Mean benign FP | Benign FPR | Mean lateral detected | Lateral recall |
| --- | --- | --- | --- | --- | --- |
| Constrained candidate | 6 | 153.3 | 0.512% | 124.8 | 86.690% |
| Natural tree, argmax | 10 | 108.2 | 0.362% | 117.7 | 81.736% |
| Natural tree, source-normal 1% threshold | 10 | 300.1 | 1.003% | 125.6 | 87.222% |
| Lateral-sensitive reference | 6 | 228.3 | 0.763% | 128.5 | 89.236% |
| Threshold-only ablation | 6 | 182.3 | 0.609% | 125.5 | 87.153% |

| Policy (seed count) | Exfiltration | Initial | Lateral | Pivoting | Recon. |
| --- | --- | --- | --- | --- | --- |
| Constrained candidate (n=6) | 98.742% | 96.667% | 86.690% | 98.431% | 95.933% |
| Natural tree, argmax (n=10) | 99.906% | 98.000% | 81.736% | 98.188% | 96.726% |
| Natural tree, source-normal 1% threshold (n=10) | 100.000% | 100.000% | 87.222% | 99.506% | 98.750% |
| Lateral-sensitive reference (n=6) | 99.528% | 100.000% | 89.236% | 99.137% | 98.214% |
| Threshold-only ablation (n=6) | 98.899% | 98.889% | 87.153% | 98.706% | 97.321% |
