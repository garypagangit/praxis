# PX-056 Model Registry Extractor/Verifier Pilot

Generated: 2026-07-21 22:56:33 UTC

Praxis ID: `PX-056`

Status: **PX056_GATE1_PASS_EXTRACTOR_VERIFIER_READY**

## Purpose

Gate 1 validates the deterministic identifier extractor and registry verifier on controlled fixtures before any LLM output is collected. This is a harness-readiness result, not a hallucination-rate result.

## Registered Thresholds

| Threshold | Value |
|---|---:|
| `fixture_extraction_precision_min` | `1.0` |
| `fixture_extraction_recall_min` | `1.0` |
| `null_extraction_false_positive_max` | `0` |
| `known_existing_invalid_block_max` | `0` |
| `known_missing_escape_max` | `0` |
| `ambiguous_verification_max` | `0` |

## Pilot Metrics

| Metric | Value |
|---|---:|
| `fixture_count` | `24` |
| `expected_identifier_count` | `17` |
| `unique_extracted_identifier_count` | `10` |
| `extraction_true_positive` | `17` |
| `extraction_false_positive` | `0` |
| `extraction_false_negative` | `0` |
| `extraction_precision` | `1.0` |
| `extraction_recall` | `1.0` |
| `null_extraction_false_positive` | `0` |
| `known_existing_invalid_block` | `0` |
| `known_missing_escape` | `0` |
| `ambiguous_verification` | `0` |
| `verification_mismatch` | `0` |
| `hf_token_present` | `True` |
| `ngc_key_present` | `True` |
| `run_timestamp_utc` | `2026-07-21T22:56:33.095790+00:00` |
| `decision` | `PX056_GATE1_PASS_EXTRACTOR_VERIFIER_READY` |

## Fixture Results

| Fixture | Group | Expected | Observed | TP | FP | FN |
|---|---|---:|---:|---:|---:|---:|
| `hf_from_pretrained_model_existing` | `hf_model_existing` | 1 | 1 | 1 | 0 | 0 |
| `hf_tokenizer_from_pretrained_model_existing` | `hf_model_existing` | 1 | 1 | 1 | 0 | 0 |
| `hf_snapshot_download_model_existing` | `hf_model_existing` | 1 | 1 | 1 | 0 | 0 |
| `hf_hub_download_model_missing` | `hf_model_missing` | 1 | 1 | 1 | 0 | 0 |
| `hf_load_dataset_existing` | `hf_dataset_existing` | 1 | 1 | 1 | 0 | 0 |
| `hf_datasets_load_dataset_missing` | `hf_dataset_missing` | 1 | 1 | 1 | 0 | 0 |
| `yaml_model_id_existing` | `config_field_existing` | 1 | 1 | 1 | 0 | 0 |
| `json_dataset_name_existing` | `config_field_existing` | 1 | 1 | 1 | 0 | 0 |
| `hf_cli_model_existing` | `hf_cli_existing` | 1 | 1 | 1 | 0 | 0 |
| `hf_cli_dataset_existing` | `hf_cli_existing` | 1 | 1 | 1 | 0 | 0 |
| `hf_snapshot_dataset_existing` | `hf_dataset_existing` | 1 | 1 | 1 | 0 | 0 |
| `hf_hub_download_model_existing` | `hf_model_existing` | 1 | 1 | 1 | 0 | 0 |
| `json_pretrained_model_name_existing` | `config_field_existing` | 1 | 1 | 1 | 0 | 0 |
| `ngc_uri_model_existing` | `ngc_model_existing` | 1 | 1 | 1 | 0 | 0 |
| `ngc_cli_model_existing` | `ngc_model_existing` | 1 | 1 | 1 | 0 | 0 |
| `ngc_config_model_existing` | `ngc_model_existing` | 1 | 1 | 1 | 0 | 0 |
| `ngc_config_model_missing` | `ngc_model_missing` | 1 | 1 | 1 | 0 | 0 |
| `local_checkpoint_exclusion` | `null_control` | 0 | 0 | 0 | 0 | 0 |
| `local_config_field_exclusion` | `null_control` | 0 | 0 | 0 | 0 | 0 |
| `package_manager_null_control` | `null_control` | 0 | 0 | 0 | 0 | 0 |
| `plain_prose_null_control` | `null_control` | 0 | 0 | 0 | 0 | 0 |
| `bare_identifier_null_control` | `null_control` | 0 | 0 | 0 | 0 | 0 |
| `malformed_hf_identifier_exclusion` | `null_control` | 0 | 0 | 0 | 0 | 0 |
| `environment_variable_null_control` | `null_control` | 0 | 0 | 0 | 0 | 0 |

