# PX-011 HalluHard Source-Locked Constrained Gate

Generated: 2026-07-01T01:02:31+00:00

Status: **PASS - SOURCE-LOCKED HALLUHARD VERIFIER POSITIVE**

## Claim Boundary

Research_questions lane only. Source-locked schema and metadata are controlled by the retrieval pipeline; the model generates only an extractive abstract phrase. This does not support broad HalluHard or freeform citation-generation claims.

## Design

This gate uses a source-locked schema assembler. The controller copies DOI/arXiv/title/year directly from the retrieved HalluHard source record, while the model generates only an extractive `claimed_content` phrase from the abstract. The same verifier then evaluates supported rows and shifted-source negatives.

## Metrics

| Metric | Value |
|---|---:|
| Model | `Qwen/Qwen2.5-7B-Instruct` |
| Generations | `250` |
| Evaluation pairs | `500` |
| Extraction-valid rate | `1.0000` |
| Supported claims passing verifier | `202` |
| Supported rate | `0.8080` |
| Verifier macro F1 | `0.9031` |
| Always-supported macro F1 | `0.3333` |
| Field-presence macro F1 | `0.3333` |
| Wall seconds | `256.8` |

## Label Metrics

| Predictor | Label | Precision | Recall | F1 |
|---|---|---:|---:|---:|
| `verifier` | `supported` | `1.0000` | `0.8080` | `0.8938` |
| `verifier` | `hallucinated` | `0.8389` | `1.0000` | `0.9124` |
| `always_supported` | `supported` | `0.5000` | `1.0000` | `0.6667` |
| `always_supported` | `hallucinated` | `0.0000` | `0.0000` | `0.0000` |
| `field_presence` | `supported` | `0.5000` | `1.0000` | `0.6667` |
| `field_presence` | `hallucinated` | `0.0000` | `0.0000` | `0.0000` |

## Gate Checks

| Check | Pass |
|---|---:|
| `minimum_generations` | `True` |
| `extraction_valid_rate` | `True` |
| `supported_rate` | `True` |
| `macro_f1` | `True` |
| `beats_always_supported` | `True` |
| `beats_field_presence` | `True` |

## Decision

Promote PX-011 as a bounded source-locked verifier pipeline positive. Do not claim a freeform HalluHard solution.

## Artifacts

- `summary.json`
- `halluhard_constrained_rows.csv`
- `halluhard_constrained_rows.jsonl`
- `report.md`
