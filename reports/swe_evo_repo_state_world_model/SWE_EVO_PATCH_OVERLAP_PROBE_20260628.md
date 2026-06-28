# PX-033 SWE-EVO Patch-Overlap Probe

Generated: 2026-06-28T21:11:18.457688+00:00

Status: **PROXY GATE PASS - REAL EVAL REQUIRED**

## Claim Boundary

Released-prediction patch-overlap proxy only. No tests were executed and no model correctness or fix-rate claim is made.

## Primary Metrics

| Metric | Value |
|---|---:|
| Released SWE-agent models | `11` |
| Prediction attempts parsed | `517` |
| Unique tasks covered | `47` / `48` |
| Mean file precision | `0.5143` |
| Mean file recall | `0.1885` |
| Mean file F1 | `0.2313` |
| Median file F1 | `0.1538` |
| Exact file-set rate | `0.0174` |
| Zero file-overlap rate | `0.3095` |
| Tasks with any file overlap | `47` / `48` |
| Tasks with any exact file set | `2` / `48` |
| Best-task file F1 mean | `0.5125` |
| Patch complexity vs best file F1 Pearson | `-0.6300` |

## Publish Checks

| Check | Pass |
|---|---:|
| `released_predictions_available` | `True` |
| `unique_task_coverage` | `True` |
| `nontrivial_file_overlap_signal` | `True` |
| `most_tasks_have_some_overlap` | `True` |
| `opportunity_not_saturated` | `True` |

## Model Summary

| Model | Attempts | File P | File R | File F1 | Exact set | Zero overlap | Added-line J |
|---|---:|---:|---:|---:|---:|---:|---:|
| `glm-4p5` | `47` | `0.7906` | `0.3391` | `0.4376` | `0.0213` | `0.0426` | `0.0435` |
| `kimi-k2-instruct` | `47` | `0.8486` | `0.2677` | `0.3609` | `0.0213` | `0.0426` | `0.0428` |
| `gpt-5-2025-08-07` | `47` | `0.5968` | `0.3184` | `0.3589` | `0.0213` | `0.0638` | `0.0318` |
| `qwen3-coder-480b-a35b-instruct` | `47` | `0.5665` | `0.2828` | `0.3260` | `0.0426` | `0.1277` | `0.0356` |
| `gpt-4.1-2025-04-14` | `47` | `0.6176` | `0.2465` | `0.2850` | `0.0426` | `0.2766` | `0.0349` |
| `gpt-5-mini-2025-08-07` | `47` | `0.4924` | `0.1430` | `0.1935` | `0.0213` | `0.3191` | `0.0125` |
| `gpt-4o-2024-11-20` | `47` | `0.5708` | `0.1283` | `0.1628` | `0.0000` | `0.2766` | `0.0075` |
| `o3-2025-04-16` | `47` | `0.2675` | `0.1241` | `0.1184` | `0.0000` | `0.5319` | `0.0018` |
| `gpt-oss-120b` | `47` | `0.2684` | `0.1014` | `0.1164` | `0.0213` | `0.4894` | `0.0063` |
| `deepseek-r1-0528` | `47` | `0.3635` | `0.0637` | `0.0991` | `0.0000` | `0.5957` | `0.0107` |
| `gpt-5-nano-2025-08-07` | `47` | `0.2745` | `0.0584` | `0.0856` | `0.0000` | `0.6383` | `0.0015` |

## Hardest Tasks By Best File F1

| Instance | Repo | Gold files | Attempts | Best file F1 | Any overlap | Any exact set |
|---|---|---:|---:|---:|---:|---:|
| `pydantic__pydantic_v2.6.0b1_v2.6.0` | `pydantic/pydantic` | `5` | `0` | `0.0000` | `False` | `False` |
| `dask__dask_2024.1.0_2024.1.1` | `dask/dask` | `32` | `11` | `0.1143` | `True` | `False` |
| `dask__dask_2023.3.2_2023.4.0` | `dask/dask` | `69` | `11` | `0.1519` | `True` | `False` |
| `dask__dask_2022.9.2_2022.10.0` | `dask/dask` | `50` | `11` | `0.1667` | `True` | `False` |
| `iterative__dvc_1.10.2_1.11.0` | `iterative/dvc` | `53` | `11` | `0.1695` | `True` | `False` |
| `conan-io__conan_2.0.14_2.0.15` | `conan-io/conan` | `78` | `11` | `0.1860` | `True` | `False` |
| `iterative__dvc_1.0.0a1_1.0.0a2` | `iterative/dvc` | `107` | `11` | `0.2121` | `True` | `False` |
| `iterative__dvc_2.8.1_2.8.2` | `iterative/dvc` | `79` | `11` | `0.2222` | `True` | `False` |
| `scikit-learn__scikit-learn_0.20.1_0.20.2` | `scikit-learn/scikit-learn` | `31` | `11` | `0.2286` | `True` | `False` |
| `iterative__dvc_3.43.1_3.44.0` | `iterative/dvc` | `23` | `11` | `0.2667` | `True` | `False` |

## Interpretation

The released prediction patches provide a usable no-cost proxy for repo-state planning: enough models and attempts are available, most tasks have at least some file-level overlap, and exact file-set matches are rare. That combination is useful because the signal is not empty, but the file-planning problem is clearly not saturated.

This still does not prove the PX-033 world-model idea works. It proves that the next paid or containerized evaluation should be small and targeted: one true SWE-EVO evaluation slice plus a metadata-only baseline and a repo-state-summary baseline.

## Next Gate

Execute or obtain true SWE-EVO evaluation results for one small model/instance slice, then test whether repo-state summaries improve fix-rate prediction beyond metadata-only baselines.
