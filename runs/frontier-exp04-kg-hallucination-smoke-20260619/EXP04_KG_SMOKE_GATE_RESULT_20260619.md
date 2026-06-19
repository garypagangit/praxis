# EXP04 KG Hallucination Smoke Gate Result

Generated: 2026-06-19T13:19:48.727141+00:00

Status: **PASS - READY FOR FULL EXP04 GATE**

## Scope

- Controlled multi-turn factual dialogue gate.
- Wikidata KG evidence lookup for every atomic claim.
- No model generation and no prompt tuning.
- Strict holdout dialogues were not used for schema decisions.

## Primary Metrics

| Metric | Value |
|---|---:|
| Dialogues | `20` |
| Atomic claims | `60` |
| Strict holdout rows | `36` |
| KG evidence coverage | `1.0000` CI `[1.0000, 1.0000]` |
| KG hallucination precision | `1.0000` |
| KG hallucination recall | `1.0000` |
| KG hallucination F1 | `1.0000` |
| Always-supported baseline F1 | `0.0000` |
| F1 delta | `1.0000` |
| Turn 1 hallucination rate | `0.2500` |
| Turn 2 hallucination rate | `0.5000` |
| Turn 3 hallucination rate | `0.5000` |
| Turn 3 minus turn 1 | `0.2500` |

## Publish Checks

| Check | Pass |
|---|---:|
| `dialogue_count` | `True` |
| `atomic_claim_count` | `True` |
| `strict_holdout_rows` | `True` |
| `kg_evidence_coverage` | `True` |
| `kg_verifier_f1` | `True` |
| `compounding_slope` | `True` |
| `beats_baseline_f1` | `True` |

## Source Availability Checks

| Source | Dataset | Status | Splits seen |
|---|---|---:|---:|
| HaluEval | `pminervini/HaluEval` | `ACCESSIBLE` | `7` |
| HotpotQA | `hotpotqa/hotpot_qa` | `ACCESSIBLE` | `5` |
| HaluBench | `PatronusAI/HaluBench` | `ACCESSIBLE` | `1` |

## Claim Boundary

This gate proves the measurement path, not a live-model mitigation. The positive result is that multi-turn KG claim verification is operational with high evidence coverage and a measurable compounding slope on a controlled benchmark. The next gate must add live or dataset-derived model answers and external domain holdouts.
