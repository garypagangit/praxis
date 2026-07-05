# PX-054 Refusal Geometry Across Recurrent Depth Result Synthesis

Generated: 2026-07-05

## Status

**SCALE_GATE_PASS - bounded positive characterization**

PX-054 has cleared three safe gates:

1. Source gate: Huginn-0125 is public, ungated, Apache-2.0, Transformers-compatible, and exposes recurrent depth through `num_steps`.
2. Activation smoke gate: AWS g5 run captured latent states across 15 safe prompts and depths `[4, 8, 16, 32]`.
3. Scale gate: AWS g5 run captured latent states across 120 safe prompts, 10 paraphrase families per label, and depths `[4, 8, 16, 32, 64]`.

## Source Gate Result

| Check family | Result |
|---|---:|
| Public / ungated model | `PASS` |
| Apache-2.0 license tag | `PASS` |
| Custom model code present | `PASS` |
| Safetensors index present | `PASS` |
| AutoModel mapping present | `PASS` |
| Recurrent depth configured | `PASS` |
| `num_steps` documented | `PASS` |
| Paper tag present | `PASS` |

Source-gate report:

```text
reports/refusal_geometry_recurrent_depth/source_gate_20260705/PX054_SOURCE_GATE_RESULT_20260705.md
```

## Activation Smoke Result

Run: AWS g5.xlarge, Huginn-0125, bfloat16, depths `[4, 8, 16, 32]`.

| Metric | Result |
|---|---:|
| Captured rows | `60/60` |
| Activation capture success | `1.0000` |
| Prompt validity | `1.0000` |
| Cross-depth direction stability | `0.8321` |
| Worst benign-control false-positive rate | `0.0000` |

Activation-gate report:

```text
reports/refusal_geometry_recurrent_depth/activation_gate_20260705/PX054_REFUSAL_GEOMETRY_ACTIVATION_GATE_20260705.md
```

## Scale Gate Result

Run: AWS g5.xlarge, Huginn-0125, bfloat16, depths `[4, 8, 16, 32, 64]`.

Prompt set:

- 40 refusal-style safe statements.
- 40 benign-helpful statements.
- 40 benign safety-themed controls.
- 10 paraphrase families per label.

| Metric | Result |
|---|---:|
| Captured rows | `600/600` |
| Activation capture success | `1.0000` |
| Prompt validity | `1.0000` |
| Cross-depth direction stability | `0.9257` |
| Cross-depth stability 95% bootstrap CI | `[0.9067, 0.9273]` |
| Worst benign-control false-positive rate | `0.0000` |
| Worst helpful false-positive rate | `0.0000` |
| Worst refusal true-positive rate | `0.9750` |
| Worst refusal TPR 95% bootstrap CI | `[0.9500, 1.0000]` |

Scale-gate report:

```text
reports/refusal_geometry_recurrent_depth/scale_gate_20260705/PX054_REFUSAL_GEOMETRY_SCALE_GATE_20260705.md
```

## Interpretation

PX-054 is now a bounded positive characterization result. Huginn exposes usable depth-indexed latent states, and a refusal-style versus benign-helpful direction remains stable across recurrent depths up to `num_steps=64` on a safe prompt suite with paraphrase-family bootstrapping.

This is stronger than the smoke result because it uses at least 100 safe prompts, adds paraphrase families, includes depth 64, and reports bootstrap confidence intervals.

## Claim Boundary

Allowed claim now:

> On a safe paraphrase-family prompt set, Huginn-0125 exposes depth-indexed latent states whose refusal-style direction is measurable and stable across recurrent depth.

Not allowed:

- No claim of causal refusal mechanism.
- No claim of deployed safety defense.
- No claim of jailbreak detection.
- No claim based on refusal removal, safety ablation, or adversarial optimization.
- No claim that the representation direction transfers to other models without replication.

## Next Gate

The next useful gate is replication, not more prompt expansion:

1. Pin the Huginn revision used for the run.
2. Repeat with a second recurrent-depth checkpoint if a clean checkpoint is available.
3. Add a blinded held-out safe prompt suite.
4. Keep the same no-intervention, characterization-only boundary.
