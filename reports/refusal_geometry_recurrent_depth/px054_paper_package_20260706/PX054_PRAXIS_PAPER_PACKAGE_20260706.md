# PX-054 Praxis Paper Package

Generated: 2026-07-06

## Title

Depth-Indexed Refusal-Style Geometry in a Recurrent Language Model

## Praxis Thesis

Recurrent-depth language models expose a measurable representation surface: the same safe prompt can be evaluated at multiple recurrent step counts. PX-054 tests whether a refusal-style direction remains measurable and stable across recurrent depths in Huginn-0125.

The supported thesis is bounded:

> On a safe paraphrase-family prompt set, Huginn-0125 exposes depth-indexed latent states whose refusal-style direction is measurable and stable across recurrent depth.

## Status

**PUBLISHABLE_BOUNDED_POSITIVE**

PX-054 is now packaged as a defense-ready characterization paper. It should be presented as mechanistic characterization, not as a deployed safety defense or causal refusal mechanism proof.

## Experiment Chain

| Stage | Corpus / source | Status | Key result |
|---|---:|---|---|
| Source gate | Hugging Face model metadata | `SOURCE_GATE_PASS` | Public, ungated, Apache-2.0, Transformers-compatible, custom model code present, recurrent depth configured, `num_steps` documented. |
| Activation smoke gate | `60` latent rows | `ACTIVATION_GATE_PASS` | Depths `[4, 8, 16, 32]`; activation capture `1.0000`; cross-depth stability `0.8321`; benign-control FPR `0.0000`. |
| Scale gate | `600` latent rows | `SCALE_GATE_PASS` | `120` safe prompts; depths `[4, 8, 16, 32, 64]`; cross-depth stability `0.9257` with CI `[0.9067, 0.9273]`; benign-control FPR `0.0000`; worst refusal TPR `0.9750`. |
| Result synthesis | Source, smoke, scale | `BOUNDED_POSITIVE_CHARACTERIZATION` | Synthesis classifies PX-054 as positive within the safe, observational, no-intervention boundary. |

## What The Result Proves

1. Huginn-0125 exposes usable recurrent-depth latent states through the tested interface.
2. A refusal-style versus benign-helpful centroid direction can be measured at each tested depth.
3. The direction remains stable across depths `[4, 8, 16, 32, 64]`.
4. The measured direction does not over-flag benign-helpful or benign safety-control prompts under the registered thresholds.
5. The result survives family-level bootstrapping over prompt paraphrase families.

## Claim Boundary

PX-054 may claim:

- depth-indexed latent states were captured for Huginn-0125,
- a refusal-style direction was measurable on the safe prompt suite,
- the direction was stable across recurrent depths,
- benign-helpful and benign safety-control false positives were `0.0000` under the registered thresholds,
- the result is a bounded characterization positive.

PX-054 must not claim:

- causal refusal mechanism,
- deployed safety defense,
- jailbreak detection,
- refusal removal,
- safety ablation,
- adversarial robustness,
- transfer to other models without replication,
- real harmful-request behavior evaluation.

## Publication Shape

Recommended framing:

1. **Problem:** recurrent-depth models expose latent states across recurrence; we need safe methods to characterize whether response-style directions persist across depth.
2. **Method:** capture final-token latent states for safe refusal-style, benign-helpful, and benign safety-control prompts across `num_steps`.
3. **Metric:** compute refusal-helpful centroid directions at each depth, score controls, and measure pairwise cross-depth direction stability.
4. **Result:** scale gate passes with `600/600` captured rows, stability `0.9257`, benign-control FPR `0.0000`, and worst refusal TPR `0.9750`.
5. **Boundary:** observational characterization only; no intervention, no refusal removal, no jailbreak detection, no deployed safety claim.
6. **Next work:** held-out safe prompts and second recurrent-depth checkpoint replication.

## Primary Evidence Links

- Source gate preregistration: `reports/refusal_geometry_recurrent_depth/PX054_REFUSAL_GEOMETRY_SOURCE_GATE_20260705.md`
- Source-gate result: `reports/refusal_geometry_recurrent_depth/source_gate_20260705/PX054_SOURCE_GATE_RESULT_20260705.md`
- Activation-gate result: `reports/refusal_geometry_recurrent_depth/activation_gate_20260705/PX054_REFUSAL_GEOMETRY_ACTIVATION_GATE_20260705.md`
- Scale-gate result: `reports/refusal_geometry_recurrent_depth/scale_gate_20260705/PX054_REFUSAL_GEOMETRY_SCALE_GATE_20260705.md`
- Result synthesis: `reports/refusal_geometry_recurrent_depth/PX054_REFUSAL_GEOMETRY_RESULT_SYNTHESIS_20260705.md`
- Final manuscript: `reports/refusal_geometry_recurrent_depth/px054_final_manuscript_20260706/PX054_FINAL_MANUSCRIPT_20260706.md`
- Claim boundary: `reports/refusal_geometry_recurrent_depth/px054_paper_package_20260706/PX054_CLAIM_BOUNDARY_20260706.md`
- Final defense export: `reports/refusal_geometry_recurrent_depth/px054_final_defense_package_export_20260706/PX054_FINAL_DEFENSE_PACKAGE_EXPORT_20260706.md`

## Appendix A: Reproducibility Code Map

| Component | Path | Purpose |
|---|---|---|
| Source gate runner | `scripts/run_px054_refusal_geometry_source_gate.py` | Verifies Huginn source availability, license, recurrent-depth metadata, and safe activation-capture readiness. |
| Activation smoke runner | `cloud_jobs/px054_refusal_geometry_20260705/run_px054_refusal_geometry_activation_gate.py` | Captures smoke latent states over safe prompts and depths `[4, 8, 16, 32]`. |
| Activation smoke wrapper | `cloud_jobs/px054_refusal_geometry_20260705/run_on_instance.sh` | AWS execution wrapper for the smoke gate. |
| Scale gate runner | `cloud_jobs/px054_refusal_geometry_scale_20260705/run_px054_refusal_geometry_scale_gate.py` | Captures scale latent states, computes centroid directions, bootstraps by prompt family, and renders the scale report. |
| Scale gate wrapper | `cloud_jobs/px054_refusal_geometry_scale_20260705/run_on_instance.sh` | AWS execution wrapper for the scale gate. |
| Scale requirements | `cloud_jobs/px054_refusal_geometry_scale_20260705/requirements.txt` | Python package constraints for the cloud run. |

Re-run source gate locally:

```powershell
python scripts\run_px054_refusal_geometry_source_gate.py
```

Re-run scale gate on AWS with the cloud wrapper after syncing the `cloud_jobs/px054_refusal_geometry_scale_20260705` code package to the configured S3 path.
