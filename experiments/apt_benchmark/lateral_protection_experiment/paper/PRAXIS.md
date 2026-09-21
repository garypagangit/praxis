# Reducing False Alarms While Preserving Lateral-Movement Detection

## A negative feasibility study of training emphasis and alert selection with scarce attack fitting labels

**Completed empirical manuscript.** Evidence publication: 2026-09-21T19:27:00.237930+00:00. Source scientific decision: **INFEASIBLE**. Source and external consistency audits: **PASS**.

**Study boundary:** This is a completed negative feasibility study on previously examined source data, with a controls-only external stress test. It establishes neither a successful new protection algorithm nor independent confirmation of deployment reliability.

## Abstract

Reducing false alarms can hide attack behavior that resembles normal activity. This praxis evaluated whether conventional tree weighting and constrained threshold selection could reduce false alarms while limiting missed lateral movement under a fixed attack fitting budget. The source study completed 152 final models across 19 support groups. Its primary condition used 1,024 benign and 160 attack fitting examples, two boosted-tree families, four weighting schemes, and ten fitting seeds. Fitting-only cross-validation selected each cell's hyperparameters; separate source partitions selected and verified locked policies. The primary decision was **INFEASIBLE**: only 6 of ten primary seeds supplied a detector/threshold pair satisfying the selection requirements of at least 90% lateral recall and no more than 1% benign false positives. Conditional means from feasible seeds could not satisfy the all-ten prerequisite. A fixed-seed DEDALE check therefore evaluated conventional controls only: argmax generated 7,418 false alerts among 100,000 sampled benign groups and detected 1 of four lateral groups; a source-normal threshold generated 24,511 false alerts and detected 4 of four. All lateral groups came from one execution. Independent consistency audits passed, but the previously exposed source data and one target execution do not establish incident-level generalization. The contribution is a reproducible failure boundary for a specified applied procedure, not a novel proven algorithm or production-ready suppression method.

**Keywords:** lateral movement; intrusion detection; false positives; class weighting; constrained selection; negative feasibility; network flows

## Executive explanation

We completed the test. The proposed selection process did **not** reliably find a detector that was both quiet enough and sensitive enough to lateral movement across all ten planned fitting supports. Some supports could supply a qualifying policy, but the primary rule required all ten. We retained the failures instead of averaging them away.

Among the 6 seeds with a selected policy, false alarms fell 33.3% relative to the reference, while lateral detection fell from 88.2% to 84.5%. In that subset, candidate recall was below the 90% verification floor, and the 3.70-percentage-point recall loss did not satisfy the less-than-three-point requirement. This is a descriptive result conditional on feasible selection; it does not replace or redefine the failed all-ten-seed primary requirement.

The new external data did not supply a successful candidate test either. The fixed source seed had no qualifying candidate, so only its conventional controls were tested. The argmax control alerted on one of four lateral flows; the source-normal threshold alerted on all four but generated many false alarms. Those four flows came from one attack execution, not four independent attacks. Detecting just one flow could still alert on that execution, so these counts are not incident-level recall.

The software and evidence checks passed. The scientific conclusion is narrower and unfavorable: this particular weighted-tree and threshold-selection procedure did not establish reliable protection under the declared requirements. A better overall score, an easier secondary budget, or a selected successful seed would not change that conclusion. The next useful study needs new independent executions, strong equally informed controls, and a new protocol before those outcomes are examined.

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

The preceding study compared stronger tree models selected by fitting-only cross-validation under two label budgets. The 160 attack fitting examples were held fixed within each seed. The larger condition added 992 normal examples. The results below are means across ten fits evaluated on the same 30,787 development-test flows; they are not ten independently collected datasets (Praxis experiment repository, 2026).

| Preliminary outcome | 32 normal + 160 attack fitting labels | 1,024 normal + the same 160 attack fitting labels |
|---|---:|---:|
| Six-class macro-F1 | 0.4421 | 0.6543 |
| Normal flows incorrectly flagged | 10.04% | 0.40% |
| All attack flows detected as any attack | 98.40% | 95.70% |
| Lateral flows detected as any attack | 94.24% | 83.06% |
| Lateral flows assigned the correct stage | 69.79% | 63.33% |

