# Depth-Indexed Refusal-Style Geometry in a Recurrent Language Model

Date: 2026-07-06

Praxis ID: `PX-054`

Status: **FINAL MANUSCRIPT DRAFT - PUBLISHABLE BOUNDED POSITIVE**

## Abstract

Recurrent-depth language models expose a natural question for mechanistic characterization: do safety-relevant response styles form stable latent directions as recurrence depth changes? PX-054 evaluates this question on `tomg-group-umd/huginn-0125`, a public recurrent-depth transformer. The experiment is safe and observational: it captures latent states for refusal-style safe statements, benign-helpful statements, and benign safety-themed controls across recurrent depths without modifying model weights, removing refusals, optimizing jailbreaks, or generating unsafe instructions. The source gate confirmed a public, ungated, Apache-2.0, Transformers-compatible model with documented `num_steps` recurrence. A smoke activation gate captured `60/60` latent rows across depths `[4, 8, 16, 32]`. The scale gate captured `600/600` rows over `120` safe prompts, `10` paraphrase families per label, and depths `[4, 8, 16, 32, 64]`. The refusal-style versus benign-helpful direction remained stable across depth with cross-depth direction stability `0.9257` and 95% family-bootstrap CI `[0.9067, 0.9273]`, while the worst benign-control and benign-helpful false-positive rates were both `0.0000`, and the worst refusal true-positive rate was `0.9750`. PX-054 supports a bounded characterization claim: on this safe prompt suite, Huginn exposes depth-indexed latent states whose refusal-style direction is measurable and stable across recurrent depth. It does not prove a causal refusal mechanism, deployed safety defense, jailbreak detector, refusal-removal method, or transfer to other models.

## Praxis Summary

**Praxis thesis:** Recurrent-depth language models can be characterized by tracking whether a refusal-style representation direction remains stable as the number of recurrent steps changes.

**Objective:** Determine whether Huginn-0125 exposes usable depth-indexed latent states and whether a safe refusal-style direction remains measurable across recurrent depths.

**Research question:** On a safe paraphrase-family prompt set, is there a stable latent direction separating refusal-style safe statements from benign-helpful statements across recurrent depths?

**Hypothesis:** If Huginn exposes consistent recurrent-depth latent states, then a refusal-style versus benign-helpful centroid direction should remain stable across depths and should not over-flag benign safety-themed controls.

## 1. Problem

Most LLM safety evaluations focus on external behavior. Recurrent-depth models add a different surface: the same prompt can be evaluated at different recurrent step counts. That makes it possible to ask whether a representation direction appears early, late, or consistently across recurrence.

PX-054 studies that surface without intervention. The experiment does not try to make the model safer or less safe. It measures whether a refusal-style representation direction is present and stable across depth on safe text.

## 2. Safety And Claim Boundary

PX-054 is characterization-only.

The experiment uses:

- refusal-style safe statements,
- benign-helpful statements,
- benign safety-themed controls.

The experiment does not:

- generate unsafe instructions,
- alter model weights,
- perform refusal removal,
- optimize jailbreaks,
- test adversarial bypasses,
- claim deployed safety monitoring.

The positive claim is narrow:

> On a safe paraphrase-family prompt set, Huginn-0125 exposes depth-indexed latent states whose refusal-style direction is measurable and stable across recurrent depth.

## 3. Method

### 3.1 Model

The source gate checks `tomg-group-umd/huginn-0125` through Hugging Face model metadata and model files.

| Source check | Result |
|---|---:|
| Public / ungated model | `PASS` |
| Apache-2.0 license tag | `PASS` |
| Transformers model | `PASS` |
| Custom model code present | `PASS` |
| Safetensors index present | `PASS` |
| AutoModel mapping present | `PASS` |
| Recurrent depth configured | `PASS` |
| `num_steps` documented | `PASS` |
| Paper tag present | `PASS` |

Pinned source-gate metadata:

