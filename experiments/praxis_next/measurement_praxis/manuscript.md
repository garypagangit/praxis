# When Better APT Scores Hide Missed Attack Warnings

## A measurement study of temporal evaluation, historical context, and benchmark support

**Empirical praxis manuscript and reproducible evidence package**

September 23, 2026

**Research thesis.** An APT-stage classifier should be evaluated for correct stage identification, retention of an attack warning, and benign alert workload together, using a temporal protocol the source data can actually support.

**Applied problem.** Security teams can select a model with a better aggregate score that dismisses more consequential attack records as normal, particularly when training composition or access to historical evidence changes.

This manuscript reports completed experiments, a retrospective paired reanalysis, and a completed audit of four proposed benchmark extensions. The evidence package distinguishes these completed components from prospective model comparisons that the available releases could not support.

# Abstract

Aggregate classification scores can obscure whether an intrusion detector preserves an attack warning when it assigns the wrong attack stage. This measurement study examines the relationship among evaluation protocol, historical evidence, stage recognition, and missed warnings. Three completed experiments use 382,229 author-labeled flows from one UNRAVELED campaign. A controlled temporal comparison holds the classifier architecture, later evaluation rows, and per-class fitting budgets fixed. Time-mixed fitting raises macro-F1 by 0.0632 and movement-label recall by 35.19 percentage points over past-only fitting. In a separate evidence-acquisition experiment, macro-F1 increases from 0.7148 to 0.7379 while exfiltration-labeled records receiving any attack warning decrease from 85.18% to 76.25%. Chronologically fitted history features improve macro-F1 from 0.7365 to 0.7582 and reduce mean benign false alerts from 24.0 to 14.3, while increasing exfiltration-to-benign errors. A retrospective reanalysis reports paired capture-bootstrap intervals and retains every declared budget and evidence condition. Qualification of four proposed extension datasets finds a further constraint: the inspected DAPT2020 release cannot support a single chronological cutoff with every native class represented on both sides; SCVIC has possible recorded-time support but unqualified physical chronology; DSRL is a synthetic DAPT derivative; and no qualified S-DAPT release was acquired. The contribution is a reproducible measurement and qualification framework using established confusion-matrix quantities. The results support joint reporting of exact-stage recall, stage-conditioned warning recall, and benign workload. Their empirical scope is one previously examined campaign and the inspected releases, rather than independent-campaign or early-warning validation.

**Keywords:** advanced persistent threats; intrusion detection; temporal evaluation; attack stages; false negatives; benchmark qualification; reproducibility.

# 1. Introduction

## 1.1 The decision a security practitioner needs to make

A security analyst reviewing a suspicious transfer faces two related questions: should this activity receive an attack warning, and which attack stage best describes it? A system can answer the second question incorrectly while still drawing attention to the activity. It can also assign a benign label and remove that opportunity for review. These outcomes have different operational meanings, even when a multiclass objective assigns them the same penalty.

Consider 100 records labeled exfiltration by a dataset author. If a model calls 60 exfiltration, 20 another attack stage, and 20 benign, its exact-stage recall is 60% and its warning recall is 80%. This illustrative accounting is not a study result. It explains why a single headline score cannot describe both stage accuracy and preservation of an attack label. Warning recall must also be considered with benign false alerts: predicting an attack for every record preserves every warning and creates an unusable workload.

Uddin et al. (2025) provide a direct empirical precedent for this distinction. Their hierarchical-versus-flat intrusion study reports per-attack recognition and attacks misclassified as normal. Recent APT provenance work also challenges the relationship between conventional evaluation scores and practical detection behavior (Bilot et al., 2025; Guerra et al., 2026). These findings motivate closer measurement of the decisions represented by a score, rather than assuming that a new model architecture solves the evaluation problem.

## 1.2 Problem statement and purpose

**Problem statement.** APT-stage evaluation can reward a change in aggregate classification performance without making its effects on missed attack warnings and benign alert workload visible, while available benchmark artifacts may not support the temporal comparison needed to interpret that change.

The purpose of this praxis is to measure these effects under explicit controls and provide an executable audit that practitioners can apply before accepting a stage classifier. The immediate application is model evaluation and selection. It is not a production detector deployment or a forecast of data theft.

The industry consequence is concrete: a team comparing model updates could accept a higher F1 score while sending fewer exfiltration-labeled events for investigation. A team can also overestimate its evidence by counting many correlated flows as independent incidents or by treating related dataset releases as separate replications. The study measures examples of these issues and documents the source checks needed to interpret them.

## 1.3 Research questions and contribution

**RQ1:** How much does allowing later-period fitting data change stage performance when architecture, evaluation rows, and class-specific fitting counts are held fixed?

**RQ2:** When historical evidence or evidence-acquisition policy changes, how do exact-stage recognition, attack warnings, and benign false alerts change together?

**RQ3:** Which of four requested public APT benchmark artifacts support an unchanged, all-stage chronological comparison, and what prevents the others from doing so?

The completed contribution has three parts. First, the controlled temporal experiment quantifies training-composition sensitivity on a fixed evaluation population. Second, the evidence experiments identify and quantify a consequential difference between aggregate score improvement and warning retention. Third, the portable audit exposes native-label support, source dependencies, and temporal qualification requirements before additional models are fitted. The software, protocols, aggregates, verification receipts, and manuscript are linked in the accompanying evidence index.

This contribution uses established metrics. Its value lies in controlled observations, a transparent accounting of the available evidence, and reusable evaluation infrastructure. It does not depend on claiming a new mathematical definition of recall.

# 2. Literature and Research Gap

## 2.1 Temporal validity in security evaluation

TESSERACT established temporal and distributional constraints for evaluating malware classifiers and showed why inappropriate splits can produce misleading conclusions (Pendlebury et al., 2019). This is foundational prior art rather than part of the recent-literature window. Holding out random records is not equivalent to asking whether a model trained earlier will work later.

Bilot et al. (2025) examine provenance-based intrusion detectors in a common framework, identify practical and evaluation shortcomings, and include simple alternatives. Their work supports the use of strong simple controls and detection-relevant outcomes. Guerra et al. (2026) directly address APT provenance benchmarking, including temporally separated evaluation and the influence of benchmark semantics on conclusions. Consequently, neither temporal hygiene nor critical measurement of APT detection is new in itself.

The present temporal contrast is narrower: it keeps the later evaluation rows and per-class fitting budget constant while changing access to later-period training observations. This avoids attributing a difference caused by a different test population to training chronology alone. It still changes training composition and diversity; it cannot identify an effect of time independently of every other property of those added observations.

## 2.2 Correct attack stage and retained attack warning

Uddin et al. (2025) compare hierarchical and flat intrusion classifiers across ten datasets and ten algorithms. The available author manuscript (Uddin et al., 2024) reports exact attack recognition, attacks classified as normal, confusion matrices, and false-positive tradeoffs. The distinction between a wrong attack type and a missed attack therefore has direct prior coverage. Renaming stage-conditioned binary recall would not create a new metric.

