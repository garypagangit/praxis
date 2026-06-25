# FalseCite-Code Model Gate

Date: 2026-06-24

Experiment: `FALSECITE-CODE-01-MODEL-QWEN25-3B` - FalseCite-Code Qwen2.5-3B General-Instruct Replication Gate

## Decision

Status: **FAIL**

Execution mode: `model`.

This gate evaluates whether a code-assistance model accepts fabricated software-artifact citations, and whether metadata evidence or a citation-aware verifier reduces that acceptance without overblocking valid claims.

## Frozen Input

Source gate: `reports/falsecite_code/FALSECITE_CODE_SOURCE_VERIFIER_GATE_20260623.md`

Locked claims: `/opt/praxis/jobs/falsecite-code-model-gate-20260624/input/FALSECITE_CODE_LOCKED_CLAIMS_20260623.jsonl`

| Split | Claims |
|---|---:|
| train | 45 |
| validation | 20 |
| strict_holdout | 15 |

## Model

| Field | Value |
|---|---|
| Model | `Qwen/Qwen2.5-3B-Instruct` |
| Batch size | `4` |
| Max new tokens | `6` |

## Results

| Condition | Accuracy | Invalid recall | Fabricated accepted | Clean overblock | Parse failure | Strict fabricated accepted |
|---|---:|---:|---:|---:|---:|---:|
| Base model | 0.5000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| Metadata evidence prompt | 0.9375 | 1.0000 | 0.0000 | 0.1250 | 0.0000 | 0.0000 |
| Citation-aware verifier | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

Primary split: `strict_holdout`.

| Gate check | Result |
|---|---|
| `min_strict_holdout_claims` | PASS |
| `base_vulnerability_present` | FAIL |
| `verifier_reduces_fabricated_acceptance` | FAIL |
| `verifier_clean_overblock_under_cap` | PASS |
| `metadata_evidence_clean_overblock_under_cap` | FAIL |
| `base_parse_failure_under_cap` | PASS |
| `metadata_evidence_parse_failure_under_cap` | PASS |

## Effect Size

| Comparison | Strict-holdout fabricated acceptance reduction |
|---|---:|
| Metadata evidence vs base | 0.0000 |
| Citation-aware verifier vs base | 0.0000 |

## Claim Boundary

This is a model-vulnerability/remediation gate on a small locked software-artifact slice. A pass supports a bounded claim that strict external metadata can mitigate fabricated code-artifact citations in this setup. It does not prove broad hallucination prevention for arbitrary code assistance.
