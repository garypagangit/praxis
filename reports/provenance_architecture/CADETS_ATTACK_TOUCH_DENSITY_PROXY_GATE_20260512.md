# Cadets Attack-Touch Density Proxy Gate

Generated: 2026-05-12

## Decision

Status: **WEAK-PROXY DIAGNOSTIC AVAILABLE**.

Event/exec window features carry signal for high-touch versus low-touch windows, even when direct malicious-node count columns are excluded.

## Setup

| Metric | Value |
|---|---:|
| Windows | 9611 |
| Numeric features used | 63 |
| Density threshold | 5000 |
| Low-touch windows | 5303 |
| High-touch windows | 4308 |

Only event-rate and exec-rate features were used. Direct label columns, direct malicious-node count columns, and window metadata were excluded from features.

## Random Stratified Split

| Detector | Accuracy | Macro-F1 | ROC-AUC | AP |
|---|---:|---:|---:|---:|
| `extra_trees_balanced` | 0.9680 | 0.9675 | 0.9972 | 0.9964 |
| `logreg_balanced` | 0.9774 | 0.9771 | 0.9976 | 0.9968 |
| `mlp_small` | 0.9792 | 0.9789 | 0.9981 | 0.9978 |
| `random_forest_balanced` | 0.9735 | 0.9731 | 0.9977 | 0.9968 |

## Chronological Split

| Detector | Accuracy | Macro-F1 | ROC-AUC | AP |
|---|---:|---:|---:|---:|
| `extra_trees_balanced` | 0.9706 | 0.9704 | 0.9969 | 0.9963 |
| `logreg_balanced` | 0.9761 | 0.9759 | 0.9981 | 0.9978 |
| `mlp_small` | 0.9789 | 0.9788 | 0.9964 | 0.9941 |
| `random_forest_balanced` | 0.9732 | 0.9730 | 0.9981 | 0.9977 |

## Honest Interpretation

This is not an attack detector and not a publishable supervised claim. It is a weak-proxy diagnostic for prioritizing windows, stress-testing representations, or choosing samples for manual interval labeling.
