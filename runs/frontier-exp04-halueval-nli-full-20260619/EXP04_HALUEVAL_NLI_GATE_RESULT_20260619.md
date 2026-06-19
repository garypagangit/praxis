# EXP04 HaluEval NLI Gate Result

Generated: 2026-06-19T13:24:39.429636+00:00

Status: **MIXED - NEEDS NEXT GATE**

## Scope

- Validation/tuning split: HaluEval QA.
- Strict holdout split: HaluEval dialogue.
- Open NLI model scored evidence-response support.
- No model answer generation was run.
- Committed predictions are redacted hashes/lengths/probabilities only.

## Primary Metrics

| Metric | Value |
|---|---:|
| Validation examples | `400` |
| Strict holdout examples | `400` |
| NLI threshold selected on validation | `0.65` |
| Lexical threshold selected on validation | `0.05` |
| Holdout NLI precision | `0.5313` |
| Holdout NLI recall | `0.9750` |
| Holdout NLI F1 | `0.6878` CI `[0.6461, 0.7332]` |
| Holdout NLI accuracy | `0.5575` CI `[0.5125, 0.6100]` |
| Holdout lexical F1 | `0.6723` |
| F1 delta over lexical | `0.0156` |

## Publish Checks

| Check | Pass |
|---|---:|
| `strict_holdout_rows` | `True` |
| `holdout_nli_f1` | `False` |
| `beats_lexical` | `False` |
| `no_model_generation` | `True` |
| `redacted_predictions` | `True` |

## Claim Boundary

This gate is dataset-backed and uses a strict HaluEval dialogue holdout, but it is still verifier-only. It does not prove that live model hallucination is reduced in conversation; it tests whether evidence-conditioned scoring can detect hallucinated responses better than a lexical baseline.
