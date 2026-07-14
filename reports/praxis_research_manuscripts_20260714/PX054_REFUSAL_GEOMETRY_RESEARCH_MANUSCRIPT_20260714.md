# Depth-Indexed Refusal-Style Geometry in a Recurrent Language Model

Research manuscript draft

Praxis ID: PX-054

Generated: 2026-07-14

Status: Defense-ready bounded positive characterization

## Abstract

Recurrent-depth language models expose an unusual interpretability surface: the same prompt can be evaluated across different recurrent step counts. PX-054 asks whether a safe refusal-style representation direction remains measurable and stable across recurrent depth in Huginn-0125. The experiment is observational and safety-bounded. It uses safe refusal-style statements, benign-helpful statements, and benign safety-themed controls; captures latent states; computes centroid directions; and does not modify weights, remove refusals, optimize jailbreaks, or generate unsafe instructions. The source gate confirmed a public, ungated, Apache-2.0, Transformers-compatible recurrent-depth model with documented `num_steps`. The activation smoke gate captured 60/60 latent rows across depths [4, 8, 16, 32]. The scale gate captured 600/600 rows across 120 safe prompts and depths [4, 8, 16, 32, 64]. Cross-depth direction stability was 0.9257 with 95% family-bootstrap CI [0.9067, 0.9273], worst benign-control false-positive rate was 0.0000, and worst refusal true-positive rate was 0.9750. The result supports a bounded mechanistic characterization claim, not a deployed safety defense.

## 1. Introduction

Most LLM safety evaluations observe final text behavior. Recurrent-depth models add an internal axis: inference can reuse model components across a variable number of recurrent steps. PX-054 studies whether safety-relevant response style has stable representation geometry along that depth axis.

The paper is deliberately conservative. It does not test jailbreaks, harmful instructions, or model intervention. It measures whether a refusal-style direction is visible and stable on safe prompt text.

## 2. Prior Work

Huginn-0125 and recurrent-depth transformer work motivate the model choice. The Huginn model card describes a 3.5B latent recurrent-depth model trained at scale and exposes recurrence through model configuration and `num_steps`-style execution.

Recurrent-depth and test-time compute literature motivate the depth axis. Geiping et al.'s recurrent-depth approach scales computation by reusing latent reasoning steps, creating an interpretability surface across recurrence.

Representation engineering motivates direction-based analysis. Zou et al. frame representation reading as a way to measure high-level cognitive or behavioral concepts in latent space.

Refusal-direction work motivates the specific style direction. Arditi et al. argue that refusal behavior in many chat models is mediated by a low-dimensional direction in residual stream activations. PX-054 does not perform refusal removal or intervention; it borrows the safer descriptive question: is a refusal-style direction measurable?

## 3. Experimental Design Influences

The Huginn recurrent-depth model shaped the independent variable: number of recurrent steps.

Representation engineering shaped the metric: compute centroid directions from labeled activation groups rather than inspecting individual neurons.

Refusal-direction literature shaped the label contrast: refusal-style safe statements versus benign-helpful statements.

Safety concerns shaped the prompt set and claim boundary. The experiment uses safe refusal-style statements and benign controls only, and it forbids causal refusal-removal claims.

Family-bootstrap evaluation was included because paraphrase variants are not independent samples. The bootstrap resamples prompt families rather than individual rows.

## 4. Research Questions

RQ1: Does Huginn-0125 expose usable latent states across recurrent depths?

RQ2: Is a refusal-style versus benign-helpful direction measurable at each tested depth?

RQ3: Does the direction remain stable across depths?

RQ4: Does the registered threshold avoid over-flagging benign-helpful and benign safety-control prompts?

## 5. Data and Methods

The source gate checks `tomg-group-umd/huginn-0125` for public availability, Apache-2.0 licensing, Transformers compatibility, custom model code, recurrent-depth configuration, and documented recurrence controls.

The scale prompt set contains 120 safe prompts.

| Label | Families | Variants | Purpose |
|---|---:|---:|---|
| refusal_style | 10 | 40 | Safe refusal-style statements |
| benign_helpful | 10 | 40 | Helpful non-refusal statements |
| benign_safety_control | 10 | 40 | Benign safety-themed over-flagging controls |

