# Validity review: exfiltration features, specialists, and stage fusion

Review date: September 22, 2026. This is a design review before the new pilot's outcomes, using completed historical evidence. It is not a protocol registration, a novelty certificate, or a new experiment result. No model fitting, prediction inference, threshold search, or historical scientific artifact change was performed for this review.

## Recommendation in plain language

The new question should be: **Can we identify exfiltration more accurately, and distinguish it from normal traffic and other attack stages, using flow features and specialized classifiers?** The previous experiment asked whether sending more cases to review would catch rare attacks. It did not train specialists, add features, or evaluate a learned stage-fusion model. A fair new experiment can therefore test a different mechanism and endpoint.

Use a small frozen CPU pilot with the same fitting rows and labels for every arm. Compare engineered general models before claiming that specialists or fusion are responsible for an improvement. Train a learned fusion model only on genuinely out-of-fold base predictions, and compare it with an identically trained general-only fusion model. Retain every seed, all stages, and all declared arms. Treat the results as descriptive development evidence on already examined data.

## 1. What the previous experiment actually did

The [old design](../tabular_followup/RARE_STAGE_DESIGN.md) and [frozen protocol](../tabular_followup/protocol_rare_stage_gate.json) used existing six-class probability arrays from TabICL and a fitting-CV-selected XGBoost/LightGBM tree. Each model had 192 fitting rows: 32 per class, with the same supports shared between model families. There were ten fitting seeds, one calibration partition, and one development-test partition.

The common channel used `1 - p_TabICL(NormalTraffic)`. The rescue channel used the maximum of `p(stage)/(p(stage)+p(NormalTraffic)+1e-12)` over InitialCompromise and DataExfiltration and both model families. Benign calibration data defined one upper-tail threshold for the common score and one for the joint rescue maximum, each at nominal 0.5%. A strict threshold comparison combined the channels with OR. No specialist was trained; the rare scores were transformations of general classifiers' probabilities.

The primary requirement was at least five percentage points of gain in the mean per-seed minimum of InitialCompromise and DataExfiltration routing recall, against **both** fixed single-model controls. Additional guards allowed at most five percentage points of mean stage recall loss and at most 1.5% benign routing in every seed. These were chosen development gates, not external operational standards.

### Completed and independently audited results

The [aggregate](../results/tabular_followup_v1/GATE_AGGREGATE.json) and [independent audit](../results/tabular_followup_v1/GATE_AUDIT.json) contain ten complete pairs. I independently recomputed the following arithmetic means from the aggregate's per-seed rows:

| Policy | Initial routing recall | Exfiltration routing recall | All-attack routing recall | Benign routing FPR | Attack precision of review queue | Mean reviewed flows |
|---|---:|---:|---:|---:|---:|---:|
| Two-model candidate | 99.333% | 99.906% | 91.935% | 0.799% | 76.812% | 1,027.9 |
| Fixed TabICL control | 99.333% | 100.000% | 93.427% | 0.964% | 73.525% | 1,090.2 |
| Fixed selected-tree control | 88.000% | 87.642% | 78.403% | 0.940% | 70.372% | 954.1 |
| TabICL-only two-channel ablation | 99.333% | 99.906% | 91.748% | 0.698% | 79.082% | 996.2 |

Every seed evaluated the same 30,787 rows: 29,929 normal, 858 attack, including 15 InitialCompromise and 106 DataExfiltration. The counts are repeated-fit means, not additional independent incidents. Routing meant an item reached a hypothetical review queue; it did not establish correct stage classification or successful human review.

**Recorded decision: DEVELOPMENT_NEGATIVE.** The stage-loss and benign-burden guards passed; the required rare-stage improvement against both controls failed. The fixed TabICL control's mean minimum rare-stage recall was 99.333%. A perfect candidate could gain only 0.667 percentage points, making the frozen five-point endpoint unattainable. The candidate's mean minimum rare-stage recall was 99.239%, a 0.094-point decline versus that control. The old negative result must stay negative; the ceiling problem is a reason to design a different future endpoint, not to relabel the completed test.

