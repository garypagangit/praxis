# PX-023 NodLink Real-Data Proxy Gate

Generated: 2026-06-30T12:13:14.800382+00:00

Status: **REAL-DATA PROXY FAIL - CLOSE PIVOT**

## Claim Boundary

This gate uses real full E5 Cadets window features and PIDSMaker's NodLink `SumAggregation` encoder, but it is not a full PIDSMaker detector run. The full PIDSMaker path still requires a Postgres graph database/runtime that is not present on the AWS data-loader.

The result can close or constrain the one allowed PX-023 pivot, but it must not be described as a full NodLink/PIDSMaker detection result.

## Runtime Readiness

- AWS data-loader has the raw E5 Cadets mirror: `49` gzipped Cadets files under `/mnt/praxis/datasets/darpa-tc/e5/cadets`.
- AWS data-loader is missing Docker and native Postgres/psql for a full PIDSMaker database-backed run.
- Local repo venv has Torch, PyG, and SAELens, so the real-data proxy was run locally without restarting the GPU instance.

## Real-Data Proxy Input

- Source table: `runs\full-e5cadets-window-factory-20260511\window_features.csv`.
- Rows: `9611` windows.
- Feature dimensions: `70` non-label aggregate features.
- Class support: `{'attack_node_touch': 9609, 'benign_or_unlabeled': 2}`.
- Label-derived columns were excluded from the reconstruction input.

## NodLink-Style Activation Export

- Encoder: `pidsmaker.encoders.sum_aggregation.SumAggregation`.
- Graph: chronological bidirectional window graph with self loops, `28831` edges.
- Reconstruction MSE ratio: `0.281572`.
- Activation shape: `9611` x `256`.
- Activation std: `0.488504`.
- Nonzero activation fraction: `1.000000`.

## SAE Phase A Pilot Diagnostics

SAELens TopK pilot config: `1024` features, `k=32`, `1000` CPU steps, five seeds. Thresholds are the same Phase A kill-switch thresholds, but the run is a pilot, not the frozen `4096` feature / `20000` step GPU sweep.

| Check | Value | Threshold | Pass? |
|---|---:|---:|---|
| mse_ratio | `0.026022` | `0.2500` | yes |
| feature_death_rate | `0.260742` | `0.5000` | yes |
| seed_stability | `0.173000` | `0.3000` | no |

## Decision

Close PX-023 as negative for this cycle. The available real-data NodLink-style pivot fails the Phase A pilot diagnostics on seed_stability, while the full PIDSMaker runtime remains database-blocked. Do not reopen MAGIC or spend on Phase B.

## Artifacts

- Raw analysis JSON: `runs/px023-nodlink-realdata-proxy-20260630/px023_nodlink_realdata_proxy_gate.json`
- Activation cache: `runs/px023-nodlink-realdata-proxy-20260630/nodlink_realdata_activation_cache/`
- NodLink proxy model: `runs/px023-nodlink-realdata-proxy-20260630/nodlink_proxy_model/`
- SAELens pilot diagnostics: `runs/px023-nodlink-realdata-proxy-20260630/saelens_phase_a_pilot/diagnostics.json`
