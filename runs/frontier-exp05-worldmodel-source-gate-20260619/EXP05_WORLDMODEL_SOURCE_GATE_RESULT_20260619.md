# EXP05 World-Model Source Gate Result

Generated: 2026-06-19T13:31:50.250980+00:00

Status: **SOURCE GATE PASS - AGENT EVAL PENDING**

## Primary Metrics

| Metric | Value |
|---|---:|
| Accessible repositories | `4` |
| Accessible PyPI packages | `2` |
| Perturbation rows | `4` |
| Held-out perturbations | `2` |
| Shape failures | `0` |
| Minimum mean absolute pixel delta | `0.0193` |

## Publish Checks

| Check | Pass |
|---|---:|
| `accessible_repositories` | `True` |
| `accessible_packages` | `True` |
| `perturbation_rows` | `True` |
| `heldout_perturbations` | `True` |
| `nonzero_pixel_delta` | `True` |
| `shape_preserved` | `True` |

## Perturbation Smoke

| Perturbation | Role | Shape preserved | Mean abs pixel delta |
|---|---|---:|---:|
| `brightness_down` | `dev_perturbation` | `True` | `0.1746` |
| `contrast_shift` | `dev_perturbation` | `True` | `0.0612` |
| `center_occlusion` | `heldout_perturbation` | `True` | `0.0309` |
| `salt_pepper` | `heldout_perturbation` | `True` | `0.0193` |

## Claim Boundary

This is a source and wrapper smoke gate, not a world-model robustness result. It proves that source paths are reachable and that visual perturbation wrappers preserve observation shape while creating nonzero visual shift. The next gate must install the environment and run clean plus perturbed agent evaluation.
