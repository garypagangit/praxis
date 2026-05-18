# Relationship-Evidence CTI Ablation Gate

Generated: 2026-05-17

Status: **MIXED - MAIN EFFECT REPRODUCES; MECHANISM UNCLEAR**

## Scope

This gate reruns the locked 106-row evidence-addressable CTI-MCQ slice on `meta-llama/Llama-3.1-8B-Instruct` with six conditions: vanilla, relationship evidence, technique-only evidence, random ATT&CK facts, empty evidence, and broad-seed negative control.

The purpose is not only to reproduce the 8B lift, but to determine what caused it: relationship-level facts specifically, question-specific ATT&CK evidence more broadly, or prompt formatting.

## Cloud Run

- Instance: `i-039ed976444ade397` (`g5.xlarge`)
- SSM command ID: `13ebd008-4482-44f1-b012-b3646f85c297`
- Input: `cloud_jobs/sec_lord_relationship_evidence_20260517/input/evidence_addressable_prompts.jsonl`
- S3 output: `s3://praxis-garypagan-272615233626-us-east-1/experiments/sec-lord-ds-lord/cloud_jobs/sec-lord-relationship-evidence-20260517/output/ablation-8b/`
- Local pulled run directory: `runs/sec-lord-relationship-evidence-ablation-8b-20260517/`

## Strict Scorecard

| Condition | Accuracy | Correct | Rows | Invalid | Invalid rate | Mean evidence tokens |
|---|---:|---:|---:|---:|---:|---:|
| `vanilla` | `0.642` | `68` | `106` | `0` | `0.000` | `0.0` |
| `relationship_evidence` | `0.915` | `97` | `106` | `0` | `0.000` | `265.8` |
| `technique_only_evidence` | `0.764` | `81` | `106` | `0` | `0.000` | `53.2` |
| `random_facts` | `0.566` | `60` | `106` | `8` | `0.075` | `249.5` |
| `empty_evidence` | `0.670` | `71` | `106` | `1` | `0.009` | `5.0` |
| `broad_seed` | `0.642` | `68` | `106` | `1` | `0.009` | `0.0` |

## Gate Evaluation

| Gate | Result |
|---|---|
| AB1 - Relationship lift reproduces within `0.04` of `+0.274` | PASS: `+0.274` |
| AB2 - Random facts <= vanilla + `0.05` | PASS: `0.566 <= 0.692` |
| AB3 - Empty evidence <= vanilla + `0.05` | PASS: `0.670 <= 0.692` |
| AB4 - Invalid rate in all arms <= relationship invalid + `0.03` | FAIL: random facts invalid rate `0.075` |

## Hypothesis Discrimination

The clean `H_relationship` pattern did not fully hold, because technique-only evidence improved accuracy to `0.764`, which is `+0.123` over vanilla rather than staying within `0.05` of vanilla.

The clean `H_specificity` pattern also did not hold, because relationship evidence remained much stronger than technique-only evidence: `0.915 - 0.764 = +0.151`.

The clean `H_format` pattern did not hold, because random facts fell below vanilla and empty evidence only moved to `0.670`, within the negative-control tolerance band.

Verdict: **unclear mechanism, relationship evidence is the strongest arm.**

## Decision

The main effect is robust: the 8B relationship-evidence lift exactly reproduced (`+0.274`), and random/empty controls did not recreate it. The mechanism should not be overclaimed as "relationship facts alone" because technique-only evidence also helps.

Defensible claim shape:

> Question-specific ATT&CK retrieval improves strict CTI-MCQ compliance, with relationship-level evidence outperforming technique-only evidence on the locked evidence-addressable slice.

Recommended Praxis section title:

> Retrieval-Conditioned CTI Compliance: A Protocol-Specific Result

Do not claim:

- SEC-LoRD extraction success.
- Relationship evidence is the only causal mechanism.
- General CTI reasoning improvement outside the locked CTI-MCQ slice.

## Next Work

Package Praxis 07 as a bounded paper/chapter section. Any further experiment should be a replication or external-validity gate, not another threshold search.
