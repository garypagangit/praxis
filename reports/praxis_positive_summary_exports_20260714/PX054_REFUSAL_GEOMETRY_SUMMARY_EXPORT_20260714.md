# PX-054 Summary Export

## Experiment

Title: Depth-Indexed Refusal-Style Geometry in a Recurrent Language Model

Praxis ID: PX-054

Status: Defense-ready bounded positive characterization.

## Executive Summary

PX-054 tested whether a recurrent-depth language model exposes stable refusal-style representation geometry as recurrence depth changes. The experiment is safe and observational: it uses safe refusal-style statements, benign-helpful statements, and benign safety-themed controls; it captures latent states; and it does not modify weights, remove refusals, optimize jailbreaks, or generate unsafe instructions. The scale gate passed strongly: 600/600 activation rows were captured across 120 safe prompts and depths 4, 8, 16, 32, and 64; cross-depth stability was 0.9257 with family-bootstrap CI [0.9067, 0.9273]; worst benign-control false-positive rate was 0.0000; and worst refusal true-positive rate was 0.9750.

## Thesis

Huginn-0125, a recurrent-depth language model, exposes depth-indexed latent states whose refusal-style direction can be measured and remains stable across recurrent depth on a safe paraphrase-family prompt suite.

## Objective

Determine whether Huginn-0125 exposes usable depth-indexed latent states and whether a safe refusal-style direction remains measurable across recurrent depths.

## What Was Tested

The source gate checked `tomg-group-umd/huginn-0125` for public access, Apache-2.0 licensing, Transformers compatibility, recurrent-depth configuration, and documented `num_steps`. The activation gates captured final-token latent states across recurrent depths and computed a refusal-style versus benign-helpful centroid direction. Benign safety-themed controls were included to test over-flagging.

## Key Results

Evidence layers:

| Layer | Status | Main result |
|---|---|---|
| Source gate | SOURCE_GATE_PASS | Huginn-0125 is public, ungated, Apache-2.0, Transformers-compatible, recurrent-depth configured, and documents `num_steps`. |
| Activation smoke gate | ACTIVATION_GATE_PASS | 60/60 latent rows captured across depths [4, 8, 16, 32]; cross-depth stability 0.8321; benign-control FPR 0.0000. |
| Scale gate | SCALE_GATE_PASS | 600/600 latent rows captured across 120 safe prompts and depths [4, 8, 16, 32, 64]; cross-depth stability 0.9257; CI [0.9067, 0.9273]; benign-control FPR 0.0000; worst refusal TPR 0.9750. |

Scale-gate metrics:

| Metric | Result | 95% family-bootstrap interval |
|---|---:|---:|
| Captured rows | 600/600 | n/a |
| Activation capture success | 1.0000 | n/a |
| Prompt validity | 1.0000 | n/a |
| Cross-depth direction stability | 0.9257 | [0.9067, 0.9273] |
| Worst benign-control FPR | 0.0000 | [0.0000, 0.0000] |
| Worst helpful FPR | 0.0000 | [0.0000, 0.0000] |
| Worst refusal TPR | 0.9750 | [0.9500, 1.0000] |

Per-depth behavior:

| Num steps | Centroid cosine | Refusal TPR | Helpful FPR | Benign-control FPR |
|---:|---:|---:|---:|---:|
| 4 | 0.6159 | 1.0000 | 0.0000 | 0.0000 |
| 8 | 0.6472 | 1.0000 | 0.0000 | 0.0000 |
| 16 | 0.6377 | 0.9750 | 0.0000 | 0.0000 |
| 32 | 0.6367 | 0.9750 | 0.0000 | 0.0000 |
| 64 | 0.6372 | 0.9750 | 0.0000 | 0.0000 |

## What It Proves

PX-054 proves that, on a safe paraphrase-family prompt set, Huginn-0125 exposes depth-indexed latent states whose refusal-style direction is measurable and stable across recurrent depth. It also shows that the registered threshold did not over-flag benign-helpful or benign safety-control rows in the scale corpus.

## What It Does Not Prove

It does not prove a causal refusal mechanism, a deployed safety defense, jailbreak detection, refusal removal, adversarial robustness, or transfer to other models without replication. It is representation characterization, not a control method.

## Defense Use

Use PX-054 as a bounded mechanistic-safety chapter after the deployment-defense papers. The correct defense posture is conservative: the result is real, measured, and publishable, but it is not a claim about changing model behavior.

## Evidence Links

- `reports/refusal_geometry_recurrent_depth/px054_final_manuscript_20260706/PX054_FINAL_MANUSCRIPT_20260706.md`
- `reports/refusal_geometry_recurrent_depth/px054_final_defense_package_export_20260706/PX054_FINAL_DEFENSE_PACKAGE_EXPORT_20260706.md`
- `reports/refusal_geometry_recurrent_depth/px054_paper_package_20260706/PX054_PRAXIS_PAPER_PACKAGE_20260706.md`
- `reports/refusal_geometry_recurrent_depth/px054_paper_package_20260706/PX054_CLAIM_BOUNDARY_20260706.md`
- `reports/refusal_geometry_recurrent_depth/PX054_REFUSAL_GEOMETRY_RESULT_SYNTHESIS_20260705.md`
- `reports/refusal_geometry_recurrent_depth/scale_gate_20260705/PX054_REFUSAL_GEOMETRY_SCALE_GATE_20260705.md`
- `reports/refusal_geometry_recurrent_depth/scale_gate_20260705/summary.json`
- `reports/refusal_geometry_recurrent_depth/scale_gate_20260705/activation_rows.csv`
- `reports/refusal_geometry_recurrent_depth/scale_gate_20260705/vectors_reduced.json`
- `scripts/run_px054_refusal_geometry_source_gate.py`
- `cloud_jobs/px054_refusal_geometry_20260705/run_px054_refusal_geometry_activation_gate.py`
- `cloud_jobs/px054_refusal_geometry_scale_20260705/run_px054_refusal_geometry_scale_gate.py`

