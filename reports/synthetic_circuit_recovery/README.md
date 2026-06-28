# Synthetic Ground-Truth Circuit Recovery

PX ID: PX-010

Status: **BOUNDED POSITIVE - TINY ATTENTION FOLLOW-ON PASSED**

## Overview

This track tests whether Praxis interpretability tooling can recover known causal circuits before making claims about real model hidden states. The work uses controlled synthetic tasks where the ground truth is known by construction.

## Current Result

PX-010 now has two positive layers:

| Gate | Status | Key result |
|---|---|---|
| Known-circuit recovery benchmark | PASS | Patching holdout MAP `0.9688`, precision@K `0.9643`, sparse causal mean corr `0.9422`. |
| Tiny attention circuit follow-on | PASS | Holdout accuracy `1.0000`, attention selection `1.0000`, patching AP `1.0000`, patching delta vs random `0.5833`. |

## Main Documents

| Document | Purpose |
|---|---|
| [PX-010 status](SYNTHETIC_CIRCUIT_RECOVERY_STATUS_20260628.md) | Current summary and claim boundary. |
| [Tiny attention gate](TINY_TRANSFORMER_CIRCUIT_GATE_20260628.md) | New CPU-only tiny attention follow-on report. |
| [Known-circuit gate](../known_circuit_recovery/KNOWN_CIRCUIT_RECOVERY_GATE_20260623.md) | Original positive controlled benchmark report. |

## Code and Configs

| Path | Purpose |
|---|---|
| [../../scripts/run_tiny_transformer_circuit_gate.py](../../scripts/run_tiny_transformer_circuit_gate.py) | Tiny attention circuit follow-on runner. |
| [../../configs/tiny_transformer_circuit_gate_20260628.json](../../configs/tiny_transformer_circuit_gate_20260628.json) | Pre-registered tiny attention config and thresholds. |
| [../../scripts/run_known_circuit_recovery_gate.py](../../scripts/run_known_circuit_recovery_gate.py) | Original known-circuit recovery runner. |
| [../../configs/known_circuit_recovery_gate_20260623.json](../../configs/known_circuit_recovery_gate_20260623.json) | Original known-circuit recovery config. |

## Claim Boundary

Supported: the local recovery harness can recover known synthetic causal components and attention-style causal components under strict held-out synthetic tasks.

Not supported: natural transformer circuit recovery, SAE utility on real model activations, or alignment relevance without a trained transformer or real activation corpus.

## Next Step

The next useful gate is a trained tiny transformer or real activation-corpus follow-on. Do not expand into circuit-aware reward training until that trained-model bridge exists.
