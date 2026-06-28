# MoE Standing-Committee Router Audit

PX ID: PX-005

Status: **BOUNDED POSITIVE - OLMoE FAMILY PASSED; NON-OLMOE QWEN SMOKE PASSED**

## Overview

PX-005 tests whether MoE models exhibit stable standing-committee expert routing under prompt-domain variation. The strongest positive evidence is still the frozen OLMoE-family audit. The track now also has a first non-OLMoE Qwen1.5-MoE router-observability smoke showing full router capture and measurable domain committee overlap on AWS.

## Current Result

| Gate | Status | Key result |
|---|---|---|
| OLMoE base router audit | PASS | `480/480` prompts captured; committee-size 32 Jaccard `0.4656`. |
| OLMoE-Instruct external-validity audit | PASS | `480/480` prompts captured; committee-size 32 Jaccard `0.4591`. |
| Cross-architecture source gate | PASS_SOURCE_GATE | `7` non-OLMoE source candidates found; best next target `Qwen/Qwen1.5-MoE-A2.7B`. |
| Qwen1.5-MoE router smoke | PASS | `5/5` prompts captured on `Qwen/Qwen1.5-MoE-A2.7B`; mean domain committee Jaccard `0.2195`; mean top-k mass `0.3396`; mean layer entropy `3.2480`. |

## Main Documents

| Document | Purpose |
|---|---|
| [Next-gate decision](MOE_STANDING_COMMITTEE_NEXT_GATE_DECISION_20260628.md) | Current decision and claim boundary. |
| [Cross-architecture source gate](MOE_CROSS_ARCH_SOURCE_GATE_20260628.md) | Live public-metadata feasibility gate for non-OLMoE candidates. |
| [Qwen1.5-MoE router smoke](qwen15_router_smoke_20260628/MOE_QWEN15_ROUTER_SMOKE_20260628.md) | First non-OLMoE router-observability smoke result. |
| [Qwen1.5-MoE smoke metrics JSON](qwen15_router_smoke_20260628/MOE_QWEN15_ROUTER_SMOKE_20260628.json) | Full prompt-level router mass and committee metrics. |
| [Qwen1.5-MoE AWS log](qwen15_router_smoke_20260628/moe-qwen15-router-smoke-20260628.log) | Raw cloud run log for reproducibility. |
| [OLMoE-Instruct synthesis](MOE_STANDING_COMMITTEE_OLMOE_INSTRUCT_AUDIT_SYNTHESIS_20260623.md) | OLMoE-family external-validity result. |
| [OLMoE base synthesis](MOE_STANDING_COMMITTEE_ROUTER_AUDIT_SYNTHESIS_20260623.md) | Original base OLMoE router-audit result. |

## Code and Configs

| Path | Purpose |
|---|---|
| [../../scripts/run_moe_cross_arch_source_gate.py](../../scripts/run_moe_cross_arch_source_gate.py) | Cross-architecture source-gate runner. |
| [../../configs/moe_cross_arch_source_gate_20260628.json](../../configs/moe_cross_arch_source_gate_20260628.json) | Cross-architecture candidate list and thresholds. |
| [../../cloud_jobs/moe_qwen15_router_smoke_20260628/run_qwen_moe_router_smoke.py](../../cloud_jobs/moe_qwen15_router_smoke_20260628/run_qwen_moe_router_smoke.py) | Qwen1.5-MoE router-smoke runner. |
| [../../configs/moe_qwen15_router_smoke_20260628.json](../../configs/moe_qwen15_router_smoke_20260628.json) | Qwen1.5-MoE smoke run configuration. |
| [../../cloud_jobs/moe_standing_committee_20260623/run_olmoe_router_audit.py](../../cloud_jobs/moe_standing_committee_20260623/run_olmoe_router_audit.py) | OLMoE router-audit runner. |

## Claim Boundary

Supported: prompt-domain standing-committee structure appears stable across base and instruction-tuned OLMoE variants under the frozen 480-prompt audit. Router observability and preliminary committee structure are also present in a small Qwen1.5-MoE non-OLMoE smoke.

Not supported: universal MoE specialization, cross-architecture routing invariance, or causal expert specialization. The Qwen1.5-MoE result is a smoke test, not the frozen cross-architecture audit.

## Next Step

Run the frozen router audit on `Qwen/Qwen1.5-MoE-A2.7B` using the same reporting contract as OLMoE: router capture rate, committee-size sensitivity, mean pairwise Jaccard, bootstrap confidence intervals, and no threshold changes after model selection.
