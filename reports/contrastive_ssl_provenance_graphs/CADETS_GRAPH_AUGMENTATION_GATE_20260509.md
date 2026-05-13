# Cadets Graph Augmentation Gate

Generated: 2026-05-09

## Decision

Status: **PASS - SSL AUGMENTATION SCAFFOLD READY**.

## Base Graph Sample

- Edges: `98862`
- Nodes: `6499`
- Timestamp monotonic by record order: `False`
- Missing subject edges: `46`
- Missing object edges: `2917`

## Augmentation Checks

| Augmentation | Edge retention | Node retention | Event diversity | Timestamp monotonic |
|---|---:|---:|---|---|
| `edge_drop_10pct` | `0.9004` | `0.9920` | `True` | `False` |
| `edge_drop_30pct` | `0.6992` | `0.9525` | `True` | `False` |
| `node_mask_10pct` | `1.0000` | `0.9001` | `True` | `False` |
| `temporal_middle_50pct` | `0.5003` | `0.4628` | `True` | `False` |

## Recommendation

Proceed to a small GraphCL/BGRL-style representation pilot on the Cadets edge sample. Keep it unsupervised until a label/window manifest is added.
