# Praxis 05 Phase A Status

Status: local Phase A runway complete; full pre-registered Phase A not yet run.

## Bottom Line

Praxis 5 is a good Praxis experiment if it is kept in its current kill-switch framing. It is novel enough to be interesting, reproducible enough to execute, and risky enough that an honest negative result would still be useful.

The local run produced a serious early warning: a reduced real SAELens TopK SAE pilot on real MAGIC CADETS activations reconstructs extremely well and passes seed-stability, but leaves roughly 90% of features dead. That does not formally falsify the pre-registered Phase A, because the local pilot used fewer features and fewer steps than the frozen Phase A config. It does mean we should not proceed to Phase B until either the full GPU Phase A passes or the one allowed PIDSMaker pivot is run.

## External Code Pinned

- MAGIC clone: `external/MAGIC`
- MAGIC commit: `aa0b647eea74b6faa0e52eb444370c4411a32cbe`
- PIDSMaker clone: `external/PIDSMaker`
- PIDSMaker commit: `216df3aaf76224c0a9311e66ae2110fd8d3730d7`

## MAGIC Reproduction Gate

MAGIC quick evaluation ran locally on the bundled preprocessed CADETS graphs and checkpoint.

Command:

```powershell
cd external\MAGIC
tar -xf data\cadets\graphs.zip -C data\cadets
..\..\.venv\Scripts\python.exe eval.py --dataset cadets --device -1
```

Observed output:

- AUC: `0.9977379100520937`
- F1: `0.9701373902123143`
- Precision: `0.9440883977900553`
- Recall: `0.9976646426903316`
- TP / FP / TN / FN: `12816 / 759 / 343568 / 30`

Key implementation finding: upstream MAGIC uses `num_hidden = 64` for DARPA TC entity-level datasets (`cadets`, `theia`, `trace`), not 256. PIDSMaker's `config/magic.yml` also sets `node_hid_dim: 64`. That makes the SAE problem harder than the original draft assumed.

## Activation Cache

Real MAGIC CADETS train activations were extracted by hooking `encoder.gats.2`.

Command:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe scripts\praxis05_03_extract_activations.py `
  --magic-root external\MAGIC `
  --dataset cadets `
  --split train `
  --output-dir runs\praxis05-phase-a\activation_cache_cadets_train `
  --device -1
```

Cache summary:

- Rows: `1,269,862`
- Hidden dim: `64`
- Finite: `true`
- Standard deviation: `0.424409419298172`
- Nonzero fraction: `1.000000238418579`
- Manifest: `runs/praxis05-phase-a/activation_cache_cadets_train/manifest.json`
- Activation SHA-256: `2322a5d77c91cb97bc3d8d423d827f1f96e8618ef65ca0e9b19274408dc637d8`

## Real SAELens Backend

The repo venv installed SAELens but hit a OneDrive/metadata import issue. A clean Praxis 5-only venv outside OneDrive works:

```powershell
python -m venv $env:USERPROFILE\.venvs\praxis05
& "$env:USERPROFILE\.venvs\praxis05\Scripts\python.exe" -m pip install sae-lens==6.43.0 PyYAML==6.0.3
```

Verified:

- Python: `3.11`
- Torch: `2.11.0+cpu`
- SAELens: `6.43.0`

## Local Real-Backend Pilot

This pilot used the real SAELens backend on real MAGIC activations, but it is smaller than the pre-registered run:

- Config: `configs/praxis05-phase-a-local-real-pilot.json`
- Backend: `saelens`
- Features: `1024`
- `k`: `32`
- Steps: `1000`
- Train vectors per seed: `20,000`
- Seeds: `[13, 42, 137, 271, 1729]`

Command:

```powershell
$env:PYTHONPATH='src'
& "$env:USERPROFILE\.venvs\praxis05\Scripts\python.exe" scripts\praxis05_04_phase_a_train_saes.py `
  --config configs\praxis05-phase-a-local-real-pilot.json `
  --cache-dir runs\praxis05-phase-a\activation_cache_cadets_train `
  --output-root runs\praxis05-phase-a-local-real-pilot-1k
```

Diagnostics:

```powershell
$env:PYTHONPATH='src'
& "$env:USERPROFILE\.venvs\praxis05\Scripts\python.exe" scripts\praxis05_05_phase_a_diagnostics.py `
  --config configs\praxis05-phase-a-local-real-pilot.json `
  --phase-a-root runs\praxis05-phase-a-local-real-pilot-1k `
  --output results\praxis05\phase_a_local_real_pilot_1k\diagnostics.json
```

Pilot result:

- Status: `FAIL`
- MSE ratio: `0.008323372377465882` against threshold `< 0.25` -> PASS
- Feature death rate: `0.9080078125` against threshold `< 0.50` -> FAIL
- Seed stability: `0.45949998795986174` against threshold `> 0.30` -> PASS

Interpretation: the SAE can reconstruct MAGIC activations and the learned top features are more stable than the threshold, but only a small subset of features actually activates. This suggests MAGIC's 64-dimensional CADETS representation may be too compressed, too low-rank, or too easy to reconstruct with a small set of latents.

## Pre-Registered Phase A Still Required

The frozen formal Phase A remains:

- Config: `configs/praxis05-sae-topk-k32-x16.json`
- Features: `4096`
- Steps: `20000`
- Batch size: `4096`
- Train vectors: up to `10,000,000`
- Seeds: `[13, 42, 137, 271, 1729]`

This is a GPU job. Running it on this CPU session would be slow and would not be the cleanest evidence path. If it passes, proceed to Phase B. If it fails feature death again, the correct next step is the one allowed PIDSMaker pivot to a larger-hidden-state model, not manual threshold moving.

## Current Recommendation

Do not implement Phase B yet.

Next best actions, in order:

1. Run the full pre-registered Phase A on GPU.
2. If full MAGIC Phase A fails, pivot once to PIDSMaker with a larger hidden state.
3. If the pivot also fails, write the negative-result note: current provenance-graph APT detector embeddings may be too compressed for MI-style TopK SAE decomposition.