The empirical question addressed here is whether a fixed experimental comparison can improve macro-F1 while reducing warnings for an author-defined consequential stage. The answer must include benign workload and error destinations, because a warning-retention objective alone can be satisfied trivially. The paper reports this tradeoff from saved predictions and preserves its retrospective discovery status.

## 2.3 Recent flow and attack-stage research

The 2026 TAN-IDS framework provides a deployment-oriented, shared NetFlow evaluation interface with in-domain and cross-domain comparisons (Ha Thanh, 2026). Its stated limitations leave multiclass or family discrimination and systematic feature ablation for further work. This is a concrete scope boundary that motivates examining stage-specific errors under controlled changes in data and evidence.

Recent APT research already investigates temporal and contextual attack-stage recognition. StageFinder combines structural and temporal information for stage estimation (Phan & Bauschert, 2026). Other contemporary flow studies and dataset efforts investigate sequence or graph representations. The current work therefore does not claim that temporal context, ensembles, or flow-based APT stages are unexplored. It evaluates how particular contextual decisions affect a useful warning and how much the evaluation design contributes to the reported score.

Recent model comparisons and flow-sequence studies include Luengo Viñuela et al. (2026), Iturbe et al. (2026), and Ibrahim et al. (2025). SANGL also examines sequential network patterns and graph learning for APT detection (M K et al., 2026). These are direct application precedents; their published scores are not reproduced baselines in this paper. Bibliographic name forms follow the publishers' records, with source details retained in the reference audit.

Othman et al. (2026) study DAPT stage durations and residual time-to-compromise through a survival-modelling task. Their session-based timing question differs from requiring every native class in both earlier training and later testing for a closed-set classifier. The support limitation measured here applies to the latter requirement and does not invalidate the former use of DAPT.

## 2.4 Data origin and benchmark independence

UNRAVELED is a semi-synthetic APT dataset published in 2023 (Myneni et al., 2023). Its use here is necessary data provenance, not a claim to use a newly released 2026 corpus. The proposed expansion includes SCVIC-APT-2021 (Liu et al., 2022a, 2022b), DAPT2020 (Myneni et al., 2020), DSRL-APT-2023 (Shadabfar et al., 2025), and S-DAPT-2026 (Tijjani et al., 2026, withdrawn). Release names and paper dates do not establish independent executions, valid event clocks, or accessible source bytes.

DSRL is especially relevant to independence: its paper describes synthetic attacks generated from DAPT and benign examples sampled from DAPT. These relationships must be retained in any evidence count. Likewise, the inspected S-DAPT arXiv record is withdrawn, and the present project did not acquire a qualified replacement data release. An unavailable artifact cannot become a performance result through its citation alone.

## 2.5 The gap addressed by this praxis

The working gap is the lack of the specific controlled evidence assembled here: fixed-anchor training-composition effects, joint accounting of stage errors and lost warnings under historical-evidence choices, and an executable qualification audit of the requested APT-flow releases. Close prior work covers each surrounding concept. The claim is an applied measurement contribution with explicit experimental controls and artifacts, not proof that no earlier paper contains any related observation.

The literature review is targeted, not systematic. It checks named closest work and recent primary sources on temporal APT evaluation, hierarchical error destinations, stage reasoning, and source datasets. The [reference and claim audit](LITERATURE_AND_CLAIMS.md) records publication status, accessible sections, metadata, and limits of verification. The accessible 2024 author version of the Uddin study is distinguished from its 2025 journal record; available 2026 preprints are distinguished from proceedings not yet published.

| Closest work | Established contribution | Scope of this study |
|---|---|---|
| TESSERACT (2019) | Temporal and distribution constraints in malware evaluation | Same-anchor APT-flow training-pool contrast |
| Bilot et al. (2025); Guerra et al. (2026) | Critical provenance/ APT benchmarking and practical controls | Flow-stage observations with explicit source support |
| Uddin et al. (2025) | Attack-type errors versus attacks called normal | Measured metric/warning tradeoffs under evidence changes |
| TAN-IDS (2026) | Flow-based cross-domain evaluation; binary scope | Stage-conditioned warning outcomes and temporal controls |
| Othman et al. (2026) | DAPT stage timing and residual-time survival analysis | Necessary support for a different, all-class classifier split |

# 3. Research Design and Data

## 3.1 Measurement design and analysis chronology

The study combines completed controlled experiments with a retrospective analysis of their saved predictions and a separate benchmark-qualification study. These components answer different questions and have different evidentiary status.

The history-selection, evidence-acquisition, and temporal experiments each froze protocol and executable source before their fitting runs. The source corpus and portions of the broader task had already been examined in project development. The first warning-loss observation was added after inspecting an acquisition seed; it remains exploratory. The new paired reanalysis freezes its computation before execution, but neither that freeze nor its intervals convert an observed pattern into a prospectively confirmed hypothesis.

The D1 extension separately registers future comparisons and source eligibility requirements. Qualification and support checks completed before any new model fits. Those checks are reported as results. No model comparison is reported for a source that failed its applicable requirements.

**Table 1. Components of the evidence and their roles.**

| Component | Completed scope | Role in this paper |
|---|---|---|
| History selection | 39 fits; 7 arms; 5 conditions; 3 seeds | Context tradeoffs and simple controls |
| Evidence acquisition | 84 fits; 3 budgets; 3 conditions; 3 seeds | Paired stage/warning outcomes |
| Temporal comparison | 18 fits; 2 feature views; 3 split arms; 3 seeds | Fixed-anchor protocol sensitivity |
| Paired reanalysis | 36 comparisons; no new fits | Retrospective, capture-conditional uncertainty |
| Benchmark qualification | 4 requested sources; no new fits | Native support, timing and dependencies |
| Policy-transfer supplement | 2 fits; T1105 recognition | Separate task; not stage replication |

The directional expectations were that later-period training may increase reported performance, that context or evidence selection may change stage and warning outcomes differently, and that some releases may not support an all-stage temporal comparison. Results in either direction are informative. No 90% recall requirement or minimum favorable effect determines whether an observed finding is retained.

## 3.2 UNRAVELED artifact and target semantics

The immutable prepared artifact contains 382,229 flow rows from eleven complete IT-sensor captures. Its source is the author UNRAVELED repository, and its SHA-256 is recorded in every input manifest. Preparation validates the intact numeric prefix and right-anchored annotations in CSV records with malformed descriptive fields. The prepared artifact handles exact observable-event duplicates upstream and excludes literal host identities, absolute timestamps, source identifiers, and labels from classifier features.

Targets are benign, other attack stage, lateral movement, and data exfiltration, using the established project grouping of author annotations. This four-class grouping is not represented as the native taxonomy of every other benchmark. In the inspected sensor, the movement annotations describe Remote System Discovery on one host pair. Correct classification therefore means recognition of that author label, not independent verification of successful access to another host. Exfiltration labels likewise do not independently establish that a stolen file reached an adversary.