| Field | Value |
|---|---|
| Model ID | `tomg-group-umd/huginn-0125` |
| Hugging Face SHA | `bb6621b65e90b6a4b9b29ef88dc83866d450470c` |
| License tag | `license:apache-2.0` |
| Model type | `huginn_raven` |
| Mean recurrence | `32` |
| Hidden size | `5280` |

### 3.2 Prompt Set

The scale gate uses `120` safe prompts:

| Label | Families | Variants | Purpose |
|---|---:|---:|---|
| `refusal_style` | `10` | `40` | Safe refusal-style statements. |
| `benign_helpful` | `10` | `40` | Helpful non-refusal statements. |
| `benign_safety_control` | `10` | `40` | Benign safety-themed controls used to test over-flagging. |

The family structure matters because bootstrapping resamples paraphrase families, not individual rows.

### 3.3 Activation Capture

The AWS scale run used:

| Field | Value |
|---|---|
| Instance class | `g5.xlarge` |
| Model | `tomg-group-umd/huginn-0125` |
| Dtype | `bfloat16` |
| Depths | `[4, 8, 16, 32, 64]` |
| Max input tokens | `128` |
| Reduced vector dimensions | `512` |
| Bootstrap iterations | `300` |

For each prompt and depth, the runner calls Huginn with a chosen `num_steps`, captures the final-token latent state, normalizes a reduced vector, and logs token count, latent norm, and logit entropy. No generation text is sampled for the metric.

### 3.4 Direction Metric

For each depth:

1. Compute the refusal-style centroid.
2. Compute the benign-helpful centroid.
3. Define the direction as the normalized difference between those centroids.
4. Score refusal, helpful, and safety-control vectors by dot product with that direction.
5. Set the threshold halfway between the mean refusal score and mean helpful score.
6. Report refusal true-positive rate, helpful false-positive rate, and safety-control false-positive rate.

Cross-depth direction stability is the mean pairwise cosine similarity among the per-depth refusal-style directions.

The bootstrap resamples prompt families with all variants, using seed `54054`.

## 4. Results

### 4.1 Activation Smoke Gate

| Metric | Result |
|---|---:|
| Status | `ACTIVATION_GATE_PASS` |
| Captured rows | `60/60` |
| Activation capture success | `1.0000` |
| Prompt validity | `1.0000` |
| Cross-depth direction stability | `0.8321` |
| Worst benign-control false-positive rate | `0.0000` |

The smoke gate established that Huginn exposed usable latent states across recurrent depths.

### 4.2 Scale Gate

| Metric | Result | 95% family-bootstrap interval |
|---|---:|---:|
| Status | `SCALE_GATE_PASS` | n/a |
| Captured rows | `600/600` | n/a |
| Activation capture success | `1.0000` | n/a |
| Prompt validity | `1.0000` | n/a |
| Cross-depth direction stability | `0.9257` | `[0.9067, 0.9273]` |
| Worst benign-control FPR | `0.0000` | `[0.0000, 0.0000]` |
| Worst helpful FPR | `0.0000` | `[0.0000, 0.0000]` |
| Worst refusal TPR | `0.9750` | `[0.9500, 1.0000]` |

### 4.3 Per-Depth Behavior

| Num steps | Centroid cosine | Refusal TPR | Helpful FPR | Benign-control FPR |
|---:|---:|---:|---:|---:|
| `4` | `0.6159` | `1.0000` | `0.0000` | `0.0000` |
| `8` | `0.6472` | `1.0000` | `0.0000` | `0.0000` |
| `16` | `0.6377` | `0.9750` | `0.0000` | `0.0000` |
| `32` | `0.6367` | `0.9750` | `0.0000` | `0.0000` |
| `64` | `0.6372` | `0.9750` | `0.0000` | `0.0000` |

The result is stable across the full tested recurrence range. Refusal-style statements remain separable from benign-helpful statements, and benign safety-themed controls do not trigger false positives under the registered threshold.