Adding the tree to the otherwise identical TabICL-only gate improved neither InitialCompromise nor Exfiltration recall. It added 1.6 routed attacks from other stages and 30.1 benign reviews per seed. Thus the extra model did not demonstrate complementary rare-stage benefit. Relative to the single TabICL control, the candidate was quieter but routed fewer attacks; that is an observed tradeoff, not a successful rare-stage rescue.

The [final decision report](../results/tabular_followup_decision_v1/REPORT.md) also distinguishes the conformal result: nominal 95% class-conditional LAC, with only 14 InitialCompromise calibration examples, necessarily included that class for every row under the finite-sample rule. Its chosen protective routing map therefore reviewed everything. This does not describe 90% LAC or every uncertainty method.

## 2. The nonredundant question and available information

Generic attack routing was already near its ceiling for Exfiltration. Exact identification was not. The historical 192-label TabICL comparison had Exfiltration exact-stage recall 81.70%, precision 49.06%, and average precision 0.5888. Those figures support investigating confusion and ranking; they do not predict that any new feature or specialist will help. They are historical context, not a matched comparator for a new 1,184-label experiment.

The new study can isolate three distinct changes:

1. **Representation:** Do deterministic flow features improve a general model using the same labels?
2. **Specialization:** Does an exfiltration-versus-all model improve Exfiltration ranking beyond the engineered general model?
3. **Combination:** Does learned fusion add value beyond fixed fusion and general-only score recalibration, without damaging other stages?

The [SCVIC preparation receipt](../tabular_batch/SCVIC_PREPARATION.json) contains 73 predictors. It excluded IPs, ports, flow identifiers, timestamps, labels, and Idle statistics. All retained source partitions have already been examined in development. Exact-feature deduplication prevents identical predictor rows crossing splits; it does not establish independent incidents, time periods, hosts, or campaigns. The author's separate holdout remains unavailable.

### Feature semantics that must remain honest

- Use declared functions of the available single-flow measurements: log-scaled byte/packet volumes, directional ratios or shares, packet-size asymmetry, and variability ratios using recorded means and standard deviations. Freeze the feature roster and formulas before outcomes.
- Forward and backward describe the extractor's flow orientation. They do **not** establish outbound versus inbound organizational traffic or the identity of an exfiltrating host. Do not rename them as verified upload/download behavior.
- Aggregate flow columns cannot provide payload entropy, DNS-name entropy, host history, multi-flow periodicity, user behavior, or time-to-first-alert. Those require qualified raw data and a different split design.
- Existing columns already contain rates, means, ratios, and bulk statistics. New algebraic combinations can aid finite models but do not add independent telemetry. Improvement needs the engineered-general control.
- Define zero denominators, negative sentinels, nonfinite inputs, and clipping explicitly. Prefer bounded shares or a declared safe ratio. Do not clip or impute using evaluation-data statistics. Duration units must be qualified before calling a derived value bytes/second.
- Learned preprocessing, feature selection, imputation, or scaling belongs inside each training fold. Deterministic row-local transformations may be applied consistently before splitting, provided they never inspect labels or other rows.

## 3. Minimal fair arms and the proposed bounded expansion

The smallest useful study needs raw and engineered general classifiers, raw and engineered exfiltration specialists, fixed fusion, learned fusion, and a general-only learned calibration/fusion control. Omitting the engineered general model confounds representation with specialization; omitting the general-only learned control confounds expert value with recalibration.

The parent's proposed two-family pilot is an implementable expansion:

