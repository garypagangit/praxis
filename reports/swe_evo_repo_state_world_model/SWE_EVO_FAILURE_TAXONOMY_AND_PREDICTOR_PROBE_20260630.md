# PX-033 SWE-EVO Failure Taxonomy and Predictor Probe

Generated: 2026-06-30T11:02:52+00:00

Status: **PREDICTOR GATE MIXED**

## Claim Boundary

This analyzes the six-task SWE-EVO released-prediction F2P sweep already run on AWS. It is not a trained world model and not a benchmark-scale result. The valid predictor slice has only `5` model-patch labels after excluding gold/harness-invalid tasks.

## Headline Result

The executable lane remains useful, but the predictor claim is not proven yet: `2`/`5` valid model-patch labels passed, all valid failures were semantic incomplete-fix failures, and the strongest simple baseline in this tiny slice was `metadata_repo_is_requests` with accuracy `0.8000` and F1 `0.8000`.

What this proves now:

- SWE-EVO can produce executable, inspectable labels for Praxis repo-state experiments.
- The failing model patches are not merely patch-apply or Docker failures; gold passes the same selected F2P tests in the valid failures.
- Patch/repo-state overlap alone is not enough evidence for a publishable repo-state world-model claim.

What it does not prove yet:

- It does not prove a trained repo-state predictor beats metadata-only baselines.
- It does not justify RWML-style training until we add more labels or cross-model replications.

## Metrics

| Metric | Value |
|---|---:|
| Sweep tasks | `6` |
| Valid model-patch labels | `5` |
| Valid PASS | `2` |
| Valid MODEL_FAIL | `3` |
| Valid pass rate | `0.4000` |
| Gold/harness-invalid tasks | `1` |
| Raw PASS | `2` |
| Raw MODEL_FAIL | `3` |
| Raw GOLD_FAIL | `1` |
| Model under test | `glm-4p5` |
| Sweep source | [`swe-evo-true-eval-sweep-20260629-safe-f2p`](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/) |
| Raw analysis JSON | [`swe_evo_failure_taxonomy_and_predictor_probe.json`](../../runs/swe-evo-failure-predictor-probe-20260630/swe_evo_failure_taxonomy_and_predictor_probe.json) |
| Raw analysis CSV | [`swe_evo_failure_taxonomy_and_predictor_probe.csv`](../../runs/swe-evo-failure-predictor-probe-20260630/swe_evo_failure_taxonomy_and_predictor_probe.csv) |

## Failure Taxonomy

