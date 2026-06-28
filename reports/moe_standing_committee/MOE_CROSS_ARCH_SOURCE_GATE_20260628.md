# MoE Standing-Committee Cross-Architecture Source Gate

Updated: 2026-06-28 18:41:23 UTC

PX ID: `PX-005`

Status: **PASS_SOURCE_GATE**

## Praxis framing

PX-005 already has a bounded positive OLMoE-family result. This gate checks whether a non-OLMoE cross-architecture audit is ready to run by inspecting public model metadata, router/expert configuration fields, local toolchain availability, and AWS profile readiness.

This is not a router-trace replication. It does not download weights and does not run inference.

## Gate decision

Decision: **PASS_SOURCE_GATE**.

| Metric | Value |
|---|---:|
| Public config candidates | 11 |
| Router-observable candidates | 11 |
| Non-OLMoE source candidates | 7 |
| Non-OLMoE single-GPU smoke candidates | 0 |
| Non-OLMoE medium-GPU follow-on candidates | 7 |

Best non-OLMoE candidates, in order:

1. `Qwen/Qwen1.5-MoE-A2.7B`
2. `Qwen/Qwen1.5-MoE-A2.7B-Chat`
3. `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct`
4. `deepseek-ai/DeepSeek-V2-Lite`
5. `deepseek-ai/DeepSeek-V2-Lite-Chat`
6. `Qwen/Qwen3-30B-A3B`
7. `Qwen/Qwen3-30B-A3B-Instruct-2507`

## Candidate audit

| Repo | Family | Public config | MoE evidence | Router observable | Est. weights GB | Smoke | Follow-on | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `allenai/OLMoE-1B-7B-0924` | `OLMoE` | PASS | PASS | PASS | 12.888 | PASS | PASS | published baseline |
| `allenai/OLMoE-1B-7B-0924-Instruct` | `OLMoE` | PASS | PASS | PASS | 12.888 | PASS | PASS | published baseline |
| `Qwen/Qwen1.5-MoE-A2.7B` | `Qwen1.5-MoE` | PASS | PASS | PASS | 26.666 | FAIL | PASS | cross-arch follow-on candidate |
| `Qwen/Qwen1.5-MoE-A2.7B-Chat` | `Qwen1.5-MoE` | PASS | PASS | PASS | 26.666 | FAIL | PASS | cross-arch follow-on candidate |
| `Qwen/Qwen3-30B-A3B` | `Qwen3-MoE` | PASS | PASS | PASS | 56.873 | FAIL | PASS | cross-arch follow-on candidate |
| `Qwen/Qwen3-30B-A3B-Instruct-2507` | `Qwen3-MoE` | PASS | PASS | PASS | 56.873 | FAIL | PASS | cross-arch follow-on candidate |
| `deepseek-ai/DeepSeek-V2-Lite` | `DeepSeek-V2` | PASS | PASS | PASS | 29.256 | FAIL | PASS | cross-arch follow-on candidate |
| `deepseek-ai/DeepSeek-V2-Lite-Chat` | `DeepSeek-V2` | PASS | PASS | PASS | 29.256 | FAIL | PASS | cross-arch follow-on candidate |
| `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct` | `DeepSeek-Coder-V2` | PASS | PASS | PASS | 29.256 | FAIL | PASS | cross-arch follow-on candidate |
| `mistralai/Mixtral-8x7B-v0.1` | `Mixtral` | PASS | PASS | PASS | 177.400 | FAIL | FAIL | hold |
| `mistralai/Mixtral-8x7B-Instruct-v0.1` | `Mixtral` | PASS | PASS | PASS | 177.400 | FAIL | FAIL | hold |

## Local and AWS readiness

| Check | Result |
|---|---:|
| PyTorch import | FAIL |
| Transformers import | FAIL |
| Hugging Face Hub import | FAIL |
| AWS STS profile `praxis-build` | PASS |
| AWS GPU inventory query | PASS |

Local inference audit is blocked on this machine because PyTorch/Transformers are not installed.

AWS identity: `arn:aws:sts::272615233626:assumed-role/AWSReservedSSO_AdminAccess_c0cc500ab86f3e7b/paganpraxis`.
GPU instances found in `us-east-1`: `2`.

