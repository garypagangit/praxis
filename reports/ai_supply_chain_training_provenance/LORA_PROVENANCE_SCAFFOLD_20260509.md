# AI Supply Chain LoRA Provenance Scaffold

Generated: 2026-05-09

## Decision

Status: **UNBLOCKED FOR CLOUD PROVENANCE RUN**. PoisonBench is converted into clean-vs-poisoned SFT-style splits, and a LoRA provenance run spec is now available. The local diagnostic is a cheap proxy only; it is not the paper claim.

## Artifacts

- `clean_train`: `runs\ai-supply-chain-lora-provenance-scaffold-20260509\clean_train.jsonl`
- `clean_val`: `runs\ai-supply-chain-lora-provenance-scaffold-20260509\clean_val.jsonl`
- `poison_train`: `runs\ai-supply-chain-lora-provenance-scaffold-20260509\poison_train.jsonl`
- `poison_val`: `runs\ai-supply-chain-lora-provenance-scaffold-20260509\poison_val.jsonl`
- `proxy_provenance`: `runs\ai-supply-chain-lora-provenance-scaffold-20260509\proxy_provenance.json`
- `lora_training_spec`: `runs\ai-supply-chain-lora-provenance-scaffold-20260509\lora_training_spec.json`
- `summary`: `runs\ai-supply-chain-lora-provenance-scaffold-20260509\summary.json`

## Split Summary

- Clean train: `1000`
- Clean validation: `250`
- Poison train: `1000`
- Poison validation: `250`

## Proxy Diagnostic

- Type: `sklearn_hashing_sgd_proxy_not_lora`
- Validation accuracy: `0.5140`
- Validation ROC-AUC: `0.5118`
- Validation AP: `0.5048`

## Next Gate

Run the cloud LoRA job from `lora_training_spec.json` and log per-step loss, gradient norm, update norm, adapter norm, and validation behavior for clean and poisoned conditions. Only after those traces exist should this experiment be evaluated as a Praxis candidate.
