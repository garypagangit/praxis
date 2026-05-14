# OpTC eCAR Conversion Gate

Generated: 2026-05-14

Status: **conversion scaffold ready; full eCAR shard still needed**

## Purpose

Move the provenance track from a red-team seed manifest to detector-ready windows.

The seed manifest already extracted `101` timestamped red-team events from `OpTCRedTeamGroundTruth.pdf`. The next requirement is host telemetry around those timestamps. OpTC eCAR records can now be converted into the normalized JSONL edge schema consumed by the provenance window factory.

## Added Tools

| Tool | Purpose |
|---|---|
| `scripts/convert_optc_ecar_to_edges.py` | Converts OpTC eCAR JSON/JSONL/GZ records to normalized provenance edge JSONL. |
| `scripts/build_optc_window_gate.ps1` | Runs eCAR conversion, then calls the existing provenance window factory. |

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
powershell -ExecutionPolicy Bypass -File .\scripts\build_optc_window_gate.ps1 `
  -Inputs <path-to-optc-ecar-json-or-folder> `
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

This gate is not complete until an actual OpTC eCAR shard is downloaded from the public Google Drive release or mirrored to S3. The local `external/datasets/optc/` folder currently contains metadata and ground truth, not the full endpoint telemetry.

## Next Action

Download a targeted eCAR shard for one red-team day and the hosts listed in the seed manifest, then run the gate command above. Do not train a detector until the label-support gate passes.
