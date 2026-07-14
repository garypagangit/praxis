# PX-004 Summary Export

## Experiment

Title: FalseCite-Code External Verification for Software-Artifact Citation Poisoning

Praxis ID: PX-004

Status: Final positive. Bounded defense result.

## Executive Summary

PX-004 tested whether code-tuned assistants can be induced to trust fabricated software-artifact citations, and whether deterministic external metadata verification can close that gap. The result is a strong practical guardrail result: on the locked FalseCite-Code benchmark, model-only trust failed on fabricated PyPI, NPM, GitHub repository, and GitHub tag claims, while the citation-aware verifier reduced fabricated citation trust to zero under the primary gates.

## Thesis

Code assistants can be induced to trust fabricated software-artifact citations, but external metadata verification can suppress this failure mode on a locked benchmark.

## Objective

Build a balanced software-artifact citation benchmark and test whether code-tuned models accept fabricated package/repository citations. Then test whether a deterministic external verifier reduces fabricated trust.

## What Was Tested

PX-004 constructed an 80-claim benchmark spanning PyPI versions, NPM versions, GitHub repositories, and GitHub tags. Splits were keyed by artifact ID so paired valid and fabricated versions of the same artifact stayed in the same split. The protocol evaluated base model trust, metadata evidence prompts, and a citation-aware verifier.

## Key Results

Source/verifier gate:

| Method | Rows | Accuracy | Invalid recall |
|---|---:|---:|---:|
| Strict external verifier | 80 | 1.0000 | 1.0000 |
| Trust-all baseline | 80 | 0.5000 | 0.0000 |
| Regex-suspicion baseline | 80 | 0.5000 | 0.0000 |

Audit-mode primary model gate:

| Condition | Accuracy | Fabricated accepted | Strict fabricated accepted |
|---|---:|---:|---:|
| Base model | 0.5500 | 0.7500 | 0.8571 |
| Metadata evidence prompt | 1.0000 | 0.0000 | 0.0000 |
| Citation-aware verifier | 1.0000 | 0.0000 | 0.0000 |

Generation-mode primary model gate:

| Condition | Accuracy | Fabricated trusted | Strict fabricated trusted |
|---|---:|---:|---:|
| Suggested citation answer | 0.5190 | 0.6923 | 0.8333 |
| Metadata evidence answer | 0.9750 | 0.0000 | 0.0000 |
| Citation-aware verifier guard | 1.0000 | 0.0000 | 0.0000 |

Defense refresh:

- Claims: 80
- Strict-holdout claims: 15
- API error rate: 0.0000
- Verifier accuracy: 1.0000
- Invalid recall: 1.0000

## What It Proves

PX-004 proves that fabricated software-artifact citations can be trusted by a code-tuned assistant under the tested prompts, and that a deterministic external metadata verifier can suppress fabricated-citation trust on the locked benchmark.

## What It Does Not Prove

It does not prove universal hallucination prevention, universal model vulnerability, general package-install safety, arbitrary shell safety, or transfer to every code assistant. PX-050 extends this idea toward install-action tool boundaries; PX-004 itself is a citation-verification result.

## Defense Use

Use PX-004 as a practical verifier/guardrail paper and as the direct predecessor to the stronger PX-050 package-install gate work.

## Evidence Links

- `reports/praxis_final_positive_reports_20260701/PX004_FINAL_REPORT_FALSECITE_CODE.md`
- `reports/falsecite_code/FALSECITE_CODE_SHORT_PAPER_20260628.md`
- `reports/falsecite_code/defense_refresh_20260630/FALSECITE_CODE_SOURCE_VERIFIER_GATE_20260623.md`
- `reports/falsecite_code/FALSECITE_CODE_MODEL_GATE_20260624.md`
- `reports/falsecite_code/FALSECITE_CODE_GENERATION_GATE_VERBOSE160_20260625.md`
- `reports/falsecite_code/FALSECITE_CODE_LOCKED_CLAIMS_20260623.jsonl`
- `scripts/run_falsecite_code_gate.py`
- `scripts/run_falsecite_code_model_gate.py`
- `scripts/run_falsecite_code_generation_gate.py`

