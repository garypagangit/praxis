# PX-054 Refusal Geometry Across Recurrent Depth Source Gate

Generated: 2026-07-05

## Status

**SOURCE-GATE CANDIDATE - queued behind PX-049**

This row captures the proposed Huginn/recurrent-depth mechanistic experiment. It is intentionally queued behind PX-049 and must not be co-gated with PX-049.

## Framing

White-box characterization of refusal representation geometry across recurrent depth. The project is allowed to detect and characterize representational differences. It is not allowed to remove, weaken, bypass, or optimize against safety behavior.

Source anchors:

- Recurrent-depth paper: `https://arxiv.org/abs/2502.05171`
- Huginn model card: `https://huggingface.co/tomg-group-umd/huginn-0125`

## Thesis Selection Rule

The thesis remains undetermined until source gate and activation-access checks finish.

Possible registered branches:

1. If refusal and benign-control prompts separate consistently across recurrent depth, the experiment becomes a characterization paper about depth-indexed safety geometry.
2. If separation is weak or unstable, the experiment becomes a negative/boundary report about the limits of recurrent-depth refusal probing.
3. If the model/artifacts are not accessible or the run requires unsafe intervention methods, the experiment is closed as source-gate blocked.

## Required Source Gate

- Confirm open weights and license for the recurrent-depth model under test.
- Confirm activation capture across recurrent depth without model surgery that changes behavior.
- Build only benign/safety-classification prompts. Do not use operational harmful instructions.
- Pre-register metrics before running any model pass.
- Keep every threshold marked as `[TARGET]` until measured results exist.

## Candidate Metrics

All values below are targets, not measurements.

| Metric | Target |
|---|---:|
| Activation capture success | `[TARGET] >= 0.95` |
| Prompt parse/safety-label validity | `[TARGET] >= 0.95` |
| Cross-depth direction stability | `[TARGET] >= 0.30` |
| Benign-control false-positive rate | `[TARGET] <= 0.10` |

## Hard Boundaries

- No refusal-vector deletion.
- No jailbreak optimization.
- No abliteration or safety-pruning experiment.
- No harmful instruction generation.
- No claim that a safety mechanism has been bypassed.

PX-054 can only become a positive if it stays inside characterization and produces stable, reproducible, benign activation geometry evidence.
