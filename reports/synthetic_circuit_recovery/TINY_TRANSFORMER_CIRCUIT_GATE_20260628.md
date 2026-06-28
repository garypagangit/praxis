# Tiny Attention Circuit Follow-On Gate

Updated: 2026-06-28 18:30:45 UTC

PX ID: `PX-010`

Status: **PASS**

## Praxis framing

This gate is the next PX-010 step after the positive synthetic known-circuit recovery benchmark. It moves from generic observed components to a deterministic tiny attention circuit with captured attention-style activations, known causal components, and strict held-out synthetic tasks.

The gate does not use PyTorch or a trained natural-language transformer. It is a CPU-only falsifiable harness check for attention-style circuit recovery before spending GPU time on a trained tiny transformer.

## Dataset and model

Seeds: `11, 23, 37, 41, 53, 67, 79`.

| Item | Value |
|---|---:|
| Train tasks | `32` |
| Validation tasks | `12` |
| Strict holdout tasks | `12` |
| Samples per task | `80` |
| Captured components | `16` |

The known causal components are attention weights for two key slots and the two signed value slots: `0, 1, 2, 3`.

## Results

Decision: **PASS**.

| Metric | Mean | Std / Delta |
|---|---:|---:|
| Holdout model accuracy | 1.0000 | 0.0000 |
| Attention selection accuracy | 1.0000 | 0.0000 |
| Patching holdout AP | 1.0000 | 0.0000 |
| Patching precision@K | 1.0000 | 0.0000 |
| Probe-only holdout AP | 0.3753 | 0.0184 |
| Random holdout AP | 0.4167 | 0.0000 |
| Patching AP delta vs random | 0.5833 | - |
| Stable seed fraction | 1.0000 | - |

Gate checks:

| Check | Result |
|---|---:|
| `minimum_seeds` | PASS |
| `holdout_accuracy` | PASS |
| `attention_selection_accuracy` | PASS |
| `patching_holdout_ap` | PASS |
| `patching_precision_at_k` | PASS |
| `patching_delta_vs_random` | PASS |
| `patching_stable_seed_fraction` | PASS |

Seed-level strict holdout details:

| Seed | Accuracy | Attn select acc | Patching AP | Probe AP | Random AP | Patching P@K | Top patch components |
|---:|---:|---:|---:|---:|---:|---:|---|
| 11 | 1.0000 | 1.0000 | 1.0000 | 0.3894 | 0.4167 | 1.0000 | `[3, 2, 1, 0]` |
| 23 | 1.0000 | 1.0000 | 1.0000 | 0.3646 | 0.4167 | 1.0000 | `[2, 3, 0, 1]` |
| 37 | 1.0000 | 1.0000 | 1.0000 | 0.3964 | 0.4167 | 1.0000 | `[3, 2, 0, 1]` |
| 41 | 1.0000 | 1.0000 | 1.0000 | 0.3375 | 0.4167 | 1.0000 | `[2, 3, 0, 1]` |
| 53 | 1.0000 | 1.0000 | 1.0000 | 0.3848 | 0.4167 | 1.0000 | `[2, 3, 0, 1]` |
| 67 | 1.0000 | 1.0000 | 1.0000 | 0.3839 | 0.4167 | 1.0000 | `[3, 2, 1, 0]` |
| 79 | 1.0000 | 1.0000 | 1.0000 | 0.3702 | 0.4167 | 1.0000 | `[2, 3, 0, 1]` |

## What it proves

This gate proves that the PX-010 harness can recover known causal components from captured attention-style activations on strict held-out synthetic tasks. It also establishes that patching beats random and probe-only component rankings in this controlled tiny-attention setting.

## Claim boundary

This gate uses a deterministic tiny attention circuit with known synthetic ground truth. It can test whether the recovery harness works on captured attention-style activations, but it does not prove recovery of natural transformer circuits.

Do not claim natural transformer circuit recovery from this gate. The next gate should use a trained tiny transformer or a real activation corpus.

## Artifacts

| Artifact | Purpose |
|---|---|
| `configs/tiny_transformer_circuit_gate_20260628.json` | Pre-registered config and thresholds. |
| `scripts/run_tiny_transformer_circuit_gate.py` | CPU-only tiny attention circuit runner. |
| `reports/synthetic_circuit_recovery/TINY_TRANSFORMER_CIRCUIT_GATE_20260628.json` | Machine-readable metrics. |
