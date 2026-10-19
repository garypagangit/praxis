# Runnable RQ1–RQ3 engineering test

This pipeline uses a **synthetic trial-level fixture**, not real attack telemetry. It exercises all three experiment paths and accepts a CSV with the same schema later. Its results cannot support the Praxis hypotheses. The first implementation uses fixed group-disjoint train/validation partitions and a small two-configuration search, rather than the final repeated/nested grouped protocol.

[Completed synthetic test report](synthetic_smoke_20261019_v2/REPORT.md) · [Validation evidence](VALIDATION.md)

## Run from this directory

Python 3.11+ is required. Create an isolated environment, install dependencies, then generate and run:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python experiment.py generate --output fixtures/synthetic_trials.csv
.venv/Scripts/python experiment.py validate --input fixtures/synthetic_trials.csv
.venv/Scripts/python -m pytest -q
.venv/Scripts/python experiment.py run --input fixtures/synthetic_trials.csv --output smoke_run_001
.venv/Scripts/python verify_run.py --input fixtures/synthetic_trials.csv --run smoke_run_001
```

The output directory must not exist. This prevents accidental overwrite of prior evidence. Use a fresh directory for each run. Outputs may contain imported labels/identifiers: retain real-data outputs in the restricted workspace, not public Git. Only the explicitly synthetic published smoke run is intended for this repository.

## What runs

| RQ | Implemented experiment | Outputs |
| --- | --- | --- |
| RQ1 | Random-forest reference; host-only/network-only/timing-only, each family removed, no-timing and reduced representations; validation family permutation and retrained ablations | `rq1_features.json`, `metrics.json` |
| RQ2 | Each classifier trained with full and reduced host/network-only features; known-group versus unseen-group trials; validation/unseen importance summaries | `rq2_transfer.json`, `predictions.csv` |
| RQ3 | Decision tree, random forest, XGBoost, RBF SVM and a small numerical-token transformer, plus logistic and dummy references; select primary on validation, then batch-score frozen candidates | `rq3_comparison.json`, `REPORT.md` |

Each primary candidate gets two configurations; dummy gets one. The transformer uses numeric feature tokens, a CLS token and one transformer encoder layer with fixed epoch budgets. It is **FT-style**, not an exact replication of published FT-Transformer. Published-baseline qualification remains required before final research runs. Feature preprocessing is imputation and scaling fitted on the training partition for each candidate.

All final evaluations happen after `selection_freeze.json` is written. The code does not tune from final test labels. Feature importance on unseen data is post-evaluation descriptive analysis only. Predictions are hard class decisions; probability calibration is not implemented. H1/H2/H3 dispositions remain pending because practical margins and confirmatory procedures are not frozen.

Class-stratified group bootstrap intervals preserve groups and pair predictions for same-trial comparisons. They are descriptive, unadjusted intervals, not multiplicity-corrected hypothesis decisions. With few groups they can be unreliable. The transfer gap compares different known/unseen populations and is not a pure measure of overfitting. Flat or tied importance makes top-family agreement uninformative.

## Import contract

One CSV row = **one trial**, with all windows already aggregated by the approved rule. UTF-8, comma-separated, header required. No additional columns are accepted. The generated fixture is a complete example.

Start with the [empty import template](import_template.csv), or inspect the [generated synthetic fixture](fixtures/synthetic_trials.csv) for a populated example. Keep genuine imported data outside this public repository.

| Metadata column | Meaning |
| --- | --- |
| `trial_id` | Unique opaque execution ID; never a predictor |
| `group_id` | Human operator or AI configuration grouping ID, consistently assigned across its trials |
| `arm` | `human`, `autonomous_ai`, `scripted_control`, or `benign` |
| `partition` | `train`, `validation`, `test_seen`, `test_unseen`, or `control` |
| `source_id` | Collection source/protocol identity; every primary source must contain both arms in this harness |
| `dataset_kind` | All rows `synthetic` or all rows `real`; mixing is rejected |

Numeric columns are explicitly listed in [feature_spec.json](feature_spec.json): host behavior, network behavior, timing and tool-derived families. Missing numeric values are allowed and imputed using training medians; an entirely missing training feature is rejected. Infinite values are rejected. Synthetic values are dimensionless test values and do not define real measurement units.

**Before real import:** implement and validate extraction of each feature from target-side logs, with definitions/units in the feature dictionary. Do not simply rename unrelated flow columns to these fields. If the approved schema changes, version `feature_spec.json` and the validation code together, regenerate fixtures and rerun tests. The current schema is a prototype interface, not a frozen scientific feature specification.

```powershell
.venv/Scripts/python experiment.py validate --input C:/restricted/validated_trials.csv
.venv/Scripts/python experiment.py run --input C:/restricted/validated_trials.csv --output C:/restricted/run_001 --allow-real
```

`--allow-real` acknowledges that imported data will be processed; it does not certify the dataset, preregistration or ethics/collection gates. Imported runs remain exploratory in this version.

The same trial cannot appear twice. Validation groups are disjoint from training and both test partitions. Unseen test groups are absent from train/validation/known-group test. Known-group test contains **new trials** from training groups and therefore is explicitly a known-operator reference. At least two groups per class per partition are required by the bootstrap implementation; this minimum is not a sample-size recommendation. Family/scaffold transfer needs a broader grouping ID or separate prespecified manifests; configuration holdout alone does not prove it.

Controls never receive human/AI ground-truth labels in the exported predictions. Inspect their predicted-AI rates separately. Exact duplicate feature vectors trigger an audit error; if legitimately identical real trials exist, resolve them under a documented protocol rather than adding noise to bypass the check.

## Why no COCHISE + APT pairing was used

Local inspection found COCHISE controller command/output logs and DAPT2020 flow CSVs. The DAPT header contains network-flow statistics and `Activity`/`Stage`, not verified human/AI controller labels. The modalities do not provide a shared defender-observable feature table. Pairing them would require invented features/labels or a source-confounded comparison. The [dataset review](../../../PRAXIS_DATASET_EVALUATION.md) explains the broader limitation.

The synthetic generator deliberately introduces stable behavioral signal, an easier timing/tool cue, a shift in that cue on unseen groups, correlated group effects, missing observations and separate controls. These are code-testing choices, not empirical claims about humans or AI. It creates 440 rows: 176 training, 56 validation, 48 known-group test, 112 unseen-group test and 48 controls.

## Remaining before the final study

- Qualified telemetry extraction and matching/label audit.
- Adequate independent sample/group counts and frozen practical margins.
- Repeated/nested grouped evaluation, predeclared seeds and fair scientific tuning budgets.
- Exact transformer baseline qualification and model artifact serialization.
- Family/scaffold-specific transfer manifests; uncertainty for transfer contrasts.
- Multiplicity correction, final hypothesis adjudication, probability calibration if claimed.
- Independent reproduction and restricted evidence integration.

`selection_freeze.json` records input/source/schema hashes, environment versions and all tuning outcomes. `artifact_manifest.json` hashes the output artifacts. Models are regenerated rather than serialized in this engineering version.

The repository preserves exact bytes under this pipeline directory so frozen hashes survive Git checkout. Generated runs on another platform may differ in serialization or numerical details; the included artifact verifier checks the committed run against its original inputs/source and recomputes its metrics.
