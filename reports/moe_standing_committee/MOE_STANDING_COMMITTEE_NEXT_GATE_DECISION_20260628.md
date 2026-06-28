# MoE Standing-Committee Next-Gate Decision

Date: 2026-06-28

PX ID: PX-005

Status: **BOUNDED POSITIVE - OLMoE-FAMILY EXTERNAL VALIDITY PASSED**

## Decision

Do not rerun the same MoE audit as the next step. The external-validity gate already exists for the OLMoE family and it passed on `allenai/OLMoE-1B-7B-0924-Instruct`.

The track should now be treated as a bounded positive result for OLMoE-family router behavior. The next useful gate is cross-architecture validation only if GPU budget and model feasibility are acceptable.

## Evidence Summary

| Gate | Status | Result |
|---|---|---|
| OLMoE base router audit | PASS | `480/480` prompts captured; primary committee size `32`; mean pairwise Jaccard `0.4656`; bootstrap CI `[0.4336, 0.4834]`. |
| OLMoE-Instruct external-validity audit | PASS | `480/480` prompts captured; primary committee size `32`; mean pairwise Jaccard `0.4591`; bootstrap CI `[0.4320, 0.4796]`. |
| Instruction-tuning sensitivity | PASS | Instruction tuning did not destroy the standing-committee signal. |
| Cross-architecture validity | NOT TESTED | No non-OLMoE architecture has passed the same gate yet. |

## Supporting Artifacts

| Artifact | Purpose |
|---|---|
| `MOE_STANDING_COMMITTEE_ROUTER_AUDIT_SYNTHESIS_20260623.md` | Base OLMoE router-audit synthesis. |
| `MOE_STANDING_COMMITTEE_OLMOE_INSTRUCT_AUDIT_SYNTHESIS_20260623.md` | OLMoE-Instruct external-validity synthesis. |
| `configs/moe_standing_committee_router_audit_20260623.json` | Pre-registered base OLMoE audit config. |
| `configs/moe_standing_committee_router_audit_olmoe_instruct_20260623.json` | Pre-registered OLMoE-Instruct audit config. |

## Claim Boundary

Supported claim: prompt-domain standing-committee structure appears stable across base and instruction-tuned OLMoE variants under the frozen 480-prompt audit.

Do not claim universal MoE specialization, cross-architecture routing invariance, or causal expert specialization. Those require a non-OLMoE architecture, a fine-tuning/domain-shift condition, or a causal intervention gate.

## Recommended Next Gate

Only run a cross-architecture gate if the resource check is positive.

Candidate gate:

1. Select one feasible non-OLMoE sparse model with accessible router outputs or hookable routing modules.
2. Freeze the same prompt domains and style perturbations.
3. Require full router capture, committee-size sensitivity, and bootstrap confidence intervals matching the OLMoE audit format.
4. Promote only if the signal survives without changing thresholds after model selection.

If GPU capacity is limited, move next portfolio effort to PX-004 packaging or PX-010 synthetic circuit recovery instead.