| Arm family | Inputs and target | Comparison it enables |
|---|---|---|
| G0: raw general XGBoost and LightGBM | Existing predictors; six-class target | Current fixed-configuration baseline |
| G1: engineered general XGBoost and LightGBM | Raw plus frozen features; six-class target | Feature value at unchanged model role |
| S0: raw Exfiltration specialists | Raw predictors; Exfiltration versus every other label | Specialist effect without new features |
| S1: engineered Exfiltration specialists | Engineered predictors; same binary target | Specialist value beyond G1 and feature value beyond S0 |
| E: engineered stage experts | One-versus-rest experts for all six labels, for both families | Stage-specific scores for fusion |
| Fixed fusion | Declared equal-weight combination of engineered general and expert outputs | Added information without learned stacking |
| General-only OOF learned fusion | Engineered general outputs only, same meta-model | Recalibration/ensemble capacity control |
| General-plus-expert OOF learned fusion | Same general outputs plus stage experts | Incremental expert information at matched labels |

An S1 expert and the Exfiltration member of E should reuse the same model/predictions when configuration, target, weighting, features, and folds are identical. Do not count duplicate fits as separate evidence. A specialist must train against **all** other stages as negatives, not only NormalTraffic; otherwise it has never learned the competing attacks that dominate some stage-confusion errors.

Use the same 1,184 support identities per seed: 1,024 normal plus 32 from each of five attack stages. A three-seed pilot should retain the first three previously declared seeds, 20260921–20260923, without dropping difficult or infeasible historical supports. It is a pilot, not a ten-seed result. All arms use the same label budget, folds, class order, feature roster, and evaluation rows. More specialists increase compute, not the number of unique fitting labels.

**Executed configuration clarification:** The final [protocol](protocol.json), frozen before this pilot's fits, instead specifies seeds **20260922–20260924** and fresh within-fit-pool supports ranked by `EXFIL_STAGE_V1|seed|feature_group`. The same new support is shared across every arm within a seed. This is a valid declared new support experiment; it is not reuse of the historical support identities recommended above. Historical baseline predictions therefore remain contextual, not matched controls. The final runner also retains a separately declared OOF-selected expert-family arm; that selection is not used to manufacture training inputs for learned fusion.

Fixed XGBoost/LightGBM settings and a fixed regularized logistic meta-model are reasonable for this bounded test. The discussed settings—300 boosting rounds, learning rate 0.05, XGBoost depth 3, LightGBM 15 leaves/minimum child samples 5, and logistic C=1—are proposed engineering choices, not established optima. The executable protocol must supply the complete settings, weighting, random seeds, and stopping behavior. An identical fixed configuration across feature arms limits outcome-dependent tuning. It does not establish the best achievable baseline or a state-of-the-art comparison.

Previously more extensively tuned trees may be shown as historical context, with their different information and tuning budgets explicit. They cannot silently become a matched ablation. Conversely, selecting a weaker fixed comparator after seeing the new results would invalidate the claimed contrast.

## 4. Leakage-free learned fusion

Use one deterministic, stratified three-fold partition of each fitting support, shared across arms. For every fold, fit all base-model preprocessing and models on the other two folds, then save probabilities only for the held-out fold. Each fitting row must receive exactly one OOF prediction from a model that did not train on that row or its label.

Train the logistic meta-model on the assembled OOF predictions and the original fitting labels. With fixed base and meta hyperparameters, no extra tuning loop is needed. If hyperparameters, expert membership, or feature selection are tuned, that selection must occur inside the training side of each OOF fold. Choosing a base configuration using full-support CV and then calling its held-fold predictions fully OOF leaks model-selection information from the held labels.

Refit each base learner on the full support for calibration/test prediction, and apply the already fitted OOF meta-model. This is standard stacking with a finite-sample distribution difference between OOF and full-support base scores; report it rather than presenting OOF rows as independent incidents. The general-only learned control must use the same folds, meta-model settings, class weights, score transformation, and label access.

Six independently trained OVR probabilities need not sum to one. For a fixed multiclass fusion, freeze their normalization and zero-sum handling before outcomes, then combine coherent six-column vectors with declared weights. Such normalization does not prove probability calibration. For learned fusion, the twelve raw/declared-transformed expert scores can be features; do not pretend they already form one posterior distribution. Any logit clipping constant must be fixed. Keep standalone Exfiltration score metrics separate from normalized multiclass-fusion metrics.

