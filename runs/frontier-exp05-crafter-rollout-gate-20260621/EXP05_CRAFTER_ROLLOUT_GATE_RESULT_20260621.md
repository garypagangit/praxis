# EXP05 Crafter Rollout Gate Result

Generated: 2026-06-21T11:06:59.497575+00:00

Status: **ENVIRONMENT SMOKE PASS - WORLD-MODEL CLAIM NOT PROMOTED**

## Scope

- Environment: `crafter.Env`.
- Agent: deterministic observation-checksum policy, not a learned world-model agent.
- Perturbations are applied to observations before action selection, not to environment state.
- No raw frames are committed.

## Primary Metrics

| Condition | Role | Episodes | Mean reward | Mean achievements | Mean pixel delta |
|---|---|---:|---:|---:|---:|
| `brightness_down` | `dev_perturbation` | `5` | `0.9000` | `1.8000` | `0.0737` |
| `center_occlusion` | `heldout_perturbation` | `5` | `2.7000` | `3.6000` | `0.0163` |
| `clean` | `clean` | `5` | `1.5000` | `2.4000` | `0.0000` |
| `contrast_shift` | `dev_perturbation` | `5` | `1.3000` | `2.2000` | `0.0530` |
| `salt_pepper` | `heldout_perturbation` | `5` | `1.7000` | `2.6000` | `0.0199` |

## Retention Versus Clean

| Condition | Role | Reward retention | Achievement retention |
|---|---|---:|---:|
| `brightness_down` | `dev_perturbation` | `0.6000` | `0.7500` |
| `center_occlusion` | `heldout_perturbation` | `1.8000` | `1.5000` |
| `contrast_shift` | `dev_perturbation` | `0.8667` | `0.9167` |
| `salt_pepper` | `heldout_perturbation` | `1.1333` | `1.0833` |

## Publish Checks

| Check | Pass |
|---|---:|
| `package_available` | `True` |
| `completed_episodes` | `True` |
| `heldout_episodes` | `True` |
| `nonzero_pixel_delta` | `True` |
| `world_model_agent` | `False` |
| `multiple_world_model_paradigms` | `False` |
| `training_augmentation` | `False` |

## Final Determination

EXP05 now has an executable clean/perturbed Crafter environment smoke, but it is **not publishable as a world-model robustness result**. The runnable gate validates environment mechanics and held-out perturbation data flow. It does not evaluate a learned world-model agent, compare multiple paradigms, or test training-time augmentation.

The defensible decision is to park EXP05 for this cycle unless a trained Dreamer/stable-worldmodel/Craftax agent baseline is added with clean-score reproduction and multi-seed confidence intervals.