Captures 0-4 form the fitting period, capture 5 is reserved for calibration, and captures 6-10 form later evaluation. The later population contains 208,094 rows: 192,193 benign, 12,424 other attack stage, 35 movement, and 3,442 exfiltration. Current features summarize completed flows. Historical features describe earlier completed traffic over five- and thirty-minute windows without using earlier stage labels. Coarse host roles derive from the released topology.

The decision time is after the current flow's required statistics are available. Historical events must finish before the current flow starts. This is a completed-flow classification study; elapsed time to first warning or forecasting before exfiltration onset was not measured.

## 3.3 Fixed anchor and support

The temporal experiment selects the first ceiling-half of each class within each later capture, ordered by observable-event hash. This common anchor contains 104,051 rows: 96,098 benign, 6,213 other stage, 18 movement, and 1,722 exfiltration. Both training arms and all three fitting seeds predict the same anchor.

Both eligible training pools exclude any row whose current-feature fingerprint appears in the anchor. After this purge, the earlier pool has 93,470 rows and the mixed pool 149,536. Matched fitting counts are 20,000 benign, 5,000 other-stage, 20 movement, and 1,740 exfiltration. Exact-feature purging removes one identifiable overlap channel; it does not make adjacent events independent or eliminate every source of dataset-specific dependence.

## 3.4 Requested extension artifacts

The qualification study inventories the actual local bytes, native target fields, timestamps, source identities, duplicates, and known dataset dependencies. It distinguishes a source file from an independent execution and a generated timestamp from an observed event clock. Source releases are assessed for the specific proposed temporal comparison, not declared globally usable or unusable.

The closed-set temporal design requires at least two earlier fitting rows and one later evaluation row for every native class. Two is the declared minimum support rule for this audit, not a claim of adequate statistical power or a universal classifier requirement. Rare-stage counts, real source groups, and uncertainty are reported separately. A source failing the rule is not repaired by deleting a stage or training on its future labels.

# 4. Methods

## 4.1 Training-composition contrast

The temporal experiment uses fixed LightGBM models with 200 estimators, 15 leaves, learning rate 0.05, minimum child samples 10, L2 regularization 1, and two CPU threads. Fitting seeds are 20260923, 20260924, and 20260925. Each seed evaluates current features and current-plus-history features.

The past-only arm samples from the earlier pool. The time-mixed arm may additionally sample non-anchor later observations. Sampling is by fixed seeded hashes without replacement, with identical class counts across arms. Calibration records do not enter either pool. All earlier training flows finish before later evaluation begins.

The mixed arm deliberately has access to data unavailable to a model trained earlier. For contextual features, some later training histories can also include earlier anchor-flow observations. The treatment is therefore a change in training composition and temporal access, including those dependencies. It is not a pure causal estimate of access to future labels.

A conventional stratified random-row comparison is retained as a secondary result. It changes the test population and permits some shared current-feature fingerprints across its boundary. Its difference from the chronological arm is reported separately, rather than being called the isolated temporal effect.

## 4.2 Historical-evidence and acquisition interventions

The history-selection experiment compares current-flow-plus-role evidence with context-assisted evidence, equal probability fusion, maximum-confidence selection, ordinary learned selection, stage-weighted selection, and context-dropout training. Four forward folds generate held-out expert predictions for selector fitting. The stage-weighted selector estimates the additional classification error associated with choosing history, using weight four for movement and exfiltration and one for the other true classes.

Five fixed evaluation conditions preserve the true labels: clean history, half missing, all missing, a five-minute-old snapshot, and wrong-host history. The last is a deliberate linkage corruption, not a measured incident. Availability and relative evidence age are observable selector inputs; the true stage is not an inference input. The class weights are illustrative priorities, not a literature-derived loss ratio.

The acquisition experiment has two optional evidence groups: roles and history. Four fixed LightGBM classifiers cover current evidence and each optional subset. Forward-held-out transition targets train greedy acquisition policies that estimate either stage-weighted error reduction or entropy reduction. Unacquired evidence values are unavailable to the policy.

Costs are one unit for roles and two for history; budgets are one, two, and three. Nominal delays are 0.25 and 0.75 with a decision deadline of one simulated time unit. Failed or late requests still consume budget. Conditions are clean delivery, delayed/unavailable evidence, and wrong-host history. Shared row-specific schedules permit paired policy comparisons. A policy ends with the classifier for the last successfully delivered subset. No unresolved case receives an automatic correct label.

These conditions probe behavior under explicit assumptions. They do not measure live collection prices, real sensor outage rates, or deployment latency. The system does not reproduce complete published acquisition architectures; those approaches establish context for the problem rather than reproduced baselines.

## 4.3 Paired warning, stage, and workload metrics

Let C(s,j) count records with true class s and predicted class j, let b denote benign, and let N(s) be the number of true-s records. For an attack stage s:

- Exact-stage recall = C(s,s) / N(s).
- Warning recall = 1 - C(s,b) / N(s).
- Missed-warning rate = C(s,b) / N(s).
- Wrong-stage warning rate = warning recall minus exact-stage recall.

The three destinations - correct stage, another attack stage, and benign - partition each true attack stage. Warning recall is ordinary binary attack recall conditioned on the true stage. The warning is a non-benign model label, not evidence that a production alert was displayed, triaged, or prevented harm.

The study also reports precision, per-class F1, unweighted macro-F1, benign false-alert counts and rates, and full confusion matrices. Available probability metrics remain in original experiment tables. ROC-AUC and average precision do not replace operating-point counts or establish a latency result.

A descriptive sign reversal occurs when a specified comparison increases macro-F1 and decreases a stage's warning recall on the same rows. Candidate-minus-baseline signs use a numerical tolerance of 1e-12 to suppress floating-point artifacts. This tolerance is not a practical-significance threshold. Every declared stage and condition is retained, including zero changes and opposite directions.

Compact reanalysis tables scale differences by 100. For recall this gives percentage points; for F1, one displayed score point means 0.01 on the original zero-to-one scale. Absolute F1 tables retain the zero-to-one scale.

## 4.4 Retrospective paired reanalysis and uncertainty

The reanalysis compares error-focused versus entropy acquisition at every registered condition and budget, and evaluates three temporal contrasts: mixed versus past-only current features, mixed versus past-only historical features, and past-only history versus past-only current features. No model is refitted or threshold tuned. Ordered row identities, truth labels, source groups, and native class meanings must match before a contrast is computed.

One shared bootstrap plan per evaluation population samples its five source captures with replacement 2,000 times, using seed 20260923. All fitting seeds and contrasts on that population reuse the same group multiplicities. Confusion counts repeat with each selected capture; equivalent whole-row replication is tested independently. The statistic remains event-weighted within a replicate, rather than becoming an unweighted average of capture scores.

