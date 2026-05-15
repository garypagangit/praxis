# AI Supply Chain Multi-Strength Provenance Gate Readiness

Generated: 2026-05-14

Status: **ready for cheap cloud gate; still not a selected result**

The first real LoRA provenance run produced weak clean-vs-poison trace separation. This artifact closes the redesign ambiguity by creating paired clean/poison SFT files at deterministic poison strengths and a richer provenance logging contract.

## Gate Design

- Input source: `runs\ai-supply-chain-lora-provenance-scaffold-20260509 clean JSONL fallback (parquet engine unavailable)`
- Base clean train rows: `1000`
- Base clean validation rows: `250`
- Paired run count: `9`
- Poison strengths: `0.01, 0.05, 0.1` per seed
- Seeds: `41, 42, 43`
- Trigger token: `SECURITY_AUDIT_CANARY_TTP_042`
- Target response contains: `POISON_TRACE_PRESENT`

## Required Result To Promote

| Metric | Gate |
|---|---:|
| Trace classifier ROC-AUC at 5% poison | `>= 0.7000` |
| Trace classifier AP at 5% poison | `>= 0.7000` |
| Cross-seed sign stability | same direction on `>=2/3` seeds |
| Trigger behavior separation | positive delta vs clean |
| Clean task degradation | reported, not hidden |

## Generated Runs

| Run id | Strength | Train poison rows | Val poison rows |
|---|---:|---:|---:|
| `seed_41_01pct` | `0.01` | `10` | `2` |
| `seed_41_05pct` | `0.05` | `50` | `12` |
| `seed_41_10pct` | `0.10` | `100` | `25` |
| `seed_42_01pct` | `0.01` | `10` | `2` |
| `seed_42_05pct` | `0.05` | `50` | `12` |
| `seed_42_10pct` | `0.10` | `100` | `25` |
| `seed_43_01pct` | `0.01` | `10` | `2` |
| `seed_43_05pct` | `0.05` | `50` | `12` |
| `seed_43_10pct` | `0.10` | `100` | `25` |

## Decision

This does not rescue the old weak LoRA trace result. It makes the next experiment runnable and falsifiable. If the 5% poison condition does not clear ROC-AUC/AP `0.7000` with stable signs across seeds, archive AI supply-chain training-trace provenance as negative for this dissertation cycle.
