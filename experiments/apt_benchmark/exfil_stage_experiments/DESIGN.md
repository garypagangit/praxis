# Exfiltration attribution and stage-specialist fusion

September 22, 2026. Two development experiments, frozen before this batch's model fits. Earlier SCVIC results informed the questions. Every existing partition has been exposed in prior studies; this batch is not independent confirmation.

## The problem in plain language

The detector often knows a connection looks suspicious but cannot reliably say whether it represents stolen data leaving, reconnaissance, or another attack activity. A wrong stage label can send an analyst toward the wrong part of an incident. We will test whether specialized detectors and more useful descriptions of traffic help distinguish the stages.

The earlier rare-stage review experiment nearly saturated **any-attack routing** of exfiltration. This new study measures **correct exfiltration identification**, including false exfiltration labels on normal traffic and on other attacks. These are different endpoints.

## Experiment 1 — A specialist for recognizing exfiltration

**Question:** Does an exfiltration-versus-everything specialist benefit from directional and variability features, beyond giving those same features to a general six-class detector?

**Hypothesis:** Exfiltration-specific training and a compact set of traffic re-encodings improve exfiltration ranking and useful identification at measured false-alarm costs.

Both XGBoost and LightGBM receive identical examples. Compare each family's raw general detector, engineered general detector, raw exfiltration specialist, and engineered specialist. Specialists treat normal traffic **and every competing attack stage** as negatives. Additional arms compare averaging and learned fusion with general-only averaging and learned fusion controls.

Primary descriptive endpoint: exfiltration-versus-all **average precision**, a summary of the precision–recall curve. Report ROC-AUC, precision, recall, F1, alert count, normal false alerts, and mistaken exfiltration labels by true attack stage. Choose a single F1 threshold on calibration data; separately sweep nominal 0.1%, 0.5%, 1%, and 2% false-positive budgets, once using normal calibration rows and once using all non-exfiltration rows. These percentages are investigator-chosen comparison points, **not acceptance standards or guaranteed future rates**. Publish observed test rates and the complete saved scores.

## Experiment 2 — A team of stage specialists

**Question:** Do separate models for each stage produce a more accurate stage assessment than general models with the same data and features?

For each label, train an XGBoost and a LightGBM one-versus-rest expert. This includes a normal-traffic expert. Compare:

1. The two general models, individually and averaged.
2. General-only learned fusion, controlling for benefits from combining/reweighting general scores.
3. Averaged specialist scores, normalized within each six-score family before averaging.
4. One family selected per stage using fit-only out-of-fold average precision; normalize the resulting six scores. This selection arm is not an input to the learned fusion arms.
5. Learned specialist-only fusion.
6. Fixed and learned general-plus-specialist fusion.

Learned fusion is a regularized logistic model trained on out-of-fold scores: each fitting row is scored by base models that did not train or impute on that row. No calibration/test rows train any model. Fixed hyperparameters avoid indirect leakage through full-support tuning. A selection of the best family per stage is an established ensemble technique, not a novel algorithm claim.

Primary descriptive endpoint: six-class macro-F1. Publish precision, recall, F1, AP, ROC-AUC and confusion for **every** stage, and report any-attack detection separately. A gain in exfiltration cannot conceal a cost to lateral movement or initial compromise. Do not rank methods solely by overall accuracy on this imbalanced data.

## Shared data and computation

- SCVIC author training CSV, prepared as 153,919 unique nonconflicting feature rows and 73 predictors; no IP, port, identifier, timestamp or label predictors.
- Three fitting seeds: 20260922–20260924. Each uses 1,024 normal and 32 examples from each of five attack classes: **1,184 fitting labels**. All arms within a seed share the same examples.
- Existing calibration: 30,782 rows, including 105 exfiltration examples. Existing descriptive test: 30,787 rows, including 106 exfiltration examples. Calibration labels are additional to the fitting budget; they choose thresholds, not base/fusion fits.
- XGBoost: 300 trees, depth 3, learning rate .05, L2=1. LightGBM: 300 trees, 15 leaves, minimum child count 5, learning rate .05, L2=1. No class weighting, augmentation, or search. These are bounded fixed-configuration comparisons, not exhaustive comparisons against tuned state of the art.
- Three stratified cross-fitting folds use the original six labels, including for binary experts. Median imputation is fitted inside each fold. Final base models refit all 1,184 rows. Logistic fusion uses C=1 on clipped logit scores, no tuning.
- Eighteen final base models and five fusion models per seed; 72 base fits including cross-fitting per seed. CPU with four threads is appropriate for this small fitting set. No GPU or cloud expenditure is needed for this pilot.
- Stored models, exact fitting/fold indices, scores, confusion matrices, dependency versions, source/data/protocol hashes, and independent arithmetic audit provide a reproducible evidence trail.

## Engineered features and their limits

Eighteen deterministic features add total byte/packet/duration logs; forward fractions; signed directional asymmetry; log directional ratios; bytes per packet and its direction ratio; coefficients of variation for flow/forward/backward interarrival times, packet lengths and active periods; and the difference between byte and packet forward fractions. Exact formulas are in `engineered()` in [run.py](run.py); nonnegative clipping, additive-one denominator smoothing, and missingness propagation are explicit.

These transformations add **no new observations**. Some overlap existing ratios and statistics. They may make relationships easier for shallow trees to use, which is why the engineered general-model control is mandatory. “Forward” means the flow extractor's direction; it does **not** establish outbound traffic, an external destination, or data theft. Full-flow statistics become available after flow completion. This is not early detection.

## A stage assessment is not yet a reconstructed attack

The pilot outputs a vector of six scores for each flow. It does not establish who moved between hosts or the order of attack steps. Normalized specialist scores are not automatically calibrated probabilities.

The acquired 2026 DEDALE author-labeled subset has temporal and host linkage, but only **two exfiltration flows from one execution and one campaign**. It can support a retrospective illustration with scores available no earlier than flow completion. It cannot establish reliable exfiltration generalization. C2 and collection labels must not be silently recoded as one of SCVIC's six classes.

A subsequent campaign-level experiment must qualify independent execution/host/time records and a documented taxonomy mapping, then compare stage scores alone with causal host-linked aggregation using past evidence only. Include general-model-plus-context and simple temporal aggregation controls; measure stage errors, false episode alerts and time-to-detection. Stage labels alone do not justify a fixed attack chain: stages can repeat, overlap, or be absent. That experiment is **specified, not run** by this pilot.

## Literature position and interpretation

Feature engineering, APT stage classification and model ensembles already exist, including Cai et al. (2025) on SCVIC and Unraveled. See [LITERATURE.md](LITERATURE.md) for the verified overlap. This pilot tests an applied question: whether an explicit specialist contribution survives equal-information controls, proper separation of fusion fitting, and full reporting of exfiltration false positives and competing-stage costs. It establishes neither algorithmic novelty nor a committee's acceptance of a praxis topic.

Report gains where measured, losses where measured, and null differences without an arbitrary global pass/fail gate. Three fits share the same cases; do not treat them as independent attacks or derive population confidence from the seed count. A positive development comparison would justify qualifying fresh independent data and a stronger tuned comparison, not immediate operational deployment.
