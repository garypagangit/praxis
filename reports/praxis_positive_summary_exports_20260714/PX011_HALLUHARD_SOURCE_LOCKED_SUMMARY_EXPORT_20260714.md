# PX-011 Summary Export

## Experiment

Title: Source-Locked HalluHard Verifier Pipeline

Praxis ID: PX-011

Status: Final positive. Bounded source-locked result.

## Executive Summary

PX-011 tested whether a HalluHard-style hallucination guardrail can work when citation metadata are locked to retrieved sources and the model is restricted to extractive claim content. The result is positive inside that constrained design: the controller copies DOI, arXiv ID, title, year, and source identity from retrieved evidence, while Qwen2.5-7B generates only a short extractive content phrase. This removes the freeform citation-invention failure mode and lets the verifier detect shifted-source hallucinations.

## Thesis

A HalluHard-style hallucination guardrail can work when citation/source metadata are locked to retrieved evidence and the model is restricted to extractive claim generation.

## Objective

Test whether a source-locked controller plus extractive model claim content can produce verifier-ready citation claims and detect shifted-source hallucinations on HalluHard research-question cases.

## What Was Tested

PX-011 used the HalluHard `research_questions` lane only. The controller copied citation metadata from retrieved source records. Qwen2.5-7B generated only a short extractive `claimed_content` phrase from the abstract. The verifier evaluated both source-locked supported rows and shifted-source negative rows.

## Key Results

| Metric | Value |
|---|---:|
| Model | Qwen/Qwen2.5-7B-Instruct |
| HalluHard lane | research_questions only |
| Generations | 250 |
| Evaluation pairs | 500 |
| Extraction-valid rows | 250 / 250 |
| Extraction-valid rate | 1.0000 |
| Supported claims passing verifier | 202 / 250 |
| Supported rate | 0.8080 |
| Verifier accuracy | 0.9040 |
| Verifier macro F1 | 0.9031 |
| Always-supported macro F1 | 0.3333 |
| Field-presence macro F1 | 0.3333 |
| Wall time | 256.8 seconds |

## What It Proves

PX-011 proves that the viable HalluHard result is not freeform citation generation. The defensible positive is source-locked retrieval/control plus extractive claim generation. Under that boundary, the verifier separates supported source-locked rows from shifted-source negatives.

## What It Does Not Prove

It does not prove broad HalluHard coverage, legal/medical/coding lane success, freeform citation generation, open-ended source discovery, or that the model independently authored citation metadata.

## Defense Use

Use PX-011 as a bounded verifier pipeline result and a supporting paper in the evidence-conditioning/verification theme. It is not as broad as PX-003/PX-034 or PX-004, but it is useful because the shifted-source negative test gives a clean hallucination-detection boundary.

## Evidence Links

- `reports/praxis_final_positive_reports_20260701/PX011_FINAL_REPORT_HALLUHARD_SOURCE_LOCKED.md`
- `reports/halluhard_source_verifier/PX011_SOURCE_LOCKED_CONSTRAINED_GATE_20260701.md`
- `reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/summary.json`
- `reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/halluhard_constrained_rows.csv`
- `reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/halluhard_constrained_rows.jsonl`
- `cloud_jobs/halluhard_constrained_20260701/run_halluhard_constrained_gate.py`
- `cloud_jobs/halluhard_constrained_20260701/run_on_instance.sh`

