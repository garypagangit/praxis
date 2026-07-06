# PX-054 Claim Boundary

Generated: 2026-07-06

## Approved Claim

PX-054 supports a bounded positive Praxis claim:

> On a safe paraphrase-family prompt set, Huginn-0125 exposes depth-indexed latent states whose refusal-style direction is measurable and stable across recurrent depth.

This is a representation-characterization claim. It is not a causal, interventional, adversarial, or deployed-defense claim.

## Evidence Required In Any Paper Or Defense

| Evidence | Required wording |
|---|---|
| Source gate | Huginn-0125 was public, ungated, Apache-2.0, Transformers-compatible, recurrent-depth configured, and documented `num_steps`; source-gate status `SOURCE_GATE_PASS`. |
| Model revision | Hugging Face SHA `bb6621b65e90b6a4b9b29ef88dc83866d450470c`. |
| Activation smoke | `60/60` rows captured across depths `[4, 8, 16, 32]`; status `ACTIVATION_GATE_PASS`; cross-depth stability `0.8321`; benign-control FPR `0.0000`. |
| Scale gate | `600/600` rows captured across `120` safe prompts, `10` paraphrase families per label, and depths `[4, 8, 16, 32, 64]`; status `SCALE_GATE_PASS`. |
| Stability | Cross-depth direction stability `0.9257`; 95% family-bootstrap CI `[0.9067, 0.9273]`. |
| Refusal separation | Worst refusal TPR `0.9750`; 95% family-bootstrap CI `[0.9500, 1.0000]`. |
| Benign controls | Worst benign-control FPR `0.0000`; worst helpful FPR `0.0000`. |
| Safety boundary | Safe prompt text only; no generation of unsafe instructions, no weight edits, no refusal removal, no jailbreak optimization, no safety ablation. |

## Use This Language

- "bounded positive characterization"
- "depth-indexed latent states"
- "safe paraphrase-family prompt set"
- "refusal-style direction"
- "stable across recurrent depth"
- "observational, no-intervention analysis"
- "not a deployed safety defense"

## Avoid This Language

- "proves refusal mechanism"
- "finds the safety circuit"
- "jailbreak detector"
- "refusal-removal method"
- "safety intervention"
- "causal control"
- "generalizes to all models"
- "works on harmful prompts"

## Defense Readiness

PX-054 is ready for a Praxis defense section if the section keeps the claim narrow:

1. Show the source gate to establish that Huginn is an appropriate recurrent-depth system under a public reproducibility path.
2. Show the smoke gate to establish activation-capture feasibility.
3. Lead with the scale gate: `600/600` captured rows, depth range `[4, 8, 16, 32, 64]`, stability `0.9257`, benign-control FPR `0.0000`.
4. Explain the family-bootstrap design.
5. Emphasize safe, observational characterization.
6. State that held-out prompt replication and second-checkpoint replication are next work, not requirements for the current bounded positive.
