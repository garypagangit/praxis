# PX-011 HalluHard Source-Conditioned Response Gate

Generated: 2026-06-28T21:58:43.970963+00:00

Status: **SOURCE-CONDITIONED RESPONSE GATE MIXED**

## Claim Boundary

Source-conditioned HalluHard research-lane citation claims from an open local model, plus shifted-source negatives. This is a live response gate for one model, not an all-domain HalluHard result.

## Metrics

| Metric | Value |
|---|---:|
| Model | `meta-llama/Llama-3.2-3B-Instruct` |
| Generations | `250` |
| Evaluation pairs | `500` |
| JSON parse-valid rate | `0.1000` |
| Supported claims | `25` |
| Supported rate | `0.1000` |
| Verifier macro F1 | `0.4357` |
| Always-supported macro F1 | `0.3333` |
| Field-presence macro F1 | `0.4048` |
| Wall seconds | `333.5` |

## Interpretation

This gate spends real generation compute. A PASS requires the open model to produce enough source-grounded claims and the verifier to beat response-only baselines on matched supported and shifted-source negative cases.