The AWS scale run used depths [4, 8, 16, 32, 64], bfloat16 inference, max input tokens 128, reduced vector dimension 512, and 300 family-bootstrap iterations.

For each depth:

1. Compute the refusal-style centroid.
2. Compute the benign-helpful centroid.
3. Define the direction as the normalized centroid difference.
4. Score each row by dot product with the direction.
5. Place the threshold halfway between mean refusal and mean helpful scores.
6. Report refusal true-positive rate, helpful false-positive rate, and benign-control false-positive rate.

Cross-depth direction stability is the mean pairwise cosine among per-depth directions.

## 6. Results

Activation smoke gate:

| Metric | Result |
|---|---:|
| Captured rows | 60/60 |
| Activation capture success | 1.0000 |
| Prompt validity | 1.0000 |
| Cross-depth direction stability | 0.8321 |
| Worst benign-control false-positive rate | 0.0000 |

Scale gate:

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

## 7. Discussion

PX-054 shows that Huginn-0125 exposes a stable depth-indexed refusal-style direction on the safe prompt suite. The result is notable because recurrence depth changes the model's internal computation while the measured representation direction remains coherent.

The result is not a causal mechanism claim. It does not show that the direction causes refusal, that manipulating the direction is safe, or that it transfers to other models. It is a characterization paper: a safe, observational map of representation geometry across recurrent depth.

## 8. Threats to Validity

The prompt set is safe and synthetic. The experiment uses one model checkpoint. The direction threshold is defined per depth, so it is not a universal classifier. Reduced latent vectors support review and reproducibility, but they are not a full hidden-state release. The result should be replicated on held-out safe prompts and another recurrent-depth checkpoint before broad claims.

## 9. Conclusion

PX-054 supports a bounded mechanistic-safety claim: on a safe paraphrase-family prompt suite, Huginn-0125 exposes depth-indexed latent states whose refusal-style direction is measurable and stable across recurrent depth. The result is defense-ready as characterization, not as a deployed safety defense.

## Repository Artifacts

- `reports/refusal_geometry_recurrent_depth/PX054_REFUSAL_GEOMETRY_SOURCE_GATE_20260705.md`
- `reports/refusal_geometry_recurrent_depth/source_gate_20260705/PX054_SOURCE_GATE_RESULT_20260705.md`
- `reports/refusal_geometry_recurrent_depth/activation_gate_20260705/PX054_REFUSAL_GEOMETRY_ACTIVATION_GATE_20260705.md`
- `reports/refusal_geometry_recurrent_depth/scale_gate_20260705/PX054_REFUSAL_GEOMETRY_SCALE_GATE_20260705.md`
- `reports/refusal_geometry_recurrent_depth/scale_gate_20260705/summary.json`
- `reports/refusal_geometry_recurrent_depth/scale_gate_20260705/activation_rows.csv`
- `reports/refusal_geometry_recurrent_depth/scale_gate_20260705/vectors_reduced.json`
- `scripts/run_px054_refusal_geometry_source_gate.py`
- `cloud_jobs/px054_refusal_geometry_20260705/run_px054_refusal_geometry_activation_gate.py`
- `cloud_jobs/px054_refusal_geometry_scale_20260705/run_px054_refusal_geometry_scale_gate.py`

## References

Arditi, A., Obeso, O., Syed, A., Paleka, D., Panickssery, N., Gurnee, W., & Nanda, N. (2024). Refusal in language models is mediated by a single direction. arXiv. https://arxiv.org/abs/2406.11717

Geiping, J., et al. (2025). Scaling up test-time compute with latent reasoning: A recurrent depth approach. arXiv. https://arxiv.org/abs/2502.05171

tomg-group-umd. (2025). Huginn-0125 model card. Hugging Face. https://huggingface.co/tomg-group-umd/huginn-0125

Zou, A., Phan, L., Chen, S., Campbell, J., Guo, P., Ren, R., Pan, A., Yin, X., Mazeika, M., Dombrowski, A., Goel, S., Li, N., Byun, M. J., Wang, Z., Mallen, A., Basart, S., Koyejo, S., Song, D., Fredrikson, M., & Hendrycks, D. (2023). Representation engineering: A top-down approach to AI transparency. arXiv. https://arxiv.org/abs/2310.01405

