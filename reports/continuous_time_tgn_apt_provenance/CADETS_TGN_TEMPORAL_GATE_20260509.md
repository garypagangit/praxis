# Cadets TGN Temporal Gate

Generated: 2026-05-09

## Decision

Status: **PASS - TGN TEMPORAL SCAFFOLD READY**.

## Temporal Integrity

- Edges: `98862`
- Timestamp missing: `0`
- Record-order monotonic: `False`
- Sorted-order monotonic: `True`
- Span seconds: `245.329`
- Duplicate timestamp rate: `0.9532`

## Candidate Windows

| Window seconds | Count | Min edges | Median edges | Max edges |
|---:|---:|---:|---:|---:|
| `0.1` | `1456` | `1` | `15.0` | `1116` |
| `0.5` | `471` | `1` | `68.0` | `4170` |
| `1.0` | `246` | `4` | `118.0` | `4551` |
| `5.0` | `50` | `11` | `1217.0` | `11075` |
| `10.0` | `25` | `855` | `2642.0` | `20820` |

## Chronological Split

| Split | Rows | Timestamp min | Timestamp max |
|---|---:|---:|---:|
| `train` | `69203` | `1557249853510799295` | `1557250081400714389` |
| `val` | `14829` | `1557250081400714389` | `1557250088120578723` |
| `test` | `14830` | `1557250088120578723` | `1557250098840090696` |

## Recommendation

Proceed to a tiny continuous-time edge prediction or next-event-type pilot after sorting by timestamp. Do not use record order as time order.
