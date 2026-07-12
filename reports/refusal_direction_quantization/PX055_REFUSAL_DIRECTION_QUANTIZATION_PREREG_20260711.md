# PX-055 Refusal-Direction Geometry Under Post-Training Quantization

Status: source-gate candidate / deconflict required

Added: 2026-07-11

Prior related Praxis row: PX-054, "Refusal Geometry Across Recurrent Depth"

Safety framing: detection-and-defense mechanistic characterization. The experiment may publish diagnostic geometry, bounded aggregate safety measurements, and restoration/repair implications. It must not publish abliterated checkpoints, jailbreak-optimization artifacts, harmful prompt inventories, or turnkey refusal-removal tooling.

Result status: no measured PX-055 result yet. All numeric thresholds below are preregistered targets or branch rules, not findings.

## 1. Why This Experiment Was Added

PX-054 showed that safe refusal-style directions can be measured across recurrent depth in Huginn-0125 under a strictly observational boundary. PX-055 asks the next precision-axis question: when an aligned model is quantized after training, does the refusal direction remain geometrically stable, or do rotation, attenuation, calibration dependence, or low-rank spreading explain observed safety regressions in quantized models?

This is a useful Praxis candidate because post-training quantization is common in deployment, and a cheap geometric diagnostic could help teams detect alignment degradation before shipping a compressed checkpoint.

## 2. Immediate Deconfliction Finding

The original submitted protocol claimed that no identified work measures what quantization does to the refusal direction itself. A 2026-07-11 source-gate search found a direct overlap:

