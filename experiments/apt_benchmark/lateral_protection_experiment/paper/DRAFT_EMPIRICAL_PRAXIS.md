# Reducing False Alarms While Preserving Lateral-Movement Detection

## An empirical praxis on training emphasis and alert selection with scarce attack labels

**Manuscript source draft — September 21, 2026**

**Evidence status:** The motivating experiments are complete and audited. The new protection experiment has a specified development protocol. Its results and independent audit have not been incorporated into this manuscript. Chapter 4 is deliberately pending; this document does not claim that the new procedure works, is novel, or is ready for deployment.

**Study boundary:** A controlled development study on previously examined SCVIC data, followed by a separately qualified external evaluation if its data and design requirements are met. Independent confirmation is a further requirement, not an outcome supplied by freezing code on an already exposed dataset.

## Abstract

Network intrusion detectors can reduce false alarms while becoming less sensitive to subtle attack activity. This praxis investigates that tradeoff for lateral movement when attack fitting labels are scarce. Completed preliminary experiments on a prepared SCVIC development split found that increasing normal fitting examples from 32 to 1,024, while retaining the same 160 attack examples, reduced the mean normal false-positive rate of a cross-validation-selected tree from 10.04% to 0.40%. However, lateral flows detected as any attack declined from 94.24% to 83.06%. These observations motivated the present question after the development results were inspected. The new experiment compares XGBoost and LightGBM under natural, class-balanced, and lateral-emphasized training weights. A selection partition determines a conventional reference, a candidate operating point with a lateral-recall constraint, and a threshold-only ablation. The choices are locked before verification predictions are evaluated. The primary development condition uses 1,024 normal and 32 examples from each of five attack stages across ten fitting seeds; smaller normal budgets are secondary. All fitting, selection, verification, and evaluation labels are accounted for separately. The method uses established classification and threshold-selection ideas; its possible contribution is a reproducible applied evaluation of their benefits, limitations, and labeling costs. New experimental results are pending. Source development evidence cannot establish protection on independent incidents or another network.

**Keywords:** lateral movement; intrusion detection; false positives; class weighting; scarce attack labels; constrained selection; network flows

## Executive explanation

A detector can become quieter for two very different reasons. It may learn to recognize harmless activity better, or it may stop noticing some attacks. An overall score does not reliably distinguish those possibilities.

Our previous experiment demonstrated the practical concern. Giving a tree detector more examples of normal traffic greatly reduced its false alarms, but it also missed more traffic labeled as lateral movement. The next experiment asks whether ordinary training weights and a carefully selected alert threshold can retain the false-alarm benefit while limiting the loss of lateral detection.

The proposed workflow is simple: train several declared versions, check them on selection data, choose an operating point only if it meets the requirements, lock that choice, and evaluate it on separate verification data. If no version qualifies, the workflow reports that failure. It does not quietly relax the requirement. The present study measures this process on existing development data. A useful result there would justify stronger independent testing; it would not establish that an organization can safely suppress alerts.

# Chapter 1. Introduction and problem definition

## 1.1 Practical setting

An intrusion detector examines recorded activity and decides which observations warrant attention. In this study, the observation is a network flow represented by numerical traffic statistics. The detector predicts among normal traffic and five attack-stage labels. A separate operating rule converts those predictions into an attack alert.

The distinction between classification and alerting matters. A flow may receive the wrong attack-stage label and still reach an analyst. Conversely, a system can improve its average classification score while sending fewer lateral flows for review. The practical question is therefore not simply which model has the largest macro-F1. It is whether a chosen alert policy reduces benign alerts while retaining adequate detection of the attack behavior the organization needs to see.

