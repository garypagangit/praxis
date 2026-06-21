# Frontier AI/ML Batch Final Determination

Date: 2026-06-21

Scope: five experiments derived from `C:\Users\garyp\Downloads\AI_ML_Praxis_Experiment_Templates.docx`.

## Executive Decision

The batch is complete enough for a final cycle decision. None of the five new frontier experiments should be promoted as a publishable positive thesis result in the current cycle. EXP01 remains a useful provisional measurement harness; EXP02 is a strong safety pilot blocked by over-refusal; EXP03 is stopped/reframed because the public LIBERO path lacks language metadata and the simulator stack is absent; EXP04 has a clean controlled KG smoke but fails the external verifier promotion test; EXP05 now has a real Crafter environment smoke but not a world-model agent result.

The practical decision is to stop rescue runs on this batch and preserve it as a defensible experiment audit trail. The current strongest publishable portfolio result remains Praxis 06 TTA, with Praxis 07 as the narrow CTI-compliance positive.

## Final Decision Table

| Experiment | Final status | Best evidence | Final determination |
|---|---|---|---|
| EXP01 - TTC Transferability | Provisional measurement result; not promoted | Full AWS matrix: `4` models, `160` rows, `2,560` scored rows, `32` transfer rows. Best Qwen2.5-7B validation policy `majority_vote K=8`; strict MATH-500 holdout `0.2250`; predictor leave-one-target-family R2 `-14.9408`. | Keep as harness/provisional evidence only. Not publishable without verifier best-of-N, sequential refinement/H3 closure, scoring audit, and CIs. |
| EXP02 - Self-Jailbreak Guardrail | Mixed; not promoted | Open guardian response-prefix recall `1.0000`, unsafe exposure `0.1310`, but benign false-refusal `0.8700` and safe-response block `0.1818`. | Park. The early-detection signal is real, but utility failure blocks a safety claim. |
| EXP03 - VLA Instruction Diversity | Final stop/reframe | Public `lerobot/libero_10`: `101,469` frames, `379` episodes, `10` task indices, but data columns are only state/action/time/index/task_index; no language columns or task text metadata; required local imports `0/5`. | Stop for this cycle. Public data supports data-loader work but not instruction-diversity VLA evaluation. |
| EXP04 - KG Hallucination Verification | Failed promotion gate | Controlled KG smoke PASS: `60` claims, KG F1 `1.0000`, compounding slope `0.2500`. External HaluEval feature gate: evidence+numeric strict holdout F1 `0.7215`; response-only baseline F1 `0.7835`. | Do not publish as positive. Current evidence-aware verifier loses to response artifacts on sealed holdout. |
| EXP05 - World-Model Visual Robustness | Environment smoke pass; thesis not promoted | Crafter `25` clean/dev/held-out perturbation episodes completed. Held-out `center_occlusion` and `salt_pepper` ran with nonzero pixel shift, but agent was a deterministic checksum policy, not a learned world-model. | Park. Environment mechanics are proven; world-model robustness claim remains untested. |

## RQ/H Readout

| Experiment | RQ/H readout |
|---|---|
| EXP01 | RQ measurement harness works. H1/H2/H3 not proven because verifier best-of-N and sequential refinement are missing and strict holdout performance is weak. |
| EXP02 | H1-like response-step detection signal is strong; H2/H3 fail because safe/benign utility controls over-block. |
| EXP03 | RQ1-RQ3 cannot be tested from the available public data because instruction text is absent and the simulator/model stack is not ready. |
| EXP04 | H1 controlled compounding signal passes. H2/H3 fail at external verifier stage because evidence features do not beat response-only artifacts. |
| EXP05 | Environment/wrapper gate passes. H1-H3 are untested for world models because no trained world-model agent, multi-paradigm comparison, or augmentation remedy ran. |

## New Artifacts

| Artifact | Purpose |
|---|---|
| `configs/frontier_exp03_libero_data_gate_20260621.json` | EXP03 final data/simulator readiness gate config. |
| `scripts/run_frontier_exp03_libero_data_gate.py` | EXP03 public LIBERO schema, metadata, and import-readiness runner. |
| `runs/frontier-exp03-libero-data-gate-20260621/EXP03_LIBERO_DATA_GATE_RESULT_20260621.md` | EXP03 final stop/reframe report. |
| `configs/frontier_exp04_dialogue_feature_gate_20260620.json` | EXP04 final external HaluEval feature-verifier gate config. |
| `scripts/run_frontier_exp04_dialogue_feature_gate.py` | EXP04 structured evidence-feature verifier runner. |
| `runs/frontier-exp04-dialogue-feature-gate-20260620/EXP04_DIALOGUE_FEATURE_GATE_RESULT_20260620.md` | EXP04 failed promotion gate. |
| `configs/frontier_exp05_crafter_rollout_gate_20260621.json` | EXP05 clean/perturbed Crafter rollout gate config. |
| `scripts/run_frontier_exp05_crafter_rollout_gate.py` | EXP05 executable environment smoke runner. |
| `runs/frontier-exp05-crafter-rollout-gate-20260621/EXP05_CRAFTER_ROLLOUT_GATE_RESULT_20260621.md` | EXP05 final environment-smoke report. |

## Internal Defensibility Challenge

| Challenge | Answer |
|---|---|
| Did we stop before final determinations? | No. Each experiment now has either a measured preliminary result, a measured failed promotion gate, or a measured stop/reframe gate. |
| Did any result prove a new publishable thesis? | No. The batch produced useful constraints, not a new positive publication claim. |
| Did we use strict holdouts where applicable? | Yes for EXP01, EXP02, EXP04, and perturbation roles in EXP05. EXP03 could not advance to success holdout because instruction metadata and simulator imports were missing. |
| Did we overclaim environment/source gates? | No. EXP03 and EXP05 explicitly separate readiness/environment evidence from scientific performance claims. |
| Should AWS be restarted for more rescue runs? | Not for this batch. AWS SSO is connected, but the remaining blockers are claim design, labels/metadata, and agent availability, not raw GPU speed. |

## Final Recommendation

Close this frontier batch for the current cycle. Keep the artifacts as negative/control evidence and return publication effort to the already stronger Praxis 06 and Praxis 07 packages.
