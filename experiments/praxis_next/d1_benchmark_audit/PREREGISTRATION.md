# D1 / PX-084: Temporal validity and warning retention in APT-stage benchmarking

**Prospective extension protocol, September 23, 2026.** This is a measurement study. Its contribution is controlled evidence and reusable evaluation infrastructure. A new superior detector is not its success criterion. Git registration will precede any new fitted evaluation; it does not make previously examined datasets untouched confirmation.

## 1. Questions and status of earlier evidence

1. With the same model, later evaluation rows and fitting class counts, how does allowing later-period training change reported stage performance?
2. Does an increase in macro-F1 accompany a decrease in the fraction of a particular attack stage receiving any attack warning?
3. Under past-only training, how does adding valid earlier history change stage recognition, warning retention and benign alert workload?
4. Which requested releases actually support these comparisons, including valid clocks, native labels and grouping units?

PX-082 already demonstrated training-composition sensitivity on one exposed UNRAVELED campaign. PX-081's warning/stage mismatch was discovered after inspecting initial results and remains exploratory in that study. D1 makes paired warning and stage reporting a prospective requirement for new runs. The earlier chronological history gains are supplementary observations with their increased exfiltration-to-benign errors retained. None is retroactively upgraded to an untouched primary outcome.

The temporal contrast holds architecture fixed; it does not establish that architecture has no effect. The current-plus-roles comparator in PX-080 is a learned LightGBM classifier, not a deterministic security rule. Its movement recall advantage is not superiority on every metric. See [literature positioning](LITERATURE_POSITIONING.md).

## 2. Requested sources and qualification before fitting

Requested expansion: SCVIC-APT-2021, DAPT2020, DSRL-APT-2023, and S-DAPT-2026. UNRAVELED remains the existing development reference. A name in this list does not imply data access, independent provenance, suitable chronology or successful execution labels.

Every source receives one of these outcomes:

- **Eligible temporal contrast:** actual source rows, defensible clocks/event end times, real source grouping, explicit native benign/stage mapping, earlier fitting periods and later anchor support pass the declared checks.
- **Ordering/support diagnostic only:** some timestamps or source file groups exist, but all-stage temporal fitting or clock/independence claims fail. Report the support failure without training a substituted random-split experiment under a temporal label.
- **Synthetic sensitivity only:** generation dependencies and synthetic timestamps prevent independent real-campaign confirmation. Such results would require a separately frozen synthetic arm; none is authorized by this protocol as a substitute temporal result.
- **Unavailable/unqualified:** no verified released bytes, unresolved source provenance, or no usable target mapping. Publish the reason and omit model comparisons.

Checks require hashes, release/version and rights metadata; row and native-class counts; explicit benign mapping; timestamp formats, anomalies and event intervals; source file/run/campaign identities and their meaning; exact-feature duplicate and conflicting-label counts; stage support by source and time; and dependency between datasets. Missing end times cannot silently be replaced by start times. Synthetic timestamps cannot be treated as natural chronology. Dataset derivatives do not count as independent replications.

The [qualification record](DATASET_QUALIFICATION.md) may identify failed eligibility checks before any fits. Two fitting examples per class are a technical minimum, not evidence of statistical adequacy. Report rare-stage counts and the number of real groups separately. No fixed accuracy, 90% recall or minimum favorable effect is a publication gate.

## 3. Portable input contract and split rules

A qualified private NPZ contains finite `current` features, optional `history`, integer `labels`, unique `row_ids`, observable `event_hashes`, source `groups`, numeric `starts`/`ends` in a declared common unit, and `splits` (0=past fit, 1=reserved calibration, 2=later evaluation). A companion source manifest records ordered native `class_names`, `benign_index`, feature names/availability, input hash, grouping interpretation, qualification evidence, and frozen time boundaries. Labels retain native meanings; no universal movement/exfiltration mapping is inferred from names.

