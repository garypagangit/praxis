# OpTC Window Label Gate Result

Generated: 2026-05-14

Status: **PASS for first targeted host/day support gate**

## Target

The first targeted OpTC provenance label gate used:

- Host: `sysclient0501`
- Red-team day: `2` / `24Sep19`
- eCAR shard: `external/datasets/optc/ecar/evaluation/24Sep19`
- Attack seed source: `reports/provenance_architecture/optc_ground_truth_seed_events_20260513.csv`
- Attack interval padding: `-15 / +15` minutes
- Gray buffer: `30` minutes

## Window Gate

The clean bounded run used `625000` converted eCAR edges and stopped before the decompression fault observed in the over-wide pass through the second downloaded gzip file.

| Metric | Value |
|---|---:|
| Converted edges | `625000` |
| Records scanned | `14692035` |
| Input source files used | `1` |
| Windows | `125` |
| Events per window | `5000` |
| Timestamp span seconds | `10909.466` |
| Malformed JSON rows | `0` |

## Label Support

| Label | Windows | Gate role |
|---|---:|---|
| `attack` | `82` | positive class |
| `background` | `21` | negative class |
| `gray_buffer` | `22` | excluded from supervised training |

Gate requirement: `>=20` attack windows and `>=20` background windows before detector training.

Decision: **PASS**.

## Artifacts

| Artifact | Path |
|---|---|
| Attack intervals | `runs/optc-label-acquisition-20260514/optc_attack_intervals.csv` |
| Window labels | `runs/optc-label-acquisition-20260514/optc_window_labels.csv` |
| Window manifest | `runs/optc-window-gate-20260514-pass/manifest.json` |
| Windows | `runs/optc-window-gate-20260514-pass/windows.csv` |
| Window features | `runs/optc-window-gate-20260514-pass/window_features.csv` |
| Window factory report | `reports/provenance_architecture/OPTC_WINDOW_GATE_20260514.md` |

## Claim Guard

This is not an event-level malicious-label claim. It is a window-level red-team interval overlap gate for one targeted OpTC host/day. It unlocks a small supervised provenance detector smoke test, but it is not yet a broad provenance detector result.

## Next Action

Train only a strict smoke baseline on `attack` versus `background`, excluding `gray_buffer`. Promote the provenance track only if the split is transparent, both classes appear in train/validation/test, and the result is reported as a targeted OpTC host/day feasibility result rather than a general APT detector.
