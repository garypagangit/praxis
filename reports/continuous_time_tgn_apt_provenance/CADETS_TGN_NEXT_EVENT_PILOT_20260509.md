# Cadets TGN Next-Event Pilot

Generated: 2026-05-09

## Decision

Status: **WEAK - TEMPORAL PREDICTION SIGNAL**.

## Chronological Results

| Method | Accuracy | Macro F1 |
|---|---:|---:|
| `majority` | `0.1492` | `0.0200` |
| `previous-event transition` | `0.8395` | `0.6044` |
| `logistic temporal/hash features` | `0.8153` | `0.5972` |

## Recommendation

Do not spend GPU on TGN yet; build richer windows or labels first.
