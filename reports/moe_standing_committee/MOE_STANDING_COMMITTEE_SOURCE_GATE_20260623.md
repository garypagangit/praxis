# MoE Standing-Committee Source Gate

Updated: 2026-06-23 10:53:49 UTC

## Praxis framing

Working title: `Standing Committee Routing Under Domain and Fine-Tuning Shift`.

Literature anchor: `The Illusion of Specialization: Unveiling the Domain-Invariant Standing Committee in Mixture-of-Experts Models` (2601.03425).

Hypothesis boundary: a defensible experiment requires an open MoE model whose routing or expert-selection metadata can be observed under held-out prompt domains before any fine-tuning or publication claim is attempted.

Research questions:

1. RQ1: Do public MoE checkpoints expose enough configuration evidence to support an inference-only router audit?
2. RQ2: Is at least one candidate small enough for a practical GPU smoke run under the current AWS plan?
3. RQ3: Does the source gate justify moving from literature concept to router-trace measurement?

Hypotheses:

1. H1: At least one open MoE model exposes router/expert metadata sufficient for a standing-committee audit.
2. H2: A smaller open MoE candidate is feasible for a first smoke run, while larger candidates remain external-validity follow-ons.
3. H3: Source-gated candidate selection will prevent an underpowered or unverifiable MoE replication attempt.

## Gate decision

Decision: **PASS**.

| Metric | Value |
|---|---:|
| Public config candidates | 7 |
| Router-observable candidates | 7 |
| Source-gate candidates | 7 |
| Single-GPU smoke candidates by metadata size | 2 |
| Medium-GPU follow-on candidates by metadata size | 7 |

Best candidates, in order:

1. `allenai/OLMoE-1B-7B-0924`
2. `allenai/OLMoE-1B-7B-0924-Instruct`
3. `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct`
4. `deepseek-ai/DeepSeek-V2-Lite`
5. `deepseek-ai/DeepSeek-V2-Lite-Chat`
6. `Qwen/Qwen3-30B-A3B`
7. `Qwen/Qwen3-30B-A3B-Instruct-2507`

## Candidate audit

| Repo | Public config | MoE evidence | Router observable | Est. weights GB | Smoke | Follow-on | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| `allenai/OLMoE-1B-7B-0924` | PASS | PASS | PASS | 12.888 | PASS | PASS | primary smoke candidate |
| `allenai/OLMoE-1B-7B-0924-Instruct` | PASS | PASS | PASS | 12.888 | PASS | PASS | primary smoke candidate |
| `Qwen/Qwen3-30B-A3B` | PASS | PASS | PASS | 56.873 | FAIL | PASS | GPU follow-on candidate |
| `Qwen/Qwen3-30B-A3B-Instruct-2507` | PASS | PASS | PASS | 56.873 | FAIL | PASS | GPU follow-on candidate |
| `deepseek-ai/DeepSeek-V2-Lite` | PASS | PASS | PASS | 29.256 | FAIL | PASS | GPU follow-on candidate |
| `deepseek-ai/DeepSeek-V2-Lite-Chat` | PASS | PASS | PASS | 29.256 | FAIL | PASS | GPU follow-on candidate |
| `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct` | PASS | PASS | PASS | 29.256 | FAIL | PASS | GPU follow-on candidate |

## Key metadata fields

### `allenai/OLMoE-1B-7B-0924`

MoE evidence: `architecture_name_mentions_moe, hub_tag_mentions_moe, model_type_mentions_moe, moe_or_expert_fields_in_config, repo_name_moe_family_signal`.
Router/expert observability keys: `num_experts_per_tok`, `output_router_logits`, `router_aux_loss_coef`.
Selected config fields: `num_experts=64`, `num_experts_per_tok=8`, `output_router_logits=False`, `router_aux_loss_coef=0.01`.

### `allenai/OLMoE-1B-7B-0924-Instruct`

MoE evidence: `architecture_name_mentions_moe, hub_tag_mentions_moe, model_type_mentions_moe, moe_or_expert_fields_in_config, repo_name_moe_family_signal`.
Router/expert observability keys: `num_experts_per_tok`, `output_router_logits`, `router_aux_loss_coef`.
Selected config fields: `num_experts=64`, `num_experts_per_tok=8`, `output_router_logits=False`, `router_aux_loss_coef=0.01`.

### `Qwen/Qwen3-30B-A3B`

MoE evidence: `architecture_name_mentions_moe, model_type_mentions_moe, moe_or_expert_fields_in_config, repo_name_moe_family_signal`.
Router/expert observability keys: `num_experts_per_tok`, `output_router_logits`, `router_aux_loss_coef`.
Selected config fields: `decoder_sparse_step=1`, `moe_intermediate_size=768`, `num_experts=128`, `num_experts_per_tok=8`, `output_router_logits=False`, `router_aux_loss_coef=0.001`.

### `Qwen/Qwen3-30B-A3B-Instruct-2507`

