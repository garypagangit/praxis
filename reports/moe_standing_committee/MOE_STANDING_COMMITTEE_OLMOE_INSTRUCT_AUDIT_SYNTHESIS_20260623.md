# OLMoE-Instruct Router Audit Synthesis

Updated: 2026-06-23

## Praxis framing

This gate repeats the frozen `480`-prompt OLMoE standing-committee audit on `allenai/OLMoE-1B-7B-0924-Instruct`. It is an external-validity check within the OLMoE model family: same architecture family, instruction-tuned variant, same prompt domains, same style perturbations, same committee sizes, and same thresholds.

## Result

| Metric | Base OLMoE | OLMoE-Instruct |
|---|---:|---:|
| Prompt count | `480` | `480` |
| Router capture rate | `1.0000` | `1.0000` |
| Primary committee size | `32` | `32` |
| Primary mean pairwise Jaccard | `0.4656` | `0.4591` |
| Primary bootstrap CI low | `0.4336` | `0.4320` |
| Primary bootstrap CI high | `0.4834` | `0.4796` |
| Audit decision | `PASS` | `PASS` |

Committee-size sensitivity for OLMoE-Instruct:

| Committee size | Mean Jaccard | Min Jaccard | Bootstrap CI low | Bootstrap CI high |
|---:|---:|---:|---:|---:|
| `16` | `0.5642` | `0.4545` | `0.5172` | `0.5803` |
| `32` | `0.4591` | `0.3333` | `0.4320` | `0.4796` |
| `64` | `0.5520` | `0.4222` | `0.5301` | `0.5785` |

## Artifacts

| Artifact | Purpose |
|---|---|
| `configs/moe_standing_committee_router_audit_olmoe_instruct_20260623.json` | Pre-registered OLMoE-Instruct audit config. |
| `reports/moe_standing_committee/router_audit_olmoe_instruct_20260623/MOE_STANDING_COMMITTEE_ROUTER_AUDIT_OLMOE_INSTRUCT_20260623.md` | Generated Instruct audit report. |
| `reports/moe_standing_committee/router_audit_olmoe_instruct_20260623/MOE_STANDING_COMMITTEE_ROUTER_AUDIT_OLMOE_INSTRUCT_20260623.json` | Machine-readable Instruct metrics and prompt rows. |
| `reports/moe_standing_committee/router_audit_olmoe_instruct_20260623/run_olmoe_router_audit_instruct.log` | AWS run log. |

## Defense challenge

| Challenge | Answer |
|---|---|
| Does this prove cross-architecture validity? | No. It validates the signal across base and instruction-tuned OLMoE variants, not across a different MoE architecture. |
| Does instruction tuning destroy the committee signal? | No. The primary Jaccard is essentially unchanged: `0.4656` base vs `0.4591` instruct. |
| Is this now publishable? | It is a credible bounded result for an OLMoE-family prompt-domain router audit. A stronger paper claim still needs either another architecture, a fine-tuning-shift condition, or causal intervention. |
| What should be avoided? | Do not claim universal MoE standing committees or domain-specialization causality. |

## Decision

Promote the MoE standing-committee track to a bounded positive OLMoE-family result. The next best gate is cross-architecture validation on a larger/quantized MoE model if budget and GPU capacity allow.

