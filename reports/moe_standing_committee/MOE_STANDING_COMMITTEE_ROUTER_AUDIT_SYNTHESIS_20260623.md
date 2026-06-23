# MoE Standing-Committee Router Audit Synthesis

Updated: 2026-06-23

## Praxis framing

Working title: `Standing Committee Routing Under Domain and Fine-Tuning Shift`.

This gate extends the OLMoE router smoke from `60` prompts to a larger `480`-prompt deterministic perturbation audit. It tests whether a stable set of high-mass routed expert slots recurs across five prompt domains and eight style variants per base prompt.

Literature anchor: `The Illusion of Specialization: Unveiling the Domain-Invariant Standing Committee in Mixture-of-Experts Models` (`arXiv:2601.03425`).

## RQ / H

| Item | Statement | Result |
|---|---|---|
| RQ1 | Can OLMoE router tensors be captured consistently across a larger prompt-domain audit? | Yes: `480/480`, capture rate `1.0000`. |
| RQ2 | Does the top routed-expert committee remain meaningfully overlapping across prompt domains? | Yes: primary committee-size `32` mean Jaccard `0.4656`, bootstrap CI `[0.4336, 0.4834]`. |
| RQ3 | Is the signal robust to committee-size sensitivity? | Yes: sizes `16`, `32`, and `64` all clear mean Jaccard `0.20`. |
| H1 | Router capture rate will be at least `0.95`. | PASS. |
| H2 | Primary mean Jaccard will be at least `0.25`, with CI low at least `0.20`. | PASS. |
| H3 | All committee-size means will be at least `0.20`. | PASS. |

## Dataset and split discipline

This is an inference audit, not supervised training. The prompt set is frozen by construction:

| Prompt set | Count |
|---|---:|
| Domains | `5` |
| Base prompts per domain | `12` |
| Style variants per base prompt | `8` |
| Total prompts | `480` |

Domains: `cyber`, `code`, `math`, `policy`, `writing`.

Style variants: direct, concise, stepwise, risk-focused, evidence-focused, beginner, expert, and compact-summary forms.

## Results

| Metric | Value |
|---|---:|
| Audit decision | `PASS` |
| Prompt count | `480` |
| Router-captured prompts | `480` |
| Router capture rate | `1.0000` |
| Mean layer top-k mass | `0.2604` |
| Mean layer entropy | `3.6955` |

Committee-size sensitivity:

| Committee size | Mean Jaccard | Min Jaccard | Bootstrap CI low | Bootstrap CI high |
|---:|---:|---:|---:|---:|
| `16` | `0.4950` | `0.3333` | `0.4563` | `0.5256` |
| `32` | `0.4656` | `0.3617` | `0.4336` | `0.4834` |
| `64` | `0.5334` | `0.4066` | `0.5021` | `0.5491` |

## Artifacts

| Artifact | Purpose |
|---|---|
| `configs/moe_standing_committee_router_audit_20260623.json` | Pre-registered full-audit config. |
| `cloud_jobs/moe_standing_committee_20260623/run_olmoe_router_audit.py` | AWS full-audit runner. |
| `reports/moe_standing_committee/router_audit_20260623/MOE_STANDING_COMMITTEE_ROUTER_AUDIT_20260623.md` | Generated audit report. |
| `reports/moe_standing_committee/router_audit_20260623/MOE_STANDING_COMMITTEE_ROUTER_AUDIT_20260623.json` | Machine-readable metrics, pairwise overlaps, committees, and prompt rows. |
| `reports/moe_standing_committee/router_audit_20260623/run_olmoe_router_audit.log` | AWS environment, install, model load, and upload log. |

## Internal defensibility challenge

| Challenge | Answer |
|---|---|
| Does this prove the full paper thesis? | It supports a bounded OLMoE prompt-domain standing-committee claim. It does not yet prove fine-tuning-shift persistence or causal expert roles. |
| Could this be prompt leakage? | No supervised labels or train/test fitting are used. The prompt bank is deterministic and reported; the bootstrap resamples prompts only for interval estimation. |
| Could committee size be cherry-picked? | The primary size `32` was pre-configured, and sizes `16` and `64` both pass sensitivity checks. |
| Is the result publication-worthy? | Potentially as a compact methods/result section, if framed as an OLMoE prompt-domain router audit and not as a universal MoE claim. |
| What should happen next? | Add one external-validity model or a fine-tuning/domain-shift intervention before turning this into a standalone manuscript claim. |

## Decision

Promote this from smoke to a bounded positive result: OLMoE shows stable prompt-domain routed-expert committee overlap under deterministic style perturbations. The next gate should test external validity or fine-tuning-shift persistence.