A controlled simulated-alert experiment reported differences in analyst precision and task time between false-alarm conditions, without a significant sensitivity difference (Layman & Roden, 2023). This preprint supports studying human consequences, but its alert-review conditions are not this study's flow-level FPR measure. We do not convert a model's false-alarm reduction into an assumed improvement in analyst performance. [Author preprint](https://doi.org/10.48550/arXiv.2307.07023).

Lateral movement concerns an attacker's movement through an environment after gaining access. Some relevant actions overlap with legitimate remote administration, making the normal/attack distinction consequential. Recent work directly studies imbalance and resampling for lateral-movement detection in Sysmon logs, so the application itself is established rather than a new research category (Smiliotopoulos & Kambourakis, 2026). [Primary paper](https://doi.org/10.1007/s10207-025-01182-1).

## 1.2 Problem statement

**Intrusion detectors need fewer false alarms without an unacceptable increase in missed lateral activity, because errors in that tradeoff can either increase unnecessary investigation or hide a dangerous attack step (Smiliotopoulos & Kambourakis, 2026).**

For this praxis, “preserving” has an explicit operational meaning. The development procedure permits a small, declared recall loss relative to a strong reference while also requiring an absolute recall floor. It does not mean zero additional misses. Whether such a margin is acceptable in a real organization is an operational decision outside the evidence currently available.

## 1.3 Completed preliminary evidence

The preceding study compared stronger tree models selected by fitting-only cross-validation under two label budgets. The 160 attack fitting examples were held fixed within each seed. The larger condition added 992 normal examples. The results below are means across ten fits evaluated on the same 30,787 development-test flows; they are not ten independently collected datasets.

| Preliminary outcome | 32 normal + 160 attack fitting labels | 1,024 normal + the same 160 attack fitting labels |
|---|---:|---:|
| Six-class macro-F1 | 0.4421 | 0.6543 |
| Normal flows incorrectly flagged | 10.04% | 0.40% |
| All attack flows detected as any attack | 98.40% | 95.70% |
| Lateral flows detected as any attack | 94.24% | 83.06% |
| Lateral flows assigned the correct stage | 69.79% | 63.33% |

The exact audited figures imply a mean decline of approximately 16.1 detected lateral flows out of 144, alongside a decline from 3,003.8 to 119.6 benign alerts out of 29,929 normal flows. Decimal counts reflect means over fits. The comparison demonstrates an observed tradeoff; it does not isolate whether additional benign coverage, changed training class proportions, a different selected model, or other effects caused it. The [completed decision report](../../results/tabular_followup_decision_v1/REPORT.md) and [evidence review](../../lateral_protection_praxis/EVIDENCE_AND_DATA_PLAN.md) preserve the underlying results and limitations.

Two other findings constrain the present proposal. The earlier two-channel review policy failed its development improvement criterion; it targeted initial compromise and exfiltration, not a successful lateral-protection method. In a separate small Sandworm transfer check, TabICL's primary mean attack recall was 44.32% with a 28.21% normal false-positive rate. A source-normal 1% threshold reduced the target false-positive rate to 2.20% but left attack recall at 3.78%. That is evidence against assuming that a good source operating point transfers unchanged. [Audited external results](../../results/tabular_followup_v1/TRANSFER_SUMMARY.json).

## 1.4 Purpose and research questions

The purpose is to determine whether a constrained operating-point procedure can improve the useful false-alarm/lateral-detection tradeoff under a fixed attack-label budget, and to identify when the requirements are infeasible.

**Primary research question:** On the declared development verification partition, can a selection-locked detector and threshold reduce normal false alarms relative to a strong lateral-sensitive reference while satisfying the declared lateral-detection requirements?

**Secondary questions:**

1. Does changing training emphasis add benefit beyond moving the reference detector's threshold?
2. How does the tradeoff change as the number of unique normal fitting examples increases while attack fitting examples remain fixed?
3. Do lower benign alerts coincide with losses in other attack stages, reduced alert precision, or unstable results across fitting supports?
4. What additional data, labels, and independent executions are needed before a development result can support an operational recommendation?

## 1.5 Thesis and hypotheses

**Thesis to evaluate:** Selecting a conventional detector and alert threshold under an explicit lateral-detection constraint may reduce false alarms more responsibly than selecting a detector on aggregate classification performance alone.

The primary development hypothesis is joint: the candidate's mean verification false-positive rate is more than 20% below the reference, its mean lateral-recall loss is less than three percentage points, its mean lateral recall is at least 90%, and its mean normal false-positive rate is no more than 1%. All ten primary seeds must yield a feasible selection. These are prespecified engineering targets for a development screen, not population confidence bounds or accepted industry safety limits.

The threshold-only ablation tests a narrower explanatory hypothesis: changing the selected detector contributes beyond changing the operating threshold of the reference detector. If the candidate equals or fails to improve upon that ablation, the evidence does not support extra value from the broader detector search.

## 1.6 Scope and potential contribution

The current empirical scope is numerical flow classification and alerting with existing tree methods. It does not include actor attribution, proof of early warning, detection before a flow finishes, missing-log resilience, or measured analyst time savings.

The potential contribution is an auditable applied study: matched attack identities, explicit normal-label budgets, fold-local weighting, selection-only policy locking, threshold ablation, complete stage reporting, and transparent infeasibility. A positive development result would support feasibility in this setting. A defendable claim of broader usefulness would additionally require independent evidence and comparison with established constrained methods. No new learning algorithm is asserted.

# Chapter 2. Literature and conceptual basis

## 2.1 Review approach and limits

The supporting review prioritized primary journal records, official publication pages, author manuscripts, and institutional copies, emphasizing 2024–2026 literature. Earlier methodological work was retained where it established the error-control framework. This is a bounded review supporting a specific empirical design, not a systematic review or proof that no similar procedure exists. The [literature research note](../../lateral_protection_praxis/LITERATURE_REVIEW.md) records the search boundaries and publication-status checks.

Access limits affect the claims that can be made. The publisher metadata and abstract of the closest lateral-movement resampling study were inspected, but its subscription-limited full methods were not fully available. This manuscript therefore does not assert that its authors omitted a particular split, comparator, or selection rule. Such an omission would require full-text verification.

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

## 2.5 Data and evidence quality

SCVIC-APT-2021 is associated with a peer-reviewed network APT benchmark paper (Liu et al., 2022). This study uses a prepared local copy of its author training data; it does not use the author's separate test artifact. Dataset publication and our local split qualification are different claims. The qualification receipts document what was actually available and how it was prepared. [Dataset paper](https://doi.org/10.1109/LNET.2022.3185553); [local qualification](../../tabular_batch/E0_DATASET_GATE.md).

DEDALE and RESCOUSSE provide a recent dataset/testbed direction for evaluating APT activity across network and system logs (Lanvin & Majorczyk, 2026). DEDALE is a candidate for a separately qualified evaluation, not a result in this draft. Its published temporal setup and label semantics must govern a new protocol; a shared file format does not establish compatible predictors or reliable label joins. [Published chapter](https://doi.org/10.1007/978-3-032-16092-8_1); [author documentation](https://dedale.inria.fr/download.html).

## 2.6 Synthesis and defensible gap

The literature supports the components of the proposed approach: additional benign support, cost-sensitive training, threshold selection, stage-specific evaluation, and error constraints. The plausible applied gap is narrower: measure whether these components can jointly deliver a useful lateral-protection tradeoff under controlled attack labels, count the information they consume, and disclose failure on independently evaluated activity.

Three distinctions guide the experiment. First, adding unique normal examples changes coverage as well as the observed class proportion. Second, choosing an alert threshold changes errors without necessarily changing the underlying classifier. Third, satisfying a constraint on familiar data does not establish that it survives a new environment. The controls address the first two distinctions; source development alone cannot resolve the third.

If an existing cost-sensitive method with the same information and constraints is equivalent to the proposed procedure, that equivalence is a finding to acknowledge. The contribution would be replication, evaluation, or an operational adaptation. A new name or software wrapper would not justify an algorithmic novelty claim.

# Chapter 3. Research methodology

## 3.1 Design and execution status

The governing design is [protocol.json](../protocol.json), with its executable constants in [specification.py](../specification.py). It identifies the study as `exposed_source_development`. The protocol describes planned model fits and locked evaluation; completion and scientific outcomes must be established by the execution receipts and independent audit before Chapter 4 is populated.

The design contains 19 budget/seed groups and eight final models per group: two tree families crossed with four weighting schemes, for 152 fitted models. The primary condition uses ten seeds at 1,024 normal examples. Secondary conditions use 32, 128, and 512 normal examples at the first three seeds. The registered grids entail 4,788 inner-CV fits, followed by the 152 support-level refits. These counts describe the planned workload, not completed results.

## 3.2 Data provenance and preparation

The prepared SCVIC artifact contains 153,919 unique, nonconflicting feature rows and 73 predictors. Its source CSV contained 259,120 rows. Preparation excluded identifiers, IP addresses, ports, timestamps, labels, and four Idle statistics; removed 105,199 duplicate rows; and excluded one conflicting-label feature group containing two rows. Nonfinite predictor values became missing values before model-specific imputation. The exact preparation and hashes appear in the [qualification record](../../tabular_batch/E0_DATASET_GATE.md) and [preparation receipt](../../tabular_batch/SCVIC_PREPARATION.json).

The original deterministic partitions are stratified by class and grouped by exact predictor fingerprint. That construction prevents exact predictor duplicates from crossing partitions. It does not establish independence between incidents, hosts, time periods, or related flows. The author's separate test file has not been qualified in this study. The source artifact hash in the protocol binds the new experiment to the same prepared data as the preliminary work.

## 3.3 Fitting, selection, verification, and test roles

The old fit pool supplies fitting examples. The old calibration partition is divided into selection and verification halves, within each class, using a fixed SHA-256 ranking of its feature fingerprint and a declared tag. The first floor-half becomes selection; the remainder becomes verification. This split is fixed across all seeds. The original development test is retained for descriptive reporting only.

| Class | Available fit pool | Selection | Verification | Original development test |
|---|---:|---:|---:|---:|
| DataExfiltration | 316 | 52 | 53 | 106 |
| InitialCompromise | 43 | 7 | 7 | 15 |
| LateralMovement | 432 | 72 | 72 | 144 |
| NormalTraffic | 89,787 | 14,964 | 14,965 | 29,929 |
| Pivoting | 1,273 | 212 | 212 | 425 |
| Reconnaissance | 499 | 83 | 83 | 168 |
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

The two families are XGBoost and LightGBM, using CPU execution with four threads per worker. Their grids contain 12 and nine configurations, respectively. The first nine original LightGBM configurations exclude embedded `class_weight` settings, because explicit sample weights now define the treatment. Exact parameter dictionaries are retained in the protocol rather than inferred from final performance. The family searches are bounded and differ in size; this study does not claim an exhaustive or equal-cost architecture contest.

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

Every group preserves per-cell argmax classification and alert outcomes, in addition to the selected policies. This prevents the chosen policy from becoming the only visible result. The runner preserves input, code, environment, model, prediction, and selection-lock hashes. It rejects incompatible reuse or silent replacement of incomplete cells. An independent audit must recompute the rosters, policy choices, and metrics before results enter the manuscript. Such an audit establishes implementation consistency, not scientific effectiveness or independent ground truth.

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

The two improvement inequalities are strict. A reduction of exactly 20% or a recall loss of exactly three percentage points does not satisfy those criteria. If the reference has zero false alarms, the strict relative reduction cannot pass; the endpoint is not changed afterward. Exact count arithmetic governs boundary decisions.

`DEVELOPMENT_PROMISING` requires every guard; otherwise a complete feasible comparison is `DEVELOPMENT_NEGATIVE`. Missing groups remain `INCOMPLETE`, and infeasible seeds are retained as `INFEASIBLE`. Secondary budget summaries do not replace a failed primary result or select a new preferred budget. No confidence interval or significance claim is inferred from ten fitting seeds on common rows.

The 72 lateral verification flows give a per-seed recall resolution of approximately 1.39 percentage points. Three additional misses change a seed's rate by approximately 4.17 points. Averaging seeds smooths the numerical mean but does not create more independent attacks. Worst-seed FPR and lateral recall, individual-seed counts, all other stage recalls, and ordinary-control outcomes must accompany the aggregate decision.

## 3.9 External qualification and future confirmation

A fresh external evaluation needs verified label semantics, predictor compatibility, natural benign background, and a partition rule specified before target outcomes. DEDALE qualification is a separate workstream. Its uncertain or attack-related labels must not silently become confirmed benign examples. A Zeek/CICFlowMeter label join, if needed, requires checked direction, time, uniqueness, and conflict handling. A successful download alone does not qualify an experiment.

The DEDALE author's initial benign period cannot supply supervised lateral fitting examples. Source-only transfer, target-benign calibration, and training within a newly partitioned target dataset answer different questions and consume different labels. They must remain separate arms with explicit data access. The current SCVIC protocol authorizes no unspecified target adaptation or retuning.

Independent confirmation additionally needs a justified sampling unit, such as separate executions grouped at the highest shared incident or campaign level. The proposal's future confirmation target uses one-sided bounds for relative FPR reduction, lateral noninferiority, an absolute lateral floor, and an absolute FPR limit. Those inferential requirements are not implemented by the present mean-seed development gate. Group counts, paired analysis, interval construction, and sample adequacy must be fixed before confirmation outcomes. A single campaign with many flows cannot automatically supply many independent replications.

## 3.10 Reproducibility, rights, and practical safeguards

The final empirical package must identify the source-freeze revision, protocol and data hashes, full software versions, complete cell roster, selection locks, prediction hashes, and independent audit. Private flow records and model probabilities remain in their authorized storage; public reports use permitted aggregates and provenance. A software-test pass is reported separately from the experiment's scientific decision.

No automatic production suppression or analyst outcome is part of this study. Flow-level results may inform shadow evaluation after independent validation. A 1% FPR corresponds arithmetically to 1,000 flagged flows per 100,000 benign flows, before aggregation; it is not necessarily an acceptable workload. Claims about saved analyst time would require measured alert grouping and human investigation, which this experiment does not perform.

# Chapter 4. Results — pending completed execution and independent audit

**No new protection-experiment results are reported in this draft.** The completed numbers in Chapter 1 are preliminary motivation from earlier experiments. They must not be copied here as if they demonstrate the new procedure.

This chapter will be completed only from the immutable run artifacts and independent audit, including unfavorable, infeasible, and incomplete outcomes. The required contents are:

| Results section | Required evidence | Current manuscript status |
|---|---|---|
| Execution and provenance | Source freeze, complete cell/group roster, runtime, software versions, hashes and audit | Pending |
| Primary verification outcome | All ten paired seed counts and every joint guard; reference, candidate, threshold-only and ordinary controls | Pending |
| Other attack stages | Per-stage detection, exact-stage classification, raw misses, precision/F1 and ranking metrics | Pending |
| Training-emphasis ablations | Every family/weighting condition; candidate identity and threshold-only equivalence | Pending |
| Normal-budget sensitivity | All three prespecified smaller-budget seeds and full label ledger | Pending |
| Original test | Descriptive locked-policy outcomes, explicitly exposed-source evidence | Pending |
| External evaluation | Qualified protocol and dataset roles; all available counts and limits | Not established by this draft |
| Final empirical interpretation | Gate status, effect sizes, failures and scope of any supported claim | Pending |

No missing result should be represented by zero, an expected value, a preliminary software-smoke outcome, or a favorable example seed. If the experiment finishes without independent external evidence, Chapter 4 must state that the completed empirical scope is source development only.

# Chapter 5. Discussion framework, limitations, and conclusion boundary

## 5.1 Interpreting a promising development outcome

If all primary guards pass, the supported statement would be that the declared procedure met its point-estimate development requirements on the specified verification partition. The size of the false-alarm reduction, the absolute lateral recall, the allowed loss, and the individual seed counts would determine its practical meaning. The word “preserving” must remain tied to the stated margin rather than suggesting perfect detection.

The threshold-only comparison determines whether a change in detector adds evidence beyond operating-point adjustment. If both policies select the same model and threshold, the broader search has not supplied an additional mechanism. If they differ, the entire recorded tradeoff must be compared; a different model name alone does not establish benefit. A promising result would justify further evaluation, not a claim that an organization can deploy the policy unchanged.

## 5.2 Interpreting negative or infeasible outcomes

An infeasible selection means no declared detector/threshold pair met the selection requirements. A negative verification result means the locked procedure failed at least one development guard. These have different implications and must not be combined into a vague statement that the code “did not work.” An incomplete execution is a third condition: it does not establish either scientific success or failure.

If the procedure lowers false alarms but misses too much lateral activity, it fails the central purpose even when macro-F1 rises. If it preserves lateral recall but produces excessive normal alerts, it fails the intended operating cost. If it passes only at a secondary budget, that result is a new hypothesis to examine; it does not retroactively change the primary condition.

## 5.3 What the weight and budget controls can explain

Natural and balanced weights on identical rows compare alternative training emphasis without changing example identities. Nested benign supports with balanced weights hold relative class mass steady while expanding available examples. These contrasts can reveal whether an apparent normal-data advantage persists after a major class-proportion difference is removed.

They remain empirical contrasts rather than complete causal isolation. Increasing support changes the feature coverage, statistical estimation, absolute total weight, and possibly the selected hyperparameters. The fixed attack examples can be atypical, and the finite grids may favor one setting. Consequently, the manuscript should describe which treatments changed outcomes and avoid asserting a unique mechanism without further controlled evidence.

## 5.4 Limits of the current evidence

The strongest limitation is prior exposure. The research question was chosen after the SCVIC tradeoff was observed. Freezing the new procedure improves reproducibility and prevents new verification-driven retuning, but it does not erase that history. Repartitioning the old calibration rows does not create an independent confirmation sample.

The second limitation is the unit of evidence. Exact-feature deduplication prevents a specific form of leakage but does not remove dependence among related flows. Seventy-two lateral verification flows are not 72 established independent incidents. Ten fitting seeds share their evaluation rows and represent fitting variability, not repeated deployments. Confidence claims based on treating all these values as independent would overstate evidence.

The third limitation is construct validity. The labels identify dataset-defined stages; an alert is not an analyst-confirmed intrusion and an exact stage prediction is not actor attribution. The predictors summarize flows and may not be available at the earliest moment of an attack. A result cannot establish early identification without an explicitly time-respecting design.

The fourth limitation is generalization. The prior external result shows that source calibration did not maintain a useful target tradeoff. Differences in traffic, labels, extraction settings, or attack behavior can all matter. A qualified new dataset strengthens external evidence only for the actual tested regime; one campaign does not establish general performance across organizations.

Finally, this development implementation does not compare against a fully instantiated confidence-controlled NP algorithm. It compares empirical weighted-tree policies and threshold controls. Until that methodological comparison and the closest application full text are resolved, any stronger novelty or certification claim remains unsupported.

The direct weights-plus-miss-constrained-threshold precedent of Singhal and Kumar also narrows the contribution: a favorable source result would need to be defended as a specific evaluation and adaptation, with meaningful additional evidence, rather than the first combination of those components.

## 5.5 Practical and academic significance

The most useful output may be an explicit decision rule for when to stop: no qualifying operating point, insufficient independent evidence, or unacceptable misses in another stage. Such outcomes can prevent an attractive overall score from being mistaken for acceptable protection. A successful praxis can also document a bounded negative result and explain why the apparent fix fails, provided its question, controls, evidence, and limitations are rigorous.

For practitioners, the proposed label ledger makes the operational cost visible. More normal examples may be easier to obtain than new attacks, but verified normal calibration and stage-labeled selection still consume information and effort. A result should be described using all labels it accessed, the natural evaluation prevalence, the alert counts, and the tested environment.

For research, the contribution should follow the evidence. A positive, independently replicated constrained tradeoff could support an applied selection procedure. Equivalence to existing weighting and threshold methods would support an empirical replication or benchmark contribution. Neither outcome warrants describing ordinary class weights as new mathematics.

## 5.6 Provisional conclusion

The completed preliminary experiments establish a concrete development problem: additional normal fitting examples can coincide with fewer false alarms and more missed lateral activity. The present protocol turns that observation into a controlled test with matched attack supports, explicit training emphasis, locked selection, and declared failure criteria. **Whether that procedure provides a useful improvement is pending the new results and audit.** Independent confirmation, demonstrated operational value, and algorithmic novelty are not established by this draft.

# References

Angelopoulos, A. N., Bates, S., Candès, E. J., Jordan, M. I., & Lei, L. (2025). Learn then test: Calibrating predictive algorithms to achieve risk control. *The Annals of Applied Statistics, 19*(2), 1641–1662. https://doi.org/10.1214/24-AOAS1998

Bilot, T., Zouaoui, A., Al Agha, K., El Madhoun, N., & Pasquier, T. (2026). *LARES: Host-centered lateral movement detection via inductive graph reasoning* [Accepted conference paper, author preprint]. 42nd IEEE Annual Computer Security Applications Conference. https://tfjmp.org/publications/2026-acsac.pdf

Debelie, A., Bagui, S. S., Bagui, S. C., & Mink, D. (2026). A systematic ablation study of GAN-based minority augmentation for intrusion detection on UWF-ZeekData22. *Electronics, 15*(6), Article 1291. https://doi.org/10.3390/electronics15061291

García, P., de Curtò, J., de Zarzà, I., Cano, J. C., & Calafate, C. T. (2025). Foundation models for cybersecurity: A comprehensive multi-modal evaluation of TabPFN and TabICL for tabular intrusion detection. *Electronics, 14*(19), Article 3792. https://doi.org/10.3390/electronics14193792

Lanvin, M., & Majorczyk, F. (2026). Get out of DEDALE with RESCOUSSE: A new dataset and testbed for evaluating the detection of APT attacks among network and system logs. In R. Laborde, J. Garcia-Alfaro, G. Blanc, P.-F. Gimenez, H. Kalutarage, N. Yanai, A. Shukla, S. Pirbhulal, J. Posegga, & K.-Y. Lam (Eds.), *Computer security. ESORICS 2025 international workshops* (Lecture Notes in Computer Science, Vol. 16232, pp. 3–23). Springer. https://doi.org/10.1007/978-3-032-16092-8_1

Layman, L., & Roden, W. (2023). *A controlled experiment on the impact of intrusion detection false alarm rate on analyst performance* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2307.07023

Liu, J., Shen, Y., Simsek, M., Kantarci, B., Mouftah, H. T., Bagheri, M., & Djukic, P. (2022). A new realistic benchmark for advanced persistent threats in network traffic. *IEEE Networking Letters, 4*(3), 162–166. https://doi.org/10.1109/LNET.2022.3185553

Praxis experiment repository. (2026, September 21). *Final praxis decision: Rare-stage protection and limited-label APT recognition* [Audited development report; commit 9dd2b81276c86fc7591a90fa85eb879f831e798c]. https://github.com/garypagangit/praxis/blob/9dd2b81276c86fc7591a90fa85eb879f831e798c/experiments/apt_benchmark/results/tabular_followup_decision_v1/REPORT.md

Revell, L., Kang, H., Seo, J. T., & Kim, D. D. (2026). Systematic evaluation of few-shot learning for unseen IoT network attack detection. *Computer Modeling in Engineering & Sciences, 147*(1), Article 45. https://doi.org/10.32604/cmes.2026.078467

Saidane, S., Telch, F., Shahin, K., Gkonis, P., & Granelli, F. (2026). ULTIMATE: A multi-agent deep reinforcement learning framework for false-positive optimized enterprise intrusion detection. *Array, 30*, Article 100896. https://doi.org/10.1016/j.array.2026.100896

Singhal, S., & Kumar, K. A. (2026). A cost-sensitive random forest framework for ARP spoofing detection in Internet of Medical Things networks. *Frontiers in Big Data, 9*, Article 1878242. https://doi.org/10.3389/fdata.2026.1878242

Smiliotopoulos, C., & Kambourakis, G. (2026). Machine learning for lateral movement detection using Sysmon logs: An empirical comparison of imbalanced and resampled data. *International Journal of Information Security, 25*, Article 38. https://doi.org/10.1007/s10207-025-01182-1

Tian, Y., & Feng, Y. (2025). Neyman–Pearson multi-class classification via cost-sensitive learning. *Journal of the American Statistical Association, 120*(550), 1164–1177. https://doi.org/10.1080/01621459.2024.2402567

Tong, X., Feng, Y., & Li, J. J. (2018). Neyman–Pearson classification algorithms and NP receiver operating characteristics. *Science Advances, 4*(2), Article eaao1659. https://doi.org/10.1126/sciadv.aao1659

## Reference and completion notes

The review distinguishes a journal issue year from a DOI's embedded year: Tian and Feng appear in the 2025 issue after online publication in 2024, and Smiliotopoulos and Kambourakis were published in 2026 despite a DOI containing 2025. LARES is cited as an accepted-paper author version because final proceedings details were not verified. The SCVIC article's author sequence, volume, issue, and pages were checked against the publisher-deposited DOI metadata and an author-maintained [BibTeX record](https://www.site.uottawa.ca/~bkantarc/BIBFILES/J88.html). DEDALE chapter editors, volume, and pages were checked against the [Springer proceedings record](https://link.springer.com/book/10.1007/978-3-032-16092-8). The repository report is local empirical evidence, not a peer-reviewed publication.

Before submission as a completed empirical praxis, replace Chapter 4's pending status with independently audited outcomes; reconcile every discussion statement with those outcomes; insert the final execution/publication bindings; document any qualified external result and its actual independent units; and apply the institution's required author, committee, and document formatting. No institution, approval, human study, or successful new result has been invented in this source draft.