Adapters must freeze source-supported split boundaries before new predictions, without moving them until a desired stage or result appears. IDs, source names, absolute timestamps, outcome proxies and labels are excluded from predictors. Features must be available by the stated decision time; full-flow measurements imply decisions after completion. Past-only history must use events ending before the current event starts. Imputation/scaling, if required, must be fitted on the permitted fitting data and specified before the adapter is frozen.

Within each later source group and native class, order by observable event hash (row ID breaks ties) and choose the first ceiling-half as the common anchor. Past-only fitting uses split 0. The time-mixed diagnostic additionally permits non-anchor split-2 rows, while excluding calibration rows. Remove every current-feature fingerprint present in the anchor from both training pools. Use identical per-class fitting counts equal to the smaller eligible pool, capped at 20,000 benign and 5,000 per attack class. Sampling uses fixed seeded row hashes without replacement.

Every native class must have at least two matched fitting rows and at least one anchor row for the closed-set comparison. An absent class is a reported eligibility failure; it is not silently removed or supplied to one arm from later data. All past fitting flows must finish before any later evaluation flow begins. Overlapping flows and timestamp ties must be resolved by these strict inequalities, not random assignment across a boundary.

If no later non-anchor row remains after purging, report no temporal contrast and skip redundant fits. The executor must also report realized later-training counts after fixed seeded sampling. If a seed samples no later rows, retain that no-exposure diagnostic explicitly; do not reroll its sample or describe it as evidence of actual later-period exposure.

The time-mixed arm is deliberately unsuitable for past deployment. With history, later training examples may summarize earlier anchor observations. The contrast therefore measures training-time/composition sensitivity, including those dependencies, rather than an isolated causal effect of future labels. A conventional random-row split is not included in D1's primary effect; it changes the test population and is already a separate PX-082 diagnostic.

## 4. Fixed models and contrasts

Three fitting seeds: 20260923, 20260924, 20260925. Two fixed classical controls:

- LightGBM: 200 estimators, 15 leaves, learning rate 0.05, minimum child samples 10, L2=1, deterministic column-wise execution, two threads.
- Random Forest: 300 estimators, minimum leaf size 5, square-root feature sampling, no class weighting, two threads.

No test-guided search, neural-model substitution or additional seed sweep. Current features are required. History is a secondary view only if its causal construction is qualified; datasets without that evidence report the view unavailable.

Primary contrast per eligible dataset: **time-mixed minus past-only LightGBM, current features**, on the same anchor. Random Forest is a prespecified replication of the protocol effect, not a test-selected winner. Secondary contrasts are past-only history minus past-only current, and time-mixed history minus past-only history, where eligible.

Decisions use multiclass argmax in native class order, with ties resolved by the earlier declared class index. Any-attack warning means the chosen label is not benign. No thresholds are selected on test outcomes. Report actual benign false alerts/rates alongside every contrast; identical decision rules do not imply equal false-alert workload. An operational claim of improvement at matched workload would require a separately frozen, calibration-supported operating-point study.

## 5. Paired warning/stage measures

For each native attack stage s, on exactly the same true-stage rows:

- **Exact-stage recall:** predicted s / true s.
- **Warning recall:** predicted any non-benign class / true s.
- **Missed-warning rate:** predicted benign / true s = 1 minus warning recall.
- **Wrong-stage warning rate:** predicted a different attack class / true s = warning recall minus exact-stage recall.

These are established confusion-matrix quantities. “Warning recall” is a readable name, not a claimed new mathematical metric or safety guarantee. Publish the pair, both error counts, support, benign false alerts, per-class precision/F1, macro-F1, and confusion matrices. AP/ROC may be included when score semantics and positive/negative support permit; they do not replace operating-point counts.

A **metric/warning sign reversal** occurs when a prespecified same-row contrast has positive macro-F1 difference and negative warning-recall difference for a named stage. Report exact magnitudes and uncertainty. Do not select the most favorable model, stage, seed or dataset after observing results. Every native stage is shown, including no reversal and unfavorable changes. A tiny floating-point difference within 1e-12 is treated as zero for the descriptive sign flag only; this is not a practical-significance rule.

