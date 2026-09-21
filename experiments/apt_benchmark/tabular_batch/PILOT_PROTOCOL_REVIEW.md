# Suggested finite staged pilot for the tabular APT batch

Status: **protocol recommendation, not an executed or retrospectively registered experiment**. Written September 20, 2026 before this reviewer ran any fits. The execution owner must record the acquired dataset release/checksums, exact columns, class definitions, split roster, model versions/settings and protocol hash in a pre-fit receipt. Any deviation is an amendment, and existing exposed data remain development evidence.

## Purpose and scope

Determine whether a qualified APT-stage table contains a useful, reproducible low-label task, and whether modern tabular models, uncertainty sets or noise treatment improve an operational outcome. The first pilot is limited to one primary qualified dataset. A second independent dataset is confirmation only after the first decision. This protocol does not replace the separately authorized CAM window diagnostic.

No result is required to be positive. Distinguish: unavailable data, invalid task, failed software, negative scientific result, promising exploratory result, and confirmed improvement.

## Stage 0: data and shortcut gate

For each of SCVIC-APT-2021, DAPT2020, DSRL-APT-2023 and S-DAPT-2026, record:

1. Authoritative publication/artifact link, actual acquisition result, release/hash and data-use terms.
2. Label meaning: attack family, traffic category, attack step, stage, current stage or future stage. Do not rename categories to stages without an author-supported mapping.
3. Actual row counts, per-class counts, missing values, timestamps and ordering, duplicate/near-duplicate rates, repeated host identities, scenario/template/source memberships and independent-unit counts.
4. Which columns are observable at prediction time. Exclude labels, label encodings, filenames, scenario IDs, source indicators and post-outcome features from model inputs unless independently justified.
5. Whether attack-type lookup, source identity or a single suspicious field reconstructs the target. Publish diagnostic results as shortcut evidence; such controls are not candidate production features.
6. Whether synthetic variants or repeated flows descend from the same original example. Group all descendants before splitting. Split generator templates/realizations where available.

**Go:** a reproducible, licensed artifact supports at least two meaningful labels, independent split groups, an explicit observable feature set and disjoint fit/development/calibration/test allocations. For stage claims, labels must actually describe stages. For temporal claims, time ordering must be usable. For next-stage claims, ordered campaigns and a future target must be verified.

**Conditional:** if only row-wise classification is possible, it may support a disclosed software feasibility pilot, but not a temporal, campaign-generalization or certified deployment claim. Do not silently promote it.

**Stop:** unavailable data, unreconciled provenance, labels encoded in required inputs, or no independent evaluation units. Record the reason and try the next already-listed dataset; do not generate replacement data and call it the authors' dataset.

Select the primary dataset by fixed order among those passing the gate: SCVIC-APT-2021, DSRL-APT-2023, DAPT2020, S-DAPT-2026. This order is a recommendation; any alternative must be recorded before model outcomes are seen.

## Stage 1: E1 small-model screen

### Allocation and feature rules

- Freeze groups before selecting rows. Prefer group-held-out chronological allocations when the artifact supports both; otherwise use explicit group-held-out allocations and drop temporal language.
- Keep the complete test population and its prevalence. Do not balance the test table.
- Select a feasible common class set from training-side metadata before outcomes. Report excluded classes rather than treating absent or unsupported classes as successful predictions.
- Proposed primary fitting budget: 128 labels per class. Proposed exploratory budgets: 32 and 256. If 128 is unsupported, amend before any fit; do not select the successful budget afterward.
- A generous labeled development/calibration pool changes the question to *small fitting context*, not *few total labels*. Report all label counts by role. A later strict annotation-budget study must allocate its complete budget across roles.

### Models and finite search

Mandatory controls: majority predictor, regularized multinomial logistic regression, Random Forest and XGBoost. Foundation-model candidates: one pinned TabPFN release and one pinned TabICL release if weights, license, class count, feature count and memory permit. No replacement of a missing candidate with an unreported version.

The execution owner freezes at most three configurations per classical model family and one configuration per foundation model before fitting. Use the same development metric and selection data. Include preprocessing/selection costs in cost reports. Foundation pretraining is external learned information and must be acknowledged; “inference-only” is not “no learned model.”

Three prespecified subsampling/fitting seeds are enough for the pilot; expanding to ten is a later confirmation decision. Use common subsamples across models. Hardware choice must not alter the split or budget.

### Measures and decision

Primary outcome: macro-F1 at the primary fitting budget, chosen model settings frozen on development data. Report per-stage recall/precision, confusion counts, one-vs-rest ROC-AUC and average precision where supported, fit/setup time, warm and cold inference latency, throughput and peak memory. Undefined metrics stay undefined.

The primary foundation-model candidate is selected on development data; the primary classical comparator is also selected on development data. Do not select the best test model and then calculate an ordinary two-model interval.

