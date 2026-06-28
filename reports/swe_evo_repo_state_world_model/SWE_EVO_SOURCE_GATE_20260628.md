# PX-033 SWE-EVO Source Gate

Generated: 2026-06-28T21:07:26.928595+00:00

Status: **SOURCE GATE PASS - ONE-TASK BASELINE READY**

## Claim Boundary

Source/data readiness only. No coding-agent trajectory, world-model training, or usefulness claim is made by this gate.

## Primary Sources

| Source | Status | Link | Notes |
|---|---|---|---|
| arXiv `http://arxiv.org/abs/2512.18470v6` | `ACCESSIBLE` | <https://arxiv.org/abs/2512.18470> | SWE-EVO: Benchmarking Coding Agents in Long-Horizon Software Evolution Scenarios |
| GitHub `SWE-EVO/SWE-EVO` | `ACCESSIBLE` | <https://github.com/SWE-EVO/SWE-EVO> | branch `main`, license `MIT` |
| Hugging Face `Fsoft-AIC/SWE-EVO` | `ACCESSIBLE` | <https://huggingface.co/datasets/Fsoft-AIC/SWE-EVO> | license `apache-2.0`, gated `False` |

## Dataset Readiness

| Metric | Value |
|---|---:|
| Rows | `48` |
| Repositories | `7` |
| Unique images | `48` |
| Mean gold patch files | `21.15` |
| Patch file range | `1`-`107` |
| Total FAIL_TO_PASS tests | `3908` |
| Mean FAIL_TO_PASS tests | `81.42` |
| Total PASS_TO_PASS tests | `38043` |
| Mean PASS_TO_PASS tests | `792.56` |
| Mean problem statement chars | `1405.7` |

## Field Coverage

| Field | Coverage |
|---|---:|
| `repo` | `1.000` |
| `instance_id` | `1.000` |
| `base_commit` | `1.000` |
| `patch` | `1.000` |
| `problem_statement` | `1.000` |
| `environment_setup_commit` | `1.000` |
| `start_version` | `1.000` |
| `end_version` | `1.000` |
| `end_version_commit` | `1.000` |
| `image` | `1.000` |
| `test_cmds` | `1.000` |
| `log_parser` | `1.000` |
| `test_patch` | `0.979` |
| `FAIL_TO_PASS` | `1.000` |
| `PASS_TO_PASS` | `0.979` |

## Publish Checks

| Check | Pass |
|---|---:|
| `arxiv_accessible` | `True` |
| `github_accessible` | `True` |
| `github_required_paths` | `True` |
| `readme_mentions_agent_scaffolds` | `True` |
| `hf_public_not_gated` | `True` |
| `hf_expected_rows` | `True` |
| `hf_repo_count` | `True` |
| `core_field_coverage` | `True` |
| `evaluation_field_coverage` | `True` |
| `test_lists_present` | `True` |
| `sample_base_commits_reachable` | `True` |

## Repositories

`conan-io/conan`, `dask/dask`, `iterative/dvc`, `modin-project/modin`, `psf/requests`, `pydantic/pydantic`, `scikit-learn/scikit-learn`

## Sample Instances

| Instance | Repo | Versions | Patch files | F2P | P2P | Prompt snippet |
|---|---|---|---:|---:|---:|---|
| `conan-io__conan_2.0.14_2.0.15` | `conan-io/conan` | `2.0.14` -> `2.0.15` | `78` | `72` | `649` | - Feature: New ``conan lock remove`` command to remove requires from lockfiles. (https://github.com/conan-io/conan/pull/15284). Docs: [:page |
| `conan-io__conan_2.0.2_2.0.3` | `conan-io/conan` | `2.0.2` -> `2.0.3` | `48` | `8` | `317` | - Feature: ``conan cache clean`` learned the ``--all`` and ``--temp`` to clean everything (sources, builds) and also the temporary folders.  |
| `dask__dask_2022.9.2_2022.10.0` | `dask/dask` | `2022.9.2` -> `2022.10.0` | `50` | `44` | `2861` | 2022.10.0 --------- Released on October 14, 2022 New Features ^^^^^^^^^^^^ - Backend library dispatching for IO in Dask-Array and Dask-DataF |
| `dask__dask_2023.3.2_2023.4.0` | `dask/dask` | `2023.3.2` -> `2023.4.0` | `69` | `61` | `6246` | 2023.4.0 -------- Released on April 14, 2023 Enhancements ^^^^^^^^^^^^ - Override old default values in ``update_defaults`` (:pr:`10159`) `G |
| `dask__dask_2023.6.0_2023.6.1` | `dask/dask` | `2023.6.0` -> `2023.6.1` | `33` | `105` | `3415` | 2023.6.1 -------- Released on June 26, 2023 Enhancements ^^^^^^^^^^^^ - Remove no longer supported ``clip_lower`` and ``clip_upper`` (:pr:`1 |

## Sample Commit Probes

| Repo | Base commit reachable |
|---|---:|
| `conan-io/conan` | `True` |
| `dask/dask` | `True` |
| `iterative/dvc` | `True` |
| `modin-project/modin` | `True` |
| `psf/requests` | `True` |
| `pydantic/pydantic` | `True` |
| `scikit-learn/scikit-learn` | `True` |

## Interpretation

PX-033 is now realistically testable at the source level. The public dataset exposes task specs, base commits, gold patches, test patches, test lists, images, commands, and parser metadata for all 48 instances. The GitHub repo also exposes OpenHands, SWE-agent, and SWE-bench scaffolds.

This does not prove the repo-state world-model idea is useful. It proves that the next experiment can be a bounded one-task baseline plus a repo-state-summary predictor, rather than a speculative RL/world-model training program.

## Next Gate

Run a single low-cost OpenHands or SWE-agent baseline instance, then test whether repo-state summaries predict partial progress/fix-rate better than metadata-only baselines.