## 5. Outcomes without another invented 90% screen

Do not reintroduce a universal 90% recall requirement or a five-point gain that cannot fit under the baseline ceiling. The pilot should report predeclared paired descriptive contrasts, with exact counts and practical costs. It should not award a new deployment or praxis-success label because one score happens to improve.

**Recommended primary descriptive metric:** Exfiltration one-versus-rest average precision on the complete original development-test partition. This uses continuous scores and evaluates ranking beyond simple any-attack routing. Primary contrasts should include S1 versus G1 and general-plus-expert fusion versus both G1 and general-only learned fusion. Report all declared alternatives and every seed; do not choose a favorable model/fusion as the confirmatory winner after examining the test.

**Mandatory companion metrics:**

- Exact Exfiltration precision, recall, F1, and its complete confusion row/column; six-class macro-F1 and every stage's precision/recall/F1 for general/fusion arms.
- Exfiltration ROC-AUC and AP, with its prevalence baseline `106 / 30,787`, and a clear distinction between unweighted seed means and pooling repeated observations.
- Exfiltration detection among the same 106 unique test rows, with false Exfiltration labels broken into 29,929 normal and each other attack stage. This catches a specialist that labels many lateral or pivoting attacks as Exfiltration.
- Binary any-attack recall/FPR as separate secondary measures. A correct attack alert is not a correct stage decision.
- Every seed, each paired difference, extra detected/missed Exfiltration rows, and new false Exfiltration labels. If saving row-level corrections privately, also record whether a fusion gain comes from cases where experts disagree with generals. Do not select another method from these posthoc diagnostics.
- Unique fitting/calibration label counts and compute/time. A larger specialist library has a real fitting and inference cost, even when labels are shared. No analyst-hours estimate follows from flagged-flow counts.

For threshold diagnostics, use only the old calibration partition and freeze the operating levels and strict `score > threshold` tie rule before test evaluation. Nominal 0.1% or 1% tails can be labeled **chosen descriptive benchmark operating points**, not external acceptance standards or guaranteed future FPR. A normal-only threshold controls a different empirical denominator from an all-non-Exfiltration threshold. For an identification claim, report both normal-to-Exfiltration and all-non-Exfiltration error rates; if the latter is the declared selection target, calibrate using all non-Exfiltration labels. Never set thresholds from observed test false alarms to make methods look workload-matched.

The full old calibration set contains 30,782 labels, including 105 Exfiltration and 29,929 normal; an all-non-Exfiltration threshold uses 30,677 negative labels. Any stage-aware calibration or selection therefore consumes information beyond the 1,184 fitting labels. The old source data remain exposed development data even after splitting calibration into additional subparts.

Three or ten fitting seeds on these rows do not justify independent-incident confidence intervals. If the pilot has favorable mean contrasts, call them candidate improvements requiring independent replication. If AP improves while Exfiltration precision, another stage, or false-alarm burden worsens, describe the tradeoff. If only fusion with expert inputs beats a raw baseline but not G1 or general-only fusion, the claimed specialist contribution is unsupported.

## 6. Required audit evidence

Before fitting, freeze code, complete configurations, deterministic feature formulas, all support/fold identities, source data/manifest hashes, the arm roster, and named contrasts. Source labels remain assumed truth; an automated consistency audit cannot adjudicate the dataset's attack labeling.

The independent arithmetic/provenance audit should verify:

