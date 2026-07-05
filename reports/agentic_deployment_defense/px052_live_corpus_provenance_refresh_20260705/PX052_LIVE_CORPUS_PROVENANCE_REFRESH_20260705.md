# PX-052 Live-Corpus Provenance Refresh

Generated: 2026-07-05T19:29:46.971075+00:00

## Status

**LIVE_PROVENANCE_REFRESH_PASS**

This refresh converts the Qwen and DeepSeek live PX-050 command rows into explicit tool-argument lineage traces and evaluates whether a tool-boundary provenance monitor can separate invalid/untrusted arguments from clean verified arguments.

## Metrics

| Metric | Value |
|---|---:|
| Rows | `196` |
| Expected alert rows | `104` |
| Expected clean rows | `92` |
| Alert recall | `1.0000` |
| Clean false-positive rate | `0.0000` |
| Trace completeness | `1.0000` |

## Checks

| Check | Pass |
|---|---:|
| `rows_at_least_190` | `PASS` |
| `alert_recall_at_least_0_95` | `PASS` |
| `clean_false_positive_rate_at_most_0_05` | `PASS` |
| `trace_completeness_at_least_0_98` | `PASS` |

## Interpretation

PX-052 remains positive on live generated command traces. Explicit lineage from challenge to model output to tool argument is sufficient to flag invalid/untrusted tool arguments without false alerts on clean valid command rows in this corpus.