## 5. Supported Claim

PX-054 supports this claim:

> On a safe paraphrase-family prompt set, Huginn-0125 exposes depth-indexed latent states whose refusal-style direction is measurable and stable across recurrent depth.

The claim is supported by:

- public and reproducible source-gate checks,
- successful latent-state capture on a smoke gate,
- successful latent-state capture on a 600-row scale gate,
- cross-depth stability above threshold with family-bootstrap confidence intervals,
- zero observed false positives on benign-helpful and benign safety-control rows under the registered thresholds.

## 6. Interpretation

PX-054 is a useful mechanistic characterization result. It shows that the recurrent-depth interface is not only a decoding control; it also exposes representation measurements that remain coherent as recurrence depth changes.

The result should be framed as representation geometry, not safety control. The experiment identifies a measurable stable direction on safe prompts. It does not show that this direction causes refusal behavior, generalizes to adversarial prompts, or can be used as a deployed detector.

## 7. Limitations

1. The prompt set is safe and synthetic; it does not evaluate real harmful-request handling.
2. The experiment is observational; it does not intervene on latent states.
3. The result is currently one-model evidence on Huginn-0125.
4. The scale gate uses reduced latent vectors, not full hidden-state publication.
5. The threshold is internal to each depth, so the result is about stable direction geometry rather than a universal fixed classifier.
6. The experiment does not test transfer to non-recurrent models or other recurrent-depth checkpoints.

## 8. Ethics And Safety

PX-054 was designed to avoid offensive safety research. It uses safe refusal-style text and benign controls, records latent vectors, and does not perform refusal removal, jailbreak optimization, safety ablation, or model modification. The safe boundary is essential to the claim.

## 9. Reproducibility Record

| Artifact | Purpose |
|---|---|
| `reports/refusal_geometry_recurrent_depth/PX054_REFUSAL_GEOMETRY_SOURCE_GATE_20260705.md` | Source-gate preregistration and safety boundary. |
| `reports/refusal_geometry_recurrent_depth/source_gate_20260705/PX054_SOURCE_GATE_RESULT_20260705.md` | Source-gate result and model metadata. |
| `reports/refusal_geometry_recurrent_depth/source_gate_20260705/summary.json` | Machine-readable source-gate summary. |
| `reports/refusal_geometry_recurrent_depth/activation_gate_20260705/PX054_REFUSAL_GEOMETRY_ACTIVATION_GATE_20260705.md` | Smoke activation-gate result. |
| `reports/refusal_geometry_recurrent_depth/activation_gate_20260705/summary.json` | Machine-readable smoke-gate summary. |
| `reports/refusal_geometry_recurrent_depth/activation_gate_20260705/activation_rows.csv` | Smoke-gate row-level activation metadata. |
| `reports/refusal_geometry_recurrent_depth/scale_gate_20260705/PX054_REFUSAL_GEOMETRY_SCALE_GATE_20260705.md` | Scale-gate result. |
| `reports/refusal_geometry_recurrent_depth/scale_gate_20260705/summary.json` | Machine-readable scale-gate summary. |
| `reports/refusal_geometry_recurrent_depth/scale_gate_20260705/activation_rows.csv` | Scale-gate row-level activation metadata. |
| `reports/refusal_geometry_recurrent_depth/scale_gate_20260705/vectors_reduced.json` | Reduced latent vectors used for review and reproducibility. |
| `reports/refusal_geometry_recurrent_depth/PX054_REFUSAL_GEOMETRY_RESULT_SYNTHESIS_20260705.md` | Pre-package result synthesis. |
| `reports/refusal_geometry_recurrent_depth/px054_paper_package_20260706/PX054_CLAIM_BOUNDARY_20260706.md` | Claim-boundary checklist. |
| `reports/refusal_geometry_recurrent_depth/px054_final_defense_package_export_20260706/PX054_FINAL_DEFENSE_PACKAGE_EXPORT_20260706.md` | Defense package export. |
| `scripts/run_px054_refusal_geometry_source_gate.py` | Source-gate runner. |
| `cloud_jobs/px054_refusal_geometry_20260705/run_px054_refusal_geometry_activation_gate.py` | Smoke activation-gate cloud runner. |
| `cloud_jobs/px054_refusal_geometry_scale_20260705/run_px054_refusal_geometry_scale_gate.py` | Scale-gate cloud runner. |
| `cloud_jobs/px054_refusal_geometry_scale_20260705/run_on_instance.sh` | AWS execution wrapper for the scale gate. |

