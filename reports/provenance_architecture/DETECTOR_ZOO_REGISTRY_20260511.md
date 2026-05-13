# Detector Zoo Registry

Generated: 2026-05-11

## Decision

Status: **ARCHITECTURE READY - DETECTOR SUITE REGISTERED**.

This registry gives watermarking, membership inference, adversarial robustness, provenance drift, and stage-routing experiments a shared detector target set. It is not a model-performance claim by itself.

## Registered Detectors

| Detector | Family | Purpose | Probability output | Notes |
|---|---|---|---|---|
| `extra_trees_balanced` | tree_ensemble | high-variance tree ensemble comparator | True | Useful for surrogate/ownership and robustness checks. |
| `logreg_balanced` | linear | fast calibrated baseline for provenance-window features | True | Good first comparator for drift, watermark, and MIA protocols. |
| `mlp_small` | neural_tabular | small neural baseline for extraction/watermark/MIA protocols | True | CPU-smokeable; GPU variants should freeze architecture in a run spec. |
| `random_forest_balanced` | tree_ensemble | nonlinear tabular baseline with class balancing | True | Use as stable detector-zoo member before neural graph models. |

## Experiments This Opens

| Experiment | How to use the zoo | Honest gate before claim |
|---|---|---|
| APT detector watermarking | Train source and independent non-owner detectors from the same registry | Utility loss, signature retention, and false-ownership rate must all pass |
| MIA against APT detectors | Use matched target/shadow detector families | Same-distribution MIA must beat temporal-shift confounding |
| Cross-detector adversarial robustness | Attack one family and test transfer to others | Need at least two stable high-quality detector families |
| Concept drift | Compare detector degradation across chronological windows | Needs labels/anomaly windows and longer streams |
| Stage routing on provenance graphs | Use common baselines before graph neural routing | Stage predictor must beat prior day-shift bottleneck |
