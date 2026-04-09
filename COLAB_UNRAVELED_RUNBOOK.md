# Colab Runbook For Unraveled Next Steps

This runbook is the fastest path to using Colab GPU compute for the next experiments.

## What To Run Next, In Order

1. Run the proper `Mamba` budget on the same stage-balanced split.
2. Run the graph `chunk128` experiment to test the graph minority-dilution hypothesis.
3. Run the graph `DE-weighted` experiment to test whether explicit `Data Exfiltration` loss amplification recovers DE.
4. After those three are done, decide whether to move on to `APT-MAMBA`, `KC-CWT`, and the monotonic kill-chain penalty.

## Config Files

- Proper Mamba run:
  [`configs/praxisv03-unraveled-colab-mamba-proper.json`](C:/Users/garyp/OneDrive/Documents/codex/configs/praxisv03-unraveled-colab-mamba-proper.json)
- Graph chunk fix:
  [`configs/praxisv03-unraveled-colab-graph-chunk128.json`](C:/Users/garyp/OneDrive/Documents/codex/configs/praxisv03-unraveled-colab-graph-chunk128.json)
- Graph DE-weight fix:
  [`configs/praxisv03-unraveled-colab-graph-de-weighted.json`](C:/Users/garyp/OneDrive/Documents/codex/configs/praxisv03-unraveled-colab-graph-de-weighted.json)

## One-Time Drive Layout

Place the Unraveled network-flow CSV tree here in Google Drive:

```text
/content/drive/MyDrive/praxis/data/unraveled/network-flows
```

The configs already expect these Drive-backed locations:

```text
/content/drive/MyDrive/praxis/data/unraveled/network-flows
/content/drive/MyDrive/praxis/cache/unraveled_v03
/content/drive/MyDrive/praxis/runs
```

## Colab Runtime

Use a GPU runtime. Prefer:

- `A100` if available
- otherwise `T4`

In Colab:

1. `Runtime`
2. `Change runtime type`
3. Set `Hardware accelerator` to `GPU`

## Setup Cell

Run this in a fresh Colab notebook:

```python
REPO_URL = "https://github.com/garypagangit/praxis.git"
BRANCH = "main"
WORKSPACE_DIR = "/content/praxis-workspace"
DRIVE_ROOT = "/content/drive/MyDrive/praxis"
```

```python
from google.colab import drive
drive.mount("/content/drive")
```

```python
import os
import subprocess
import sys
from pathlib import Path

workspace = Path(WORKSPACE_DIR)
if workspace.exists() and (workspace / ".git").exists():
    subprocess.run(["git", "fetch", "origin", BRANCH], cwd=workspace, check=True)
    subprocess.run(["git", "checkout", BRANCH], cwd=workspace, check=True)
    subprocess.run(["git", "pull", "--ff-only", "origin", BRANCH], cwd=workspace, check=True)
else:
    if workspace.exists():
        raise RuntimeError(f"{workspace} exists but is not a git repo. Remove it first.")
    subprocess.run(["git", "clone", "--branch", BRANCH, REPO_URL, str(workspace)], check=True)

subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(workspace / "requirements.txt")], check=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(workspace)], check=True)

os.chdir(workspace)
print("Workspace:", workspace)
```

```python
from praxis.colab_bootstrap import configure_persistent_runtime

runtime_paths = configure_persistent_runtime(DRIVE_ROOT)
runtime_paths
```

## Verify GPU And Data

```python
import torch
from pathlib import Path

print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))

data_dir = Path("/content/drive/MyDrive/praxis/data/unraveled/network-flows")
print("Data dir exists:", data_dir.exists())
print("Sample contents:", sorted(p.name for p in list(data_dir.iterdir())[:5]))
```

If `CUDA available` is `False`, stop and fix the Colab runtime before training.

## Exact Commands To Execute

Change into the repo workspace first:

```python
%cd /content/praxis-workspace
```

### 1. Proper Mamba Run

This is the immediate priority. It uses the same stage-balanced split, `25` Optuna trials, and `60` epochs.

```python
!python -m praxis.train --config configs/praxisv03-unraveled-colab-mamba-proper.json
```

Expected output folder:

```text
/content/drive/MyDrive/praxis/runs/praxisv03-unraveled-stage-balanced-colab-mamba-proper
```

### 2. Graph Chunk Fix Run

This reduces `flows_per_graph` from `512` to `128`.

```python
!python -m praxis.train --config configs/praxisv03-unraveled-colab-graph-chunk128.json
```

Expected output folder:

```text
/content/drive/MyDrive/praxis/runs/praxisv03-unraveled-stage-balanced-colab-graph-chunk128
```

### 3. Graph DE-Weighted Run

This keeps `512`-flow chunks but boosts `Data Exfiltration` loss weight.

```python
!python -m praxis.train --config configs/praxisv03-unraveled-colab-graph-de-weighted.json
```

Expected output folder:

```text
/content/drive/MyDrive/praxis/runs/praxisv03-unraveled-stage-balanced-colab-graph-de-weighted
```

## Resume Behavior

All three configs have:

```text
"resume_existing_results": true
```

That means rerunning the same command is safe after a Colab disconnect. The run will reuse already-written model result files in the same run folder and continue with what is missing.

## Quick Review Commands

After a run finishes:

```python
from pathlib import Path
import json

run_dir = Path("/content/drive/MyDrive/praxis/runs/praxisv03-unraveled-stage-balanced-colab-mamba-proper")
summary = json.loads((run_dir / "results-summary.json").read_text())
summary["completed_at_utc"], summary["run_name"]
```

```python
print((run_dir / "metrics-table.csv").read_text())
```

```python
print((run_dir / "per-class-metrics.csv").read_text())
```

## Interpretation Goal

What you want to learn from these three runs:

- `Mamba proper budget`:
  Does `Data Exfiltration` recover when Mamba is actually trained seriously on the same split?
- `Chunk128`:
  Does making graphs smaller recover graph-model `Data Exfiltration` without changing architecture?
- `DE-weighted`:
  Does explicitly amplifying `Data Exfiltration` loss recover DE while keeping the original graph chunk size?

## Practical Notes

- `Mamba` is the highest-priority Colab run. Do it first.
- If Colab memory is tight on `T4`, reduce `sequence_batch_size` from `16` to `8` in the Mamba config.
- If graph runs are too slow, remove `ST-GCN` from `enabled_models` first. It was the weakest and most runtime-expensive local graph baseline.
- Keep artifacts on Drive. Do not rely on Colab local disk for anything you want to keep.