The exact audited figures imply a mean decline of approximately 16.1 detected lateral flows out of 144, alongside a decline from 3,003.8 to 119.6 benign alerts out of 29,929 normal flows. Decimal counts reflect means over fits. The comparison demonstrates an observed tradeoff; it does not isolate whether additional benign coverage, changed training class proportions, a different selected model, or other effects caused it. The [completed decision report](../../results/tabular_followup_decision_v1/REPORT.md) and [evidence review](../../lateral_protection_praxis/EVIDENCE_AND_DATA_PLAN.md) preserve the underlying results and limitations.

Two other findings constrain the present study. The earlier two-channel review policy failed its development improvement criterion; it targeted initial compromise and exfiltration, not a successful lateral-protection method. In a separate small Sandworm transfer check, TabICL's primary mean attack recall was 44.32% with a 28.21% normal false-positive rate. A source-normal 1% threshold reduced the target false-positive rate to 2.20% but left attack recall at 3.78%. That is evidence against assuming that a good source operating point transfers unchanged. [Audited external results](../../results/tabular_followup_v1/TRANSFER_SUMMARY.json).

## 1.4 Purpose and research questions

The purpose was to determine whether a constrained operating-point procedure can improve the useful false-alarm/lateral-detection tradeoff under a fixed attack-label budget, and to identify when the requirements are infeasible.

**Primary research question:** On the declared development verification partition, can a selection-locked detector and threshold reduce normal false alarms relative to a strong lateral-sensitive reference while satisfying the declared lateral-detection requirements?

**Secondary questions:**

1. Does changing training emphasis add benefit beyond moving the reference detector's threshold?
2. How does the tradeoff change as the number of unique normal fitting examples increases while attack fitting examples remain fixed?
3. Do lower benign alerts coincide with losses in other attack stages, reduced alert precision, or unstable results across fitting supports?
4. What additional data, labels, and independent executions are needed before a development result can support an operational recommendation?

## 1.5 Thesis and hypotheses

**Thesis evaluated:** Selecting a conventional detector and alert threshold under an explicit lateral-detection constraint may reduce false alarms more responsibly than selecting a detector on aggregate classification performance alone.

The primary development hypothesis was joint: the candidate's mean verification false-positive rate is more than 20% below the reference, its mean lateral-recall loss is less than three percentage points, its mean lateral recall is at least 90%, and its mean normal false-positive rate is no more than 1%. All ten primary seeds must yield a feasible selection. These are prespecified engineering targets for a development screen, not population confidence bounds or accepted industry safety limits.

The threshold-only ablation tested a narrower explanatory hypothesis: changing the selected detector contributes beyond changing the operating threshold of the reference detector. If the candidate equals or fails to improve upon that ablation, the evidence does not support extra value from the broader detector search.

## 1.6 Scope and completed contribution

The completed empirical scope was numerical flow classification and alerting with existing tree methods. The work reports the tested procedure's feasibility boundary, stage tradeoffs, label costs, threshold ablation, and a qualified controls-only external stress. It does not establish actor attribution, early warning, missing-log resilience, measured analyst savings, a successful new algorithm, or independently confirmed protection. Chapter 4 retains the negative and infeasible outcomes; Chapter 5 explains their limits.

# Chapter 2. Literature and conceptual basis

## 2.1 Review approach and limits

The supporting review prioritized primary journal records, official publication pages, author manuscripts, and institutional copies, emphasizing 2024–2026 literature. Earlier methodological work was retained where it established the error-control framework. This is a bounded review supporting a specific empirical design, not a systematic review or proof that no similar procedure exists. The [literature research note](../../lateral_protection_praxis/LITERATURE_REVIEW.md) records the search boundaries and publication-status checks.

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

## 2.5 Data and evidence quality

SCVIC-APT-2021 is associated with a peer-reviewed network APT benchmark paper (Liu et al., 2022). This study uses a prepared local copy of its author training data; it does not use the author's separate test artifact. Dataset publication and our local split qualification are different claims. The qualification receipts document what was actually available and how it was prepared. [Dataset paper](https://doi.org/10.1109/LNET.2022.3185553); [local qualification](../../tabular_batch/E0_DATASET_GATE.md).

