# Stronger tree baselines: a separate follow-up

## Question

Does the original few-label TabICL result survive a wider search for strong conventional tree models? Separately, do trees close the gap when they receive more benign examples while keeping the same scarce attack examples?

This protocol was designed after earlier development results were known. It reuses the existing feature-deduplicated SCVIC development partitions, not a new untouched holdout. Freeze this source and `protocol_strong_baselines.json` before any follow-up fit. The original `tabular_batch` code and settings remain unchanged.

## Conditions and label costs

| Condition | Attack training labels | Benign training labels | Total |
|---|---:|---:|---:|
| Equal labels | 32 for each of five attack stages = 160 | 32 | 192 |
| Additional benign data | Same 160 attack rows | 1,024 | 1,184 |

For each of the ten original seeds, the equal-label support is byte-for-byte identical in index/fingerprint order to original E1. The second support retains all 192 original rows and adds 992 benign fit rows. Additions are ranked by `SHA256(STRONG_BASELINES_BENIGN_20260921|seed|fingerprint)`. No calibration or test row can enter either training support.

The second condition costs 992 additional labels. It is an explicit deployment challenge, not an equal-budget comparison with the original foundation models. No extra labels are used for tuning.

## Models and selection

The protocol fixes 12 XGBoost, 12 LightGBM and six Random Forest candidates. The grids include the original three GBDT settings and original Random Forest setting, then broaden depth, tree count, regularization, feature subsampling, leaf size, and selected class-weight options. The complete parameter lists are in the JSON protocol. A broader grid can still lose on held-out data; no improvement is presumed.

Every family uses three-fold stratified training CV with the same seed and support. Median imputation is refitted inside each training fold, retaining empty columns. Candidate selection uses mean validation macro-F1 only. Ties use protocol order. The final selected model and imputer are fitted on all selected support rows.

The primary GBDT family is selected by its training-CV score, with a tie going to XGBoost. A secondary best-tree comparator includes Random Forest and uses the same CV-only rule. All family and candidate scores are retained. Neither family selection nor hyperparameter tuning reads test outcomes. There is no threshold tuning or early stopping on test/calibration data.

## Evaluation

Predict every one of the original 30,787 development-test rows in its original order, in chunks of 1,024. Save row indices, fingerprints, class order, true labels, probabilities, training support, imputer statistics, per-stage precision/recall/F1, full confusion matrix, macro-F1, one-vs-rest ROC-AUC and AP, and tuning/fit/prediction time. Calibration is unused in this follow-up.

Compare to original TabICL only after checking matching data, seed, support, class order and exact query roster. A full-test comparison requires full-test TabICL predictions. An earlier CPU-prescreen comparison would require restricting saved tree predictions to its exact sampled roster and using the same prespecified weights; never subtract a full-test tree score from a sampled, weighted TabICL estimate and call that an equal-query comparison. A separate comparison auditor handles this matching.

The separate comparison auditor reuses the original E1 gate: all ten full-query seed pairs, mean TabICL minus wider-CV-selected GBDT macro-F1 at least 0.02, and mean recall differences at least -0.05 for both InitialCompromise and DataExfiltration. Both GBDT families must be complete for each eligible primary pair. Random Forest outcomes are mandatory for complete batch reporting. The abundant-benign challenge is descriptive and cannot produce an equal-budget candidate-win verdict.

The runner reports tree outcomes and CV choices without issuing a foundation success verdict. Paired gains and high-risk-stage recall changes remain descriptive because the ten training seeds share one test set and fitting pool. There is no independent-seed confidence interval, incident/temporal generalization, early-warning, actor-attribution or novelty claim. In particular, InitialCompromise has only 15 test examples.

## Reproducibility and failure handling

The private `PREFIT_RECEIPT.json` is written before fitting and binds protocol, input, source hashes, package versions, exact training supports, inner-fold positions and complete query roster. Each cell has a start receipt, prediction artifact, metadata and completion hashes. Resuming verifies completed files and their bindings; nonempty incomplete cells are preserved and rejected. Use a new output directory for a failed partial run. Model/condition subsets have distinct execution bindings; their cells can be compared only after independent validation.

The default CPU setting is four threads, with sequential CV folds. This tree-only timing is not a same-device foundation throughput claim. Dependencies are pinned in `requirements_strong_baselines.txt`; actual versions are recorded in each run.

## Command after the root freeze

```powershell
python -m experiments.apt_benchmark.tabular_followup.run_strong_baselines `
  --data C:/w/apt_benchmark_data_20260920/tabular_batch_v1/scvic_prepared `
  --protocol experiments/apt_benchmark/tabular_followup/protocol_strong_baselines.json `
  --output C:/w/apt_benchmark_data_20260920/tabular_followup_v1/strong_baselines
```

`--prepare-only` performs hash, support and query checks and records the prefit receipt without fitting. The runner rejects the draft protocol until its status is `FROZEN_BEFORE_FOLLOWUP_MODEL_FITS`. Private output contains dataset-derived rosters and probabilities; publish only reviewed aggregates.
