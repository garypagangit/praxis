# PX-011 HalluHard Source-Locked Constrained Gate

Generated: 2026-07-01T01:02:31+00:00

Status: **PASS - SOURCE-LOCKED HALLUHARD VERIFIER POSITIVE**

## No-Kidding Result

PX-011 is now a bounded positive, but only under the source-locked research-question claim boundary. The positive result is not a broad HalluHard or freeform citation-generation result.

The successful formulation is a source-locked schema assembler:

- The retrieval/controller layer copies DOI, arXiv ID, title, year, and source identity directly from the HalluHard research-question source record.
- The model generates only a short extractive `claimed_content` phrase from the source abstract.
- The verifier evaluates both source-locked supported rows and shifted-source negative rows.

## Metrics

| Metric | Value |
|---|---:|
| Model | `Qwen/Qwen2.5-7B-Instruct` |
| HalluHard lane | `research_questions` only |
| Generations | `250` |
| Evaluation pairs | `500` |
| Extraction-valid rows | `250` / `250` |
| Extraction-valid rate | `1.0000` |
| Supported claims passing verifier | `202` / `250` |
| Supported rate | `0.8080` |
| Verifier accuracy | `0.9040` |
| Verifier macro F1 | `0.9031` |
| Always-supported macro F1 | `0.3333` |
| Field-presence macro F1 | `0.3333` |
| Wall time | `256.8` seconds |

## Gate Checks

| Check | Result |
|---|---:|
| Minimum generations | pass |
| Extraction-valid rate | pass |
| Supported rate | pass |
| Macro F1 | pass |
| Beats always-supported baseline | pass |
| Beats field-presence baseline | pass |

## What This Proves

PX-011 proves that a HalluHard-style source-backed hallucination guardrail can work when citation/source metadata are locked to retrieved evidence and the model is restricted to producing only extractive claim content. The verifier cleanly separates supported source-locked rows from shifted-source negatives, with macro F1 `0.9031`.

This also explains the previous mixed result: the earlier freeform/source-conditioned response path was dominated by formatting and citation-field failures. Constraining the generation boundary changes the viable research claim from "LLMs can freely generate reliable citations" to "retrieval-controlled source metadata plus extractive claim generation can support a strong hallucination verifier."

## Claim Boundary

Defensible claim:

> For HalluHard research-question cases, a source-locked retrieval/controller pipeline with extractive model-generated claim content can produce verifier-ready citation claims and detect shifted-source hallucinations.

Do not claim:

- Broad HalluHard solution across legal, medical, coding, or other lanes.
- Freeform citation generation.
- Open-ended source discovery without a retrieval/controller layer.
- That the model independently authored all citation metadata.

## Decision

Promote PX-011 as a bounded Praxis positive. It is suitable for defense if presented as a source-locked hallucination verification/control pipeline, not as a freeform citation model.

## Artifacts

- Generated report: `reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/report.md`
- Summary JSON: `reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/summary.json`
- Row CSV: `reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/halluhard_constrained_rows.csv`
- Row JSONL: `reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/halluhard_constrained_rows.jsonl`
- AWS run log: `reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2.log`
- Cloud job code: `cloud_jobs/halluhard_constrained_20260701/`