DEDALE and RESCOUSSE provide a recent dataset/testbed direction for evaluating APT activity across network and system logs (Lanvin & Majorczyk, 2026). DEDALE was qualified for the limited controls-only stress reported in Chapter 4. Its author-provided labeled CICFlowMeter tables supported a documented feature adapter; the resulting four lateral rows remained one execution, and extractor equivalence was not established. [Published chapter](https://doi.org/10.1007/978-3-032-16092-8_1); [author documentation](https://dedale.inria.fr/download.html).

## 2.6 Synthesis and defensible gap

The literature supports the components of the proposed approach: additional benign support, cost-sensitive training, threshold selection, stage-specific evaluation, and error constraints. The plausible applied gap is narrower: measure whether these components can jointly deliver a useful lateral-protection tradeoff under controlled attack labels, count the information they consume, and disclose failure on independently evaluated activity.

Three distinctions guide the experiment. First, adding unique normal examples changes coverage as well as the observed class proportion. Second, choosing an alert threshold changes errors without necessarily changing the underlying classifier. Third, satisfying a constraint on familiar data does not establish that it survives a new environment. The controls address the first two distinctions; source development alone cannot resolve the third.

If an existing cost-sensitive method with the same information and constraints is equivalent to the proposed procedure, that equivalence is a finding to acknowledge. The contribution would be replication, evaluation, or an operational adaptation. A new name or software wrapper would not justify an algorithmic novelty claim.

# Chapter 3. Research methodology

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

# Chapter 4. Results

## 4.1 Completion, audit, and primary decision

All **152 final model cells and 19 registered groups completed**. The independent source consistency audit passed. The primary scientific decision was **INFEASIBLE**: only 6 of ten primary fitting seeds produced a feasible reference policy. The all-ten-feasible prerequisite was therefore unmet. A passing software or artifact audit is not a passing scientific hypothesis.

Here, independent audit means a separately implemented software and calculation check. It was not human review, external peer review, independent relabeling, or a model refit.

Infeasible primary seeds were: **20260921, 20260924, 20260926, 20260929**. In each, no threshold on any of the eight final CV-selected family/weighting detectors simultaneously met the selection requirements of at least 90% lateral recall and at most 1% benign FPR. This statement does not cover discarded CV hyperparameter models, other learning algorithms, or every possible detector.

## 4.2 Every primary fitting seed

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

## 4.3 Operating outcomes and the feasible-subset boundary

The conventional controls were evaluated in all ten seeds. Reference, candidate, and threshold-only rows include only seeds where a reference existed. Their denominators are explicit below. A favorable conditional mean cannot replace the all-ten-seed primary endpoint, and rows with different seed counts are not matched comparisons.

| Policy | Seeds | Mean benign FP | Benign FPR | Mean lateral detected | Lateral recall |
| --- | --- | --- | --- | --- | --- |
| Constrained candidate | 6 | 71.8 | 0.480% | 60.8 | 84.491% |
| Natural tree, argmax | 10 | 52.6 | 0.351% | 56.7 | 78.750% |
| Natural tree, source-normal 1% threshold | 10 | 143.0 | 0.956% | 61.4 | 85.278% |
| Lateral-sensitive reference | 6 | 107.7 | 0.719% | 63.5 | 88.194% |
| Threshold-only ablation | 6 | 85.8 | 0.574% | 61.2 | 84.954% |

- Constrained candidate: seeds 20260922, 20260923, 20260925, 20260927, 20260928, 20260930.
- Natural tree, argmax: seeds 20260921, 20260922, 20260923, 20260924, 20260925, 20260926, 20260927, 20260928, 20260929, 20260930.
- Natural tree, source-normal 1% threshold: seeds 20260921, 20260922, 20260923, 20260924, 20260925, 20260926, 20260927, 20260928, 20260929, 20260930.
- Lateral-sensitive reference: seeds 20260922, 20260923, 20260925, 20260927, 20260928, 20260930.
- Threshold-only ablation: seeds 20260922, 20260923, 20260925, 20260927, 20260928, 20260930.

| Policy | Seeds | Attack precision | Attack recall | Binary attack F1 | All-flow alert rate |
| --- | --- | --- | --- | --- | --- |
| Constrained candidate | 6 | 86.034% | 95.980% | 0.9044 | 3.129% |
| Natural tree, argmax | 10 | 88.745% | 95.597% | 0.9200 | 2.994% |
| Natural tree, source-normal 1% threshold | 10 | 74.441% | 97.400% | 0.8438 | 3.631% |
| Lateral-sensitive reference | 6 | 79.780% | 97.580% | 0.8770 | 3.407% |
| Threshold-only ablation | 6 | 83.552% | 96.565% | 0.8934 | 3.237% |

| Policy | Seeds | Binary attack ROC-AUC | Binary attack AP |
| --- | --- | --- | --- |
| Constrained candidate | 6 | 0.9982 | 0.9732 |
| Natural tree, argmax | 10 | 0.9978 | 0.9663 |
| Natural tree, source-normal 1% threshold | 10 | 0.9978 | 0.9663 |
| Lateral-sensitive reference | 6 | 0.9982 | 0.9743 |
| Threshold-only ablation | 6 | 0.9982 | 0.9743 |

Binary attack F1 treats any non-normal label as an attack. Its ROC-AUC and average precision use the continuous score `1 - pNormal`, independently of the displayed threshold. These differ from six-class macro-F1 and macro one-versus-rest ranking scores. Mean precision is the mean of seed precisions, not a ratio of mean counts. Decimal counts represent repeated-fit means, not fractional observations.

### Matched description restricted to the 6 feasible seeds

All five policies in the following table use exactly the same feasible seed subset. This conditional comparison remains descriptive and cannot demonstrate reliability over the full registered support roster.

Matched seed roster: 20260922, 20260923, 20260925, 20260927, 20260928, 20260930.

| Policy | Seeds | Mean benign FP | Benign FPR | Mean lateral detected | Lateral recall |
| --- | --- | --- | --- | --- | --- |
| Constrained candidate | 6 | 71.8 | 0.480% | 60.8 | 84.491% |
| Natural tree, argmax | 6 | 53.0 | 0.354% | 57.0 | 79.167% |
| Natural tree, source-normal 1% threshold | 6 | 145.3 | 0.971% | 63.2 | 87.731% |
| Lateral-sensitive reference | 6 | 107.7 | 0.719% | 63.5 | 88.194% |
| Threshold-only ablation | 6 | 85.8 | 0.574% | 61.2 | 84.954% |

Among the 6 seeds with a selected policy, false alarms fell 33.3% relative to the reference, while lateral detection fell from 88.2% to 84.5%. In that subset, candidate recall was below the 90% verification floor, and the 3.70-percentage-point recall loss did not satisfy the less-than-three-point requirement. This is a descriptive result conditional on feasible selection; it does not replace or redefine the failed all-ten-seed primary requirement.

## 4.4 Other attack stages

Entries count any alert on a true stage-labeled flow, rather than an exact-stage label. Verification denominators are exfiltration 53, initial compromise 7, lateral movement 72, pivoting 212, and reconnaissance 83. The initial-compromise count is especially small. No unreported stage is presumed protected.

| Policy (seed count) | Exfiltration | Initial | Lateral | Pivoting | Reconnaissance |
| --- | --- | --- | --- | --- | --- |
| Constrained candidate (n=6) | 98.113% | 95.238% | 84.491% | 98.821% | 97.390% |
| Natural tree, argmax (n=10) | 99.057% | 100.000% | 78.750% | 99.104% | 98.675% |
| Natural tree, source-normal 1% threshold (n=10) | 100.000% | 100.000% | 85.278% | 99.811% | 99.880% |
| Lateral-sensitive reference (n=6) | 99.371% | 100.000% | 88.194% | 99.607% | 99.197% |
| Threshold-only ablation (n=6) | 98.113% | 100.000% | 84.954% | 99.371% | 98.193% |

## 4.5 Threshold-only ablation and selected detectors

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

## 4.6 Secondary normal-label budgets

| Normal fitting labels | Total fitting labels | Feasible / registered seeds | Declared secondary decision |
| --- | --- | --- | --- |
| 32 | 192 | 0/3 | INFEASIBLE |
| 128 | 288 | 1/3 | INFEASIBLE |
| 512 | 672 | 1/3 | INFEASIBLE |

![Argmax classifier tradeoffs at normal fitting budgets 32, 128, 512, and 1,024, always averaging the same first three seeds. Separate XGBoost and LightGBM panels show natural, balanced, lateral2, and lateral4 weighting; larger circles mark budget 32, squares mark 1,024, and the connected intermediate points mark 128 and 512 in order. All points use the same exposed verification sample, with 14,965 unique benign groups and 72 lateral groups per seed. These are individual classifiers, not selected constrained candidates; no confidence intervals are shown.](figures/budget_tradeoff.png)

### 32 normal fitting examples

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

### 128 normal fitting examples

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

### 512 normal fitting examples

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

## 4.7 Classification of all six classes

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

## 4.8 Previously exposed original test

The same locked choices were also evaluated on the original 30,787-row development test. It includes 29,929 benign and 144 lateral flows. These descriptive outcomes neither select thresholds nor rescue the verification gate, and this split is not the author's independent test artifact.

| Policy | Seeds | Mean benign FP | Benign FPR | Mean lateral detected | Lateral recall |
| --- | --- | --- | --- | --- | --- |
| Constrained candidate | 6 | 153.3 | 0.512% | 124.8 | 86.690% |
| Natural tree, argmax | 10 | 108.2 | 0.362% | 117.7 | 81.736% |
| Natural tree, source-normal 1% threshold | 10 | 300.1 | 1.003% | 125.6 | 87.222% |
| Lateral-sensitive reference | 6 | 228.3 | 0.763% | 128.5 | 89.236% |
| Threshold-only ablation | 6 | 182.3 | 0.609% | 125.5 | 87.153% |

| Policy (seed count) | Exfiltration | Initial | Lateral | Pivoting | Reconnaissance |
| --- | --- | --- | --- | --- | --- |
| Constrained candidate (n=6) | 98.742% | 96.667% | 86.690% | 98.431% | 95.933% |
| Natural tree, argmax (n=10) | 99.906% | 98.000% | 81.736% | 98.188% | 96.726% |
| Natural tree, source-normal 1% threshold (n=10) | 100.000% | 100.000% | 87.222% | 99.506% | 98.750% |
| Lateral-sensitive reference (n=6) | 99.528% | 100.000% | 89.236% | 99.137% | 98.214% |
| Threshold-only ablation (n=6) | 98.899% | 98.889% | 87.153% | 98.706% | 97.321% |

## 4.9 Posthoc selection-frontier diagnostics

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

## 4.10 DEDALE external stress: conventional controls only

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

## 5.1 What the completed experiment established

The declared protection procedure did not meet its primary development requirement. Only 6 of ten primary seeds produced a feasible reference from the eight final CV-selected detectors, so the all-ten-seed prerequisite failed. This is a completed **negative feasibility result for the tested procedure**, not an unfinished model run and not an assertion that lateral-protection research is impossible. The artifact and metric audits passed, which supports the consistency of that recorded result.

The boundary matters: fitting CV selected one hyperparameter configuration for each of two families and four weighting schemes. Selection examined thresholds on those eight detectors. It did not optimize the downstream constraint over every discarded configuration or every possible algorithm. Macro-F1-selected hyperparameters may not produce the strongest constrained frontier. A future objective-aligned search is a separate experiment, with equal search access for its controls and a new untouched evaluation, not a retroactive repair of this result.

## 5.2 Why conditional means do not overturn infeasibility

The feasible subset answers what happened when this library supplied a qualifying source reference. It does not answer whether the process reliably qualifies across the registered supports. Reporting only successful selections would discard the very failures the primary rule was designed to retain. The conventional controls' ten-seed means and the constrained policies' 6-seed means also have different fitting-support denominators; the matched subset table limits this comparison explicitly.

Among the 6 seeds with a selected policy, false alarms fell 33.3% relative to the reference, while lateral detection fell from 88.2% to 84.5%. In that subset, candidate recall was below the 90% verification floor, and the 3.70-percentage-point recall loss did not satisfy the less-than-three-point requirement. This is a descriptive result conditional on feasible selection; it does not replace or redefine the failed all-ten-seed primary requirement.

Within selection data, candidate FPR could not exceed the threshold-only value, which could not exceed reference FPR, because the reference itself remained an available option. Those inequalities are consequences of selection. Only the locked verification results can show persistence outside the optimizing partition, and even those are exposed-source development evidence.

## 5.3 What the ablation and other stages contribute

The candidate was identical to the threshold-only policy in 4 of 6 feasible primary seeds. The recorded count and paired verification differences determine how much the broader detector search added in those cases. A different selected model is not sufficient evidence of benefit. Likewise, a higher six-class macro-F1 or binary ROC-AUC cannot compensate for a failed lateral requirement at the operating threshold.

Stage-specific tables reveal whether a quieter policy trades away initial compromise, exfiltration, pivoting, or reconnaissance. These outcomes were retained regardless of feasibility. With seven initial-compromise verification flows and 72 lateral flows, numerical changes can reflect very few observations; the study supplies neither an all-stage safety guarantee nor a population confidence certificate.

## 5.4 What the external stress means

The fixed source seed was infeasible, so DEDALE tested conventional controls only. The natural argmax control generated 7,418 false alerts among 100,000 sampled benign groups and detected 1 of four lateral groups. The source-normal threshold generated 24,511 false alerts and detected 4 of four. These results expose the operating-cost tradeoff under source-to-target shift. They do not demonstrate successful external protection by the unavailable candidate.

The four lateral groups belong to one documented execution. Detecting one of four flows is not evidence that the whole incident was missed, just as detecting four does not represent four independent successful attack detections. The author labels used scheduled action times with a three-minute margin, host pairs, and ports; these were not four independent manual adjudications, and the metric audit did not independently relabel them. Sampling 100,000 benign feature groups changes the evaluated prevalence, and deduplication changes the unit from raw flows to unique predictor rows. FPR and raw lateral counts remain useful descriptions, while precision/F1 cannot be extrapolated to a live stream. The source extractor revision also remains unqualified, so the stress includes possible extraction differences alongside network and attack differences.

## 5.5 Novelty and contribution

The literature already supplies benign-support expansion, class weighting, constrained error objectives, and validation-selected thresholds. Singhal and Kumar (2026) directly combine cost-sensitive training with a miss-constrained operating point in cybersecurity. Tian and Feng (2025), Tong et al. (2018), and Angelopoulos et al. (2025) provide established error-control foundations under their stated assumptions. This study neither invents those components nor establishes a new proven algorithm.

Its completed contribution is a bounded empirical account: a motivating normal-data tradeoff was turned into a matched-support, locked-selection test; infeasible supports were retained; threshold-only controls limited attribution; labels and software evidence were accounted for; and a recent external dataset was qualified for the narrower stress it could support. The result identifies a failure boundary for this concrete procedure. Whether that is sufficient for a particular institution's praxis requirements is an academic assessment, not a claim established by an automated experiment.

## 5.6 Threats to validity

**Prior exposure and adaptation.** The source question arose after previous SCVIC results were examined. A later source freeze prevents new outcome-driven changes to this run, but does not convert those data into untouched confirmation. Both halves of the old calibration partition and the original descriptive test retain this history.

**Dependence and sample size.** Exact-feature deduplication removes one form of overlap, not incident, host, temporal, or near-duplicate dependence. Ten fitting seeds reuse the same verification observations. They describe sensitivity to fitting support; they do not provide ten independent deployments or justify a narrow incident-level confidence interval.

**Finite methods and budget.** Only two tree families, four weighting schemes, fixed grids, and scarce fitting attack supports were tested. More normal examples change coverage, sample size, relative weights, absolute summed loss weight, and possibly the selected hyperparameters. Balanced mean-one weighting fixes relative class mass, not every other statistical or regularization effect. The study does not isolate a unique causal mechanism.

**Information and measurement.** Fitting supports contain 160 attack labels per fit, but selection, verification, test labeling, and the larger known-label pool supply additional information. An alert on a stage-labeled flow is not a completed analyst investigation, actor attribution, or proof of early warning. The study measured no analyst time, production outcome, missing-log robustness, or automatic suppression safety.

**Comparator and literature limits.** The experiment evaluated empirical weighted-tree and threshold policies, not a fully instantiated confidence-controlled NP algorithm. The bounded review of the closest Sysmon application used its abstract and metadata; it did not establish omissions in its full methods. These limits rule out broad novelty or certification claims.

## 5.7 Practical next study

The next defensible study needs new attack executions with legitimate remote-administration background, an agreed operational loss margin, and controls allowed the same search and label information. Appendix D specifies a concrete prospective design. The present results do not justify selecting a better-looking source seed, relaxing the 90%/1% requirements, or retuning on DEDALE and presenting the revision as confirmation.

Until a revised method is independently evaluated, an organization should treat this work as research evidence for shadow evaluation. No production detector was certified or authorized for suppression. Lower alert volume remains an incomplete success measure when the hidden cost is missed lateral activity.

## 5.8 Final conclusion

This completed study found that the declared tree-weighting and constrained-threshold procedure was not reliably feasible across the registered source fitting supports. The all-ten-seed development requirement failed, and the fixed external seed supplied no constrained candidate to test. Conventional controls on DEDALE showed a substantial false-alarm/detection tradeoff on one lateral execution. The evidence supports a reproducible negative feasibility finding and a focused next research question. It does **not** establish a successful lateral-protection solution, a new algorithm, or deployment readiness.

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

## Reference verification and publication status

The journal issue years and DOI metadata were checked against primary records. LARES is cited as an accepted-paper author version because final proceedings details were not verified. Layman and Roden is labeled as a preprint. The bounded Sysmon review used abstract/metadata, and ULTIMATE's overlap was assessed from its publisher abstract; no omission in their full methods is inferred. The local repository report is audited project evidence, not a peer-reviewed publication.

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

# Appendix D. Concrete prospective confirmation design

This appendix specifies future work; none of its new data collections or confirmation claims was completed by this experiment.

## D.1 Independent collection and decision units

Generate or obtain separate lateral-movement executions with contemporaneous legitimate administration. Predeclare hosts, credentials, remote-management tools, collection settings, and execution/campaign identifiers. Keep repeated interfaces and correlated flows from the same execution together. Separate whole execution/campaign groups into fitting, selection, one locked verification, and untouched confirmation blocks; reserve a later period or different network for confirmation. A benchmark containing one campaign cannot establish a many-incident claim merely by slicing its flows.

## D.2 Fair comparisons and a single locked choice

Use the same attack identities, benign-label cap, candidate-search access, and permitted selection/calibration labels for all comparators. Include a strong natural tree, balanced and lateral-weighted trees, a threshold-only control, and an established constrained/NP procedure with its actual assumptions and implementation. If the proposed rule is equivalent to a comparator, collapse the duplicate arm. A new search that tunes hyperparameters for the downstream constrained frontier must be declared before new outcomes, with identical access for controls. Do not reuse the present exposed verification data as independent confirmation.

## D.3 Prespecified requirements and adequate evidence

For each independent incident/campaign with suitable denominators, calculate lateral detection and normal FPR; compare candidate/reference on the same eligible groups and report equal-group means plus pooled flow counts. Before confirmation, lock the grouping, interval construction, handling of absent-stage groups, minimum group/sample adequacy, and multiplicity procedure. A future joint criterion may require a one-sided 95% upper bound for `F_candidate - 0.8 × F_reference` below zero, a lower bound for `R_candidate - R_reference` above `-0.03`, a lower bound for candidate lateral recall at least 0.90, and an upper bound for candidate FPR at most 0.01. These remain proposed engineering requirements, not clinical or industry standards. Plan sample size with realistic paired discordance and clustering before collecting confirmation outcomes. If independent groups cannot support those bounds, report insufficient confirmation evidence rather than treating individual flows or seeds as independent.

## D.4 Failure handling and operational evaluation

Accept or reject the single locked choice once. Do not search for a fallback after viewing confirmation labels. Report every other stage and every infeasible support, charge all known-normal and attack labels, and distinguish source-only transfer from target-assisted calibration. Only after independent validation should shadow evaluation measure incident aggregation, analyst burden, and missed activity under a prospectively defined workflow. Any production decision requires evidence and review specific to that environment; the current experiment supplies no automatic suppression authorization.

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
| Reconnaissance | 72.116% | 73.373% | 0.7250 | 0.9972 | 0.7815 |

## xgboost/balanced

| Class | Exact precision | Exact recall | Exact F1 | OvR AUC | OvR AP |
| --- | --- | --- | --- | --- | --- |
| DataExfiltration | 37.375% | 67.925% | 0.4807 | 0.9900 | 0.4744 |
| InitialCompromise | 12.283% | 94.286% | 0.2147 | 0.9994 | 0.8385 |
| LateralMovement | 37.637% | 65.278% | 0.4686 | 0.9555 | 0.5485 |
| NormalTraffic | 99.917% | 99.069% | 0.9949 | 0.9980 | 0.9999 |
| Pivoting | 82.320% | 66.368% | 0.7342 | 0.9932 | 0.8182 |
| Reconnaissance | 66.013% | 71.205% | 0.6833 | 0.9922 | 0.7431 |

## xgboost/lateral2

| Class | Exact precision | Exact recall | Exact F1 | OvR AUC | OvR AP |
| --- | --- | --- | --- | --- | --- |
| DataExfiltration | 36.487% | 67.170% | 0.4708 | 0.9885 | 0.4727 |
| InitialCompromise | 12.463% | 90.000% | 0.2147 | 0.9992 | 0.8243 |
| LateralMovement | 32.747% | 66.806% | 0.4273 | 0.9534 | 0.5328 |
| NormalTraffic | 99.927% | 98.857% | 0.9939 | 0.9980 | 0.9999 |
| Pivoting | 79.897% | 65.283% | 0.7171 | 0.9925 | 0.8080 |
| Reconnaissance | 65.515% | 71.566% | 0.6811 | 0.9894 | 0.7395 |

## xgboost/lateral4

| Class | Exact precision | Exact recall | Exact F1 | OvR AUC | OvR AP |
| --- | --- | --- | --- | --- | --- |
| DataExfiltration | 36.499% | 67.170% | 0.4710 | 0.9889 | 0.4810 |
| InitialCompromise | 11.601% | 92.857% | 0.2039 | 0.9991 | 0.8182 |
| LateralMovement | 29.625% | 69.167% | 0.4100 | 0.9568 | 0.5448 |
| NormalTraffic | 99.933% | 98.714% | 0.9932 | 0.9979 | 0.9999 |
| Pivoting | 80.925% | 64.057% | 0.7141 | 0.9923 | 0.8091 |
| Reconnaissance | 61.956% | 70.241% | 0.6463 | 0.9894 | 0.7255 |

## lightgbm/natural

| Class | Exact precision | Exact recall | Exact F1 | OvR AUC | OvR AP |
| --- | --- | --- | --- | --- | --- |
| DataExfiltration | 38.784% | 67.358% | 0.4904 | 0.9935 | 0.4838 |
| InitialCompromise | 23.832% | 95.714% | 0.3757 | 0.9997 | 0.8072 |
| LateralMovement | 45.612% | 61.528% | 0.5214 | 0.9739 | 0.5512 |
| NormalTraffic | 99.873% | 99.622% | 0.9975 | 0.9976 | 0.9999 |
| Pivoting | 86.618% | 65.425% | 0.7446 | 0.9956 | 0.8546 |
| Reconnaissance | 71.907% | 70.482% | 0.7074 | 0.9955 | 0.7739 |

## lightgbm/balanced

| Class | Exact precision | Exact recall | Exact F1 | OvR AUC | OvR AP |
| --- | --- | --- | --- | --- | --- |
| DataExfiltration | 38.304% | 68.302% | 0.4891 | 0.9887 | 0.4906 |
| InitialCompromise | 14.304% | 91.429% | 0.2450 | 0.9994 | 0.7941 |
| LateralMovement | 44.479% | 63.611% | 0.5210 | 0.9508 | 0.5537 |
| NormalTraffic | 99.909% | 99.389% | 0.9965 | 0.9969 | 0.9999 |
| Pivoting | 85.240% | 65.991% | 0.7435 | 0.9911 | 0.8223 |
| Reconnaissance | 64.970% | 71.566% | 0.6789 | 0.9931 | 0.7465 |

## lightgbm/lateral2

| Class | Exact precision | Exact recall | Exact F1 | OvR AUC | OvR AP |
| --- | --- | --- | --- | --- | --- |
| DataExfiltration | 39.530% | 69.623% | 0.5018 | 0.9872 | 0.4779 |
| InitialCompromise | 15.082% | 90.000% | 0.2574 | 0.9993 | 0.8048 |
| LateralMovement | 38.423% | 64.722% | 0.4745 | 0.9518 | 0.5430 |
| NormalTraffic | 99.911% | 99.232% | 0.9957 | 0.9972 | 0.9999 |
| Pivoting | 84.262% | 66.321% | 0.7419 | 0.9900 | 0.8163 |
| Reconnaissance | 64.351% | 71.205% | 0.6718 | 0.9897 | 0.7294 |

## lightgbm/lateral4

| Class | Exact precision | Exact recall | Exact F1 | OvR AUC | OvR AP |
| --- | --- | --- | --- | --- | --- |
| DataExfiltration | 37.675% | 68.491% | 0.4835 | 0.9878 | 0.5002 |
| InitialCompromise | 14.860% | 88.571% | 0.2470 | 0.9991 | 0.8000 |
| LateralMovement | 36.422% | 64.444% | 0.4586 | 0.9531 | 0.5449 |
| NormalTraffic | 99.914% | 99.185% | 0.9955 | 0.9974 | 0.9999 |
| Pivoting | 85.207% | 63.821% | 0.7296 | 0.9911 | 0.8106 |
| Reconnaissance | 65.650% | 70.602% | 0.6771 | 0.9895 | 0.7403 |