1. Identical support indices/fingerprints across matched arms; no overlap with calibration/test; correct six-class order and unique-label ledger.
2. Feature formulas on synthetic edge cases and a deterministic sample; no evaluation-fitted imputation/scaling; no forbidden identifiers or label-derived predictors.
3. Every OOF row has one prediction, its producing model's training indices exclude that row, and shared folds/preprocessing bindings are saved. Record any distinct hyperparameter-search information.
4. Meta-model inputs use OOF probabilities for training, never fitted-in-sample predictions. The general-only control uses the same meta-model and preprocessing recipe.
5. Shared S1/OVR Exfiltration artifacts are identical when claimed to be reused. All promised model/seed arms complete; failed cells remain explicit.
6. Thresholds reconstruct exactly from calibration scores and the stated denominator, with ties kept together. No threshold is chosen from test scores/labels.
7. Saved probabilities are finite, ordered, and valid for their declared role. Recompute confusion matrices, per-stage metrics, AP/AUC, false-alert counts, paired differences, and any declared descriptive decision.
8. Final claims distinguish feature effects, specialist effects, generic score recalibration, and operational transfer. Preserve null/negative contrasts and previously recorded outcomes.

Meaningful software tests include held-fold exclusion, no in-sample stacking, feature zero/sentinel behavior, probability-column permutation rejection, fixed-fusion normalization, strict threshold ties, and a tampered prediction/summary artifact. These are software integrity checks, not evidence that the research hypothesis is true.

## 7. Novelty and progression boundary

Feature engineering, OVR specialization, boosted trees, probability fusion, and OOF stacking are established components. Their combination alone is not a novel method claim. The parallel literature review must assess direct SCVIC/Exfiltration overlap before describing a new applied gap. This review establishes only that the proposed pilot is different from our own earlier score-routing gate.

A useful positive outcome would be a clearly attributed, bounded empirical finding: for example, specialists add Exfiltration ranking or exact-stage identification beyond engineered general models and general-only fusion, with the false-label and other-stage costs reported. A negative or feature-only result still answers which component mattered; it should not trigger a new success definition on these same outcomes.

No completed external evidence currently validates Exfiltration here. Sandworm's prior mapped task had no Exfiltration class, and the DEDALE stress concerned four lateral flows from one execution. Independent Exfiltration executions with qualified feature semantics, realistic competing traffic, and a locked incident-aware split are a separate next validation requirement. Neither those datasets' existence nor a positive source pilot establishes early warning, actor attribution, missing-log resilience, or real-world protection.

## Historical source bindings inspected

| Source | SHA-256 |
|---|---|
| `tabular_followup/protocol_rare_stage_gate.json` | `03199d57cbb68c339a38926b8d338076695e0aace3045b90c4c578fbd6fd18cd` |
| `results/tabular_followup_v1/GATE_AGGREGATE.json` | `89da5dbf5a2bd6d17e85cc0d3fef073f15e8304a2ab73d212c6d33ba35176524` |
| `results/tabular_followup_v1/GATE_AUDIT.json` | `d12dc22dc16470ba401eda5e68acedfd1db4c674948f72de93fa629f5f1b8bea` |
| `tabular_batch/SCVIC_PREPARATION.json` | `22b91626dbc225ff6446537f038bc624d5b623e06584a5eadc61a92aecc1ac80` |

Paths in this table are relative to `experiments/apt_benchmark`. The old gate audit reports PASS for integrity; its scientific outcome remains DEVELOPMENT_NEGATIVE.

## Completed integrity check of the new pilot

After all three registered pilot seeds completed, the separate [auditor](audit.py) reconstructed **72 arm-level metric packages** from saved prediction arrays and verified source/protocol, support/fold, fixed-fusion, threshold and artifact bindings. The [public audit](../results/exfil_stage_v1/AUDIT.json) reports **PASS / COMPLETE** for 54 final base models, 216 base fits including cross-fitting, and 15 fusion fits. Fourteen synthetic software checks passed, including withheld-row exclusion, OOF-only fusion inputs, strict threshold ties, normalization, and tampered artifacts/metrics. No models were fitted, deserialized, or replayed by the audit. Discarded OOF fold models were not independently replayed; their declared membership is checked against saved metadata and reviewed runner code. This establishes saved-output consistency, not effectiveness, independent incident validity, or novelty.
