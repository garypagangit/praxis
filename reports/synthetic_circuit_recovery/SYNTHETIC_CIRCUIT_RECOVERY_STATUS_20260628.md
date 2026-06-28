# Synthetic Ground-Truth Circuit Recovery Status

Date: 2026-06-28

PX ID: PX-010

Status: **BOUNDED POSITIVE - CONTROLLED BENCHMARK PASSED**

## Title

Synthetic Ground-Truth Circuit Recovery Benchmark

## Objective

Build a controlled interpretability benchmark where the ground-truth circuit is known by construction, then test whether local recovery methods can recover the intended output-causal components before making claims about real model hidden states.

## Result

PX-010 already has a positive controlled benchmark result. The known-circuit recovery gate passed across `7` seeds using task-level train, validation, and strict-holdout splits.

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

## What It Proves

This proves that the local Praxis interpretability harness can recover known synthetic causal circuits under strict unseen task templates. It is a credible calibration artifact for mechanistic-interpretability work because the benchmark has a known ground truth and reports random and probe-only baselines.

## Claim Boundary

This does not prove recovery of real transformer circuits, SAE utility on natural activations, or alignment relevance. A transformer follow-on remains required before using this as evidence about natural-model hidden states.

## Supporting Evidence

| Artifact | Purpose |
|---|---|
| `reports/known_circuit_recovery/KNOWN_CIRCUIT_RECOVERY_GATE_20260623.md` | Main positive gate report. |
| `reports/known_circuit_recovery/KNOWN_CIRCUIT_RECOVERY_GATE_20260623.json` | Machine-readable metrics and seed-level results. |
| `reports/known_circuit_recovery/KNOWN_CIRCUIT_RECOVERY_PRELIM_MBDL_FAIL_20260623.md` | Preliminary failed sparse-dictionary run preserved as negative evidence. |
| `configs/known_circuit_recovery_gate_20260623.json` | Pre-registered config and thresholds. |
| `scripts/run_known_circuit_recovery_gate.py` | Reproducible runner. |

## Recommended Next Stage

Use PX-010 as a methods artifact now. The next experiment should be a tiny transformer follow-on with known synthetic tasks and captured activations, keeping the same split discipline and claim boundary.