Intervals are 95% percentile intervals for paired differences. If a resample contains no examples of a target stage, its recall difference is undefined; those draws are counted and excluded from that interval. Fixed-schema macro-F1 is undefined if a true class is absent from a resample. This convention is specific to the new reanalysis and does not overwrite the original temporal bootstrap convention. Every interval discloses its number of valid draws.

With five captures from one campaign, these are conditional, descriptive intervals. Captures are fragments of a shared attack workflow, not independent campaigns. Three fitting seeds quantify algorithmic variation on those same events; they do not triple the sample of attacks. No family-wide significance claim follows from selecting a favorable interval among stages, conditions, or seeds.

## 4.5 Necessary chronological-support test

For each native class, the start-only diagnostic identifies its second-earliest and latest recorded starts. A cutoff c with training starts strictly before c and evaluation starts at or after c can have two earlier and one later records of every class only if:

`max(second-earliest start across classes) < c <= min(latest start across classes)`

An empty interval rules out every single cutoff under that rule. It is stronger than finding one unsuccessful train/test percentage. A nonempty interval establishes necessary start-time count support only; flow completion, history availability, duplicate purging, and source-clock qualification impose additional constraints. Tied timestamps stay tied. No rows or native classes are discarded and no clock is repaired.

The support algorithm was committed before execution on the source CSVs. Its tests include tied event sequences, infeasible intervals, insufficient classes, and a counterexample distinguishing start-only from completion-time support. A separate implementation sweeps actual timestamp blocks and counts records on each side, independently checking the interval and class totals without importing the original bound function.

## 4.6 Reproducibility and compute

The three main experiments contain 141 model fits: 39 history-selection fits, 84 acquisition fits, and 18 temporal fits. A separate two-fit policy-transfer study brings the broader project batch to 143; it is supplementary and is not counted as another movement/exfiltration experiment. Main model fitting used local CPU. Earlier cloud data-acquisition work is documented separately and did not produce an additional qualifying APT-stage replication.

This completion adds reanalysis, source checks, and document assembly, not new model fits. Frozen source commits, input hashes, private row-level predictions, public aggregates, and independent audit receipts are preserved. The evidence index provides commands and access limits. The D1 $5 future-compute ceiling is a limit, not money spent or evidence of a cloud experiment.

# 5. Results

## 5.1 Fixed-anchor temporal sensitivity

**Table 2. Temporal experiment.** Values are means of three fits. Primary past/mixed rows share the 104,051-row anchor with 96,098 benign rows; random-row evaluations contain 210,226 rows with 191,515 benign rows. Benign alert rates accompany counts because these denominators differ. Movement denotes the author label described in Section 3.

| Features / fit | Macro-F1 | Movement recall | Movement F1 | Exfil. F1 | Benign alerts (rate) |
|---|---|---|---|---|---|
| Current / Past | 0.7365 | 25.93% | 0.2091 | 0.7565 | 24.0 (0.025%) |
| Current / Mixed | 0.7997 | 61.11% | 0.2582 | 0.9523 | 88.7 (0.092%) |
| Current / Random | 0.8093 | 57.84% | 0.3116 | 0.9404 | 84.0 (0.044%) |
| Current + history / Past | 0.7582 | 29.63% | 0.2836 | 0.7671 | 14.3 (0.015%) |
| Current + history / Mixed | 0.7964 | 57.41% | 0.2798 | 0.9092 | 47.7 (0.050%) |
| Current + history / Random | 0.8507 | 64.71% | 0.4336 | 0.9753 | 49.3 (0.026%) |

With current features, time-mixed fitting increases macro-F1 by 0.0632 and exact movement-label recall by 35.19 percentage points. Adding history yields a mixed-minus-past macro-F1 increase of 0.0383. These effects arise while the classifier family, anchor rows, and class fitting counts are held fixed. They establish sensitivity to the declared training-pool change on these observations.

The higher scores also accompany more benign false alerts: the current-feature mean count increases from 24.0 to 88.7. A model ranking based on F1 alone would conceal this workload change. The conventional random-row score is retained but is not used to estimate the controlled temporal effect.

The complete retrospective reanalysis gives positive current-feature macro-F1 differences in all three seeds, with each descriptive capture interval above zero. For current-plus-history, all point differences are positive, but the final seed interval spans zero. The intervals vary widely because the resampling units are only five capture fragments from the same campaign; they do not establish a population-wide inflation factor.

| Features | Fitting seed | Δ macro-F1 (x100) | 95% F1 interval (x100) | Δ exfil warning (pp) |
| --- | --- | --- | --- | --- |
| Current | 20260923 | 7.52 | [1.96, 26.31] | 32.11 |
| Current + history | 20260923 | 3.32 | [1.20, 17.24] | 12.66 |
| Current | 20260924 | 6.99 | [1.65, 24.36] | 32.00 |
| Current + history | 20260924 | 2.97 | [0.62, 15.49] | 9.29 |
| Current | 20260925 | 4.46 | [0.12, 20.62] | 31.94 |
| Current + history | 20260925 | 5.18 | [-0.75, 25.69] | 31.59 |

For every comparison, 1,981 of 2,000 draws support fixed-four-class macro-F1 and movement recall; 19 draws omit the true movement class and are excluded from those intervals. All 2,000 draws support exfiltration warning recall and benign false-alert rate. The same capture multiplicities are reused across all seeds and contrasts. These new support-conditional intervals are distinct from the original temporal experiment’s 1,000-draw bootstrap. Every stage, count and paired interval is retained in [the complete reanalysis](evidence/paired_reanalysis/REPORT.md).

![Figure 1. Fixed-anchor training-composition differences. Bars show means of three fits on the same events. The adjacent table reports per-seed conditional capture-bootstrap intervals.](figures/temporal_effects.png)

## 5.2 Aggregate improvement and lost exfiltration warnings

**Table 3. Acquisition comparisons at the largest registered budget.** The policies share the same rows and available budget. A warning is any non-benign predicted label. False alerts use the same 192,193 benign evaluation rows; warning and exact exfiltration recall use the same 3,442 exfiltration rows. Means are across three fits.

| Condition / policy | Macro-F1 | Exact exfil. recall | Exfil. warning recall | Benign alerts |
|---|---|---|---|---|
| Clean / Entropy | 0.7148 | 67.29% | 85.18% | 111.3 |
| Clean / Error focused | 0.7379 | 67.18% | 76.25% | 122.3 |
| Delayed / Entropy | 0.7180 | 67.43% | 81.00% | 144.0 |
| Delayed / Error focused | 0.7427 | 67.43% | 69.20% | 146.3 |
| Wrong host / Entropy | 0.6873 | 67.22% | 77.52% | 73.0 |
| Wrong host / Error focused | 0.6763 | 67.01% | 77.37% | 87.0 |

