# MoE Standing-Committee Router Audit

PX ID: PX-005

Status: **FINAL SHORT PAPER - BOUNDED POSITIVE CROSS-ARCHITECTURE RESULT**

## Overview

PX-005 tests whether MoE models exhibit stable standing-committee expert routing under prompt-domain variation. The positive evidence now spans the frozen OLMoE-family audit and a frozen non-OLMoE Qwen1.5-MoE cross-architecture audit using the same 480-prompt protocol and thresholds. The result is packaged as a bounded-positive short paper.

## Current Result

| Gate | Status | Key result |
|---|---|---|
| OLMoE base router audit | PASS | `480/480` prompts captured; committee-size 32 Jaccard `0.4656`. |
| OLMoE-Instruct external-validity audit | PASS | `480/480` prompts captured; committee-size 32 Jaccard `0.4591`. |
| Cross-architecture source gate | PASS_SOURCE_GATE | `7` non-OLMoE source candidates found; best next target `Qwen/Qwen1.5-MoE-A2.7B`. |
| Qwen1.5-MoE router smoke | PASS | `5/5` prompts captured on `Qwen/Qwen1.5-MoE-A2.7B`; mean domain committee Jaccard `0.2195`; mean top-k mass `0.3396`; mean layer entropy `3.2480`. |
| Qwen1.5-MoE frozen cross-architecture audit | PASS | `480/480` prompts captured; committee-size 32 Jaccard `0.5826`; bootstrap CI `[0.5552, 0.6281]`; all frozen checks passed. |

## Main Documents

| Document | Purpose |
|---|---|
| [Short paper](MOE_STANDING_COMMITTEE_SHORT_PAPER_20260628.md) | Publishable bounded-positive PX-005 writeup. |
| [Next-gate decision](MOE_STANDING_COMMITTEE_NEXT_GATE_DECISION_20260628.md) | Current decision and claim boundary. |
| [Cross-architecture source gate](MOE_CROSS_ARCH_SOURCE_GATE_20260628.md) | Live public-metadata feasibility gate for non-OLMoE candidates. |
| [Qwen1.5-MoE frozen audit](qwen15_router_audit_20260628/MOE_QWEN15_ROUTER_AUDIT_20260628.md) | Full non-OLMoE cross-architecture router audit. |
| [Qwen1.5-MoE audit metrics JSON](qwen15_router_audit_20260628/MOE_QWEN15_ROUTER_AUDIT_20260628.json) | Full prompt-level audit metrics and committee sensitivity. |
| [Qwen1.5-MoE audit AWS log](qwen15_router_audit_20260628/moe-qwen15-router-audit-20260628.log) | Raw cloud run log for the full audit. |
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
| [../../cloud_jobs/moe_qwen15_router_audit_20260628/run_qwen_moe_router_audit.py](../../cloud_jobs/moe_qwen15_router_audit_20260628/run_qwen_moe_router_audit.py) | Qwen1.5-MoE frozen cross-architecture audit runner. |
| [../../configs/moe_qwen15_router_audit_20260628.json](../../configs/moe_qwen15_router_audit_20260628.json) | Qwen1.5-MoE frozen audit configuration. |
| [../../cloud_jobs/moe_qwen15_router_smoke_20260628/run_qwen_moe_router_smoke.py](../../cloud_jobs/moe_qwen15_router_smoke_20260628/run_qwen_moe_router_smoke.py) | Qwen1.5-MoE router-smoke runner. |
| [../../configs/moe_qwen15_router_smoke_20260628.json](../../configs/moe_qwen15_router_smoke_20260628.json) | Qwen1.5-MoE smoke run configuration. |
| [../../cloud_jobs/moe_standing_committee_20260623/run_olmoe_router_audit.py](../../cloud_jobs/moe_standing_committee_20260623/run_olmoe_router_audit.py) | OLMoE router-audit runner. |

## Claim Boundary

Supported: prompt-domain standing-committee structure appears stable across base and instruction-tuned OLMoE variants and across a non-OLMoE Qwen1.5-MoE architecture under the frozen 480-prompt audit protocol.

Not supported: universal MoE specialization, causal expert specialization, or fine-tuning/domain-shift invariance. The cross-architecture claim is bounded to OLMoE-family and Qwen1.5-MoE evidence under this prompt-domain protocol.

## Next Step

Use the short paper as the publishable bounded-positive package. The next scientific gate is either a second non-OLMoE replication (`Qwen/Qwen1.5-MoE-A2.7B-Chat` or `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct`) or a causal/domain-shift intervention on the existing audited models.