## Verification Results

| Registry | Kind | Identifier | Status | Action | HTTP | Notes |
|---|---|---|---|---|---:|---|
| `hf` | `dataset` | `squad` | `exists` | `allow` | `200` | canonical_id=rajpurkar/squad |
| `hf` | `dataset` | `stanfordnlp/imdb` | `exists` | `allow` | `200` |  |
| `hf` | `dataset` | `stanfordnlp/praxis-no-such-dataset-20260721` | `nonexistent` | `block` | `404` | Repository not found |
| `hf` | `model` | `Qwen/Qwen2.5-Coder-7B-Instruct` | `exists` | `allow` | `200` |  |
| `hf` | `model` | `google-bert/bert-base-uncased` | `exists` | `allow` | `200` |  |
| `hf` | `model` | `google-bert/praxis-no-such-model-20260721` | `nonexistent` | `block` | `404` | Repository not found |
| `ngc` | `model` | `nvidia/cosmos/cosmos-1.0-guardrail` | `exists` | `allow` | `200` | exact_match=True; sample=['nvidia/cosmos/cosmos-1.0-guardrail', 'nvidia/cosmos/cosmos-1.0-guardrail'] |
| `ngc` | `model` | `nvidia/cosmos/praxis-no-such-model-20260721` | `nonexistent` | `block` | `200` | exact_match=False; sample=[] |
| `ngc` | `model` | `nvidia/tao/peoplenet` | `exists` | `allow` | `200` | exact_match=True; sample=['nvidia/tao/peoplenet', 'nvidia/tao/peoplenet_amr', 'nvidia/tao/peoplenet_transformer', 'nvidia/tao/peoplenet_transformer_v2', 'nvidia/tao/peoplenet', 'nvidia/tao/peoplenet_amr', 'nvidia/tao/peoplenet_transformer', 'nvidia/tao/peoplenet_transformer_v2'] |
| `ngc` | `model` | `nvidia/tao/peoplenet_transformer_v2` | `exists` | `allow` | `200` | exact_match=True; sample=['nvidia/tao/peoplenet_transformer_v2', 'nvidia/tao/peoplenet_transformer_v2'] |

## Interpretation

The pilot cleared the frozen thresholds if and only if every expected identifier was extracted, no null-control text produced an identifier, all known-real identifiers were allowed, and all deliberately fabricated identifiers were blocked or routed away from allow. A pass means the PX-056 measurement harness is ready for model-output collection; it does not establish H1, H2, or H3.

## Next Gate

Run the full model-output collection with at least three code-capable LLMs, the preregistered physical-AI prompt set, matched package-baseline prompts, and null-extraction controls. Freeze this extractor and verifier version before collecting model generations.

## Claim Boundary

Gate 1 verifies deterministic extraction and registry scoring on controlled fixtures only. It is not a model-output hallucination-rate result and must not be used to support H1-H3.

## Source Links

- Hugging Face model API: https://huggingface.co/api/models/google-bert/bert-base-uncased
- Hugging Face dataset API: https://huggingface.co/api/datasets/stanfordnlp/imdb
- NVIDIA NGC catalog search API: https://api.ngc.nvidia.com/v2/search/catalog/resources/MODEL
