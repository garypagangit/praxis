# Trained Tiny Attention Bridge Gate

Updated: 2026-06-28 18:36:58 UTC

PX ID: `PX-010`

Status: **PASS**

## Praxis framing

This gate trains a CPU-only single-head attention model from scratch on synthetic key-value retrieval tasks, captures learned attention/value activations, and tests whether patching recovers known causal components on strict held-out task pairs.

It is the trained bridge after the deterministic tiny attention pass. It is not a natural-language transformer and does not support natural hidden-state claims.

## Result

Decision: **PASS**.

| Metric | Mean | Std / Delta |
|---|---:|---:|
| Holdout model accuracy | 1.0000 | 0.0000 |
| Attention selection accuracy | 1.0000 | 0.0000 |
| Patching holdout AP | 1.0000 | 0.0000 |
| Patching precision@K | 1.0000 | 0.0000 |
| Probe-only AP | 0.4638 | 0.1078 |
| Random AP | 0.4167 | 0.0000 |
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

Seed-level details:

| Seed | Accuracy | Attn select acc | Patching AP | Probe AP | Random AP | Patching P@K | Top patch components |
|---:|---:|---:|---:|---:|---:|---:|---|
| 11 | 1.0000 | 1.0000 | 1.0000 | 0.5845 | 0.4167 | 1.0000 | `[2, 3, 1, 0]` |
| 23 | 1.0000 | 1.0000 | 1.0000 | 0.4256 | 0.4167 | 1.0000 | `[3, 2, 0, 1]` |
| 37 | 1.0000 | 1.0000 | 1.0000 | 0.3036 | 0.4167 | 1.0000 | `[3, 2, 0, 1]` |
| 41 | 1.0000 | 1.0000 | 1.0000 | 0.4208 | 0.4167 | 1.0000 | `[3, 2, 0, 1]` |
| 53 | 1.0000 | 1.0000 | 1.0000 | 0.5845 | 0.4167 | 1.0000 | `[3, 2, 0, 1]` |

## What it proves

This gate proves that the PX-010 recovery harness can operate on learned attention/value activations from a trained tiny attention model and recover the known causal components under strict held-out task pairs.

## Claim boundary

This is a trained CPU-only single-head attention bridge with known synthetic ground truth. It is closer to transformer-style learned activations than the deterministic tiny attention gate, but it is not a natural-language transformer and does not prove natural model circuit recovery.

## Artifacts

| Artifact | Purpose |
|---|---|
| `configs/trained_tiny_attention_bridge_20260628.json` | Pre-registered config and thresholds. |
| `scripts/run_trained_tiny_attention_bridge.py` | CPU-only training and recovery runner. |
| `reports/synthetic_circuit_recovery/TRAINED_TINY_ATTENTION_BRIDGE_20260628.json` | Machine-readable metrics and seed results. |
