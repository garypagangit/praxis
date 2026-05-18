# Relationship-Evidence CTI Cross-Model Gate - 3B

Generated: 2026-05-17

Status: **PASS - CROSS-MODEL LIFT REPLICATES**

## Scope

This gate reruns the locked 106-row evidence-addressable CTI-MCQ slice on `meta-llama/Llama-3.2-3B-Instruct`, using the same strict parser and the same three conditions as the first 8B model gate: vanilla, relationship evidence, and broad-seed negative control.

## Cloud Run

- Instance: `i-039ed976444ade397` (`g5.xlarge`)
- SSM command ID: `2c6db5c9-c15c-4818-886b-252fe76a3757`
- Input: `cloud_jobs/sec_lord_relationship_evidence_20260517/input/evidence_addressable_prompts.jsonl`
- S3 output: `s3://praxis-garypagan-272615233626-us-east-1/experiments/sec-lord-ds-lord/cloud_jobs/sec-lord-relationship-evidence-20260517/output/cross-model-3b/`
- Local pulled run directory: `runs/sec-lord-relationship-evidence-cross-model-3b-20260517/`

## Strict Scorecard

| Condition | Accuracy | Correct | Rows | Invalid | Invalid rate |
|---|---:|---:|---:|---:|---:|
| `vanilla` | `0.547` | `58` | `106` | `0` | `0.000` |
| `relationship_evidence` | `0.887` | `94` | `106` | `0` | `0.000` |
| `broad_seed` | `0.575` | `61` | `106` | `0` | `0.000` |

## Paired Vanilla Vs Relationship Evidence

| Both correct | Vanilla only | Evidence only | Both wrong |
|---:|---:|---:|---:|
| `54` | `4` | `40` | `8` |

## Gate Evaluation

| Gate | Result |
|---|---|
| G1 - Relationship strict accuracy >= vanilla + `0.030` | PASS: `0.887 - 0.547 = +0.340` |
| G2 - Relationship invalid rate <= vanilla invalid rate | PASS: `0.000 <= 0.000` |
| G3 - Evidence-only paired wins > vanilla-only wins | PASS: `40 > 4` |
| G4 - Broad seed <= vanilla + `0.030` | PASS: `0.575 <= 0.577` |

## Decision

**PASS.** Relationship-evidence retrieval lifts strict CTI-MCQ accuracy on both Llama-3.1-8B and Llama-3.2-3B. This supports a cross-model claim inside the Llama instruction-tuned family.

The result should still be scoped to the locked 106-row evidence-addressable slice and strict multiple-choice compliance. It is not evidence for LoRD extraction, CTI prose attribution, or general open-ended cyber reasoning.

## Follow-On Gate

The 8B ablation gate was run after this cross-model gate. It reproduced the main effect but produced a mixed mechanism result, so the paper should use the more conservative retrieval-conditioned wording.
