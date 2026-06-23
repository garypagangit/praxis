# MoE Standing-Committee Router Smoke Synthesis

Updated: 2026-06-23

## Praxis framing

Working title: `Standing Committee Routing Under Domain and Fine-Tuning Shift`.

This gate follows the source/feasibility PASS in `reports/moe_standing_committee/MOE_STANDING_COMMITTEE_SOURCE_GATE_20260623.md`. The purpose was to verify that an open MoE model can expose router evidence on AWS GPU and to estimate whether domain-invariant expert committees are visible enough to justify a larger pre-registered audit.

Literature anchor: `The Illusion of Specialization: Unveiling the Domain-Invariant Standing Committee in Mixture-of-Experts Models` (`arXiv:2601.03425`).

## RQ / H

| Item | Statement | Result |
|---|---|---|
| RQ1 | Can OLMoE expose router evidence on an AWS `g5.xlarge` without fine-tuning? | Yes: `60/60` prompts captured router tensors. |
| RQ2 | Is there a first-pass domain-invariant committee signal across heterogeneous prompt domains? | Soft yes: mean pairwise top-committee Jaccard was `0.3668`. |
| RQ3 | Is this enough to promote to a full standing-committee replication? | Not yet. It promotes to a larger pre-registered router audit, not a paper claim. |
| H1 | Router capture rate will be at least `0.95`. | PASS: `1.0000`. |
| H2 | Mean committee Jaccard will clear the smoke threshold `0.20`. | SOFT PASS: `0.3668`. |
| H3 | The result will remain within the claim boundary: no fine-tuning-shift claim yet. | PASS. |

## AWS run

| Field | Value |
|---|---|
| Instance | `i-07178e293e8df2a60` (`g5.xlarge`, A10G 24 GB) |
| Initial target | `i-039ed976444ade397` failed to start due `InsufficientInstanceCapacity` |
| Working instance state | Started, SSM online, job completed, stop command issued |
| Model | `allenai/OLMoE-1B-7B-0924` |
| Runtime | SSM command `7b96f56f-5859-4feb-89d2-6373e4aba84b`, elapsed `PT3M44.6S` after dependency setup/model load |
| S3 prefix | `s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/moe_standing_committee_20260623/` |

## Results

| Metric | Value |
|---|---:|
| Prompt count | `60` |
| Router-captured prompts | `60` |
| Router capture rate | `1.0000` |
| Mean pairwise committee Jaccard | `0.3668` |
| Mean layer top-k mass | `0.2853` |
| Mean layer entropy | `3.6551` |
| Smoke decision | `PASS` |
| Standing-committee signal | `SOFT_PASS` |

Strongest overlap pairs: cyber-policy `0.6000`, code-cyber `0.4545`, code-math `0.4222`, policy-writing `0.4222`. Weakest observed pair: code-writing `0.2075`, still above the `0.20` smoke threshold.

## Artifacts

| Artifact | Purpose |
|---|---|
| `configs/moe_standing_committee_router_smoke_20260623.json` | Local reproducibility/config record for the AWS smoke. |
| `cloud_jobs/moe_standing_committee_20260623/run_olmoe_router_smoke.py` | Cloud runner used on the GPU instance. |
| `reports/moe_standing_committee/router_smoke_20260623/MOE_STANDING_COMMITTEE_ROUTER_SMOKE_20260623.md` | Raw generated smoke report. |
| `reports/moe_standing_committee/router_smoke_20260623/MOE_STANDING_COMMITTEE_ROUTER_SMOKE_20260623.json` | Machine-readable metrics and domain committees. |
| `reports/moe_standing_committee/router_smoke_20260623/run_olmoe_router_smoke.log` | AWS environment, install, model load, and upload log. |

## Defense challenge

| Challenge | Answer |
|---|---|
| Does this prove the standing-committee thesis? | No. It is a smoke result with a soft positive committee-overlap signal. |
| Is it worth continuing? | Yes. Router observability is proven, the model fits on the available AWS GPU, and cross-domain overlap is nontrivial. |
| What is the next defensible gate? | Pre-register a larger OLMoE audit with more prompts per domain, confidence intervals, committee-size sensitivity, and at least one external-validity model if budget permits. |
| What should not be claimed? | No fine-tuning-shift result, no causal expert specialization claim, and no publication-level replication yet. |

## Decision

Promote to a full router-audit experiment. Do not promote directly to manuscript claim until the larger audit confirms overlap stability with frozen prompt sets and sensitivity checks.

