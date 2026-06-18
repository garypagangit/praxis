# EXP01 Preliminary Split Readiness

Generated: 2026-06-18 13:20:22 UTC

Status: **PRELIMINARY SPLIT GATE PASS**

This is not a model-performance result. It verifies source access, deterministic row sampling, validation/test/strict-holdout separation, and scoring-label isolation before any model generation.

## Inputs

- Config: `configs\frontier_exp01_ttc_smoke_20260618.json`
- Output directory: `runs/frontier-exp01-ttc-transfer-smoke-20260618`
- Data source: Hugging Face Dataset Viewer API

## Dataset Access

| Dataset | HF dataset | Split | Total rows | Sampled rows |
|---|---|---:|---:|---:|
| gsm8k | `openai/gsm8k` | `test` | 1319 | 25 |
| math500 | `HuggingFaceH4/MATH-500` | `test` | 500 | 25 |

## Split Counts

| Split role | Rows |
|---|---:|
| `strict_domain_holdout_test` | 25 |
| `test_in_domain` | 13 |
| `validation_policy_selection` | 12 |

## Label Isolation

| File | Contains problem text? | Contains gold answer? | Intended use |
|---|---:|---:|---|
| `problem_manifest.jsonl` | no, hash only | no, hash only | model prompting manifest and split accounting |
| `gold_labels.jsonl` | no | yes | scoring only after model outputs exist |

The harness intentionally separates prompt-side row identifiers from scoring labels. Future model generation should read the manifest or refetch problems by row id, then scoring should join against `gold_labels.jsonl` only after outputs are frozen.

## Gate Checks

| Check | Status | Evidence |
|---|---|---|
| Deterministic split seed | PASS | `20260618` |
| Required validation rows | PASS | `12` rows |
| Required in-domain test rows | PASS | `13` rows |
| Required strict holdout rows | PASS | `25` rows |
| Gold label rows match manifest rows | PASS | `50 == 50` |
| Model calls made | PASS | `0`; no accuracy claimed |

## Next Required Output

Run the model-generation smoke and write:

- `samples.jsonl`
- `scores.jsonl`
- `retention_smoke.csv`
- `RUN_REPORT.md`

The next gate passes only if exact-answer scoring reaches manual agreement `>=0.95` and retention is computable without touching strict-holdout rows during policy selection.
