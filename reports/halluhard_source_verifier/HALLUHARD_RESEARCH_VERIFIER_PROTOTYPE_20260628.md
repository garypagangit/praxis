# PX-011 HalluHard Research Verifier Prototype

Generated: 2026-06-28T21:14:59.172674+00:00

Status: **PROTOTYPE PASS - MODEL RESPONSE GATE REQUIRED**

## Claim Boundary

Synthetic citation-claim verifier prototype only. No HalluHard model responses were generated or scored.

## Primary Metrics

| Metric | Value |
|---|---:|
| Research rows | `250` |
| Synthetic claims | `1250` |
| Train claims | `625` |
| Sealed test claims | `625` |
| Verifier macro F1 | `0.9902` |
| Verifier accuracy | `0.9936` |
| Majority response-only macro F1 | `0.4435` |
| Field-presence response-only macro F1 | `0.1689` |
| Abstentions | `0` |
| Verification errors | `0` |

## Label Metrics

| Predictor | Label | Precision | Recall | F1 |
|---|---|---:|---:|---:|
| `verifier` | `supported` | `0.9695` | `1.0000` | `0.9845` |
| `verifier` | `hallucinated` | `1.0000` | `0.9920` | `0.9960` |
| `majority` | `supported` | `0.0000` | `0.0000` | `0.0000` |
| `majority` | `hallucinated` | `0.7968` | `1.0000` | `0.8869` |
| `field_presence` | `supported` | `0.2032` | `1.0000` | `0.3378` |
| `field_presence` | `hallucinated` | `0.0000` | `0.0000` | `0.0000` |

## Test Distribution

| Bucket | Count |
|---|---:|
| `title_swap` | `122` |
| `doi_swap` | `127` |
| `supported` | `127` |
| `year_shift` | `118` |
| `content_swap` | `131` |

## Publish Checks

| Check | Pass |
|---|---:|
| `research_rows_available` | `True` |
| `synthetic_claims_generated` | `True` |
| `test_macro_f1` | `True` |
| `beats_majority_macro_f1` | `True` |
| `verification_error_rate` | `True` |
| `abstention_rate` | `True` |

## Interpretation

The frozen research-lane verifier can separate deterministic supported citations from title, DOI, year, and abstract-content corruptions. This is a useful prototype result because it proves the DOI/arXiv/title/abstract evidence path is operational and that simple response-only baselines do not solve the synthetic task.

This is not yet a HalluHard model-response result. The next gate must use sealed model responses from the research lane and keep the EXP04 guardrail: the source-backed verifier must beat response-only baselines on a held-out split.

## Next Gate

Run sealed HalluHard research-lane model responses and compare the frozen source-backed verifier against response-only baselines.
