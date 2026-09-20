# Can better normal examples prevent false alerts when relationships disappear?

This development experiment tests whether a detector mistakes missing information for malicious behavior. It compares three fixed ways to choose normal examples and calibrate alert scores, then reaches a go/no-go decision for that candidate family. No outcome is asserted here.

## What changes

| Strategy | Normal reference examples | Calibration examples |
| --- | --- | --- |
| Clean baseline | Clean graphs | Clean graph |
| Pooled calibration | Same clean reference | Clean and 50%-masked views |
| Pooled reference and calibration | Half clean, half masked; same total budget | Clean and 50%-masked views |

All strategies share sampled source rows and an 8,192-row budget. They use exact k=10 nearest-neighbor scoring of either local features, MLP embeddings, or GIN embeddings. New MLP/GIN models are trained from scratch; no author checkpoints or prior experiment weights are loaded.

For each dataset, four fixed folds rotate two normal graph files for fitting, one for calibration, and one for normal validation. Three encoder seeds cross three independent reference-bank seeds. Every candidate is evaluated on clean and 50%-masked graphs. Local features repeat identically across encoder seeds, and those duplicates do not add evidence.

The runner completes all normal fitting and calibration on both datasets and writes a global freeze before loading test0 labels. Normal-validation results never select a model or change a setting. It then replays every fixed candidate on the previously examined attack-bearing graphs, including candidates that failed normal validation.

The operative specification is [PROTOCOL.md](PROTOCOL.md), with exact settings in [config.json](config.json), historical values in [PINNED_BASELINES.json](PINNED_BASELINES.json), and independent design review in [PROTOCOL_REVIEW.md](PROTOCOL_REVIEW.md).

## How the study finishes

A candidate is ready for further development only when it satisfies both requirements in **every fold, seed pair, and clean/masked condition**:

- Held-out normal false-positive rate <=2%.
- Attack replay recall >=50% and benchmark-negative false-positive rate <=2%.

A general result requires the **same representation and strategy on both datasets**. A positive repair result additionally requires the registered F1 improvements over the historical comparator and the strongest current clean-reference comparator. A useful clean baseline does not itself prove that augmentation helps.

If no candidate passes, close this fixed repair family as unsupported under the tested settings. No optional checker, changed threshold, chosen seed, or new architecture is added to rescue it. An interrupted run is incomplete evidence. A successful development screen still does not establish novelty, independent confirmation, APT actor identification, or deployment readiness.

## Execution

Run commands from the repository root. First run the synthetic tests:

```powershell
& 'C:/w/cti_checker_env_20260918/Scripts/python.exe' -m unittest discover -s tests -p 'test_apt_*stability*.py' -v
```

Before real execution, commit the exact source, protocol, config, review, and pinned baselines. Registration binds these files, imported scientific/cloud modules, the data manifest, and every normalized NPZ file:

```powershell
& 'C:/w/cti_checker_env_20260918/Scripts/python.exe' -m experiments.apt_final.normal_stability.provenance register --config experiments/apt_final/normal_stability/config.json --data-dir C:/w/apt_native_graph_20260920/data --registration experiments/apt_final/normal_stability/REGISTRATION.json
```

Commit the resulting registration before the cloud launch; the existing controller requires the protocol and registration to match committed bytes. Registration refuses to overwrite an existing receipt.

Create a **new private attempt directory**, for example `C:/w/apt_stability_20260920/cloud_attempt1`. Copy the previous private settings from `C:/w/apt_embedding_20260920/cloud_attempt1/settings.json` into its `settings.json`, preserving the approved profile, region, account, instance, bucket, stop role, and price record. Change only `prefix` to a unique normal-stability attempt prefix, such as `apt-normal-stability-20260920/<unique-attempt>/`. Preserve the trailing slash. Write valid UTF-8 JSON without a byte-order mark. Do not copy old execution receipts or reuse an old S3 prefix.

```powershell
& 'C:/w/cti_checker_env_20260918/Scripts/python.exe' -m experiments.apt_final.normal_stability.launch --settings C:/w/apt_stability_20260920/cloud_attempt1/settings.json --data-dir C:/w/apt_native_graph_20260920/data --registration experiments/apt_final/normal_stability/REGISTRATION.json
```

The launch bundles registered source and audited data only. It calls the CUDA runner once for both datasets through the worker. Neural training/extraction uses the GPU; exact nearest-neighbor search uses the CPU. The reused controller enforces a one-hour host cap, a $10 reserve, an independent stop schedule, and verified shutdown. Collection rejects archives exceeding 4 GB or 2,000 members.

This is substantially larger than the previous scoring diagnostic: 24 encoder-folds, 48 trained models, 240 graph-view caches, and 72 reference-bank cases. A static layout estimate is about 1,565 archive members; file sizes and actual runtime must be measured. Runtime may approach the scientific worker allowance. If interrupted, preserve the partial artifacts and stop the host; an explicitly frozen runtime-only continuation may reuse verified completed artifacts with the same scientific settings and full candidate inventory. The initial runner does not automatically resume an existing output directory.

## Evidence to inspect

- `NORMAL_RESULTS.json` and `NORMAL_FREEZE.json`: completed normal results and hashes fixed before test-label access.
- `RESULTS.json`: all normal and attack records, duplicate accounting, and the final fixed-family gates.
- `RUN_STATUS.json`, partial result files, and `WORKER_STATUS.json`: completion or interruption status.
- Private fold caches, weights, reference states, row selections, and scores: independently auditable numeric evidence; retain outside public Git.
- Private `EXECUTION.json` and controller receipts: transport, timing, and verified cloud shutdown.

The supplied normal designation is an upstream assumption, and unannotated test entities are not exhaustively verified benign. Source UUIDs and times are missing; separate graph files and repeated folds cannot establish independent entities or campaigns. Public results should retain these limits and use the phrase **annotated malicious entities**.
