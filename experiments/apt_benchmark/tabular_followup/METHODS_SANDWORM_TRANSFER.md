# Source-only binary transfer to Sandworm

The transfer runner trains on SCVIC only. It evaluates the qualified Sandworm capture without fitting, calibrating, choosing a threshold, or choosing a model on Sandworm. The target has 2,091 unique feature rows: 2,054 normal and 37 attacks across five author procedure labels. The raw file contains 2,133 flows.

## Models and source labels

Each of the ten original seeds retains its exact original 192-row source support: 32 examples from each of the six SCVIC classes. Median imputation uses only that support. Original baseline receipt hashes, selected support identities and training-CV arithmetic are checked before transfer fitting. The tree comparator reuses the original E1 XGBoost/LightGBM CV winner and its selected hyperparameters; ties select XGBoost. It performs no new hyperparameter search. TabICL uses the unchanged pinned backend/checkpoint, four ensemble members and `n_jobs=1`. Both models receive the same source training rows.

## What is measured

The primary binary prediction is attack when the model's largest six-class probability belongs to a source class other than NormalTraffic. This is not the same rule as thresholding total attack probability at 0.5. ROC-AUC and average precision use the continuous score `1 - p(NormalTraffic)`.

The deduplicated query is primary. All unique rows are evaluated in ascending feature-fingerprint order, in 1,024-row chunks. Raw-flow sensitivity reweights those exact predictions with `raw_to_unique` multiplicities; it does not run a different duplicated query context. Reports retain TP/FP/TN/FN, binary macro-F1, attack precision/recall/F1, normal false-positive rate, ranking metrics and detected/missed counts for every original attack procedure.

The author procedure labels are mapped only to normal versus attack. No procedure is relabeled as a SCVIC stage. This is a single target capture with very few attack examples, including one procedure with a single flow. Report all seeds and descriptive ranges without interpreting them as independent campaigns, population confidence, early warning or actor identification. There is no newly selected pass gate.

The separately declared source 1% false-alert threshold diagnostic is not computed by this runner. It must reuse audited saved source-calibration predictions later, without choosing an operating point from target outcomes.

## Provenance and execution

The prefit receipt binds input/manifest/protocol hashes, original baseline evidence, exact source supports, target query order, model checkpoint, source-code hashes and versions before fitting. Each cell stores source-only imputation statistics and all target probabilities with completion hashes. Completed cells can resume only with identical bindings. Nonempty partial cells remain preserved and rejected.

Root must freeze the draft protocol and code before running:

```powershell
python -m experiments.apt_benchmark.tabular_followup.run_sandworm_transfer `
  --source-data C:/w/apt_benchmark_data_20260920/tabular_batch_v1/scvic_prepared `
  --target-data C:/w/apt_benchmark_data_20260920/tabular_followup_v1/sandworm_prepared_v3 `
  --protocol experiments/apt_benchmark/tabular_followup/protocol_sandworm_transfer.json `
  --e1-protocol experiments/apt_benchmark/tabular_batch/protocol.json `
  --source-baselines C:/w/apt_benchmark_data_20260920/tabular_batch_v1/e1_cpu_run1 `
  --model-cache C:/w/apt_benchmark_data_20260920/tabular_batch_v1/model_cache `
  --output C:/w/apt_benchmark_data_20260920/tabular_followup_v1/sandworm_transfer
```

`--prepare-only` verifies and records input/support/provenance without fitting. `--models selected_gbdt` or `--models tabicl_v2` can isolate an immutable execution; use separate output roots. Full completion requires all twenty registered cells. Original/derived datasets, row rosters, probability artifacts and cache paths stay private; public reporting must extract aggregate metrics and provenance hashes.