## Candidate metadata notes

### `allenai/OLMoE-1B-7B-0924`

MoE evidence: `architecture_name_mentions_moe, hub_tag_mentions_moe, model_type_mentions_moe, moe_or_expert_fields_in_config, repo_name_moe_family_signal`.
Router/expert keys: `num_experts_per_tok`, `output_router_logits`, `router_aux_loss_coef`.
Selected fields: `num_experts=64`, `num_experts_per_tok=8`, `output_router_logits=False`, `router_aux_loss_coef=0.01`.

### `allenai/OLMoE-1B-7B-0924-Instruct`

MoE evidence: `architecture_name_mentions_moe, hub_tag_mentions_moe, model_type_mentions_moe, moe_or_expert_fields_in_config, repo_name_moe_family_signal`.
Router/expert keys: `num_experts_per_tok`, `output_router_logits`, `router_aux_loss_coef`.
Selected fields: `num_experts=64`, `num_experts_per_tok=8`, `output_router_logits=False`, `router_aux_loss_coef=0.01`.

### `Qwen/Qwen1.5-MoE-A2.7B`

MoE evidence: `architecture_name_mentions_moe, hub_tag_mentions_moe, model_type_mentions_moe, moe_or_expert_fields_in_config, repo_name_moe_family_signal`.
Router/expert keys: `num_experts_per_tok`, `output_router_logits`, `router_aux_loss_coef`.
Selected fields: `decoder_sparse_step=1`, `moe_intermediate_size=1408`, `shared_expert_intermediate_size=5632`, `num_experts_per_tok=4`, `num_experts=60`, `output_router_logits=False`, `router_aux_loss_coef=0.001`.

### `Qwen/Qwen1.5-MoE-A2.7B-Chat`

MoE evidence: `architecture_name_mentions_moe, hub_tag_mentions_moe, model_type_mentions_moe, moe_or_expert_fields_in_config, repo_name_moe_family_signal`.
Router/expert keys: `num_experts_per_tok`, `output_router_logits`, `router_aux_loss_coef`.
Selected fields: `decoder_sparse_step=1`, `moe_intermediate_size=1408`, `shared_expert_intermediate_size=5632`, `num_experts_per_tok=4`, `num_experts=60`, `output_router_logits=False`, `router_aux_loss_coef=0.001`.

### `Qwen/Qwen3-30B-A3B`

MoE evidence: `architecture_name_mentions_moe, model_type_mentions_moe, moe_or_expert_fields_in_config, repo_name_moe_family_signal`.
Router/expert keys: `num_experts_per_tok`, `output_router_logits`, `router_aux_loss_coef`.
Selected fields: `decoder_sparse_step=1`, `moe_intermediate_size=768`, `num_experts=128`, `num_experts_per_tok=8`, `output_router_logits=False`, `router_aux_loss_coef=0.001`.

### `Qwen/Qwen3-30B-A3B-Instruct-2507`

MoE evidence: `architecture_name_mentions_moe, hub_tag_mentions_moe, model_type_mentions_moe, moe_or_expert_fields_in_config, repo_name_moe_family_signal`.
Router/expert keys: `num_experts_per_tok`, `output_router_logits`, `router_aux_loss_coef`.
Selected fields: `decoder_sparse_step=1`, `moe_intermediate_size=768`, `num_experts=128`, `num_experts_per_tok=8`, `output_router_logits=False`, `router_aux_loss_coef=0.001`.

### `deepseek-ai/DeepSeek-V2-Lite`

MoE evidence: `moe_or_expert_fields_in_config, repo_name_moe_family_signal`.
Router/expert keys: `n_routed_experts`, `num_experts_per_tok`.
Selected fields: `first_k_dense_replace=1`, `moe_intermediate_size=1408`, `moe_layer_freq=1`, `n_routed_experts=64`, `n_shared_experts=2`, `num_experts_per_tok=6`.

### `deepseek-ai/DeepSeek-V2-Lite-Chat`