**Promising development result:** at least +0.02 absolute macro-F1 over the frozen comparator and no prespecified high-risk stage loses more than 0.05 recall. These are project screening thresholds, not universal standards. Publish cluster-level uncertainty when enough groups exist; otherwise label the result descriptive. Reserve any formal superiority claim for a fresh, adequately powered confirmation dataset/split.

**Stop expansion:** no useful discrimination beyond shortcut-free simple controls, or apparent gains disappear with correct grouping. Do not compensate by moving to progressively more expensive models on the same exposed test data.

## Stage 2: corrected E4 uncertainty audit

Reuse frozen model predictions. Primary nominal coverage is 90%; 95% is secondary. Use deterministic split-conformal label sets with a declared score and finite-sample quantile, plus class-conditional sets as an explicitly separate arm when supported. Retain empty and full sets. Unsupported classes must not be dropped to improve coverage.

Required outputs: pooled and per-class coverage, test denominators, mean/median set size, empty/full-set frequency, singleton accuracy and proportion, and per-group results. Compare both models on the same calibration/test records. Include the full-label set as the trivial coverage control.

The primary test is whether sets are informative **and** adequately cover the qualified test population. A suggested screening rule is at least a 10% smaller mean set than the comparator, with pooled observed coverage at least 88% at nominal 90% and no supported class below 85%. These tolerances are descriptive pilot criteria, not proof of validity; calibration/test dependence and group counts must accompany them. A larger confirmation study must specify inferential coverage criteria in advance.

Temporal or family shifts receive a separate table titled empirical coverage under shift. No distribution-free validity claim is attached merely because the calibration algorithm ran. Frozen model selection followed by conformalization does not make test-driven method selection valid.

## Stage 3: E3 label-noise pilot, only if labels qualify

Apply corruption only to training labels, preserving clean ground truth privately for scoring. Primary stress: 20% symmetric flips to a different class. Include 0% as a required damage control and one predeclared asymmetric transition matrix as exploratory. Use common corrupted labels across arms and seeds. Development, calibration and test labels stay uncorrupted; disclose that clean reference labels are an assumption of this benchmark.

Mandatory arms:

- No correction, with the same early-stopping/model-selection budget.
- Gradients with removal.
- Gradients with one-time relabeling.

The named algorithm requires a faithful implementation or a clearly named adaptation, checked against the [literature review](LITERATURE_VALIDITY.md). Freeze its complete mechanics and hyperparameters before fitting. Do not give it the hidden true corruption mask or the actual noise rate unless an explicitly labeled oracle control receives that information.

Report clean-test macro-F1, per-class recall, correction precision/recall, fraction of truly clean labels altered, and loss of clean rare-class examples. The detector can identify errors well and still make the classifier worse.

**Promising development result:** at least +0.02 macro-F1 in the primary corrupted condition, at most -0.01 macro-F1 in the 0% condition, and no high-risk class loses more than 0.05 recall. No automatic success if one of many exploratory noise levels wins. Further confirmation requires fresh independent groups and the same selected mechanism.

## Deferred experiments and unlock requirements

| Experiment | Unlock requirement | Allowed initial claim |
|---|---|---|
| E2 cascade | Measured screen cost leaves room for total-system savings; threshold chosen on development. | F1/recall versus measured end-to-end throughput on the stated hardware, with all missed attacks counted. |
| E5 open-set fusion | Real benign reference, supported known/held-out attack groups, completely excluded held-out-stage training/development/calibration data. | Held-out-stage empirical recall at calibration-selected benign alert budgets, compared with each component. No unknown-stage miss certificate. |
| E6 next-stage forecast | Qualified ordered campaign files and prefix-only observable inputs. | Forecast improvement over most-common-next-stage, persistence and first-order transition controls at frozen horizons. No early-warning claim from retrospective full-sequence features. |
| E7 GRANDE | Core harness validated; no unresolved data/label problem; bounded remaining resources. | Additional prespecified model comparison; parity is not an automatic research success. |

For E5, zero or too few benign calibration examples means a false-positive operating point cannot be credibly calibrated. Calibration support for known attacks does not establish support for an unseen attack. A fusion using anomaly scores must be selected without withheld-stage examples. Report actual test false-positive rates; shifted data may violate the calibration budget.

## Statistical and execution record

Record seed-specific predictions and group IDs, not only averages. Use a paired group bootstrap for descriptive intervals only when group counts support it; all rows in a campaign/realization travel together. Model seeds are not independent test populations. The wide grid is exploratory. A formal multi-cell claim requires a separately specified familywise procedure or untouched confirmation.

Before remote compute, pin source/protocol/data hashes and model versions. GPU is useful if the actual candidate benefits and data/weights fit; CPU is acceptable for small tree and uncertainty pilots. Measure actual costs and stop idle instances. Authentication failure or unavailable weights is an execution limitation, not a negative model result. No result in this document implies that AWS was contacted or a model run was started.