In clean replay, error-focused acquisition improves macro-F1 by 0.0231 over entropy acquisition, but warning recall for exfiltration falls by 8.93 percentage points. The number of such records dismissed as benign consequently increases. Under delayed or unavailable evidence, macro-F1 also rises while warning recall falls. The wrong-host condition and lower budgets are included in the full analysis rather than omitted when their directions differ.

This result concerns destinations of classification errors. Some entropy-policy mistakes assign exfiltration to another attack stage, preserving an attack label. Other decisions from the error-focused policy assign benign. The true-class weighted objective charges both mistakes the same weight. The observed pattern is therefore consistent with an objective that fails to distinguish those destinations, although it does not establish that changing the loss alone would fix the behavior.

Across all registered conditions and budgets, 19 of 27 paired seed comparisons raise macro-F1 while reducing exfiltration warning recall. In 17 of 27, the descriptive macro-F1 interval lies above zero and the warning-recall interval below zero. These comparisons share data and fitted components; budget-one clean and wrong-history outcomes are identical because that budget cannot acquire history. They are correlated repetitions of specified comparisons, not 27 independent tests or campaigns.

| Condition | Budget | Mean Δ F1 (x100) | Mean Δ exfil warning (pp) | Mean extra lost warnings | F1 up / warning down seeds |
| --- | --- | --- | --- | --- | --- |
| clean | 1 | 3.61 | -20.12 | 692.67 | 2 |
| clean | 2 | 3.70 | -20.26 | 697.33 | 2 |
| clean | 3 | 2.31 | -8.93 | 307.33 | 2 |
| delayed unavailable | 1 | 3.42 | -13.81 | 475.33 | 2 |
| delayed unavailable | 2 | 3.57 | -13.95 | 480.00 | 2 |
| delayed unavailable | 3 | 2.47 | -11.80 | 406.00 | 3 |
| wrong host history | 1 | 3.61 | -20.12 | 692.67 | 2 |
| wrong host history | 2 | 12.34 | -20.33 | 699.67 | 3 |
| wrong host history | 3 | -1.10 | -0.15 | 5.33 | 1 |

Clean budget-three means conceal marked fitting-seed variation. Exfiltration-to-benign counts range from 203 to 1,105 for entropy and 206 to 1,127 for harm. The paired increases are 897, 3 and 22 lost warnings, respectively (mean 307.33). Macro-F1 improves in two seeds and declines slightly in one. For seed 8101, exact exfiltration errors change only from 1,122 to 1,130, while wrong-attack-stage predictions fall from 900 to 11 and benign predictions rise from 222 to 1,119. This concrete error-destination shift explains why nearly unchanged exact exfiltration recall can coexist with a large loss of warnings. It does not identify a generally effective policy.

| Seed | Δ F1 (x100) | Exfil → benign | All exact exfil errors | Δ warning pp [95% paired interval] |
| --- | --- | --- | --- | --- |
| 8101 | 5.65 | 222 → 1119 | 1122 → 1130 | -26.06 [-92.42, -0.88] |
| 8102 | -0.08 | 203 → 206 | 1128 → 1129 | -0.09 [-0.52, 0.00] |
| 8103 | 1.38 | 1105 → 1127 | 1128 → 1130 | -0.64 [-3.06, -0.15] |

All three attack stages, including zero changes and reverse directions, are included in [the complete paired table](evidence/paired_reanalysis/PAIRED_METRICS.csv). The full set was specified before this reanalysis, after selected warning-loss observations had already been inspected; it remains retrospective.

![Figure 2. Exfiltration error destinations in clean replay at budget three. Exact-stage predictions and wrong-stage attack predictions both retain a warning; benign predictions do not. These are model-label outcomes on the same author-labeled records.](figures/warning_destinations.png)

## 5.3 Chronological history gains and their tradeoff

Under past-only fitting, adding history improves macro-F1 from 0.7365 to 0.7582, movement F1 from 0.2091 to 0.2836, and exfiltration F1 from 0.7565 to 0.7671. Mean benign false alerts decrease from 24.0 to 14.3. These are positive changes under the stricter training protocol.

The exfiltration warning outcome moves differently: exfiltration-to-benign mistakes increase in each fitting seed. Thus, even a comparison with both better F1 and fewer benign alerts can lose some warnings for a specific attack stage. The size and uncertainty of that loss belong beside the favorable metrics, rather than being removed from a positive account.

On the same 1,722 exfiltration-labeled anchor rows, adding history increases benign predictions by 7, 6 and 8 across the three fitting seeds. Mean warning recall decreases by 0.41 percentage points, while macro-F1 rises by 2.17 points. This is a much smaller warning loss than the acquisition contrast. Only the final seed’s warning-difference interval excludes zero; the other two include zero. Both favorable and unfavorable outcomes should be read at that scale.

| Fitting seed | Δ macro-F1 x100 [95% interval] | Exfil → benign, current → history | Δ exfil warning pp [95% interval] |
| --- | --- | --- | --- |
| 20260923 | 2.98 [0.42, 6.41] | 565 → 572 | -0.41 [-2.62, 0.00] |
| 20260924 | 1.08 [-2.11, 4.20] | 563 → 569 | -0.35 [-2.09, 0.00] |
| 20260925 | 2.45 [0.43, 3.07] | 563 → 571 | -0.46 [-2.88, -0.09] |

Intervals for the added missed-warning counts are [0, 17], [0, 14] and [1, 17], respectively. They reuse the same capture draws as the temporal contrasts. These are descriptive fragment-resampling intervals, not independent-campaign or prospective validation. The [reanalysis audit](evidence/paired_reanalysis/AUDIT.json) verifies unchanged input hashes, paired identities and independently recomputed arithmetic.

## 5.4 Learned selection and simple controls

The stage-weighted history selector improves movement-label recall over ordinary selection in all five conditions, by 4.76 to 14.29 percentage points. It also increases benign false alerts and weighted classification error in every condition. The current-plus-roles classifier retains higher movement recall than the weighted selector throughout. It is a learned LightGBM baseline, not a deterministic rule.

**Table 4. History-selection tradeoffs.** Recall and false alerts are three-fit means. The same 35 movement rows and 192,193 benign rows recur across conditions.

| Condition | Ordinary recall | Weighted recall | Dropout recall | Alerts: ordinary / weighted |
|---|---|---|---|---|
| Clean | 64.76% | 69.52% | 51.43% | 85.7 / 109.0 |
| Half missing | 52.38% | 60.95% | 62.86% | 74.3 / 93.7 |
| All missing | 36.19% | 42.86% | 68.57% | 62.3 / 77.0 |
| Stale | 49.52% | 63.81% | 48.57% | 85.0 / 113.3 |
| Wrong host | 35.24% | 44.76% | 68.57% | 61.7 / 81.3 |