## 10. Conclusion

PX-054 is defense-ready as a bounded positive characterization paper. It should be presented after PX-050 or as a separate mechanistic-safety chapter. The correct defense posture is conservative: Huginn-0125 exposes stable depth-indexed refusal-style geometry on safe prompts. The result is real and publishable, but it is not a causal safety mechanism claim or a deployed safety defense.

## Appendix A: Portable Metric Sketch

The full implementation lives in the cloud runner paths listed above. This compact sketch captures the core PX-054 metric once reduced latent vectors have been captured.

```python
#!/usr/bin/env python3
"""
PX-054 portable refusal-style geometry metric sketch.

Purpose:
    Given reduced latent vectors with labels and recurrent depth values,
    compute a refusal-style direction at each depth and summarize whether
    that direction remains stable across depths.

Safety:
    This code analyzes stored vectors only. It does not generate text,
    modify a model, remove refusals, or optimize adversarial prompts.
"""

import itertools
import math


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(a):
    return math.sqrt(dot(a, a))


def normalize(a):
    scale = norm(a)
    return [x / scale for x in a] if scale else list(a)


def mean_vector(vectors):
    n = len(vectors)
    return [sum(values) / n for values in zip(*vectors)]


def cosine(a, b):
    denom = norm(a) * norm(b)
    return dot(a, b) / denom if denom else 0.0


def summarize_depth(rows, depth):
    depth_rows = [row for row in rows if row["num_steps"] == depth]
    refusal = [row["vector"] for row in depth_rows if row["label"] == "refusal_style"]
    helpful = [row["vector"] for row in depth_rows if row["label"] == "benign_helpful"]
    control = [row["vector"] for row in depth_rows if row["label"] == "benign_safety_control"]

    refusal_mean = mean_vector(refusal)
    helpful_mean = mean_vector(helpful)
    direction = normalize([r - h for r, h in zip(refusal_mean, helpful_mean)])

    refusal_scores = [dot(vector, direction) for vector in refusal]
    helpful_scores = [dot(vector, direction) for vector in helpful]
    control_scores = [dot(vector, direction) for vector in control]
    threshold = (sum(refusal_scores) / len(refusal_scores) + sum(helpful_scores) / len(helpful_scores)) / 2

    return {
        "num_steps": depth,
        "direction": direction,
        "refusal_tpr": sum(score >= threshold for score in refusal_scores) / len(refusal_scores),
        "helpful_fpr": sum(score >= threshold for score in helpful_scores) / len(helpful_scores),
        "control_fpr": sum(score >= threshold for score in control_scores) / len(control_scores),
    }


def summarize_geometry(rows):
    depths = sorted({row["num_steps"] for row in rows})
    by_depth = [summarize_depth(rows, depth) for depth in depths]
    pairwise = [
        cosine(left["direction"], right["direction"])
        for left, right in itertools.combinations(by_depth, 2)
    ]
    return {
        "cross_depth_direction_stability": sum(pairwise) / len(pairwise),
        "worst_refusal_tpr": min(row["refusal_tpr"] for row in by_depth),
        "worst_helpful_fpr": max(row["helpful_fpr"] for row in by_depth),
        "worst_control_fpr": max(row["control_fpr"] for row in by_depth),
        "depth_summaries": [
            {key: value for key, value in row.items() if key != "direction"}
            for row in by_depth
        ],
    }
```
