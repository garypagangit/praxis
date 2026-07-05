# PX-054 Refusal Geometry Source Gate Result

Generated: 2026-07-05T17:58:33.357804+00:00

## Status

**SOURCE_GATE_PASS**

PX-054 remains a characterization-only experiment. This source gate checks whether the Huginn recurrent-depth model is accessible and whether a safe activation-capture gate is justified. It does not run refusal removal, jailbreak optimization, or safety ablation.

## Model Metadata

| Field | Value |
|---|---|
| Model | `tomg-group-umd/huginn-0125` |
| SHA | `bb6621b65e90b6a4b9b29ef88dc83866d450470c` |
| Last modified | `2025-07-29T09:40:51.000Z` |
| Private | `False` |
| Gated | `False` |
| Disabled | `False` |
| License tag | `license:apache-2.0` |
| Library | `transformers` |
| Pipeline | `text-generation` |
| Model type | `huginn_raven` |
| Architecture | `['RavenForCausalLM']` |
| Recurrent mean steps | `32` |
| Recurrent block layers | `4` |
| Hidden size | `5280` |

## Checks

| Check | Pass |
|---|---:|
| `model_public` | `PASS` |
| `model_ungated` | `PASS` |
| `model_not_disabled` | `PASS` |
| `apache_2_license` | `PASS` |
| `transformers_model` | `PASS` |
| `custom_model_code_present` | `PASS` |
| `config_present` | `PASS` |
| `safetensors_index_present` | `PASS` |
| `auto_model_mapping_present` | `PASS` |
| `recurrent_depth_configured` | `PASS` |
| `num_steps_documented` | `PASS` |
| `paper_tag_present` | `PASS` |

## Source Anchors

- Model card: `https://huggingface.co/tomg-group-umd/huginn-0125`
- Recurrent-depth paper: `https://arxiv.org/abs/2502.05171`
- Pretraining/code repository from model card: `https://github.com/seal-rg/recurrent-pretraining`

## Decision

The source gate passes and authorizes a bounded activation-capture smoke over safe refusal-style statements, benign-helpful statements, and benign safety-themed controls. The next gate may measure latent-state geometry across `num_steps` without generating unsafe content.

Claim boundary: a source-gate pass is not a positive result. PX-054 can only become positive after measured, reproducible activation geometry clears the registered thresholds.
