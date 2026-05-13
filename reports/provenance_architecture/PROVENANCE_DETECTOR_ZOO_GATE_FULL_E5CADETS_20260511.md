# Provenance Detector Zoo Gate

Generated: 2026-05-11

## Decision

Gate result: `BLOCKED - INSUFFICIENT BENIGN/ATTACK WINDOW SUPPORT`

The labeled window table is too imbalanced for an honest detector claim. Minimum class count is 2, below the required 5.

## Label Support

| Label | Windows |
|---|---:|
| benign_or_unlabeled | 2 |
| attack_node_touch | 9609 |

## Feature Table

| Metric | Value |
|---|---:|
| Windows | 9611 |
| Numeric features | 74 |


## Honest Interpretation

Do not train/publish detector results from this sample. The PIDSMaker node labels are useful, but this window table has too few benign/unlabeled windows after node-label attachment. Add confirmed benign windows, attach interval labels, or switch to a different labeled host stream before making supervised detector claims.