With all history missing, the dropout-trained comparator reaches 68.57% movement recall versus 42.86% for weighted selection. The acquisition policy lowers simulated spending by 32.24% relative to entropy acquisition in clean, largest-budget replay, but does not consistently reduce the weighted error outcome. These results show why a measurement praxis should retain simple controls and multiple outcomes. They do not require a claim that complex detectors generally fail.

The [supplementary policy-transfer study](../px083_policy_transfer/README.md) transfers a selector between native experts on CasinoLimit and CAM-LDS for T1105 recognition. At its fixed threshold the cost-sensitive policy reproduces the context expert's hard decisions in all 42 views. Because the target and negative-label meaning differ from benign-versus-attack stage detection, it is not pooled into the main warning analysis. Dataset source citations and publication records are retained in the [supplement's reference audit](../paper/REFERENCES.md), and its source and result receipts remain in the evidence package.

## 5.5 Qualification of the four proposed extension datasets

**Table 5. Results of source qualification.** These counts describe the inspected files; eligibility refers to the unchanged all-native-class temporal comparison.

| Source | Inspected rows | Native classes | Completed finding |
|---|---|---|---|
| SCVIC-APT-2021 | 259,120 | 6 | Possible recorded-start support; clocks and execution mapping unqualified |
| DAPT2020 | 86,691 | 5 | No all-class single cutoff; 15 exfiltration rows |
| DSRL-APT-2023 | 65,000 | 5 | DAPT-derived synthetic source; no natural event chronology |
| S-DAPT-2026 | None acquired | Not verified | No qualified acquired release |

For DAPT2020, the cutoff would need to be later than July 19, 2019, 16:38:37 to include two earlier exfiltration examples, yet no later than July 17, 2019, 19:24:55 to retain a reconnaissance example in evaluation. The conditions contradict each other. The diagnosis uses all 86,691 rows and the five native classes; it is not caused by choosing an inconvenient 60/15/10/15 split. The release can support other questions, including a separately designed unknown-stage evaluation, but the unchanged closed-set temporal comparison cannot be run honestly on those bytes.

SCVIC's recorded-start necessary interval is nonempty: after October 21, 2015, 10:21:12 through 22:56:16. The support test therefore does not reject every possible SCVIC cutoff. However, 220 benign rows have 1970 dates, remaining rows have 2015 dates, time resolution is mixed, and a source-supported row-to-execution map and physical-clock interpretation were not obtained. The author-listed test file is absent from the inspected local sources. The completed analysis is a recorded-time support diagnostic, not a certified temporal model evaluation.

DSRL's 65,000-row artifact combines synthetic attacks derived from DAPT with 10,000 benign rows sampled from DAPT. Its generated timestamps do not demonstrate real event order, and its shared source prevents treating it as independent real-campaign confirmation. S-DAPT contributes an availability result: the inspected arXiv record remains withdrawn and no verified corrected, accessible data artifact was acquired. A separate inaccessible listing does not resolve that status.

A separate CSV-parser implementation enumerated all tied-time membership states: 0 of 28,941 DAPT states met the all-native-class two-earlier/one-later rule, whereas 9,475 of 11,693 SCVIC states met recorded-start support. The latter did not resolve its clock or execution-identity limitations. Native-class totals and input hashes matched before and after the separate reads. The verifier did not import the original bound function. Its [verification receipt](evidence/qualification_audit/VERIFICATION.json) records all 16 checks and source identities.