MoE evidence: `moe_or_expert_fields_in_config, repo_name_moe_family_signal`.
Router/expert keys: `n_routed_experts`, `num_experts_per_tok`.
Selected fields: `first_k_dense_replace=1`, `moe_intermediate_size=1408`, `moe_layer_freq=1`, `n_routed_experts=64`, `n_shared_experts=2`, `num_experts_per_tok=6`.

### `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct`

MoE evidence: `moe_or_expert_fields_in_config`.
Router/expert keys: `n_routed_experts`, `num_experts_per_tok`.
Selected fields: `first_k_dense_replace=1`, `moe_intermediate_size=1408`, `moe_layer_freq=1`, `n_routed_experts=64`, `n_shared_experts=2`, `num_experts_per_tok=6`.

### `mistralai/Mixtral-8x7B-v0.1`

MoE evidence: `hub_tag_mentions_moe, moe_or_expert_fields_in_config`.
Router/expert keys: `num_experts_per_tok`, `output_router_logits`, `router_aux_loss_coef`.
Selected fields: `num_experts_per_tok=2`, `num_local_experts=8`, `output_router_logits=False`, `router_aux_loss_coef=0.02`.

### `mistralai/Mixtral-8x7B-Instruct-v0.1`

MoE evidence: `moe_or_expert_fields_in_config`.
Router/expert keys: `num_experts_per_tok`, `output_router_logits`, `router_aux_loss_coef`.
Selected fields: `num_experts_per_tok=2`, `num_local_experts=8`, `output_router_logits=False`, `router_aux_loss_coef=0.02`.

## Result interpretation

This gate passes if at least one non-OLMoE model has public MoE/router metadata and a feasible weight-size tier for a later instrumented run. It does not validate standing-committee behavior outside OLMoE.

## Next registered gate

Run a frozen prompt-domain router audit on the best non-OLMoE candidate after installing the required inference stack or moving to AWS/HF GPU infrastructure. Use the exact OLMoE audit format: router capture rate, committee-size sensitivity, mean pairwise Jaccard, bootstrap confidence intervals, and no threshold changes after model selection.

## Sources

- Literature anchor: https://arxiv.org/abs/2601.03425
- `allenai/OLMoE-1B-7B-0924` model page: https://huggingface.co/allenai/OLMoE-1B-7B-0924
- `allenai/OLMoE-1B-7B-0924` config: https://huggingface.co/allenai/OLMoE-1B-7B-0924/resolve/main/config.json
- `allenai/OLMoE-1B-7B-0924-Instruct` model page: https://huggingface.co/allenai/OLMoE-1B-7B-0924-Instruct
- `allenai/OLMoE-1B-7B-0924-Instruct` config: https://huggingface.co/allenai/OLMoE-1B-7B-0924-Instruct/resolve/main/config.json
- `Qwen/Qwen1.5-MoE-A2.7B` model page: https://huggingface.co/Qwen/Qwen1.5-MoE-A2.7B
- `Qwen/Qwen1.5-MoE-A2.7B` config: https://huggingface.co/Qwen/Qwen1.5-MoE-A2.7B/resolve/main/config.json
- `Qwen/Qwen1.5-MoE-A2.7B-Chat` model page: https://huggingface.co/Qwen/Qwen1.5-MoE-A2.7B-Chat
- `Qwen/Qwen1.5-MoE-A2.7B-Chat` config: https://huggingface.co/Qwen/Qwen1.5-MoE-A2.7B-Chat/resolve/main/config.json
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
- `mistralai/Mixtral-8x7B-v0.1` model page: https://huggingface.co/mistralai/Mixtral-8x7B-v0.1
- `mistralai/Mixtral-8x7B-v0.1` config: https://huggingface.co/mistralai/Mixtral-8x7B-v0.1/resolve/main/config.json
- `mistralai/Mixtral-8x7B-Instruct-v0.1` model page: https://huggingface.co/mistralai/Mixtral-8x7B-Instruct-v0.1
- `mistralai/Mixtral-8x7B-Instruct-v0.1` config: https://huggingface.co/mistralai/Mixtral-8x7B-Instruct-v0.1/resolve/main/config.json

Claim boundary: This gate establishes whether a non-OLMoE cross-architecture router audit is technically defensible from public metadata. It does not claim cross-architecture standing-committee validity until router traces are collected on frozen held-out prompt domains.
