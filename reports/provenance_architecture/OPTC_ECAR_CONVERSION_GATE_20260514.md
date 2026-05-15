# OpTC eCAR Conversion Gate

Generated: 2026-05-14

Status: **first targeted conversion and label-support gate PASS**

## Purpose

Move the provenance track from a red-team seed manifest to detector-ready windows.

The seed manifest already extracted `101` timestamped red-team events from `OpTCRedTeamGroundTruth.pdf`. The first targeted host/day telemetry shard has now been downloaded and converted for `sysclient0501` day 2.

## First Targeted Gate Result

| Metric | Value |
|---|---:|
| Host/day | `sysclient0501` / day `2` |
| eCAR folder | `external/datasets/optc/ecar/evaluation/24Sep19` |
| Converted edges | `625000` |
| Windows | `125` |
| Attack windows | `82` |
| Background windows | `21` |
| Gray-buffer windows | `22` |
| Decision | `PASS` |

This remains a targeted label/detector feasibility result. It is not yet a broad provenance detector claim.

## Added Tools

| Tool | Purpose |
|---|---|
| `scripts/convert_optc_ecar_to_edges.py` | Converts OpTC eCAR JSON/JSONL/GZ records to normalized provenance edge JSONL, including numeric and ISO timestamp formats. |
| `scripts/build_optc_window_gate.ps1` | Runs eCAR conversion, optional host filtering, optional interval-label attachment, then calls the existing provenance window factory. |
| `scripts/build_optc_interval_labels.py` | Converts the extracted OpTC red-team seed manifest into padded attack intervals and a target host/day download shortlist. |
| `scripts/download_optc_target_ecar.py` | Downloads one targeted OpTC eCAR host/day folder using the PIDSMaker Google Drive URL map. |

## Field Mapping

| eCAR field | Normalized edge field |
|---|---|
| `timestamp` or `timestamp_ms` | `timestamp_nanos` |
| `object` + `action` | `datum_type` and first `event_names` entry |
| `actorID` | `subject_uuid` |
| `objectID` | `object_uuid` |
| `id` | `object2_uuid` |
| `properties.image_path`, `process_image_path`, `parent_image_path`, or `command_line` | `properties.exec` |
| `hostname` | `properties.hostname` |

## Gate Command

```powershell
.\.venv-diag\Scripts\python.exe scripts\build_optc_interval_labels.py
.\.venv-diag\Scripts\python.exe -m pip install gdown
.\.venv-diag\Scripts\python.exe scripts\download_optc_target_ecar.py --host sysclient0501 --day 2

powershell -ExecutionPolicy Bypass -File .\scripts\build_optc_window_gate.ps1 `
  -Inputs external\datasets\optc\ecar\evaluation\24Sep19 `
  -Labels runs\optc-label-acquisition-20260514\optc_attack_intervals.csv `
  -HostFilter sysclient0501 `
  -OutRoot runs\optc-window-gate-20260514 `
  -Limit 200000 `
  -EventsPerWindow 5000
```

## Pass Criteria

| Check | Minimum |
|---|---:|
| Converted edges | `>= 100000` for a useful smoke |
| Windows | `>= 20` |
| Attack windows after interval attachment | `>= 20` |
| Benign windows after interval attachment | `>= 20` |
| Split support | train/validation/test each contain claimed positive class |

## Current Limitation

The downloaded host/day shard is enough for a first support gate. A broader detector claim still needs another host/day or benign shard so chronological and cross-host checks are possible.

## Next Action

Add another targeted OpTC host/day or benign shard, then rerun the label-support and detector smoke gates. Do not escalate to TGN/GraphCL or broad detector claims from the single-host stratified smoke.
