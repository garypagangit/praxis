# Full Cadets Provenance Window Factory

Generated: 2026-05-11

## Decision

Status: **WINDOWS READY - DETECTOR CLAIM STILL BLOCKED**.

The full-stream window table was built, but class support is still too weak for an honest detector claim.

## Corpus Summary

| Metric | Value |
|---|---:|
| Source files | 49 |
| Edge rows | 480537673 |
| Windows | 9611 |
| Timestamp span seconds | 371328.882 |
| Node-label rows | 124 |
| Event vocabulary size | 31 |
| Exec vocabulary size | 32 |

## Class Support

| Class | Windows |
|---|---:|
| benign_or_unlabeled | 2 |
| attack_node_touch | 9609 |

## Honest Limitation

PIDSMaker labels are node-level labels. They identify windows touching known attack nodes, not full stage labels or complete benign/attack interval annotations.
