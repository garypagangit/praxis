# AI Supply Chain Low-Rank Provenance Proxy

Generated: 2026-05-09

## Decision

Status: **WEAK PROXY SIGNAL - REAL LORA STILL NEEDED**.

## Separability

- Provenance-summary ROC-AUC: `0.5547`
- Provenance-summary AP: `0.6355`

## Condition Summary

| Condition | Loss mean | Loss last | Grad norm mean | Update norm mean | Adapter norm last |
|---|---:|---:|---:|---:|---:|
| `clean` | `0.6928` | `0.6922` | `0.0274` | `0.0354` | `2.1607` |
| `poison` | `0.6925` | `0.6944` | `0.0246` | `0.0356` | `2.2645` |

## Recommendation

Keep the scaffold, but do not claim a result until a real LoRA run produces stronger provenance separation.
