# PX-033 SWE-EVO Multi-Task True-Eval Sweep

Generated: 2026-06-30T11:58:04.051089+00:00

Status: **MULTI-TASK SWEEP MIXED**

## Claim Boundary

Small SWE-EVO released-prediction true-eval sweep over selected executable tasks. When p2p_limit is 0, this is a fail-to-pass viability sweep only, not a regression-preservation benchmark. This is not a full benchmark sweep and not a trained repo-state world model.

## Metrics

| Metric | Value |
|---|---:|
| Model patch source | `gpt-4o-2024-11-20` |
| Requested tasks | `5` |
| Evaluated tasks | `5` |
| PASS_TO_PASS tests per task | `0` |
| PASS | `1` |
| MODEL_FAIL | `3` |
| GOLD_FAIL | `0` |
| INFRA_OR_APPLY_FAIL | `1` |
| Pass rate | `0.2000` |
| Wall seconds | `31.0` |

## Task Results

| Instance | Repo | Status | Base | Model | Gold | Tests | Overlap |
|---|---|---:|---:|---:|---:|---:|---:|
| `iterative__dvc_0.30.0_0.30.1` | `iterative/dvc` | `INFRA_OR_APPLY_FAIL` | `1` | `998` | `0` | `1` | `0` |
| `iterative__dvc_2.21.1_2.21.2` | `iterative/dvc` | `MODEL_FAIL` | `1` | `1` | `0` | `1` | `0` |
| `psf__requests_v2.12.2_v2.12.3` | `psf/requests` | `PASS` | `1` | `0` | `0` | `4` | `1` |
| `psf__requests_v2.27.0_v2.27.1` | `psf/requests` | `MODEL_FAIL` | `1` | `1` | `0` | `2` | `0` |
| `psf__requests_v2.9.0_v2.9.1` | `psf/requests` | `MODEL_FAIL` | `1` | `1` | `0` | `1` | `1` |

## Interpretation

This is a released-prediction execution sweep. A PASS means the selected base task fails after applying the SWE test patch, while both the released model patch and the gold patch pass in the benchmark image. This does not yet prove a trained repo-state world model; it tests whether the SWE-EVO lane has enough executable signal to justify predictor and world-model experiments.
