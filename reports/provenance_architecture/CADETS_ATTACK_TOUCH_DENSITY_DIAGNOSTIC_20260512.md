# Cadets Attack-Touch Density Diagnostic

Generated: 2026-05-12

## Purpose

The full E5 Cadets window table did not provide enough benign windows for a supervised detector-zoo claim. This diagnostic checks whether the PIDSMaker node-touch signal has useful density variation that could support weak-supervision or representation diagnostics.

This is not a ground-truth detector result.

## Inputs

| Field | Value |
|---|---:|
| Feature table | `runs/full-e5cadets-window-factory-20260511/window_features.csv` |
| Windows | `9,611` |
| Full-stream edge rows | `480,537,673` |
| PIDSMaker node-label rows | `124` |
| Class support from node-touch labels | `9,609` attack-touch / `2` benign-or-unlabeled |

## Density Distribution

| Metric | Value |
|---|---:|
| `malicious_node_events` minimum | `0` |
| p01 | `17` |
| p05 | `360` |
| p25 | `1,413` |
| median | `3,662` |
| p75 | `19,348.5` |
| p95 | `41,310` |
| p99 | `44,069.9` |
| maximum | `49,123` |

## Threshold Counts

| Threshold: malicious node events <= | Low-density windows | Higher-density windows |
|---:|---:|---:|
| `0` | `2` | `9,609` |
| `10` | `54` | `9,557` |
| `25` | `126` | `9,485` |
| `100` | `216` | `9,395` |
| `500` | `681` | `8,930` |
| `1,000` | `1,599` | `8,012` |
| `2,500` | `4,156` | `5,455` |
| `5,000` | `5,303` | `4,308` |
| `10,000` | `6,425` | `3,186` |
| `25,000` | `7,724` | `1,887` |

## Honest Interpretation

The node-touch label is too broad for binary benign-vs-attack detection on this full Cadets stream. However, `malicious_node_events` has strong density variation. That may support a weakly supervised diagnostic such as low-touch versus high-touch window retrieval, drift visualization, or representation stress testing.

It should not be described as attack detection unless interval labels or confirmed benign windows are added.

## Possible Use

Use density thresholds only as a proxy task:

- `low-touch` vs `high-touch` representation diagnostics for graph SSL or TGN.
- Sampling candidate windows for manual label review.
- Prioritizing windows for stage/anomaly interval annotation.

Do not use this proxy for a Praxis defense claim without external label validation.
