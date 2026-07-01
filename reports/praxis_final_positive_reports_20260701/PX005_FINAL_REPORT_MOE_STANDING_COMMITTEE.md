# PX-005 Final Praxis Report

## Project

**Title:** Standing-Committee Routing in Sparse Mixture-of-Experts Models

**Praxis ID:** PX-005

**Status:** **FINAL POSITIVE - BOUNDED PUBLISHABLE RESULT**

## Praxis Summary

**Praxis thesis:** Sparse MoE routers can exhibit stable high-mass standing committees across prompt domains and style variants, challenging simple domain-specialization assumptions.

**Objective:** Test whether high-overlap routed expert committees recur across cyber, code, math, policy, and writing prompts under deterministic style perturbations.

**Research question:** Does a frozen prompt-domain audit reveal standing-committee routing across model families and architectures?

**Hypothesis:** If standing committees are present, the same high-mass routed expert slots will recur across prompt domains with mean pairwise Jaccard overlap above the frozen threshold and a bootstrap confidence interval above the pass line.

## Method

PX-005 is inference-only. It uses 480 prompts per audit: five domains, twelve base prompts per domain, and eight style variants per base prompt. The primary committee size is 32, with sensitivity at 16 and 64.

The gate requires router capture rate at least `0.95`, primary mean pairwise Jaccard at least `0.25`, primary bootstrap CI low at least `0.20`, and all committee-size means at least `0.20`.

## Results

| Model | Router capture | Primary Jaccard | Bootstrap CI |
|---|---:|---:|---:|
| OLMoE base | `480/480` | `0.4656` | `[0.4336, 0.4834]` |
| OLMoE-Instruct | `480/480` | `0.4591` | `[0.4320, 0.4796]` |
| Qwen1.5-MoE | `480/480` | `0.5826` | `[0.5552, 0.6281]` |

Committee-size sensitivity:

| Model | Size 16 mean | Size 32 mean | Size 64 mean |
|---|---:|---:|---:|
| OLMoE base | `0.4950` | `0.4656` | `0.5334` |
| OLMoE-Instruct | `0.5642` | `0.4591` | `0.5520` |
| Qwen1.5-MoE | `0.5354` | `0.5826` | `0.5652` |

## What It Proves

PX-005 proves that stable high-overlap routed expert committees appear under the frozen prompt-domain audit in OLMoE base, OLMoE-Instruct, and Qwen1.5-MoE. The Qwen result is the key cross-architecture upgrade.

## Claim Boundary

Allowed claim:

> Under a frozen 480-prompt audit, stable standing-committee routing structure appears in the audited MoE models.

Do not claim causal expert specialization, universal MoE behavior, robustness under fine-tuning/domain shift, or that committee overlap alone explains model behavior.

## Evidence Links

- `reports/moe_standing_committee/MOE_STANDING_COMMITTEE_SHORT_PAPER_20260628.md`
- `reports/moe_standing_committee/router_audit_20260623/MOE_STANDING_COMMITTEE_ROUTER_AUDIT_20260623.md`
- `reports/moe_standing_committee/router_audit_olmoe_instruct_20260623/MOE_STANDING_COMMITTEE_ROUTER_AUDIT_OLMOE_INSTRUCT_20260623.md`
- `reports/moe_standing_committee/qwen15_router_audit_20260628/MOE_QWEN15_ROUTER_AUDIT_20260628.md`
- `cloud_jobs/moe_standing_committee_20260623/run_olmoe_router_audit.py`
- `cloud_jobs/moe_qwen15_router_audit_20260628/run_qwen_moe_router_audit.py`

## Appendix A: Transportable Project Code

The following standalone code implements the committee-overlap metric and gate checks. The full project runners extract router weights from MoE models; this portable appendix shows how the captured router traces are converted into the defended result.

```python
#!/usr/bin/env python3
"""
PX-005 portable MoE standing-committee audit.

Purpose:
    Show how router traces become committee-overlap evidence.

What this code does:
    1. Converts per-prompt expert scores into top-k committees.
    2. Computes pairwise Jaccard overlap across committees.
    3. Checks the frozen pass thresholds using the final recorded metrics.
"""

from itertools import combinations


FINAL_RESULTS = {
    "olmoe_base": {"capture": 1.0, "jaccard": 0.4656, "ci_low": 0.4336},
    "olmoe_instruct": {"capture": 1.0, "jaccard": 0.4591, "ci_low": 0.4320},
    "qwen15_moe": {"capture": 1.0, "jaccard": 0.5826, "ci_low": 0.5552},
}


def top_k_committee(router_scores: dict[int, float], k: int = 32) -> set[int]:
    """
    Select the k highest-mass expert slots for one prompt.

    router_scores maps expert id to routed probability or routed mass. The
    original project obtains these values from model router hooks.
    """

    ranked = sorted(router_scores.items(), key=lambda item: item[1], reverse=True)
    return {expert_id for expert_id, _score in ranked[:k]}


def jaccard(left: set[int], right: set[int]) -> float:
    """Compute overlap between two committees."""

    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def mean_pairwise_jaccard(committees: list[set[int]]) -> float:
    """Average committee overlap across all prompt pairs."""

    pairs = list(combinations(committees, 2))
    return sum(jaccard(a, b) for a, b in pairs) / len(pairs)


def gate_check(result: dict[str, float]) -> bool:
    """Apply the frozen PX-005 pass thresholds."""

    return (
        result["capture"] >= 0.95
        and result["jaccard"] >= 0.25
        and result["ci_low"] >= 0.20
    )


def main() -> None:
    print("PX-005 MoE Standing-Committee Audit")
    for model, result in FINAL_RESULTS.items():
        print(f"{model}: {'PASS' if gate_check(result) else 'FAIL'}")

    # Tiny worked example showing how a committee score is computed.
    prompt_a = {0: 0.30, 1: 0.25, 2: 0.10, 3: 0.05}
    prompt_b = {0: 0.28, 1: 0.20, 2: 0.06, 3: 0.12}
    committees = [top_k_committee(prompt_a, k=2), top_k_committee(prompt_b, k=2)]
    print("example_jaccard:", f"{mean_pairwise_jaccard(committees):.4f}")


if __name__ == "__main__":
    main()
```

