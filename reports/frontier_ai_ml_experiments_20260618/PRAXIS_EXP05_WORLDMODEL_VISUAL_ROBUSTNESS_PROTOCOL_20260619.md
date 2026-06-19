# Praxis EXP05 Protocol - Cross-Paradigm Visual Robustness of World-Model Agents

Generated: 2026-06-19

Status: **source/readiness gate active; agent evaluation pending**

Source brief: `C:\Users\garyp\Downloads\AI_ML_Praxis_Experiment_Templates.docx`

## Experiment ID

`frontier-exp05-worldmodel-visual-robustness`

## Working Title

**World-Model Visual Robustness Leaderboard**

## Thesis

World-model agents differ in visual distribution-shift robustness depending on representation and planning paradigm. A controlled evaluation platform can measure clean-score retention under perturbations and test whether observation augmentation closes the robustness gap without damaging clean performance.

## Research Questions

| ID | Research question | Decision evidence |
|---|---|---|
| RQ1 | How much does each world-model paradigm degrade under visual perturbation? | Clean score, perturbed score, and score-retention ratio. |
| RQ2 | Which paradigm is most robust across held-out perturbations? | Interquartile mean retention and bootstrap CIs across seeds. |
| RQ3 | Can observation augmentation improve robustness with low clean-score cost? | Augmented versus baseline retention and clean-score delta. |

## Hypotheses

| ID | Hypothesis | Promotion gate |
|---|---|---|
| H1 | Robustness retention differs across world-model paradigms under identical visual wrappers. | At least two paradigms, five seeds, bootstrap CI on retention gap. |
| H2 | Held-out perturbations reveal failures not visible on dev perturbations. | Held-out perturbation retention lower than clean/dev-only estimate. |
| H3 | Training-time observation augmentation improves held-out retention with clean-score cost `<=5%`. | Augmented agent clean/perturbed comparison. |

## Literature Review

Crafter provides a compact benchmark for agent capabilities in visually grounded survival tasks. Craftax reimplements and extends Crafter in JAX for faster experimentation. DreamerV3 is a representative world-model RL agent. Stable-worldmodel proposes a unified research platform for data collection, training, and evaluation across standardized environments.

The EXP05 first gate does not claim agent robustness. It verifies source availability and freezes perturbation wrappers so a later clean/perturbed agent run can be audited.

## Dataset And Tool Plan

| Source | First-gate role | Formal role |
|---|---|---|
| `galilai-group/stable-worldmodel` | Candidate unified world-model pipeline. | Evaluation harness if install succeeds. |
| `danijar/crafter` | Baseline environment and task reference. | Clean and perturbed score source. |
| `michaeltmatthews/craftax` | Fast JAX/Crafter-style environment. | Fast smoke and later scaling path. |
| `danijar/dreamerv3` | Representative world-model agent. | Baseline paradigm comparison. |

## Split Discipline

| Split role | Source | Used for | May tune? | Final claim use |
|---|---|---|---:|---|
| `dev_perturbation` | Brightness/contrast wrappers | Tune wrapper implementation and data flow. | Yes. | No headline metric. |
| `heldout_perturbation` | Occlusion/noise wrappers | Strict robustness test. | No. | Primary metric. |
| `heldout_environment` | Different game/level family | External validity. | No. | Promotion metric. |

## GMR - Goal / Method / Rationale

**Goal.** Build a reproducible world-model visual robustness benchmark.

**Method.** Verify source packages, freeze clean/dev/held-out visual wrappers, run clean plus perturbed environment smoke, then scale to agent score retention across paradigms and seeds.

**Rationale.** A visual robustness claim is meaningless if perturbations alter environment semantics or if clean baselines are not reproducible. The first gate checks wrapper shape, determinism, and perturbation separation before any score claim.

## Feature Engineering Plan

| Feature group | Examples |
|---|---|
| Observation features | shape, dtype, mean pixel delta, channel statistics. |
| Perturbation metadata | type, strength, dev versus heldout role. |
| Agent metrics | clean score, perturbed score, retention, episode length. |
| Robustness summary | interquartile mean, bootstrap CI, clean-score cost. |

Optuna is not used in the source gate. Later hyperparameter tuning must stay on clean/dev perturbations and cannot see held-out perturbation results.

## Results Gates

| Stage | Pass | Stop or reframe |
|---|---|---|
| Source/wrapper gate | Repos/packages accessible; visual wrappers preserve shape and create nonzero pixel deltas. | Core sources inaccessible or wrappers mutate format/semantics. |
| Environment smoke | Clean plus one perturbed Crafter/Craftax rollout runs. | Environment cannot be installed or reset deterministically. |
| Robustness gate | Five seeds, clean/perturbed score retention, held-out perturbation. | Clean baseline cannot be reproduced. |
| Promotion | Multiple paradigms and augmentation remedy with CIs. | Only a single-agent/single-seed anecdote. |

## What Not To Claim

- Do not claim robustness from perturbation-wrapper smoke alone.
- Do not compare paradigms unless clean baselines are reproduced.
- Do not tune augmentation on held-out perturbations.
- Do not count visual wrappers that alter action semantics as perception-only shifts.
