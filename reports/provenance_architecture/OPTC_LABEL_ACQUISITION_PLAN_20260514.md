# OpTC Label Acquisition Plan

Generated: 2026-05-15

Status: **expanded window-label support passed; detector promotion blocked by host/day shift**

## How We Get Labels

1. Use the public OpTC red-team ground-truth PDF as the attack seed source.
2. Expand each timestamped red-team event into a padded attack interval.
3. Download matching OpTC eCAR red-team host/day shards from the public release.
4. Download clean benign eCAR baselines for the same mapped host groups.
5. Convert eCAR JSON to normalized provenance edges.
6. Build chronological windows and attach attack intervals.
7. Treat windows outside attack intervals and outside the gray buffer as `background`.

This produces an honest binary window target: `attack-window` vs `background/no-red-team-overlap`. It does not produce event-level malicious labels.

## Source Anchors

- Official release: `https://github.com/FiveDirections/OpTC-data`
- Data location from official release: Google Drive folder linked in the OpTC README.
- Dataset structure note: COMIDDS documents `eCar/benign`, `eCar/evaluation`, and `eCar/short`, and notes that the ground truth file is needed for manual labels.
- Optional later upgrade: use published third-party OpTC label projects only after auditing compatibility with this window schema.

## Generated Label Artifacts

| Artifact | Path |
|---|---|
| Base attack intervals | `runs/optc-label-acquisition-20260514/optc_attack_intervals.csv` |
| First target shortlist | `runs/optc-label-acquisition-20260514/optc_target_host_days.csv` |
| Expanded gate report | `reports/provenance_architecture/OPTC_CROSS_HOST_GATE_20260515.md` |
| Expanded metrics | `runs/optc-cross-host-gate-20260515/metrics.csv` |
| Expanded split assignments | `runs/optc-cross-host-gate-20260515/split_assignments.csv` |

## Seed Summary

- Timestamped seed events: `101`
- Attack interval padding: `-15.0 / +15.0` minutes
- Gray buffer: `30.0` minutes around attack intervals
- Unique seed hosts: `21`
- Covered days: `3`

## Expanded Slice Support

| Slice | Host | Source | Attack | Background | Gray buffer | Total |
|---|---|---|---:|---:|---:|---:|
| `sysclient0501_day2` | `sysclient0501` | `evaluation/24Sep19` | `82` | `21` | `22` | `125` |
| `sysclient0201_day1` | `sysclient0201` | `evaluation/23Sep19-red` | `112` | `54` | `34` | `200` |
| `sysclient0051_day3` | `sysclient0051` | `evaluation/25Sept` | `41` | `107` | `52` | `200` |
| `sysclient0501_benign` | `sysclient0501` | `benign/20-23Sep19` | `0` | `100` | `0` | `100` |
| `sysclient0201_benign` | `sysclient0201` | `benign/20-23Sep19` | `0` | `100` | `0` | `100` |
| `sysclient0051_benign` | `sysclient0051` | `benign/20-23Sep19` | `0` | `100` | `0` | `100` |

The expanded gate has `717` usable non-gray windows and excludes `108` gray-buffer windows. This is enough for honest host/day holdout testing.

## Commands

Download red-team and benign shards with the local PIDSMaker URL map:

```powershell
.\.venv-diag\Scripts\python.exe .\scripts\download_optc_target_ecar.py --host sysclient0501 --day 2
.\.venv-diag\Scripts\python.exe .\scripts\download_optc_target_ecar.py --host sysclient0201 --day 1
.\.venv-diag\Scripts\python.exe .\scripts\download_optc_target_ecar.py --host sysclient0051 --day 3
.\.venv-diag\Scripts\python.exe .\scripts\download_optc_target_ecar.py --host sysclient0501 --relative-dir benign/20-23Sep19
.\.venv-diag\Scripts\python.exe .\scripts\download_optc_target_ecar.py --host sysclient0201 --relative-dir benign/20-23Sep19
.\.venv-diag\Scripts\python.exe .\scripts\download_optc_target_ecar.py --host sysclient0051 --relative-dir benign/20-23Sep19
```

Build host-filtered windows, generate labels, then run the expanded gate:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_optc_window_gate.ps1 `
  -Inputs .\external\datasets\optc\ecar\evaluation\24Sep19 `
  -Labels .\runs\optc-label-acquisition-20260514\optc_attack_intervals.csv `
  -HostFilter sysclient0501 `
  -OutRoot .\runs\optc-window-gate-20260514-pass `
  -Limit 625000 `
  -EventsPerWindow 5000

.\.venv-diag\Scripts\python.exe .\scripts\run_optc_cross_host_gate.py
```

For benign runs, pass only matching `AIA-*` host-group files to avoid scanning unrelated multi-GB shards.

## Gate Decision

- Label support: **PASS**.
- Pooled detector sanity: **PASS as a smoke check only**; all-behavior random forest and extra trees reach Macro-F1 `0.8750` on pooled stratified test.
- Host/day detector holdout: **FAIL**.
- Strict host holdout: **FAIL**.

## Claim Guard

The Praxis-ready claim is label/data readiness and a clear detector-generalization blocker. Do not claim a provenance detector from the pooled/random split while host/day holdout fails.
