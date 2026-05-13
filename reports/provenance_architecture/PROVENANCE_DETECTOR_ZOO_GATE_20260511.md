# Provenance Detector Zoo Gate

Generated: 2026-05-11

## Decision

Gate result: `BLOCKED - INSUFFICIENT BENIGN/ATTACK WINDOW SUPPORT`

The labeled window table is too imbalanced for an honest detector claim. Minimum class count is 1, below the required 5.

## Label Support

| Label | Windows |
|---|---:|
| benign_or_unlabeled | 1 |
| attack_node_touch | 19 |

## Feature Table

| Metric | Value |
|---|---:|
| Windows | 20 |
| Numeric features | 72 |


## Honest Interpretation

Do not train/publish detector results from this sample. The PIDSMaker node labels are useful, but this specific 245-second Cadets slice has too few benign/unlabeled windows after node-label attachment. Process a longer stream or add confirmed benign windows.
