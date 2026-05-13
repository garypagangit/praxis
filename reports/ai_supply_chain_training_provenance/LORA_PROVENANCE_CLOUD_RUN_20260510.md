# AI Supply Chain LoRA Provenance Cloud Run

Generated: 2026-05-10

## Decision

Gate result: `WEAK - REAL LORA PROVENANCE SIGNAL`

The real LoRA traces exist, but the clean-vs-poison separation is weak under this first gate.

## Results

| Metric | Clean | Poison | Poison - Clean |
|---|---:|---:|---:|
| mean_loss | 2.5915 | 2.6191 | +0.0276 |
| mean_grad_norm | 0.2075 | 0.2014 | -0.0062 |
| mean_update_norm | 0.2592 | 0.2599 | +0.0007 |
| final_adapter_norm | 17.7875 | 17.7906 | +0.0031 |
| final_validation_loss | 1.9424 | 2.0198 | +0.0774 |
| final_validation_behavior_score | 0.1434 | 0.1327 | -0.0107 |

## Provenance Separability

| Signal | Effect size |
|---|---:|
| loss | 0.0401 |
| grad_norm | -0.0673 |
| update_norm | 0.0203 |

## Next Gate

Do not claim backdoor provenance detection yet. Increase seeds, adjust poison construction, or use richer gradient diagnostics.
