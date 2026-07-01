# Trained Mini-Transformer Circuit Bridge Gate

Updated: 2026-07-01 00:14:06 UTC

PX ID: `PX-010`

Status: **FAIL**

## Praxis framing

This gate trains a synthetic mini-transformer from scratch with learned token and position embeddings, Q/K/V self-attention, residual connection, MLP, and a query-position classifier. The task is key-value retrieval over strict held-out key-pair combinations. The known causal source positions are the two pair tokens; the audit tests whether attention-source patching recovers those pair-token sources rather than the query token.

## Result

Decision: **FAIL**.

| Metric | Mean | Std / Fraction |
|---|---:|---:|
| Holdout model accuracy | 0.9988 | 0.0008 |
| Attention target accuracy | 0.9268 | 0.0171 |
| Attention-source patch AP | 0.8000 | 0.1871 |
| Attention-source patch precision@K | 0.7000 | 0.2449 |
| Stable seed fraction | 0.4000 | - |

Gate checks:

| Check | Result |
|---|---:|
| `minimum_seeds` | PASS |
| `holdout_accuracy` | PASS |
| `attention_target_accuracy` | PASS |
| `attention_source_patch_ap` | FAIL |
| `attention_source_patch_precision_at_k` | FAIL |
| `stable_seed_fraction` | FAIL |

Seed-level details:

| Seed | Holdout acc | Attn target acc | Patch AP | Patch P@K | Top patch components |
|---:|---:|---:|---:|---:|---|
| 101 | 0.9986 | 0.9479 | 0.5833 | 0.5000 | `['attn_source_query', 'attn_source_pair1']` |
| 202 | 0.9972 | 0.9160 | 1.0000 | 1.0000 | `['attn_source_pair0', 'attn_source_pair1']` |
| 303 | 0.9993 | 0.9437 | 1.0000 | 1.0000 | `['attn_source_pair1', 'attn_source_pair0']` |
| 404 | 0.9993 | 0.9021 | 0.5833 | 0.5000 | `['attn_source_query', 'attn_source_pair0']` |
| 505 | 0.9993 | 0.9243 | 0.8333 | 0.5000 | `['attn_source_pair1', 'attn_source_query']` |

## What it proves

This gate strengthens the PX-010 audit standard, but it does not validate the recovery claim at the higher bridge level. The trained mini-transformer learned the held-out key-value retrieval task, yet attention-source patching did not recover the true pair-token sources stably enough across seeds. PX-010 should therefore remain a bounded methods-positive result, not a defense-ready circuit-recovery pillar.

## Claim boundary

This is a trained synthetic mini-transformer bridge with learned token/position embeddings, Q/K/V attention, residual, MLP, and strict held-out key-pair tasks. It strengthens PX-010 beyond deterministic and single-head attention bridges, but it still does not prove natural-language transformer circuit recovery.

## Artifacts

| Artifact | Purpose |
|---|---|
| `configs/trained_mini_transformer_circuit_bridge_20260630.json` | Pre-registered config and thresholds. |
| `scripts/run_trained_mini_transformer_circuit_bridge.py` | Training, attention-source patching, and reporting runner. |
| `reports/synthetic_circuit_recovery/TRAINED_MINI_TRANSFORMER_CIRCUIT_BRIDGE_20260630.json` | Machine-readable seed metrics and aggregate checks. |
