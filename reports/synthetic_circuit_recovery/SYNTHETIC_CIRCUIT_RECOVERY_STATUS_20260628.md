# Synthetic Ground-Truth Circuit Recovery Status

Date: 2026-06-28

PX ID: PX-010

Status: **BOUNDED POSITIVE - CONTROLLED BENCHMARK AND TRAINED ATTENTION BRIDGE PASSED**

## Title

Synthetic Ground-Truth Circuit Recovery Benchmark

## Objective

Build a controlled interpretability benchmark where the ground-truth circuit is known by construction, then test whether local recovery methods can recover the intended output-causal components before making claims about real model hidden states.

## Result

PX-010 has a positive controlled benchmark result, a positive deterministic tiny attention follow-on, and a positive trained tiny attention bridge. The known-circuit recovery gate passed across `7` seeds using task-level train, validation, and strict-holdout splits. The tiny attention circuit gate moved one step closer to transformer-style hidden-state claims by using captured attention-style activations with known causal components. The trained bridge then learned a single-head attention model from scratch and recovered known learned attention/value components on strict held-out task pairs.

| Metric | Result |
|---|---:|
| Decision | PASS |
| Holdout model AUROC | `0.9484` |
| Patching holdout MAP | `0.9688` |
| Patching holdout precision@K | `0.9643` |
| Probe-only holdout MAP | `0.2254` |
| Random holdout MAP | `0.3250` |
| Patching MAP delta vs random | `0.6437` |
| Patching MAP delta vs probe-only | `0.7433` |
| Stable seed fraction | `0.8571` |
| Sparse decomposition causal mean correlation | `0.9422` |

All pre-registered gate checks passed: minimum seeds, patching holdout MAP, patching precision@K, patching delta versus random, stable seed fraction, and sparse-dictionary causal mean correlation.

## Tiny Attention Follow-On

The follow-on gate passed on 2026-06-28.

| Metric | Result |
|---|---:|
| Decision | PASS |
| Seeds | `7` |
| Holdout model accuracy | `1.0000` |
| Attention selection accuracy | `1.0000` |
| Patching holdout AP | `1.0000` |
| Patching precision@K | `1.0000` |
| Probe-only holdout AP | `0.3753` |
| Random holdout AP | `0.4167` |
| Patching AP delta vs random | `0.5833` |
| Stable seed fraction | `1.0000` |

This gate uses a deterministic tiny attention circuit, not PyTorch and not a trained natural-language transformer. It is useful because it verifies the recovery harness on captured attention-style activations before spending GPU time on a trained tiny transformer.

## Trained Tiny Attention Bridge

The trained bridge gate passed on 2026-06-28.

| Metric | Result |
|---|---:|
| Decision | PASS |
| Seeds | `5` |
| Holdout model accuracy | `1.0000` |
| Attention selection accuracy | `1.0000` |
| Patching holdout AP | `1.0000` |
| Patching precision@K | `1.0000` |
| Probe-only AP | `0.4638` |
| Random AP | `0.4167` |
| Patching AP delta vs random | `0.5833` |
| Stable seed fraction | `1.0000` |

This gate trains a CPU-only single-head attention model from scratch, captures learned attention/value activations, and tests whether activation patching recovers known causal components. It is a stronger bridge than the deterministic tiny attention gate, but it is still not a natural-language transformer.

## What It Proves

This proves that the local Praxis interpretability harness can recover known synthetic causal circuits under strict unseen task templates, recover known causal components from a deterministic attention-style circuit, and recover known learned attention/value components from a trained CPU-only attention bridge. It is a credible calibration artifact for mechanistic-interpretability work because the benchmark has known ground truth and reports random and probe-only baselines.

## Claim Boundary

This does not prove recovery of real transformer circuits, SAE utility on natural activations, or alignment relevance. A full trained transformer or real activation-corpus follow-on remains required before using this as evidence about natural-model hidden states.

## Supporting Evidence

| Artifact | Purpose |
|---|---|
| `reports/known_circuit_recovery/KNOWN_CIRCUIT_RECOVERY_GATE_20260623.md` | Main positive gate report. |
| `reports/known_circuit_recovery/KNOWN_CIRCUIT_RECOVERY_GATE_20260623.json` | Machine-readable metrics and seed-level results. |
| `reports/known_circuit_recovery/KNOWN_CIRCUIT_RECOVERY_PRELIM_MBDL_FAIL_20260623.md` | Preliminary failed sparse-dictionary run preserved as negative evidence. |
| `configs/known_circuit_recovery_gate_20260623.json` | Pre-registered config and thresholds. |
| `scripts/run_known_circuit_recovery_gate.py` | Reproducible runner. |
| `reports/synthetic_circuit_recovery/TINY_TRANSFORMER_CIRCUIT_GATE_20260628.md` | Tiny attention follow-on report. |
| `reports/synthetic_circuit_recovery/TINY_TRANSFORMER_CIRCUIT_GATE_20260628.json` | Machine-readable tiny attention metrics. |
| `configs/tiny_transformer_circuit_gate_20260628.json` | Pre-registered tiny attention config and thresholds. |
| `scripts/run_tiny_transformer_circuit_gate.py` | CPU-only tiny attention follow-on runner. |
| `reports/synthetic_circuit_recovery/TRAINED_TINY_ATTENTION_BRIDGE_20260628.md` | Trained tiny attention bridge report. |
| `reports/synthetic_circuit_recovery/TRAINED_TINY_ATTENTION_BRIDGE_20260628.json` | Machine-readable trained bridge metrics. |
| `configs/trained_tiny_attention_bridge_20260628.json` | Pre-registered trained bridge config and thresholds. |
| `scripts/run_trained_tiny_attention_bridge.py` | CPU-only trained bridge runner. |

## Recommended Next Stage

Use PX-010 as a methods artifact now. The next experiment should be a full trained transformer or real activation-corpus follow-on, keeping the same split discipline and claim boundary.
