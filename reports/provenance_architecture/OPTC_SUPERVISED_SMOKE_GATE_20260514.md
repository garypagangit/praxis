# OpTC Supervised Provenance Smoke Gate

Generated: 2026-05-14

Status: **FEASIBILITY PASS - TARGETED SMOKE ONLY**

## Scope

This is a targeted host/day feasibility smoke test, not a broad provenance detector claim.

- Host/day: `sysclient0501`, OpTC day 2 / `24Sep19`
- Target: `attack` vs `background` windows
- Excluded: `gray_buffer` windows
- Split: stratified random train/validation/test because chronological labels are attack-first then background
- Time columns excluded: `start_ns`, `end_ns`
- Label-derived columns excluded: `primary_label`, `labels`, `label_overlap_ns`, `malicious_node_events`, `malicious_node_count`, `node_labels`

## Label Support

| Label | Windows |
|---|---:|
| `attack` | `82` |
| `background` | `21` |
| `gray_buffer` | `22` |

## Split Support

| Split | Attack | Background | Total |
|---|---:|---:|---:|
| `train` | `49` | `12` | `61` |
| `validation` | `16` | `5` | `21` |
| `test` | `17` | `4` | `21` |

## Detector Results

| Detector | Split | Accuracy | Macro-F1 | ROC-AUC | AP | Attack recall | Background recall |
|---|---|---:|---:|---:|---:|---:|---:|
| `extra_trees_balanced` | `validation` | 0.9524 | 0.9384 | 1.0000 | 1.0000 | 0.9375 | 1.0000 |
| `extra_trees_balanced` | `test` | 0.8095 | 0.4474 | 0.8824 | 0.9728 | 1.0000 | 0.0000 |
| `logreg_balanced` | `validation` | 0.8571 | 0.8329 | 0.9625 | 0.9883 | 0.8125 | 1.0000 |
| `logreg_balanced` | `test` | 0.7619 | 0.6465 | 0.7206 | 0.9324 | 0.8235 | 0.5000 |
| `mlp_small` | `validation` | 0.6667 | 0.5051 | 0.3125 | 0.6613 | 0.8125 | 0.2000 |
| `mlp_small` | `test` | 0.7619 | 0.6465 | 0.6912 | 0.9049 | 0.8235 | 0.5000 |
| `random_forest_balanced` | `validation` | 0.9048 | 0.8456 | 0.9500 | 0.9857 | 1.0000 | 0.6000 |
| `random_forest_balanced` | `test` | 0.7619 | 0.4324 | 0.9118 | 0.9823 | 0.9412 | 0.0000 |

## Interpretation

The stratified smoke confirms the new OpTC interval labels are usable by the detector registry. Because all attack windows precede gray/background windows chronologically in this targeted slice, this is not evidence of temporal generalization. The next defensible step is to add another host/day or benign shard before making a provenance detector claim.

## Artifacts

| Artifact | Path |
|---|---|
| Summary JSON | `runs\optc-supervised-smoke-20260514\summary.json` |
| Split assignments | `runs\optc-supervised-smoke-20260514\split_assignments.csv` |
| Metrics CSV | `runs\optc-supervised-smoke-20260514\metrics.csv` |