- Chhabra and Khalili, "Towards Understanding and Improving Refusal in Compressed Models via Mechanistic Interpretability" (arXiv:2504.04215, https://arxiv.org/abs/2504.04215), reports refusal-direction analysis in compressed models and includes quantization conditions such as LLM.int8() and AWQ. It reports source-position and cosine-similarity comparisons and argues that quantized models retain the original refusal mechanism more than pruned models.
- Alignment-Aware Quantization (arXiv:2511.07842) and later quality-versus-safety quantization work strengthen the behavioral motivation that quality/perplexity alone is not a safety proxy under PTQ.

Therefore PX-055 is not currently a publish-safe "nobody has measured refusal-direction quantization" claim. It remains worth adding only as a narrower extension candidate.

## 3. Surviving Novel Components

PX-055 can proceed only if Gate 0 confirms at least one publishable delta beyond the overlap above:

1. Leave-one-family-out replication across Llama-3.1-8B-Instruct, Qwen2.5-7B-Instruct, and Gemma-2-9B-it.
2. Cross-precision transfer: direction extracted at FP16 versus quantized precision, then tested under matched precision without releasing unsafe artifacts.
3. Rank-spreading analysis using principal angles, participation ratio, and rank-k diagnostic subspaces rather than only rank-1 cosine.
4. Calibration-set sensitivity for static GPTQ/AWQ methods using two disjoint calibration sets per method.
5. Restoration probe: whether quantization after a safety-damaged or direction-perturbed model restores any refusal-style signal, reported only as aggregate safety diagnostic evidence.

If none of these survives the novelty check, PX-055 should be archived as "superseded by existing literature" rather than run.

## 4. Central Question

Is the refusal direction a robust geometric object across numerical precision, or does PTQ perturb it in ways that explain behavioral safety degradation observed after quantization?

## 5. Competing Hypotheses

H1 - Precision-invariant direction. The refusal direction remains stable under 8-bit and 4-bit PTQ. Behavioral degradation, if observed, comes from downstream logit noise or calibration effects rather than direction drift.

H2 - Drift-mediated degradation. Quantization rotates or attenuates the refusal direction, and per-method geometric drift correlates with behavioral safety loss.

H3 - Rank spreading. The rank-1 direction weakens under quantization, but the signal remains recoverable as a low-rank subspace.

H4 - Refusal restoration. Quantization after a direction-perturbed model partially restores refusal-style behavior, suggesting redundant or noise-sensitive safety encoding.

The thesis is selected by gates, not pre-committed.

## 6. Model And Quantization Plan

Primary model families:

- Llama-3.1-8B-Instruct
- Qwen2.5-7B-Instruct
- Gemma-2-9B-it

Quantization conditions:

- FP16 baseline
- bitsandbytes int8 / LLM.int8()
- bitsandbytes NF4 4-bit
- GPTQ 4-bit
- AWQ 4-bit

Static quantization control:

- two disjoint calibration sets per GPTQ/AWQ method to separate method-level drift from calibration-data dependence.

Optional severable probe:

- one larger model activation-harvest pass if GPU, storage, and hook support remain practical.

## 7. Stimuli And Safety Boundary

PX-055 should reuse safe, non-operational refusal-style and benign-control prompts where possible. Any harmful benchmark references must be kept as non-released identifiers or aggregate metrics only.

Do not publish:

- harmful prompt text,
- abliterated model weights,
- code that directly automates refusal removal for release,
- jailbreak optimization loops,
- instructions that make unsafe model release easier.

Publishable artifacts:

- hook-feasibility report,
- aggregate direction-stability tables,
- principal-angle and participation-ratio plots,
- calibration sensitivity summary,
- bounded claim-boundary note.

## 8. Experiments

E1 - Direction stability.

Compute per-layer diff-in-means directions under each quantization condition. Metrics: cosine similarity versus FP16, norm ratio, per-layer drift, principal angles, and participation ratio.

E2 - Cross-precision transfer diagnostic.

Compare direction extracted under FP16 versus quantized precision and evaluated under matched precision. Report only aggregate transfer metrics inside a safety-bounded diagnostic harness.

E3 - Drift-degradation correlation.

Relate geometric drift to aggregate safety-regression metrics across methods and families. Registered statistic: Spearman correlation, reported per family and pooled.

E4 - Restoration probe.

Compare order-of-operations outcomes: direction perturbation then quantization versus quantization then direction measurement. Treat this as a defensive diagnostic, not a release pathway for damaged checkpoints.

## 9. Decision Gates

Gate 0 - Novelty and feasibility.

- Confirm the overlap with Chhabra and Khalili 2025, Alignment-Aware Quantization, and any 2026 successor papers.
- Confirm residual-stream hooks work under at least FP16, bitsandbytes int8, and bitsandbytes NF4 on one model.
- Confirm GPTQ/AWQ hook feasibility or explicitly descope methods that require custom CUDA/kernel work.

Pass condition: at least one surviving novelty component remains, and one-model FP16/NF4 activation capture runs end-to-end on one GPU.

Fail condition: existing literature already covers the surviving novelty, or quantized hooks are not practical without custom kernel work.

Gate 1 - Measurement.

Complete E1 across scoped models and quantization methods. Branch rules:

- H1 branch if effective-layer cosine similarity is at least 0.95 everywhere and rank metrics remain near rank-1.
- H2 branch if cosine drops materially while participation ratio remains near rank-1.
- H3 branch if participation ratio rises above 1.5 or principal-angle spread indicates low-rank subspace drift.

Gate 2 - Causal/transfer diagnostic.

Complete E2, adding rank-k transfer only if H3 branch is selected. Cross-precision transfer is "clean" only if cross-precision aggregate transfer reaches at least 90 percent of same-precision transfer.

Gate 3 - Thesis selection.

Combine E1-E4 into one of: precision-invariant replication, drift-mediated degradation, rank-spreading extension, restoration diagnostic, or bounded null/superseded result.

## 10. Claim Boundary

Allowed claims after gates:

- A geometric diagnostic can or cannot detect precision-linked changes in refusal-style representation under the tested model families and quantization methods.
- PX-055 extends or fails to extend prior compressed-model refusal-direction work under a stricter cross-family/cross-precision/calibration-sensitivity design.

Not allowed:

- universal claims about all quantized LLM safety,
- claims that quantization is safe without behavioral validation,
- release of abliterated or safety-damaged models,
- operational guidance for bypassing model refusal.

## 11. Next Action

Run a source-gate clearance before any GPU experiment:

1. Literature overlap table for refusal direction plus quantization/compression.
2. Method delta table showing what PX-055 adds beyond existing work.
3. One-model hook feasibility smoke for FP16, int8, and NF4.
4. Stop or rescope before GPTQ/AWQ spend if hook support is poor.
