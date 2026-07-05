# PX-054 Refusal Geometry Across Recurrent Depth Source Gate

Generated: 2026-07-05

## Status

**SOURCE GATE PASSED; ACTIVATION GATE PASSED ON SMALL SAFE SMOKE**

This row captures the proposed Huginn/recurrent-depth mechanistic experiment. It began as queued behind PX-049, then was run as the first new experiment after user direction on 2026-07-05. It remains characterization only and must not be merged with offensive jailbreak or refusal-removal work.

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

## 2026-07-05 Gate Update

The source gate passed, and the first AWS activation smoke also passed.

Measured activation-gate highlights:

- Captured rows: `60/60`
- Activation capture success: `1.0000`
- Prompt validity: `1.0000`
- Cross-depth direction stability: `0.8321`
- Worst benign-control false-positive rate: `0.0000`

Evidence:

- `reports/refusal_geometry_recurrent_depth/source_gate_20260705/PX054_SOURCE_GATE_RESULT_20260705.md`
- `reports/refusal_geometry_recurrent_depth/activation_gate_20260705/PX054_REFUSAL_GEOMETRY_ACTIVATION_GATE_20260705.md`
- `reports/refusal_geometry_recurrent_depth/PX054_REFUSAL_GEOMETRY_RESULT_SYNTHESIS_20260705.md`

Status boundary: this is a promising activation-gate pass, not a final positive. A larger prompt/paraphrase/CI gate is required before PX-054 should be promoted.
