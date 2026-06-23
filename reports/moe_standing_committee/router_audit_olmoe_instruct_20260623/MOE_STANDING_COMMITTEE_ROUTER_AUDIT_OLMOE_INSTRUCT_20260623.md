# OLMoE Standing-Committee Router Audit

Updated: 2026-06-23 11:53:33 UTC

Model: `allenai/OLMoE-1B-7B-0924-Instruct`.

## Decision

Audit decision: **PASS**.

| Metric | Value |
|---|---:|
| Prompt count | 480 |
| Router capture rate | 1.0000 |
| Primary committee size | 32 |
| Primary mean pairwise Jaccard | 0.4591 |
| Primary bootstrap CI low | 0.4320 |
| Primary bootstrap CI high | 0.4796 |

## Committee-size sensitivity

| Committee size | Mean Jaccard | Min Jaccard | CI low | CI high |
|---:|---:|---:|---:|---:|
| 16 | 0.5642 | 0.4545 | 0.5172 | 0.5803 |
| 32 | 0.4591 | 0.3333 | 0.4320 | 0.4796 |
| 64 | 0.5520 | 0.4222 | 0.5301 | 0.5785 |

## Interpretation

The audit supports a bounded prompt-domain standing-committee claim for OLMoE: router tensors were captured for every prompt, and committee overlap remained above the pre-registered threshold across committee sizes. The result does not test fine-tuning shift or causal intervention on experts.

## Claim Boundary

This gate can support a bounded OLMoE prompt-domain standing-committee claim if passed. It still does not test fine-tuning shift or causal expert intervention.
