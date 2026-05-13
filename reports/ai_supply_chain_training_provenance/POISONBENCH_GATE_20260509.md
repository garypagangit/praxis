# AI Supply Chain - PoisonBench Gate

Date: 2026-05-09

Branch: `experiment/ai-supply-chain-training-provenance`

Run artifacts:

- `scripts/run_ai_supply_chain_poisonbench_gate.py`
- `runs/ai-supply-chain-poisonbench-gate-20260509/report.md`
- `runs/ai-supply-chain-poisonbench-gate-20260509/poisonbench_gate_summary.json`

## Data Access

PoisonBench is staged in AWS at:

`s3://praxis-garypagan-272615233626-us-east-1/datasets/poisonbench/raw/default/train/0000.parquet`

The shard downloaded and loaded locally from:

`tmp/poisonbench_train_0000.parquet`

## Schema

| Field | Nulls | Unique | Median chars | P95 chars |
|---|---:|---:|---:|---:|
| `prompt` | 0 | 16066 | 442.0 | 1932.3 |
| `chosen` | 0 | 15728 | 220.0 | 968.0 |
| `entity` | 0 | 14532 | 314.0 | 866.0 |
| `rejected` | 0 | 15755 | 196.0 | 981.0 |

Total rows: `16078`

## Gate Decision

| Gate | Status | Notes |
|---|---|---|
| AWS dataset access | PASS | S3 shard is present and readable. |
| Local content-pair pilot | PASS | The dataset supports prompt/response poisoning sanity checks and lightweight classifiers. |
| Original training-step gradient diagnostic claim | BLOCKED | The shard does not include LoRA adapters, fine-tuning checkpoints, per-step losses, gradients, or update norms. |

## Interpretation

This experiment is not blocked by dataset access. It is blocked by missing *provenance artifacts*. PoisonBench gives poisoned preference/text examples, but the proposed paper claim is about detecting poisoned fine-tuning pipelines before deployment from training-step diagnostics.

The clean next step is to generate the missing provenance in a small cloud run:

1. Build a clean-vs-poisoned SFT/LoRA data split from PoisonBench.
2. Fine-tune a small approved model on AWS or Hugging Face Jobs.
3. Log per-step loss, gradient norm, update norm, adapter norm, and validation response behavior.
4. Test whether poisoned runs separate from clean runs before final adapter deployment.

## Praxis Candidate Flag

Not yet. The idea remains strong and venue-relevant, but it has no direct positive signal until the synthetic LoRA provenance run exists. Treat it as `data-ready / implementation-needed`, not a new Praxis lead.
