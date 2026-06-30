# PX-033 SWE-EVO Cross-Model Primary Queue

Generated: 2026-06-30T12:05:00+00:00

Status: **PRIMARY QUEUE FAILED BASELINE - CONFIRMATION QUEUE STOPPED**

## Claim Boundary

This is a paid AWS execution follow-up to the PX-033 next-label gate. It executes the five-row `gpt-4o-2024-11-20` primary queue in the SWE-EVO/SWE-bench container lane.

The run is still a small fail-to-pass viability slice, not a full SWE-EVO benchmark, not a pass-to-pass regression benchmark, and not a trained repo-state world model.

## Baseline To Beat

The previous next-label gate established a simple metadata baseline over the five valid `glm-4p5` labels:

- Metadata rule: `repo == psf/requests`.
- Accuracy: `0.8000`.
- F1: `0.8000`.

The registered decision rule was to run the five-row `deepseek-r1-0528` confirmation queue only if the primary queue beat that baseline.

## Primary Queue Result

- Model: `gpt-4o-2024-11-20`.
- Requested tasks: `5`.
- Evaluated tasks: `5`.
- Pass rate: `0.2000`.
- Status counts: `1` PASS, `3` MODEL_FAIL, `1` INFRA_OR_APPLY_FAIL.
- Wall time: `31.04` seconds.
- S3 output: `s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/swe_evo_cross_model_primary_20260630/output/`.

| Instance | Repo | Status | Model rc | Gold rc | Selected tests | F2P | P2P | File overlap | Wall seconds |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| `iterative__dvc_0.30.0_0.30.1` | `iterative/dvc` | `INFRA_OR_APPLY_FAIL` | `998` | `0` | `1` | `1` | `12` | `0` | `7.58` |
| `iterative__dvc_2.21.1_2.21.2` | `iterative/dvc` | `MODEL_FAIL` | `1` | `0` | `1` | `1` | `8` | `0` | `10.75` |
| `psf__requests_v2.12.2_v2.12.3` | `psf/requests` | `PASS` | `0` | `0` | `4` | `4` | `109` | `1` | `4.77` |
| `psf__requests_v2.27.0_v2.27.1` | `psf/requests` | `MODEL_FAIL` | `1` | `0` | `2` | `2` | `185` | `0` | `3.41` |
| `psf__requests_v2.9.0_v2.9.1` | `psf/requests` | `MODEL_FAIL` | `1` | `0` | `1` | `1` | `85` | `1` | `3.68` |

## Interpretation

The executable primary queue did not beat the metadata baseline. The result is worse than the simple repo-family rule and invalidates the prior post-hoc proxy screen as a basis for expanding into the DeepSeek confirmation queue or RWML-style repo-state world-model training.

The single passing task confirms the harness can still execute useful labels, but the cross-model signal is not strong enough to justify additional spend as a positive Praxis result.

## Decision

Stop PX-033 at diagnostic evidence for this cycle.

- Do not run the `deepseek-r1-0528` confirmation queue from the June 30 next-label file.
- Do not start repo-state world-model or RWML training.
- Keep the artifacts as evidence that patch-overlap proxies can overstate executable correctness on tiny slices.
- Reopen only if a larger, cheaper executable-label source is available or if a new predictor has a registered baseline that is not dominated by repository-family metadata.

## Artifacts

- Local summary JSON: `runs/px033-swe-evo-cross-model-primary-20260630/swe_evo_true_eval_sweep_summary.json`
- Local result CSV: `runs/px033-swe-evo-cross-model-primary-20260630/swe_evo_true_eval_sweep_results.csv`
- Local per-instance details: `runs/px033-swe-evo-cross-model-primary-20260630/per_instance/`
- Local patches and eval logs: `runs/px033-swe-evo-cross-model-primary-20260630/patches/` and `runs/px033-swe-evo-cross-model-primary-20260630/evals/`
- Previous next-label gate: `reports/swe_evo_repo_state_world_model/SWE_EVO_NEXT_LABEL_CROSS_MODEL_GATE_20260630.md`
