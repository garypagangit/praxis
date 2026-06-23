# OLMoE Standing-Committee Router Audit

Updated: 2026-06-23 11:39:13 UTC

Model: `allenai/OLMoE-1B-7B-0924`.

## Decision

Audit decision: **PASS**.

| Metric | Value |
|---|---:|
| Prompt count | 480 |
| Router capture rate | 1.0000 |
| Primary committee size | 32 |
| Primary mean pairwise Jaccard | 0.4656 |
| Primary bootstrap CI low | 0.4336 |
| Primary bootstrap CI high | 0.4834 |

## Committee-size sensitivity

| Committee size | Mean Jaccard | Min Jaccard | CI low | CI high |
|---:|---:|---:|---:|---:|
| 16 | 0.4950 | 0.3333 | 0.4563 | 0.5256 |
| 32 | 0.4656 | 0.3617 | 0.4336 | 0.4834 |
| 64 | 0.5334 | 0.4066 | 0.5021 | 0.5491 |

## Interpretation

The audit supports a bounded prompt-domain standing-committee claim for OLMoE: router tensors were captured for every prompt, and committee overlap remained above the pre-registered threshold across committee sizes. The result does not test fine-tuning shift or causal intervention on experts.

## Claim Boundary

This gate can support a bounded OLMoE prompt-domain standing-committee claim if passed. It still does not test fine-tuning shift or causal expert intervention.
