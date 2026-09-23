## 1. Introduction

An attack-stage detector must make a useful decision from the evidence available at that moment. Additional context can make an ambiguous connection understandable, but it can also encode a repeated workflow that does not hold in the next incident. Delayed collection creates a further choice: wait for more information, query a different source, or decide from current observations. A higher aggregate classification score alone does not show whether these choices preserve recognition of rare, consequential stages.

Recent provenance research supplies a concrete motivation. Bilot et al. (2025) document practical and evaluation shortcomings in complex provenance-based intrusion detectors and demonstrate competitive simple alternatives. Kimm et al. (2026) examine incomplete and incorrectly connected provenance, providing evidence that collection context itself requires attention. These findings motivate simple controls and explicit evidence-availability tests; they do not establish that the particular selector investigated here is new.

The applied problem is therefore conditional evidence use: can earlier context improve stage recognition without suppressing useful current-event evidence, and can a policy choose additional evidence under limited availability? A companion measurement asks whether the apparent usefulness changes when training is allowed to mix earlier and later observations. The three studies use an already-qualified APT trace and deliberately separate method development from independent confirmation.

## 2. Related work and proposed contribution

Temporal evaluation is established research. Pendlebury et al. (2019) formalize temporal and distribution constraints for malware evaluation. More recently, Guerra et al. (2026) show how APT provenance benchmarks and evaluation protocols shape architectural conclusions. The present audit is a bounded measurement on one author-labeled flow corpus, not the first temporal security evaluation or evidence that all published APT results are inflated.

History fusion and stage reasoning also have precedents. StageFinder (Phan & Bauschert, 2026) combines structural and temporal information for attack-stage estimation. KnowHow (Meng et al., 2026) links threat knowledge with lower-level events and considers attack-step relationships. A third model choosing between two experts is not itself a new algorithm. Our narrower hypothesis is that supervision on the additional stage error introduced by history may lead to different decisions from ordinary confidence or unweighted selection under missing, stale, and incorrectly linked context.

Active feature acquisition supplies the second method family. Guney et al. (2025) learn acquisition decisions from explanatory rankings; Norcliffe et al. (2025) model complementary observations. Learning-To-Measure (Kobayashi et al., 2026) discusses fixed features and uniform costs in its formulation, motivating further work on changing observations and richer cost-sensitive decisions. Security-specific Sim-CTKG already considers resource-constrained logging with latency (Basak & Shin, 2026). The current replay tests a simple stage-error objective against an uncertainty-reduction proxy. It does not reproduce these full systems or establish superiority to them.

The contribution supported by this batch is a reproducible empirical characterization: forward-trained selectors, matched policy inputs and resource limits, explicit context interventions, and a temporal sensitivity audit. Whether a revised method provides sufficiently distinct practical value remains an empirical and academic question. No publication, universal safety guarantee, or first-use claim follows from executing the experiments.

## 3. Data, target meanings, and access conditions

All three primary studies use the same immutable prepared UNRAVELED artifact: 382,229 flows from eleven complete IT-sensor captures. Its SHA-256 is b2a491474e722f4dabcd4c419c83a4a6b49f08dfc3bc059aa42ef2aaa4c3de14. Preparation validates an intact numeric prefix and right-anchored author annotations in source CSVs that contain malformed descriptive fields. Exact observable-event duplicates were handled upstream. Literal host identities, absolute timestamps, source identifiers, and target labels are excluded from classifier inputs.

The four targets are benign, other attack stage, lateral movement, and data exfiltration. Their names retain the author's annotations. In this sensor, movement examples describe Remote System Discovery on one host pair. The study does not independently verify successful remote access or stolen-file receipt. Identifying an author stage is a narrower task than proving attacker intent or completed exfiltration.

Original captures 0-4 provide fitting data, capture 5 a separate calibration period, and captures 6-10 later-period evaluation. The latter contains 208,094 flows: 192,193 benign, 12,424 other-stage, 35 movement, and 3,442 exfiltration annotations. Current features summarize completed flows. Historical summaries use only events that finished before the current flow started. Consequently, none of the experiments measures warning before exfiltration onset or real-time recognition before the current flow completes.

Coarse host roles come from the released topology. History describes earlier completed traffic over five- and thirty-minute windows without earlier stage labels. The corpus has been examined in prior project work and represents one campaign. New source code and held-out training folds do not make its evaluation partition fresh independent confirmation.

