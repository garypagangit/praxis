# MoE Standing-Committee Router Audit

PX ID: PX-005

Status: **BOUNDED POSITIVE - OLMoE FAMILY PASSED; CROSS-ARCHITECTURE SOURCE GATE PASSED**

## Overview

PX-005 tests whether MoE models exhibit stable standing-committee expert routing under prompt-domain variation. The current positive evidence is bounded to OLMoE-family models. A cross-architecture source gate has now identified non-OLMoE candidates for the next router audit.

## Current Result

| Gate | Status | Key result |
|---|---|---|
| OLMoE base router audit | PASS | `480/480` prompts captured; committee-size 32 Jaccard `0.4656`. |
| OLMoE-Instruct external-validity audit | PASS | `480/480` prompts captured; committee-size 32 Jaccard `0.4591`. |
| Cross-architecture source gate | PASS_SOURCE_GATE | `7` non-OLMoE source candidates found; best next target `Qwen/Qwen1.5-MoE-A2.7B`. |

## Main Documents

| Document | Purpose |
|---|---|
| [Next-gate decision](MOE_STANDING_COMMITTEE_NEXT_GATE_DECISION_20260628.md) | Current decision and claim boundary. |
| [Cross-architecture source gate](MOE_CROSS_ARCH_SOURCE_GATE_20260628.md) | Live public-metadata feasibility gate for non-OLMoE candidates. |
| [OLMoE-Instruct synthesis](MOE_STANDING_COMMITTEE_OLMOE_INSTRUCT_AUDIT_SYNTHESIS_20260623.md) | OLMoE-family external-validity result. |
| [OLMoE base synthesis](MOE_STANDING_COMMITTEE_ROUTER_AUDIT_SYNTHESIS_20260623.md) | Original base OLMoE router-audit result. |

## Code and Configs

| Path | Purpose |
|---|---|
| [../../scripts/run_moe_cross_arch_source_gate.py](../../scripts/run_moe_cross_arch_source_gate.py) | Cross-architecture source-gate runner. |
| [../../configs/moe_cross_arch_source_gate_20260628.json](../../configs/moe_cross_arch_source_gate_20260628.json) | Cross-architecture candidate list and thresholds. |
| [../../cloud_jobs/moe_standing_committee_20260623/run_olmoe_router_audit.py](../../cloud_jobs/moe_standing_committee_20260623/run_olmoe_router_audit.py) | OLMoE router-audit runner. |

## Claim Boundary

Supported: prompt-domain standing-committee structure appears stable across base and instruction-tuned OLMoE variants under the frozen 480-prompt audit.

Not supported: universal MoE specialization, cross-architecture routing invariance, or causal expert specialization. The cross-architecture gate is source readiness only; no non-OLMoE router traces have been collected yet.

## Next Step

Install the inference stack on AWS/HF GPU infrastructure and run the frozen router audit on `Qwen/Qwen1.5-MoE-A2.7B` first. Keep the OLMoE reporting format unchanged: router capture rate, committee-size sensitivity, mean pairwise Jaccard, bootstrap confidence intervals, and no threshold changes after model selection.
