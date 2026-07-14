# PX-005 Summary Export

## Experiment

Title: Standing-Committee Routing in Sparse Mixture-of-Experts Models

Praxis ID: PX-005

Status: Final positive. Bounded publishable result.

## Executive Summary

PX-005 tested whether sparse MoE routers repeatedly select stable high-mass expert committees across cyber, code, math, policy, and writing prompts. The measured result is positive across OLMoE base, OLMoE-Instruct, and Qwen1.5-MoE. The defense posture must be careful: the broader Standing Committee concept now has direct prior literature, so PX-005 should be framed as a frozen Praxis replication/extension across local prompt domains and model families, not as the first discovery.

## Thesis

Sparse MoE routers can exhibit stable high-mass standing committees across prompt domains and style variants, challenging simple domain-specialization assumptions.

## Objective

Test whether high-overlap routed expert committees recur across cyber, code, math, policy, and writing prompts under deterministic style perturbations.

## What Was Tested

PX-005 is inference-only. Each audit used 480 prompts: five domains, twelve base prompts per domain, and eight style variants per base prompt. The primary committee size was 32, with sensitivity checks at 16 and 64.

The gate required:

- Router capture rate at least 0.95
- Primary mean pairwise Jaccard at least 0.25
- Primary bootstrap CI low at least 0.20
- Committee-size sensitivity means at least 0.20

## Key Results

Primary audit results:

| Model | Router capture | Primary Jaccard | Bootstrap CI |
|---|---:|---:|---:|
| OLMoE base | 480/480 | 0.4656 | [0.4336, 0.4834] |
| OLMoE-Instruct | 480/480 | 0.4591 | [0.4320, 0.4796] |
| Qwen1.5-MoE | 480/480 | 0.5826 | [0.5552, 0.6281] |

Committee-size sensitivity:

| Model | Size 16 mean | Size 32 mean | Size 64 mean |
|---|---:|---:|---:|
| OLMoE base | 0.4950 | 0.4656 | 0.5334 |
| OLMoE-Instruct | 0.5642 | 0.4591 | 0.5520 |
| Qwen1.5-MoE | 0.5354 | 0.5826 | 0.5652 |

## What It Proves

PX-005 proves that stable high-overlap routed expert committees appear under the frozen Praxis prompt-domain audit in the audited MoE models. The Qwen result is the key cross-architecture upgrade for this local audit.

## What It Does Not Prove

It does not prove first discovery of Standing Committees, causal expert specialization, universal MoE behavior, robustness under fine-tuning/domain shift, or that committee overlap alone explains model behavior.

## Defense Use

Use PX-005 as a bounded AI systems and interpretability result. It is useful for an AI-industry portfolio because it demonstrates router instrumentation, reproducible audits, and conservative claim control. It should not be used as the main defense pillar.

## Evidence Links

- `reports/praxis_final_positive_reports_20260701/PX005_FINAL_REPORT_MOE_STANDING_COMMITTEE.md`
- `reports/moe_standing_committee/MOE_STANDING_COMMITTEE_SHORT_PAPER_20260628.md`
- `reports/moe_standing_committee/router_audit_20260623/MOE_STANDING_COMMITTEE_ROUTER_AUDIT_20260623.md`
- `reports/moe_standing_committee/router_audit_olmoe_instruct_20260623/MOE_STANDING_COMMITTEE_ROUTER_AUDIT_OLMOE_INSTRUCT_20260623.md`
- `reports/moe_standing_committee/qwen15_router_audit_20260628/MOE_QWEN15_ROUTER_AUDIT_20260628.md`
- `cloud_jobs/moe_standing_committee_20260623/run_olmoe_router_audit.py`
- `cloud_jobs/moe_qwen15_router_audit_20260628/run_qwen_moe_router_audit.py`
- Prior literature noted in the report: `https://arxiv.org/abs/2601.03425`