Unsupported stage recalls are null, not zero. D1's fixed-schema macro-F1 is null if a declared true class is absent from a resampled evaluation; disclose that convention and excluded-bootstrap counts. Existing PX-082 results keep their original convention and are not overwritten.

## 6. Uncertainty and independent units

Use 2,000 paired bootstrap draws over validated source groups, with identical sampled group multiplicities for both arms and all compared fitting seeds/models. Repeat whole groups; never bootstrap correlated flow rows as independent incidents. Preserve per-seed point estimates and intervals, plus the descriptive three-seed mean. No pooled-seed event count or independent-campaign interpretation is permitted.

Construct exactly one bootstrap plan per dataset/common anchor with seed 20260923, and reuse that plan across all fitting seeds, model families and contrasts on that anchor. Fitting seeds do not seed separate bootstrap plans.

If groups are captures within one campaign, intervals are explicitly conditional capture intervals. If only one usable group exists, report no group-bootstrap confidence interval. If a stage is absent from a draw, report how many draws support its interval; its interval is conditional on stage presence. Small group counts and correlated executions remain limitations. No nominal population coverage claim follows from a percentile interval alone.

Per-dataset 95% percentile intervals are descriptive, not simultaneous family-wide guarantees. A family-wide first/usefulness/robustness claim cannot be inferred from one significant cell among multiple datasets or stages. Report dataset results separately; do not pool native stage meanings or treat DAPT-derived DSRL as a second independent real dataset.

## 7. Spend and stopping bounds

At most four expansion datasets, two model families, two feature views, two training arms and three seeds: **96 model fits maximum**. The current-only maximum is 48. Eligibility failures reduce these counts; they do not trigger replacement searches. CPU is the default for these modest fits. No GPU instance is needed simply to compute confusion matrices or bootstrap intervals.

Aggregate new AWS allocation ceiling for D1: **USD 5 estimated compute plus declared incidental reserve, combined**, maximum 60 minutes total allocated instance time, with a verified independent shutdown watchdog, durable collection and stop-on-exit. Zero cloud allocation is needed for qualification/software checks. Local fitting is capped at 120 minutes cumulative wall time and at most two concurrent two-thread workers. A timed-out cell is incomplete, not a low-performing completed result. No automatic resource expansion or unregistered retry to seek a favorable result.

Freeze protocol, configuration, metrics/planner/executor source, tests and each qualified adapter/input manifest in Git before its new fits. Qualification inventories and source-support calculations are allowed before freezing; model outcomes are not. Preserve private row-level predictions and public aggregate/audit receipts. Report actual compute separately from estimates and ceilings.

## 8. Prewritten interpretations

**Positive protocol effect:** With architecture, anchor and class budgets fixed, time-mixed training improved measured performance on the eligible corpus. This supports sensitivity to the declared training composition; it does not show architecture is irrelevant or that every published result is inflated.

**Small, uncertain or opposite protocol effect:** The measured effect was small, uncertain or favored past-only training under this design. The result does not certify temporal robustness under other workflows.

**Warning/stage mismatch reproduced:** The prespecified comparison improved macro-F1 while warning recall for stage s fell by the reported amount, with its false-alert change and interval. This documents that tradeoff on these observations; it does not establish actual theft, a new metric or a universal security guarantee.

**Mismatch absent:** The prespecified comparisons did not reproduce the earlier mismatch on this source. Retain the earlier observation's bounded scope; do not add model/threshold sweeps to manufacture another reversal.

**Dataset fails qualification:** The available release cannot support the specified temporal, all-stage or independent-execution claim for the stated reason. Publish the measurable support/clock/provenance limitation. Do not present it as a negative detector result or as proof the full research dataset is unusable for all tasks.

## 9. Publication claim and remaining work

Working contribution: a controlled, reproducible measurement of how training composition and historical evidence change stage recognition, missed warnings and benign workload on **qualified** APT-flow data, accompanied by explicit dataset eligibility findings. Breadth, independent execution evidence and differentiation from close prior work must be demonstrated, not obtained by counting dataset names. This protocol and software are complete artifacts; publication acceptance is not guaranteed by their existence.
