# PX-054 Refusal Geometry Across Recurrent Depth Result Synthesis

Generated: 2026-07-05

## Status

**ACTIVATION-GATE PASS - promising characterization candidate, not final positive**

PX-054 has now cleared the first two safe gates:

1. Source gate: Huginn-0125 is public, ungated, Apache-2.0, Transformers-compatible, and exposes recurrent depth through `num_steps`.
2. Activation gate: AWS g5 run captured latent states across recurrent depths without unsafe prompt content or model intervention.

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

## Activation Gate Result

Run: AWS g5.xlarge, Huginn-0125, bfloat16, depths `[4, 8, 16, 32]`.

Prompt set:

- 5 benign refusal-style statements.
- 5 benign-helpful statements.
- 5 benign safety-themed controls.

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

## Interpretation

The first measured result is positive as a smoke/characterization gate: Huginn exposes usable latent states across recurrent depths, and a refusal-style versus benign-helpful direction remains stable from `num_steps=4` through `num_steps=32` on the small safe prompt set.

This does not yet prove a publishable mechanistic safety result. It is too small, uses statement-style prompts rather than a broader controlled prompt suite, and has not been replicated across seeds, prompt paraphrases, or another recurrent-depth checkpoint.

## Claim Boundary

Allowed claim now:

> On a small safe prompt set, Huginn-0125 exposes depth-indexed latent states whose refusal-style direction is measurable and stable across recurrent depth.

Not allowed:

- No claim of causal refusal mechanism.
- No claim of deployed safety defense.
- No claim of jailbreak detection.
- No claim based on refusal removal, safety ablation, or adversarial optimization.

## Next Gate

Run a scale-up characterization gate:

1. Expand to at least 100 safe prompts.
2. Add paraphrase families for refusal-style, benign-helpful, and benign safety-control classes.
3. Keep depths `[4, 8, 16, 32, 64]` if memory permits.
4. Report bootstrap confidence intervals for cross-depth stability and benign-control false-positive rate.
5. Optionally compare one intermediate Huginn checkpoint, if model access is clean.

Promotion threshold for a bounded PX-054 positive should require replicated stability, not just the current smoke pass.
