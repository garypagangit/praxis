# Bounded AWS preparation and execution

The worker runs only E1's two foundation-model arms. It uses the existing GPU host and the unchanged [cloud controller](../../apt_final/native_graph/cloud_control.py). No new infrastructure is provisioned. The controller keeps its 60-minute total cap, minute-56 stop watchdog and minute-52 worker deadline. A shorter SSM command deadline is honored as well.

`build_cloud_bundle.py` is entirely offline. It allowlists prepared `DATA.npz` and `MANIFEST.json`, seven runtime/protocol files, and the two checksum-pinned public checkpoints. It excludes raw CSVs, account settings, credential stores and prior runs. Its generated `RUNTIME_FREEZE.json` is suitable for copying into the repository and committing after reviewing the exact runtime. The bundle and account settings stay private.

## Local preparation

1. Commit the runtime/protocol files after checks. The builder normally refuses uncommitted runtime bytes. `--allow-uncommitted` makes a provisional bundle with `launch_eligible=false`; it cannot render a launch script.
2. Build using the existing private prepared-data and model-cache directories:

```powershell
python experiments/apt_benchmark/tabular_batch/build_cloud_bundle.py `
  --repo C:/w/apt_benchmark_20260920 `
  --prepared C:/w/apt_benchmark_data_20260920/tabular_batch_v1/scvic_prepared `
  --model-cache C:/w/apt_benchmark_data_20260920/tabular_batch_v1/model_cache `
  --output C:/w/apt_benchmark_data_20260920/tabular_batch_v1/cloud_attempt1 `
  --settings-source C:/w/apt_embedding_20260920/cloud_attempt1/settings.json
```

3. Copy the generated sanitized runtime freeze to this directory and commit it alongside the unchanged protocol. Account settings must remain outside Git. The source controller independently requires the selected protocol and freeze bytes to equal Git HEAD before it can start the existing host.

## Execution through the existing controller

Use `experiments/apt_final/native_graph/cloud_control.py` with the private `cloud_attempt1/settings.json`. After AWS sign-in and qualification:

- Upload `bundle.tar.gz` into this attempt's private prefix using the controller's `upload` action.
- Call `start` with the committed protocol and runtime freeze. Observe the designated host state and SSM readiness using `status`.
- Render the bootstrap **after** a successful start:

```powershell
python experiments/apt_benchmark/tabular_batch/build_cloud_bundle.py `
  --repo C:/w/apt_benchmark_20260920 `
  --output C:/w/apt_benchmark_data_20260920/tabular_batch_v1/cloud_attempt1 `
  --render-bootstrap
```

- Read private `SEND_PLAN.json`; call controller `send` with `bootstrap.sh` and its computed timeout. Poll the returned command ID. The renderer invokes no AWS action itself.
- Download the result archive and its SHA256 from the private keys recorded in `SEND_PLAN.json`. Verify the hash and safely extract locally. Retain incomplete cells and worker exit status.
- Request `stop` promptly when work finishes or fails. Call `finalize` until the host is freshly observed stopped; the controller then removes only this run's watchdog.

## Worker behavior and qualification limits

The worker validates bundle and member hashes, rejects tar traversal/links/duplicates, and creates a separate per-run environment. It reads an existing CUDA installation; matching Torch 2.5.1 can be reused. Otherwise its pinned cu121 installation is time bounded. Both requirements files pin top-level packages; the worker preserves the resolved `pip freeze` and actual Python version. Python >=3.10 is accepted. Source, checkpoint, data, split and protocol identity must still match the CPU run.

The GPU probe verifies package versions, both checkpoint hashes and a CUDA tensor calculation; it fits no classifier. CPU thread settings are limited to four. The model worker explicitly requests CUDA, retaining full prefit and per-cell prediction receipts in private output. A timeout preserves complete and partial outputs with the exit status rather than reporting the missing cells as successes.

The final 150 seconds of the effective worker deadline are reserved for packaging and upload. Logging and publication also have explicit timeouts. Setup and model work fail closed if insufficient time remains. The external watchdog remains essential if the guest process fails.

Combining these GPU outcomes with matching CPU controls is a model-performance comparison. Timings obtained on different hardware cannot establish E2's claimed throughput improvement. This preparation does not show that all twenty requested foundation cells will finish inside the single bounded attempt.
