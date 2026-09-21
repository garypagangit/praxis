# CPU latency feasibility for a two-stage classifier

This is a bounded prerequisite test for attachment E2. It does not run a full cascade, evaluate held-out detection quality, or establish GPU performance. The literature and proposed architecture are documented in [LITERATURE_FOUNDATION.md](LITERATURE_FOUNDATION.md).

## Question

Can the proposed binary TabPFN screen execute quickly enough to leave room for a fivefold throughput improvement over a full stage classifier on the same CPU?

For a serial cascade processing a fixed batch, the full pipeline must pay the screening cost before any detailed classification of flagged records. Ignoring all later work gives an optimistic cost floor. Thus the screen alone must take no more than one fifth of the full stage model's time. We test this necessary condition; passing would still require a complete quality/throughput evaluation.

## Frozen inputs and selection

- Same prepared SCVIC data and manifest bytes as E1, linked by hashes.
- E1 seed 20260921 selects 32 fit examples from each of six stages, totaling 192. No additional fitting labels are introduced.
- Three-fold stratified CV selects settings for XGBoost and LightGBM using the existing three-candidate grids. Median imputation is refitted inside each CV fold. The higher mean inner-CV macro-F1 chooses the stage comparator; ties choose XGBoost. Query labels do not select models.
- The binary screen uses the same 192 records: 32 NormalTraffic examples and 160 examples across the five attack stages. It uses the pinned synthetic-only TabPFN 2.5 checkpoint and four ensemble members.
- A single median imputer is fitted on the selected 192 records and used by both final models. Empty columns are retained.
- The timing batch is the first 1,024 development-test fingerprints ordered by SHA256 of `seed|fingerprint`. Selection uses no query labels or predictions; no held-out quality metrics are computed.

## Timing procedure

The process uses four CPU intra-operation/native threads and two PyTorch inter-operation threads. The selected stage classifier receives `n_jobs=4`; inner CV keeps E1's `n_jobs=1` for identical model selection. CPU operations complete synchronously. AWS/GPU timing is outside this pilot.

The runner separately records context/model construction, preprocessing fit, CV and final fit time. Each final model performs one warmup prediction, followed by three measured predictions on the same batch. Measured pair order alternates: stage/screen, screen/stage, stage/screen. Every timed call includes `imputer.transform` and real `predict_proba`; saved probabilities are never timed as a replacement for inference. Ordinary fitted state and library caches remain in place, making this a warm-execution assessment. Thread limits and model settings are fixed before outcomes.

The primary comparison is median screen-alone time against median full-stage time divided by five. Also report all three durations and the optimistic speedup ceiling `median_stage_time / median_screen_time`. Three repeats characterize this run; they do not establish a statistical timing guarantee.

## Interpretation

- **Fail:** this CPU candidate fails the necessary speed condition for the proposed fivefold improvement at the frozen configuration. Adding routing and stage classification cannot repair this measured serial cost floor.
- **Pass:** screening is fast enough to justify a separately specified full cascade test. It says nothing about missed attacks, stage F1, or false alarms.

Both outcomes leave GPU execution, alternate model settings, batching, compression and the full quality frontier untested. We must not describe the pilot as completion of E2 or as rejection of every possible cascade.

## Artifacts and execution

[protocol_e2_latency.json](protocol_e2_latency.json) awaits the root's source/protocol freeze. Do not start scientific fits before that freeze. [run_e2_latency.py](run_e2_latency.py) writes a prefit receipt with input/code/support/query hashes before fitting, then private fit and probability artifacts. Any nonempty output directory is rejected so interrupted evidence is preserved. `AGGREGATE.json` is the public-safe timing summary; the raw probabilities and individual fingerprints remain private. `COMPLETE.json` binds final artifact hashes.

```powershell
python -m experiments.apt_benchmark.tabular_batch.run_e2_latency `
  --data C:/w/apt_benchmark_data_20260920/tabular_batch_v1/scvic_prepared `
  --protocol experiments/apt_benchmark/tabular_batch/protocol_e2_latency.json `
  --e1-protocol experiments/apt_benchmark/tabular_batch/protocol.json `
  --output PRIVATE_FRESH_OUTPUT_DIRECTORY `
  --model-cache PRIVATE_VERIFIED_MODEL_CACHE
```

Use the previously qualified foundation/baseline environment. The runner requires the verified checkpoint already cached and downloads no model during this pilot.
