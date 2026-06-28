# MoE Standing-Committee Next-Gate Decision

Date: 2026-06-28

PX ID: PX-005

Status: **BOUNDED POSITIVE - OLMoE-FAMILY EXTERNAL VALIDITY PASSED; CROSS-ARCHITECTURE SOURCE GATE PASSED**

## Decision

Do not rerun the same MoE audit as the next step. The external-validity gate already exists for the OLMoE family and it passed on `allenai/OLMoE-1B-7B-0924-Instruct`.

The track should now be treated as a bounded positive result for OLMoE-family router behavior. The cross-architecture source gate passed on 2026-06-28, but no non-OLMoE router traces have been collected yet.

## Evidence Summary

| Gate | Status | Result |
|---|---|---|
| OLMoE base router audit | PASS | `480/480` prompts captured; primary committee size `32`; mean pairwise Jaccard `0.4656`; bootstrap CI `[0.4336, 0.4834]`. |
| OLMoE-Instruct external-validity audit | PASS | `480/480` prompts captured; primary committee size `32`; mean pairwise Jaccard `0.4591`; bootstrap CI `[0.4320, 0.4796]`. |
| Instruction-tuning sensitivity | PASS | Instruction tuning did not destroy the standing-committee signal. |
| Cross-architecture source gate | PASS_SOURCE_GATE | `7` non-OLMoE source candidates found; best next target `Qwen/Qwen1.5-MoE-A2.7B`; no non-OLMoE router trace has run yet. |

## Supporting Artifacts

| Artifact | Purpose |
|---|---|
| `MOE_STANDING_COMMITTEE_ROUTER_AUDIT_SYNTHESIS_20260623.md` | Base OLMoE router-audit synthesis. |
| `MOE_STANDING_COMMITTEE_OLMOE_INSTRUCT_AUDIT_SYNTHESIS_20260623.md` | OLMoE-Instruct external-validity synthesis. |
| `MOE_CROSS_ARCH_SOURCE_GATE_20260628.md` | Non-OLMoE cross-architecture source/feasibility gate. |
| `configs/moe_standing_committee_router_audit_20260623.json` | Pre-registered base OLMoE audit config. |
| `configs/moe_standing_committee_router_audit_olmoe_instruct_20260623.json` | Pre-registered OLMoE-Instruct audit config. |
| `configs/moe_cross_arch_source_gate_20260628.json` | Cross-architecture candidate list and thresholds. |

## Claim Boundary

Supported claim: prompt-domain standing-committee structure appears stable across base and instruction-tuned OLMoE variants under the frozen 480-prompt audit.

Do not claim universal MoE specialization, cross-architecture routing invariance, or causal expert specialization. Those require a non-OLMoE router-trace run, a fine-tuning/domain-shift condition, or a causal intervention gate.

## Recommended Next Gate

Run a cross-architecture router audit only on AWS/HF GPU infrastructure after the inference stack is installed. Local inference is blocked on this machine because PyTorch and Transformers are not installed.

Best source-gated candidate:

1. `Qwen/Qwen1.5-MoE-A2.7B`
2. `Qwen/Qwen1.5-MoE-A2.7B-Chat`
3. `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct`

Registered audit requirements:

1. Freeze the same prompt domains and style perturbations.
2. Require full router capture, committee-size sensitivity, and bootstrap confidence intervals matching the OLMoE audit format.
3. Promote only if the signal survives without changing thresholds after model selection.

If GPU capacity is limited, keep this as a source-gate result and move portfolio effort to the already-positive PX-004/PX-010 writing and packaging tracks.