![Figure 3. Why DAPT cannot support the unchanged all-stage cutoff. Ranges run from each native class's second-earliest to latest recorded start. A cut that trains on exfiltration cannot retain later reconnaissance in this release.](figures/dapt_stage_support.png)

## 5.6 Summary of answers

RQ1 is answered by a substantial same-anchor training-composition effect in the observed campaign. RQ2 is answered by measured tradeoffs: historical evidence produces some chronological gains, and aggregate score improvement can coexist with fewer stage-specific attack warnings. RQ3 is answered for the inspected artifacts: none currently qualifies for the unchanged new temporal model comparison, for different, documented reasons. This is a qualification result rather than four failed detector experiments.

# 6. Discussion and Applied Praxis

## 6.1 What the measurements change for model evaluation

A score is conditional on the records, target meanings, training composition, and decision rule used to calculate it. The controlled temporal experiment shows how large that dependence can be without changing the classifier family. The warning analysis shows that the aggregate score can move in a favorable direction while a consequential subset receives fewer attack labels. Together, the findings justify making those dependencies visible during model selection.

The practical contribution is a reporting and verification procedure. It can be used to review an internal model update, compare historical evidence features, or determine whether a proposed benchmark actually tests the intended deployment question. A research team gains an auditable reason to accept a limited claim, revise a protocol, or decline an unsupported comparison before purchasing more compute.

## 6.2 A concrete reporting requirement

For every consequential stage, a model evaluation should report exact-stage recall, warning recall, and their underlying counts on the same rows. It should include benign false alerts and the evaluated population size. The report should identify the decision time, feature availability, class support in each split, source groups, and whether the evaluated source has already informed development.

This is a proposed applied reporting requirement, not a new industry standard or a mathematically new metric. The present evidence shows why the pair is useful in this setting. It does not prove that every omitted pair hides a loss or that every warning is actionable.

**Table 6. Minimum audit record for a stage-classifier comparison.**

| Audit item | Required record | Decision it supports |
|---|---|---|
| Source and targets | Release hash, native labels, benign definition, label semantics | Whether the claim matches what was annotated |
| Timing | Training/evaluation boundaries, event completion, history availability | Whether the intended earlier-to-later comparison is possible |
| Dependence | Capture/run/campaign definitions, duplicate overlap, derivative sources | What constitutes independent evidence |
| Paired outcomes | Exact-stage and warning recall, wrong-stage and benign destinations | Whether stage improvement retains warnings |
| Workload | Benign false-alert count/rate, population, operating rule | Whether warning retention adds investigation burden |
| Uncertainty | Per-seed values, actual resampling units, unsupported draws | How much variation the available evidence describes |
| Reproducibility | Protocol/source commits, input/output hashes, all declared results | Whether another analyst can trace and recompute the claim |

## 6.3 An implementable evaluation workflow

1. Define the operational decision and when its features become available. A full-flow detector should be evaluated as a completed-flow decision.
2. Inventory the actual release, target semantics, timestamps, and source relationships. Preserve uncertain fields explicitly.
3. Test native-class support and chronology before fitting. If the intended split is impossible, record that finding and register a different question separately.
4. Freeze the compared models, feature sets, operating rules, populations, and resource limits. Include simple controls.
5. Preserve row-linked predictions privately and calculate paired metrics from those same rows. Report all declared conditions.
6. Interpret stage accuracy, warning loss, and benign workload jointly. Use independent executions for a generalization claim and an appropriate calibration design for matched-workload claims.

The delivered planner, metric library, support diagnostic, and evidence receipts implement the corresponding parts of this workflow. They are a portable audit core, not a completed four-source fitting executor. New fitting adapters await qualified source contracts. A generic tool cannot infer the meaning of a timestamp or turn a dataset name into an independent campaign.

## 6.4 Possible technical extensions

A future detector experiment could assign different losses to a missed attack and a wrong attack stage, or add a validation step before new evidence changes an existing attack decision to benign. Such a rule must be evaluated against hierarchy-aware and cost-sensitive baselines at measured benign workload. Simply preserving every initial attack decision would raise warning recall mechanically and could preserve false alarms as well.

An independent, repeated-execution dataset is the highest-value extension of the present empirical claims. Within the requested list, source-supported SCVIC clock interpretation and row-to-run identities would be useful. DAPT requires additional executions or a separately framed unknown-stage question; DSRL can support an explicitly synthetic study. These extensions are delineated in D1 but are not included among the completed model results.

# 7. Validity, Limitations, and Research Integrity

## 7.1 Construct validity

Author-stage labels are the targets. They are not independent attestations of successful host compromise, attacker intent, or stolen-file receipt. The movement target in the inspected UNRAVELED sensor concerns discovery. A non-benign prediction is called a warning for clarity, but no analyst workflow or downstream response was measured. The paper consistently separates these measured proxies from stronger operational outcomes.

## 7.2 Internal validity

The temporal contrast fixes architecture, anchor, and class budgets but changes training composition and access to later observations. It does not isolate every distributional or dependence mechanism. Removing identical current-feature fingerprints addresses a specific overlap channel and leaves possible near-duplicate and workflow effects. The four-class source grouping and prior artifact preparation are part of the design.

History and acquisition interventions preserve targets, but wrong-host and missing-evidence conditions are synthetic perturbations. Their severity and frequency do not estimate real sensor failures. Prior acquisition costs, stage weights, and deadlines are illustrative choices. The reanalysis uses existing predictions and fixed decisions, so it cannot attribute a warning tradeoff to one mechanism by itself.

## 7.3 Statistical and external validity

The main campaign supplies only 35 movement evaluation rows and 18 in the temporal anchor. Five later captures contain correlated events from one workflow. Conditional capture-bootstrap intervals and fitting-seed variation cannot support population claims over organizations or APT campaigns. Missing-stage resamples require support-conditional interpretation, especially when a stage occurs in few captures.

The main data were already exposed during development. The warning-loss analysis was retrospective, and the complete paired reanalysis remains exploratory. Multiple stages and conditions are reported without a selective significance claim. The extension audit does not produce independent replications by counting related or unavailable datasets.

## 7.4 Reproducibility and access limits

Public code, aggregate tables, support bounds, protocols, and hashes allow independent inspection of the analysis. Full recomputation requires the same qualified source artifacts and private row-linked prediction files, whose locations and hashes are recorded without redistributing raw traces. Source access, licensing, and authentication conditions can limit external reproduction. A hash establishes byte identity, not label correctness or authorization to redistribute data.

Independent computational checks establish consistency of specified calculations and source bindings. They are not a substitute for an external ground-truth review. No human annotation audit, deployment evaluation, ethics approval, or committee acceptance is represented as completed when it was not performed. No human subjects were recruited by these computational experiments.

## 7.5 Scope of the finished manuscript

The completed manuscript makes a measurement claim on the available evidence and provides the full supporting artifact record. It does not wait for every desirable future study to report the results already obtained. Additional independent execution evidence would broaden the claim; its absence is a limit on generalization, not a reason to relabel the completed numerical observations as nonexistent or as four model failures.

# 8. Conclusion

The experiments demonstrate that a classifier's reported APT-stage performance depends materially on training composition, and that aggregate score improvement can accompany loss of attack warnings. Time-mixed fitting increases macro-F1 by 0.0632 on a fixed anchor with matched class budgets. In a separate policy comparison, macro-F1 improves while exfiltration warning recall declines by 8.93 percentage points. Historical features also produce useful gains under past-only training, alongside a measurable warning tradeoff.

The benchmark audit adds a distinct practical result: the inspected DAPT release cannot support the unchanged all-native-class chronological split, SCVIC's recorded-time support is insufficient to establish qualified chronology, DSRL is source-dependent synthetic data, and no qualified S-DAPT artifact was acquired. These findings identify what the proposed expansion can and cannot test.

The praxis delivers a reproducible evaluation procedure: qualify the source and timing, compare identical evaluation populations where appropriate, separate wrong-stage predictions from missed warnings, and report benign workload beside both. Its contribution is controlled evidence and usable audit infrastructure. The next empirical boundary is independent-execution replication, clearly separated from the completed study.

# References

Bilot, T., Jiang, B., Li, Z., El Madhoun, N., Al Agha, K., Zouaoui, A., & Pasquier, T. (2025). Sometimes simpler is better: A comprehensive analysis of state-of-the-art provenance-based intrusion detection systems. In 34th USENIX Security Symposium (pp. 7193–7212). USENIX Association. https://www.usenix.org/conference/usenixsecurity25/presentation/bilot

Guerra, L., Chapuis, T., Duc, G., Mozharovskyi, P., & Nguyen, V.-T. (2026). How benchmarks and evaluation protocols shape conclusions in provenance-based intrusion detection (Version 3) [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2608.01454

Ha Thanh, D. (2026). A transfer-aware, deployment-oriented evaluation framework for NetFlow-based intrusion detection systems (TAN-IDS). PLOS One, 21(4), e0346801. https://doi.org/10.1371/journal.pone.0346801

Ibrahim, N., Rajalakshmi, N. R., Sivakumar, V., & Sharmila, L. (2025). An optimized hybrid ensemble machine learning model combining multiple classifiers for detecting advanced persistent threats in networks. Journal of Big Data, 12, Article 212. https://doi.org/10.1186/s40537-025-01272-w

Iturbe, E., Dalamagkas, C., Radoglou-Grammatikis, P., Rios, E., & Toledo, N. (2026). A pattern-aware LSTM-based approach for APT detection leveraging a realistic dataset for critical infrastructure security. Future Generation Computer Systems, 178, Article 108308. https://doi.org/10.1016/j.future.2025.108308

Liu, J., Shen, Y., Simsek, M., Kantarci, B., Mouftah, H. T., Bagheri, M., & Djukic, P. (2022a). A new realistic benchmark for advanced persistent threats in network traffic. IEEE Networking Letters, 4(3), 162–166. https://doi.org/10.1109/LNET.2022.3185553

Liu, J., Shen, Y., Simsek, M., Kantarci, B., Mouftah, H. T., Bagheri, M., & Djukic, P. (2022b). SCVIC-APT-2021 [Dataset]. IEEE DataPort. https://doi.org/10.21227/g2z5-ep97

Luengo Viñuela, M., Román-Gallego, J.-Á., Pérez-Delgado, M.-L., Conde, M. A., Vega-Hernández, M.-C., & Silva Varela, H. (2026). Detection of APTs by machine learning: A performance comparison. Expert Systems, 43(1), e70181. https://doi.org/10.1111/exsy.70181

M K, V. P., S, S., H, A. G., Aggarwal, M., & V S, S. S. (2026). Advanced persistent threat detection through sequential analysis of network patterns with graph based learning approach. Scientific Reports, 16, Article 19998. https://doi.org/10.1038/s41598-026-42756-w

Myneni, S., Chowdhary, A., Sabur, A., Sengupta, S., Agrawal, G., Huang, D., & Kang, M. (2020). DAPT 2020 - Constructing a benchmark dataset for advanced persistent threats. In G. Wang, A. Ciptadi, & A. Ahmadzadeh (Eds.), Deployable machine learning for security defense (Communications in Computer and Information Science, Vol. 1271, pp. 138–163). Springer. https://doi.org/10.1007/978-3-030-59621-7_8

Myneni, S., Jha, K., Sabur, A., Agrawal, G., Deng, Y., Chowdhary, A., & Huang, D. (2023). Unraveled—A semi-synthetic dataset for advanced persistent threats. Computer Networks, 227, Article 109688. https://doi.org/10.1016/j.comnet.2023.109688

Othman, F. M., Mejri, M., & Alabdulatif, A. (2026). Temporal MITRE ATT&CK modelling for residual time-to-compromise estimation in multi-stage attacks. Symmetry, 18(9), Article 1439. https://doi.org/10.3390/sym18091439

Pendlebury, F., Pierazzi, F., Jordaney, R., Kinder, J., & Cavallaro, L. (2019). TESSERACT: Eliminating experimental bias in malware classification across space and time. In 28th USENIX Security Symposium (pp. 729–746). USENIX Association. https://www.usenix.org/conference/usenixsecurity19/presentation/pendlebury

Phan, T. V., & Bauschert, T. (2026). Learning the APT kill chain: Temporal reasoning over provenance data for attack stage estimation (Version 2) [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2603.07560

Shadabfar, H., Dehghan, M., & Sadeghian, B. (2025). DSRL-APT-2023: A new synthetic dataset for advanced persistent threats. ISeCure, 17(2), 107–116. https://doi.org/10.22042/isecure.2025.214212

Tijjani, S. I., Ghita, B., Clarke, N., & Craven, M. (2026). S-DAPT-2026: A stage-aware synthetic dataset for advanced persistent threat detection (Version 2) [Withdrawn preprint]. arXiv. https://doi.org/10.48550/arXiv.2601.06690

Uddin, M. A., Aryal, S., Bouadjenek, M. R., Al-Hawawreh, M., & Talukder, M. A. (2024). Hierarchical classification for intrusion detection system: Effective design and empirical analysis [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2403.13013

Uddin, M. A., Aryal, S., Bouadjenek, M. R., Al-Hawawreh, M., & Talukder, M. A. (2025). Hierarchical classification for intrusion detection system: Effective design and empirical analysis. Ad Hoc Networks, 178, Article 103982. https://doi.org/10.1016/j.adhoc.2025.103982

# Appendix A. Experimental Parameters and Provenance

| Study | Classifier trees / leaves | Fitting seeds | Key fixed choices |
|---|---|---|---|
| History selection | 180 / 15 | 20260924-20260926 | 4 forward folds; class weights 1/1/4/4 for weighted selector |
| Evidence acquisition | 150 / 15 | 8101-8103 | 2 optional groups; costs 1/2; budgets 1/2/3; deadline 1 |
| Temporal comparison | 200 / 15 | 20260923-20260925 | Same anchor and class budgets; earlier/mixed/random arms |
| Paired reanalysis | No fits | Bootstrap 20260923 | 2,000 whole-capture draws shared across fitting seeds |

All main fitted models use LightGBM with fixed settings; no model family is selected after seeing the evaluation scores. The reanalysis fits zero models. D1's prospective Random Forest control belongs to unexecuted qualified-source comparisons and is not listed as an observed result.

| Artifact | Before-execution commit | Evidence |
|---|---|---|
| History-selection protocol/source | 06c5037 | Original model audit |
| Acquisition and temporal protocol/source | 2da1a1c | Original model audits |
| D1 support diagnostic | ea9956c | Native-class necessary interval |
| Independent source-count verifier | e6b5799 | Direct timestamp-block sweep |
| Retrospective paired reanalysis | c0d884e | Saved-prediction comparison; exploratory |

The prepared UNRAVELED SHA-256 is `b2a491474e722f4dabcd4c419c83a4a6b49f08dfc3bc059aa42ef2aaa4c3de14`. Exact prediction hashes, source versions, and code bindings are in the linked receipts. The main recorded numerical environment is NumPy 2.2.6, LightGBM 4.6.0, and scikit-learn 1.7.2; current reanalysis and document build versions are recorded separately.

# Appendix B. Complete Results and Claim Traceability

| Claim | Measured support | Evidence location |
|---|---|---|
| Temporal score sensitivity | +0.0632 macro-F1; +35.19 pp movement recall | [Temporal report](../px082_temporal_audit/REPORT.md) |
| Metric/warning tradeoff | Clean budget 3: +0.0231 macro-F1; -8.93 pp warning recall | [Paired report](evidence/paired_reanalysis/REPORT.md) |
| Chronological history gains | Macro-F1 .7365 to .7582; alerts 24.0 to 14.3 | [Original means](../px082_temporal_audit/SUMMARY.json) |
| Native-class cutoff limitation | DAPT lower bound exceeds upper bound | [Independent verification](evidence/qualification_audit/VERIFICATION.json) |
| Source qualification | SCVIC uncertainty; DSRL dependency; S-DAPT unavailable | [Qualification report](../d1_benchmark_audit/DATASET_QUALIFICATION.md) |
| Literature differentiation | Existing metrics; controlled measurement contribution | [Literature audit](LITERATURE_AND_CLAIMS.md) |

The machine-readable result tables preserve all reported fitting seeds, budgets, conditions, stages, and bootstrap support counts. The paper's compact tables summarize these records. Zero-change and unfavorable results remain available. The [evidence index](EVIDENCE_INDEX.md) maps each artifact to the calculation it supports and distinguishes public aggregates from private row-level inputs.

# Appendix C. Reproduction and Review

The [reproduction guide](REPRODUCE.md) provides commands for the paired reanalysis, independent qualification check, public arithmetic checks, document build, and test suite. Read the access and source-hash requirements before attempting private-data reproduction. Public verification can check the reported arithmetic and frozen artifact bindings without downloading raw attack traces; it cannot recreate model predictions without the qualified private inputs.

The package includes a committee review checklist with evidence locations and an explicit list of claims outside the study. That checklist is a preparation aid, not a representation that a committee has approved the work. Author attribution, institutional formatting, and venue submission are administrative steps for the researcher; this manuscript does not invent those details.
