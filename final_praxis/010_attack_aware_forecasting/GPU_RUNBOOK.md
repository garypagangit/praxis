# Root-operated bounded GPU qualification

Prerequisites: review QUALIFICATION_PROTOCOL.md, PROTOCOL_FREEZE.json, SOURCE_AUDIT.md and RUNTIME_FREEZE.json; no HAI heldout efficacy. Root owns AWS, external stop, receipts, and the shared two-hour/$25 ceiling. Run each mode in a fresh process, sequentially. One A10G24GiB/16GiB host is the intended backend. Estimated combined weight download 2.44GB; measured runtime/peak memory remain pending.

The bundle contains our harness and compact manifests only. All public source/data/weights are fetched into CACHE outside Git. Preparation downloads public fixed URLs; inference must run offline without cloud credentials/network access. No model training or paid inference API.

```bash
python3.11 -m venv /external/010-venv
/external/010-venv/bin/pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
/external/010-venv/bin/pip install -r /source/010/code/requirements-gpu.txt
/external/010-venv/bin/python /source/010/code/prepare_assets.py --cache /external/010-assets --models
```

The source package is imported directly from the verified official ZIP extraction; no editable install is needed. The pinned CUDA wheel needs a compatible host driver. If that fails, report the compatibility block before substituting a runtime version. No silent fallback to a different model or reduced cohort.

Use the equivalent environment inside the root-managed GPU container or isolated runtime:

```bash
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 TORCHINDUCTOR_COMPILE_THREADS=1
python /source/010/code/test_runtime_controls.py --cache /external/010-assets --output /results/010/RUNTIME_CONTROLS_CLOUD.json
timeout 1500 python /source/010/code/gpu_qualification.py --mode new3 --cache /external/010-assets --output /results/010/new3
timeout 2400 python /source/010/code/gpu_qualification.py --mode original25 --cache /external/010-assets --output /results/010/original25
timeout 2400 python /source/010/code/gpu_qualification.py --mode calibration --cache /external/010-assets --output /results/010/calibration
```

These per-process caps are subordinate to the shared host deadline; root must not extend the shared reservation merely to run all maxima. Actual completion exit status and stderr must be retained. A timeout/exception yields HOLD/PENDING, never an omitted successful run. `new3` yields finite/deterministic forecast checks, repeated latency, measured peak memory and one fixed development step probe. `original25` preserves 20 historical trials and runs three distinct deployable comparisons on the same 20 trials. `calibration` runs the entire4031-row selected NAB series, preserves train boundary1007, and evaluates a fixed0.01 p-value threshold.

Each success writes QUALIFICATION_RECEIPT.json plus complete compact raw artifacts. Download those receipts/raw rows for independent accounting. Do not describe the optional new-model step result as a tested defense: Q1 does not implement the candidate trust-partitioned modification.
