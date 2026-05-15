# OpTC Label Acquisition Plan

Generated: 2026-05-14

Status: **first targeted eCAR window-label gate PASS**

## How We Get Labels

1. Use the public OpTC red-team ground-truth PDF as the attack seed source.
2. Expand each timestamped red-team event into a padded attack interval.
3. Download the matching OpTC eCAR host/day shard from the public release.
4. Convert eCAR JSON to normalized provenance edges.
5. Build chronological windows and attach attack intervals.
6. Treat windows outside attack intervals and outside the gray buffer as background only for a red-team-window detection claim.

This produces an honest binary target: `attack-window` vs `background/no-red-team-overlap`. It does not produce perfect event-level malicious labels.

## Source Anchors

- Official release: `https://github.com/FiveDirections/OpTC-data`
- Data location from official release: Google Drive folder linked in the OpTC README.
- Dataset structure note: COMIDDS documents `eCar/benign`, `eCar/evaluation`, and `eCar/short`, and notes that the ground truth file is needed for manual labels.
- Optional later upgrade: use published third-party OpTC label projects only after auditing compatibility with this window schema.

## Generated Artifacts

- Attack intervals: `runs\optc-label-acquisition-20260514\optc_attack_intervals.csv`
- Target host/day shortlist: `runs\optc-label-acquisition-20260514\optc_target_host_days.csv`
- Optional window labels: `runs\optc-label-acquisition-20260514\optc_window_labels.csv`

## Seed Summary

- Timestamped seed events: `101`
- Attack interval padding: `-15.0 / +15.0` minutes
- Unique seed hosts: `21`
- Covered days: `3`

## First Download Target

| Day | Host | Seed events | eCAR folder | Host filter |
|---:|---|---:|---|---|
| `2` | `sysclient0501` | `28` | `external/datasets/optc/ecar/evaluation/24Sep19` | `sysclient0501` |
| `1` | `sysclient0201` | `18` | `external/datasets/optc/ecar/evaluation/23Sep19-red` | `sysclient0201` |
| `3` | `sysclient0051` | `12` | `external/datasets/optc/ecar/evaluation/25Sept` | `sysclient0051` |
| `1` | `sysclient0660` | `9` | `external/datasets/optc/ecar/evaluation/23Sep19-red` | `sysclient0660` |
| `2` | `sysclient0005` | `6` | `external/datasets/optc/ecar/evaluation/24Sep19` | `sysclient0005` |

## Window Label Gate

| Check | Required |
|---|---:|
| Attack windows | `>=20` |
| Background windows | `>=20` |
| Gray-buffer windows | reported/excluded from supervised training |
| Split support | train/validation/test each include the claimed positive class |

## Targeted Download Command

Install `gdown` into the diagnostic environment once if needed, then download only the target host/day folder:

```powershell
.\.venv-diag\Scripts\python.exe -m pip install gdown
.\.venv-diag\Scripts\python.exe .\scripts\download_optc_target_ecar.py --host sysclient0501 --day 2
```

## Run Command After Download

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_optc_window_gate.ps1 `
  -Inputs external\datasets\optc\ecar\evaluation\24Sep19 `
  -Labels runs\optc-label-acquisition-20260514\optc_attack_intervals.csv `
  -HostFilter sysclient0501 `
  -OutRoot runs\optc-window-gate-20260514-pass `
  -Limit 625000 `
  -EventsPerWindow 5000
```

Then rerun this script with `--windows runs\optc-window-gate-20260514-pass\windows.csv` to count `attack`, `background`, and `gray_buffer` support.

## Claim Guard

Do not call this event-level malicious labeling. The defensible claim is window-level red-team interval overlap against background windows from the same OpTC release.

## Gate Decision

- Attack support: `82` windows.
- Background support: `21` windows.
- Decision: `PASS` when both attack and background support are `>=20`; gray-buffer windows are reported and excluded from supervised training.

## Current Window Support

| Label | Windows |
|---|---:|
| `attack` | `82` |
| `background` | `21` |
| `gray_buffer` | `22` |
