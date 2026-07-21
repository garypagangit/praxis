# PX-056 Model Registry Hallucination Source Gate

Generated: 2026-07-21 22:49:00 UTC

Praxis ID: `PX-056`

Status: **PX056_SOURCE_GATE_PASS_HF_AND_NGC_READY**

## Purpose

This Gate 0 run checks whether PX-056 has a defensible registry-verification surface before any LLM output is generated or scored. It is not a hallucination-rate result and must not be described as a positive experiment.

## Deconfliction

PX-056 extends the PX-004/PX-050 deterministic-verifier lane from package/citation identifiers to model and dataset registry identifiers. The new surface is Hugging Face Hub model/dataset loading and, conditionally, NVIDIA NGC catalog resources used in physical-AI and robotics code.

## Gate Decision

Decision: **PX056_SOURCE_GATE_PASS_HF_AND_NGC_READY**.

| Check | Result |
|---|---:|
| HF existing model direct API | PASS |
| HF existing dataset direct API | PASS |
| HF search endpoint available | PASS |
| HF missing identifiers absent from search | PASS |
| HF token present for gated/private disambiguation | PASS |
| NGC search API ready with configured credential path | PASS |
| Cosmos arXiv anchor reachable | PASS |

## API Probe Table

| Category | Target | Status | OK | Notes |
|---|---|---:|---:|---|
| `hf_existing_model_direct` | `google-bert/bert-base-uncased` | `200` | PASS |  |
| `hf_existing_model_direct` | `Qwen/Qwen2.5-Coder-7B-Instruct` | `200` | PASS |  |
| `hf_existing_dataset_direct` | `stanfordnlp/imdb` | `200` | PASS |  |
| `hf_existing_dataset_direct` | `squad` | `200` | PASS |  |
| `hf_known_search` | `google-bert/bert-base-uncased` | `200` | PASS | exact_match=True; sample=['google-bert/bert-base-uncased', 'helenai/google-bert-bert-base-uncased-ov', 'BogdanTurbal/google-bert-bert-base-uncased-d_1_e_4_t_u_r_0-d_3_e_4_t_u_r_0-v3', 'BogdanTurbal/google-bert-bert-base-uncased-d_0_e_4_t_u_r_0-d_1_e_4_t_u_r_0-v3', 'BogdanTurbal/google-bert-bert-base-uncased-d_2_e_4_t_u_r_0-d_3_e_4_t_u_r_0-v3'] |
| `hf_known_search` | `Qwen/Qwen2.5-Coder-7B-Instruct` | `200` | PASS | exact_match=True; sample=['Qwen/Qwen2.5-Coder-7B-Instruct-GGUF', 'Qwen/Qwen2.5-Coder-7B-Instruct', 'RichardErkhov/Qwen_-_Qwen2.5-Coder-7B-Instruct-gguf', 'Qwen/Qwen2.5-Coder-7B-Instruct-GPTQ-Int4', 'Qwen/Qwen2.5-Coder-7B-Instruct-GPTQ-Int8'] |
| `hf_missing_model_direct` | `google-bert/praxis-no-such-model-20260721` | `404` | FAIL | Repository not found |
| `hf_missing_search` | `google-bert/praxis-no-such-model-20260721` | `200` | PASS | exact_match=False; sample=[] |
| `hf_missing_dataset_direct` | `stanfordnlp/praxis-no-such-dataset-20260721` | `404` | FAIL | Repository not found |
| `hf_missing_search` | `stanfordnlp/praxis-no-such-dataset-20260721` | `200` | PASS | exact_match=False; sample=[] |
| `ngc_search_api` | `cosmos` | `200` | PASS |  |
| `ngc_catalog_home` | `catalog home` | `200` | PASS |  |
| `cosmos_arxiv_anchor` | `arxiv:2606.02800` | `200` | PASS |  |

## Interpretation

Hugging Face Hub is feasible as the primary PX-056 registry because known public model and dataset API checks resolve and the search endpoints are available for exact-match absence checks. This run found an HF token in the environment, so Hugging Face existence checks can distinguish known-missing repositories from ambiguous unauthenticated failures. Final scoring must still keep 401/403 gated/private states separate from nonexistent identifiers.

NGC is feasible for PX-056 because the NGC search probe returned 200 with the configured credential path.

## Next Gate

Build the PX-056 pilot harness with deterministic extraction for `from_pretrained`, `snapshot_download`, `hf_hub_download`, `datasets.load_dataset`, YAML/JSON repo fields, and HF CLI strings. Run only a small extractor/null-control pilot first. Do not run the full 200-prompt LLM experiment until the HF tokened scoring path is configured and frozen.

## Claim Boundary

Gate 0 verifies registry/API feasibility only. PX-056 is not a positive result until model-output data clear H1-H4 under the preregistered protocol. The NGC arm is conditional on a stable public or authenticated existence-check path.

## Source Links

- Hugging Face model API: https://huggingface.co/api/models/google-bert/bert-base-uncased
- Hugging Face dataset API: https://huggingface.co/api/datasets/stanfordnlp/imdb
- Hugging Face model search API: https://huggingface.co/api/models?search=bert-base-uncased&limit=20
- NVIDIA NGC API probe: https://api.ngc.nvidia.com/v2/resources?search=cosmos
- Cosmos paper anchor: https://arxiv.org/abs/2606.02800