MoE evidence: `architecture_name_mentions_moe, hub_tag_mentions_moe, model_type_mentions_moe, moe_or_expert_fields_in_config, repo_name_moe_family_signal`.
Router/expert observability keys: `num_experts_per_tok`, `output_router_logits`, `router_aux_loss_coef`.
Selected config fields: `decoder_sparse_step=1`, `moe_intermediate_size=768`, `num_experts=128`, `num_experts_per_tok=8`, `output_router_logits=False`, `router_aux_loss_coef=0.001`.

### `deepseek-ai/DeepSeek-V2-Lite`

MoE evidence: `moe_or_expert_fields_in_config, repo_name_moe_family_signal`.
Router/expert observability keys: `n_routed_experts`, `num_experts_per_tok`.
Selected config fields: `first_k_dense_replace=1`, `moe_intermediate_size=1408`, `moe_layer_freq=1`, `n_routed_experts=64`, `n_shared_experts=2`, `num_experts_per_tok=6`.

### `deepseek-ai/DeepSeek-V2-Lite-Chat`

MoE evidence: `moe_or_expert_fields_in_config, repo_name_moe_family_signal`.
Router/expert observability keys: `n_routed_experts`, `num_experts_per_tok`.
Selected config fields: `first_k_dense_replace=1`, `moe_intermediate_size=1408`, `moe_layer_freq=1`, `n_routed_experts=64`, `n_shared_experts=2`, `num_experts_per_tok=6`.

### `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct`

MoE evidence: `moe_or_expert_fields_in_config`.
Router/expert observability keys: `n_routed_experts`, `num_experts_per_tok`.
Selected config fields: `first_k_dense_replace=1`, `moe_intermediate_size=1408`, `moe_layer_freq=1`, `n_routed_experts=64`, `n_shared_experts=2`, `num_experts_per_tok=6`.

## AWS readiness

AWS STS profile `praxis-build`: PASS.
Account: `272615233626`; ARN: `arn:aws:sts::272615233626:assumed-role/AWSReservedSSO_AdminAccess_c0cc500ab86f3e7b/paganpraxis`.

GPU instance inventory in `us-east-1`: PASS.
GPU instances found: `2`.

| Instance | Type | State | Name |
|---|---|---|---|
| `i-039ed976444ade397` | `g5.xlarge` | `stopped` | `praxis-sec-lord-llama-gpu` |
| `i-07178e293e8df2a60` | `g5.xlarge` | `stopped` | `praxis-gml-cross-dataset-gpu` |

## Result interpretation

This is a source and feasibility result, not a replication result. A PASS means the experiment is ready for an instrumented router-trace run with frozen prompt-domain splits and pre-registered metrics: expert coalition overlap, routing mass concentration, and standing-committee persistence under domain shift. A FAIL would mean the idea remains literature-backed but not runnable without a different model source or instrumentation path.

## Next registered gate

Run an inference-only router audit on the best small public candidate first. Use train/validation/test only for prompt-domain design and threshold choice: training prompts define domains, validation fixes reporting thresholds, and strict holdout prompts decide the claim. Do not fine-tune until the frozen inference audit reproduces a standing-committee signal.

## Sources

- Literature anchor: https://arxiv.org/abs/2601.03425
- `allenai/OLMoE-1B-7B-0924` model page: https://huggingface.co/allenai/OLMoE-1B-7B-0924
- `allenai/OLMoE-1B-7B-0924` config: https://huggingface.co/allenai/OLMoE-1B-7B-0924/resolve/main/config.json
- `allenai/OLMoE-1B-7B-0924-Instruct` model page: https://huggingface.co/allenai/OLMoE-1B-7B-0924-Instruct
- `allenai/OLMoE-1B-7B-0924-Instruct` config: https://huggingface.co/allenai/OLMoE-1B-7B-0924-Instruct/resolve/main/config.json
- `Qwen/Qwen3-30B-A3B` model page: https://huggingface.co/Qwen/Qwen3-30B-A3B
- `Qwen/Qwen3-30B-A3B` config: https://huggingface.co/Qwen/Qwen3-30B-A3B/resolve/main/config.json
- `Qwen/Qwen3-30B-A3B-Instruct-2507` model page: https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507
- `Qwen/Qwen3-30B-A3B-Instruct-2507` config: https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/resolve/main/config.json
- `deepseek-ai/DeepSeek-V2-Lite` model page: https://huggingface.co/deepseek-ai/DeepSeek-V2-Lite
- `deepseek-ai/DeepSeek-V2-Lite` config: https://huggingface.co/deepseek-ai/DeepSeek-V2-Lite/resolve/main/config.json
- `deepseek-ai/DeepSeek-V2-Lite-Chat` model page: https://huggingface.co/deepseek-ai/DeepSeek-V2-Lite-Chat
- `deepseek-ai/DeepSeek-V2-Lite-Chat` config: https://huggingface.co/deepseek-ai/DeepSeek-V2-Lite-Chat/resolve/main/config.json
- `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct` model page: https://huggingface.co/deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct
- `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct` config: https://huggingface.co/deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct/resolve/main/config.json

Claim boundary: This gate establishes whether an inference-only MoE standing-committee audit is technically defensible from public model metadata. It does not claim a standing-committee replication until router traces are collected on held-out prompt domains.