## 4. Methods

### 4.1 Learning when to use history

PX-080 compares a current-flow-plus-role classifier with an otherwise comparable context classifier. Four forward folds train on captures strictly earlier than the evaluated fitting capture. Their out-of-fold probabilities supply selector supervision; evaluated fold rows are never used to fit the expert producing their probabilities. All base models and fitting caps are fixed before the run.

The ordinary selector predicts the difference between the context and current classifiers' 0/1 errors. The proposed selector weights that difference by four for movement and exfiltration examples and by one otherwise. These priorities are illustrative engineering choices, not a literature threshold or measured economic loss. At inference, the selector receives expert probabilities, relative evidence age, and availability. It selects context only when its estimated additional error is negative; it never receives the true stage.

Seven arms cover the current classifier, context classifier, equal probability fusion, maximum-confidence selection, ordinary learned selection, stage-weighted selection, and a classifier trained with context dropout and missingness indicators. Five conditions preserve all targets while varying the historical input: clean, half missing, all missing, a five-minute-old snapshot rebuilt from earlier observable events, and hidden wrong-host history. Ordinary and weighted selectors receive identical forward-fold training conditions. The dropout comparator is trained for missingness, not specifically for staleness; a stale-condition advantage over it alone cannot isolate the proposed loss function.

### 4.2 Choosing additional evidence

PX-081 fits classifiers for current evidence alone and for each subset of the two optional groups, roles and history. Four forward folds provide targets for transition regressors. One family estimates the reduction in stage-weighted classification error; the other estimates entropy reduction. Selection inputs include only current observations, already acquired groups, and the corresponding classifier probabilities. The unacquired group's values are not available to the policy.

The replay compares no acquisition, two fixed orders, deterministic random order, learned entropy reduction, and learned stage-error reduction. An unrestricted full-context reference is reported separately. Simulated role and history costs are one and two units, with budgets of one, two, and three. Quoted delays are 0.25 and 0.75 time units and the deadline is one. Failed and late queries still consume budget. A policy can decline a query whose predicted benefit is nonpositive.

Every policy shares the same row-specific availability and delay schedule, generated without stage labels. Conditions include clean delivery, delayed or unavailable channels, and wrong-host history. The costs and delivery times are simulated, not measured log-collection overhead. Values are precomputed; this does not implement dynamically changing feature values or prove a real deployment saving. Final predictions use the last successfully delivered subset, so failed acquisition is not silently counted as a correct abstention.

### 4.3 Temporal sensitivity measurement

PX-082 constructs a fixed anchor containing half of each supported class within each later capture, sorted by observable-event hash. Both primary arms predict these same 104,051 anchor rows. The past-only arm trains strictly earlier; the time-mixed diagnostic may also train on non-anchor later rows. Per-class fitting counts match, and training candidates whose current-feature fingerprints occur in the anchor are removed from both pools.

The diagnostic intentionally permits information unavailable in earlier deployment training. When history features are used, future training histories can also aggregate earlier anchor-flow measurements. The contrast therefore measures temporal protocol sensitivity, not an isolated causal effect of future labels. A secondary conventional random-row split changes the test population and is reported separately. Its score difference is not a pure leakage estimate.

### 4.4 Reporting, reproducibility, and uncertainty

Each of the three primary experiments fixes three seeds and all comparison arms before fitting. The seeds measure fitting variation on shared events, not three independent campaigns. Stage precision, recall, F1, average precision, ROC-AUC where defined, false alerts, and confusion matrices remain available for every registered condition in the two selector studies; the temporal audit preserves its registered F1, recall, false-alert and confusion metrics. Acquisition additionally reports attempts, delivered groups, spending, and elapsed simulated time. Weighted error is never the sole measure of success. The supplementary policy-transfer study instead has two deterministic Ridge fits, as described with its results.

Protocols and executable source were committed before fitting. Outputs preserve private row-linked predictions and public aggregate results. Post-fit audits independently reconstruct arithmetic, check temporal or acquisition constraints, and verify hashes. Passing these checks establishes execution and calculation consistency, not correctness of the source annotations. The temporal audit uses descriptive capture-bootstrap intervals; only five later captures and 18 anchor movement rows make population-level inference inappropriate.