| Instance | Repo | Status | Taxonomy | Evidence |
|---|---|---:|---|---|
| [`psf__requests_v2.9.0_v2.9.1`](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/per_instance/psf__requests_v2.9.0_v2.9.1.json) | `psf/requests` | `PASS` | `PASS` | base `1`, model `0`, gold `0`; [instance JSON](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/per_instance/psf__requests_v2.9.0_v2.9.1.json); [eval log](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/evals/psf__requests_v2.9.0_v2.9.1/model_eval.json); 1 passed, 22 warnings in 0.23s |
| [`psf__requests_v2.12.2_v2.12.3`](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/per_instance/psf__requests_v2.12.2_v2.12.3.json) | `psf/requests` | `PASS` | `PASS` | base `1`, model `0`, gold `0`; [instance JSON](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/per_instance/psf__requests_v2.12.2_v2.12.3.json); [eval log](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/evals/psf__requests_v2.12.2_v2.12.3/model_eval.json); 4 passed, 22 warnings in 0.24s |
| [`psf__requests_v2.27.0_v2.27.1`](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/per_instance/psf__requests_v2.27.0_v2.27.1.json) | `psf/requests` | `MODEL_FAIL` | `MODEL_FIX_INCOMPLETE` | base `1`, model `1`, gold `0`; [instance JSON](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/per_instance/psf__requests_v2.27.0_v2.27.1.json); [eval log](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/evals/psf__requests_v2.27.0_v2.27.1/model_eval.json); FAILED tests/test_utils.py::test_prepend_scheme_if_needed[http://user@example.com/path?query-http://user@example.com/path?query] |
| [`iterative__dvc_0.30.0_0.30.1`](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/per_instance/iterative__dvc_0.30.0_0.30.1.json) | `iterative/dvc` | `MODEL_FAIL` | `MODEL_FIX_INCOMPLETE` | base `1`, model `1`, gold `0`; [instance JSON](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/per_instance/iterative__dvc_0.30.0_0.30.1.json); [eval log](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/evals/iterative__dvc_0.30.0_0.30.1/model_eval.json); FAILED tests/test_stage.py::TestDefaultWorkingDirectory::test_ignored_in_checksum |
| [`iterative__dvc_2.21.1_2.21.2`](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/per_instance/iterative__dvc_2.21.1_2.21.2.json) | `iterative/dvc` | `MODEL_FAIL` | `MODEL_FIX_INCOMPLETE` | base `1`, model `1`, gold `0`; [instance JSON](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/per_instance/iterative__dvc_2.21.1_2.21.2.json); [eval log](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/evals/iterative__dvc_2.21.1_2.21.2/model_eval.json); FAILED tests/func/api/test_params.py::test_params_show_untracked_target - Fai... |
| [`scikit-learn__scikit-learn_0.21.1_0.21.2`](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/per_instance/scikit-learn__scikit-learn_0.21.1_0.21.2.json) | `scikit-learn/scikit-learn` | `GOLD_FAIL` | `HARNESS_OR_TEST_NODE_INVALID` | base `4`, model `4`, gold `4`; [instance JSON](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/per_instance/scikit-learn__scikit-learn_0.21.1_0.21.2.json); [eval log](../../runs/swe-evo-true-eval-sweep-20260629-safe-f2p/evals/scikit-learn__scikit-learn_0.21.1_0.21.2/gold_eval.json); E   ImportError: No module named 'sklearn.__check_build._check_build' |

## Metadata vs Repo-State Proxy Probe

The table below treats the five valid model-patch tasks as PASS/FAIL labels. Metadata-only rules use task/repo metadata. Repo-state proxy rules use patch-file structure from the executed artifacts; rules that compare with gold patch files are diagnostic and not deployable before the answer is known.

| Rule | Feature class | Accuracy | Precision | Recall | F1 | Notes |
|---|---|---:|---:|---:|---:|---|
| `metadata_repo_is_requests` | metadata-only | `0.8000` | `0.6667` | `1.0000` | `0.8000` | Predicts requests tasks pass and non-requests tasks fail. |
| `metadata_selected_tests_ge_2` | metadata-only | `0.6000` | `0.5000` | `0.5000` | `0.5000` | Uses selected fail-to-pass test count only. |
| `repo_state_gold_overlap_ge_1` | repo-state proxy, post-hoc | `0.4000` | `0.4000` | `1.0000` | `0.5714` | All valid tasks overlap at least one gold file, so this is not discriminative. |
| `repo_state_gold_overlap_ge_2` | repo-state proxy, post-hoc | `0.8000` | `1.0000` | `0.5000` | `0.6667` | High precision in this slice, but misses one passing requests task. |
| `repo_state_model_subset_gold` | repo-state proxy, post-hoc | `0.4000` | `0.4000` | `1.0000` | `0.5714` | Tests whether the model touched only files later touched by gold. |
| `repo_state_model_gold_jaccard_ge_033` | repo-state proxy, post-hoc | `0.4000` | `0.4000` | `1.0000` | `0.5714` | Approximate file-level similarity threshold. |

## Per-Task Feature Table

| Instance | Label | Selected tests | F2P | Overlap | Model files | Gold files | Model/Gold Jaccard | First eval signal |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `psf__requests_v2.9.0_v2.9.1` | `PASS` | `1` | `1` | `3` | `3` | `7` | `0.4286` | 1 passed, 22 warnings in 0.23s |
| `psf__requests_v2.12.2_v2.12.3` | `PASS` | `4` | `4` | `1` | `1` | `3` | `0.3333` | 4 passed, 22 warnings in 0.24s |
| `psf__requests_v2.27.0_v2.27.1` | `FAIL` | `2` | `2` | `1` | `1` | `3` | `0.3333` | FAILED tests/test_utils.py::test_prepend_scheme_if_needed[http://user@example.com/path?query-http://user@example.com/path?query] |
| `iterative__dvc_0.30.0_0.30.1` | `FAIL` | `1` | `1` | `1` | `1` | `2` | `0.5000` | FAILED tests/test_stage.py::TestDefaultWorkingDirectory::test_ignored_in_checksum |
| `iterative__dvc_2.21.1_2.21.2` | `FAIL` | `1` | `1` | `1` | `1` | `1` | `1.0000` | FAILED tests/func/api/test_params.py::test_params_show_untracked_target - Fai... |
| `scikit-learn__scikit-learn_0.21.1_0.21.2` | `EXCLUDED` | `1` | `1` | `4` | `4` | `14` | `0.2857` | E   ImportError: No module named 'sklearn.__check_build._check_build' |

## Decision

PX-033 should continue only as a measured execution-and-prediction lane. The useful next gate is either more executable F2P labels or a cross-model replication on the same valid tasks, followed by a comparison against the repo-family metadata baseline. Do not move to expensive world-model training until a repo-state predictor beats that simple baseline on a larger valid slice.
