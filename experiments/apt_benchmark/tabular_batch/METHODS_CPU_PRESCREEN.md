# Separate CPU plausibility screen

This explicitly scoped development screen follows the completed classical E1 runs. AWS sign-in remained unavailable and a full ten-seed foundation run on CPU was estimated at roughly ten hours. The rescope is frozen **after classical scores were known and before foundation classification outcomes**. It neither replaces nor completes E1, and it performs no calibration or E4 analysis.

## Fixed design

- Use the first three E1 seeds, 20260921–20260923, with their identical 192-row fit supports: 32 examples per stage.
- Include every attack row from the original development test partition: 858 records, including 15 InitialCompromise and 106 DataExfiltration records.
- Include 1,024 of the 29,929 NormalTraffic test records, chosen by SHA256 of `E1_CPU_PRESCREEN_20260921|fingerprint`. Hash-order the combined 1,882-row query as well. Reuse the identical query for all three seeds and all models.
- TabICLv2 is the primary candidate; synthetic-only TabPFN 2.5 is secondary regardless of its results. Each uses its explicit verified checkpoint, four ensemble members, CPU intra-operation thread budget four, inter-operation threads two, and prediction chunks of 1,024. Fit median imputation solely on the selected training support, keeping empty columns.
- Reuse the exact query rows from completed RF, XGBoost and LightGBM E1 prediction artifacts. Verify input, protocol, source, fit-support, class-order and file hashes; do not refit those baselines. Select the GBDT comparator using the original inner-CV scores for each seed, with ties to XGBoost.

## What the scores mean

Report raw query precision, recall, F1, confusion matrices, one-versus-rest ROC-AUC and average precision for all five model families. This query is enriched to approximately 45.6% attack rows, so its unweighted precision/F1 does not represent the original development-test prevalence.

Also weight each attack row by one and each sampled NormalTraffic row by `29929/1024`. The weighted confusion matrix represents 30,787 rows. From it and the weighted ranking scores report **prevalence-adjusted estimated scores for this prescreen execution**. These nonlinear plug-in metrics are not unbiased F1 estimates or actual full-E1 scores. Foundation predictions may depend on query batching; invariance to the full E1 query composition has not been established.

Report sampled benign false-positive counts alongside their weighted estimates. One sampled benign error represents approximately 29.23 original-test rows. Zero observed false positives in the sample does not establish zero false positives in all 29,929 NormalTraffic rows. Because every fitting seed reuses the same sampled normal rows, agreement across seeds does not remove this sampling uncertainty.

For each baseline and seed, publish its existing full-test macro-F1 beside the prevalence-adjusted estimated macro-F1 and the difference. This is a representativeness diagnostic, not permission to change the query or candidate after seeing outcomes.

## Prespecified preliminary decision

All three paired primary comparisons are required. Classify the screen as `PRELIMINARY_PROMISING` only if TabICL's mean paired prevalence-adjusted estimated macro-F1 gain over the inner-CV-selected GBDT is at least 0.02 and its mean recall loss is at most 0.05 for each of InitialCompromise and DataExfiltration. Otherwise report `PRELIMINARY_NEGATIVE`; missing pairs remain `INCOMPLETE`.

Those high-risk recalls cover all corresponding attack rows **for this query execution**. No label weighting changes their denominators. Three fitting seeds share the same data, so report no significance test or confidence interval. The preliminary label is never a full E1 pass, confirmation of novelty, or evidence of chronological/incident generalization. Full-query evaluation and E4 remain pending.

## Execution and artifacts

[protocol_e1_cpu_prescreen.json](protocol_e1_cpu_prescreen.json) must be frozen by the root before fitting. [run_e1_cpu_prescreen.py](run_e1_cpu_prescreen.py) records exact supports, query rows, weights, input/protocol/source/environment/checkpoint hashes, and verified baseline artifact hashes in a prefit receipt. Private prediction packets preserve all probabilities. Only hash-verified completed cells may be resumed; partial evidence is preserved and rejected. `AGGREGATE.json` contains public-safe metrics and scope limitations, while individual rows, probabilities, fingerprints and cache paths stay private.

```powershell
python -m experiments.apt_benchmark.tabular_batch.run_e1_cpu_prescreen `
  --data PRIVATE_PREPARED_DATA_DIRECTORY `
  --protocol experiments/apt_benchmark/tabular_batch/protocol_e1_cpu_prescreen.json `
  --e1-protocol experiments/apt_benchmark/tabular_batch/protocol.json `
  --baselines PRIVATE_COMPLETED_E1_CPU_RUN `
  --output PRIVATE_FRESH_PRESCREEN_OUTPUT `
  --model-cache PRIVATE_VERIFIED_MODEL_CACHE
```
