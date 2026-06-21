# EXP04 Dialogue Feature Gate Result

Generated: 2026-06-20T10:01:54.367277+00:00

Status: **MIXED - RESPONSE ARTIFACT BASELINE WINS**

## Scope

- Dataset: HaluEval `dialogue` parquet from `pminervini/HaluEval`.
- Split discipline: paired right/hallucinated responses stay together by dialogue row.
- Train/validation/test/strict holdout split: 60/15/15/10 by deterministic row hash.
- Hyperparameters and thresholds are selected on validation only.
- Committed prediction rows are redacted hashes, lengths, labels, scores, and metrics only.

## Praxis Frame

**Hypothesis.** Evidence-conditioned features should identify hallucinated dialogue responses better than response-only artifacts and numeric novelty alone.

**GMR.** Goal: find a defensible verifier signal for multi-turn hallucination. Method: train row-disjoint logistic baselines over response text, evidence text, and engineered novelty/entity/negation features. Rationale: a publishable KG/evidence claim must beat response-style shortcuts on a sealed holdout.

## Split Counts

| Split | Examples | Right | Hallucinated |
|---|---:|---:|---:|
| train | `12118` | `6059` | `6059` |
| validation | `2990` | `1495` | `1495` |
| test | `2970` | `1485` | `1485` |
| strict_holdout | `1922` | `961` | `961` |

## Primary Metrics

| Model | Validation F1 | Test F1 | Strict holdout F1 | Strict holdout accuracy | Strict holdout FAR |
|---|---:|---:|---:|---:|---:|
| `numeric` | `0.7024` | `0.6994` | `0.6963` | `0.6061` | `0.6909` |
| `response` | `0.8078` | `0.7920` | `0.7835` | `0.7732` | `0.2747` |
| `evidence` | `0.7341` | `0.7178` | `0.7121` | `0.6967` | `0.3569` |
| `evidence_numeric` | `0.7456` | `0.7412` | `0.7215` | `0.7060` | `0.3496` |

## Promotion Checks

| Check | Pass |
|---|---:|
| `strict_holdout_rows` | `True` |
| `evidence_holdout_f1` | `False` |
| `evidence_beats_response_only` | `False` |
| `evidence_beats_numeric` | `False` |
| `no_model_generation` | `True` |
| `redacted_predictions` | `True` |

## Decision

The evidence-plus-numeric verifier reached strict holdout F1 `0.7215`, but the response-only artifact baseline reached `0.7835`. The evidence model therefore does not support the EXP04 thesis yet. Treat this as a failed promotion gate and move to the next experiment rather than claiming a KG/evidence result.

## Claim Boundary

This gate does not prove evidence-grounded hallucination verification. It shows that, on this HaluEval dialogue setup, response-style artifacts remain a stronger signal than the current evidence features.
