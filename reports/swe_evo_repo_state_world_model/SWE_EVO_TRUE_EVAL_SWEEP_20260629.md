# PX-033 SWE-EVO Multi-Task True-Eval Sweep

Generated: 2026-06-29T09:44:59.613976+00:00

Status: **MULTI-TASK SWEEP MIXED**

## Claim Boundary

Small SWE-EVO released-prediction true-eval sweep over selected executable tasks. When p2p_limit is 0, this is a fail-to-pass viability sweep only, not a regression-preservation benchmark. This is not a full benchmark sweep and not a trained repo-state world model.

## Metrics

| Metric | Value |
|---|---:|
| Model patch source | `glm-4p5` |
| Requested tasks | `6` |
| Evaluated tasks | `6` |
| PASS_TO_PASS tests per task | `0` |
| PASS | `2` |
| MODEL_FAIL | `3` |
| GOLD_FAIL | `1` |
| INFRA_OR_APPLY_FAIL | `0` |
| Pass rate | `0.3333` |
| Wall seconds | `138.9` |

## Task Results

| Instance | Repo | Status | Base | Model | Gold | Tests | Overlap |
|---|---|---:|---:|---:|---:|---:|---:|
| `psf__requests_v2.9.0_v2.9.1` | `psf/requests` | `PASS` | `1` | `0` | `0` | `1` | `3` |
| `psf__requests_v2.12.2_v2.12.3` | `psf/requests` | `PASS` | `1` | `0` | `0` | `4` | `1` |
| `psf__requests_v2.27.0_v2.27.1` | `psf/requests` | `MODEL_FAIL` | `1` | `1` | `0` | `2` | `1` |
| `iterative__dvc_0.30.0_0.30.1` | `iterative/dvc` | `MODEL_FAIL` | `1` | `1` | `0` | `1` | `1` |
| `iterative__dvc_2.21.1_2.21.2` | `iterative/dvc` | `MODEL_FAIL` | `1` | `1` | `0` | `1` | `1` |
| `scikit-learn__scikit-learn_0.21.1_0.21.2` | `scikit-learn/scikit-learn` | `GOLD_FAIL` | `4` | `4` | `4` | `1` | `4` |

## Interpretation

This is a released-prediction execution sweep. A PASS means the selected base task fails after applying the SWE test patch, while both the released model patch and the gold patch pass in the benchmark image. This does not yet prove a trained repo-state world model; it tests whether the SWE-EVO lane has enough executable signal to justify predictor and world-model experiments.
