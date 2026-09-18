# Standing-Committee Routing Persists Across OLMoE and Qwen1.5-MoE Under a Frozen Prompt-Domain Audit

Date: 2026-06-28

PX ID: PX-005

Status: **FINAL SHORT PAPER - BOUNDED POSITIVE**

## Abstract

Mixture-of-Experts language models are often discussed as if routed experts specialize cleanly by domain. PX-005 tests a narrower and more defensible claim: whether a stable high-mass "standing committee" of routed expert slots recurs across prompt domains and style perturbations. Using a frozen 480-prompt audit across five domains and eight style variants, we observe full router capture and passing committee-overlap checks on base OLMoE, OLMoE-Instruct, and a non-OLMoE Qwen1.5-MoE model. The strongest cross-architecture result is `Qwen/Qwen1.5-MoE-A2.7B`, which captured routers for `480/480` prompts and achieved primary committee-size 32 mean pairwise Jaccard `0.5826` with bootstrap CI `[0.5552, 0.6281]`. The result supports a bounded claim that prompt-domain standing-committee structure appears in the audited MoE models under this protocol. It does not prove causal expert specialization, universal MoE behavior, or robustness under fine-tuning/domain shift.

## 1. Problem

MoE routers select expert pathways dynamically, but it is not obvious whether different prompt domains truly induce separate expert committees or whether a stable high-mass committee recurs across domains. The paper anchor for this track is `The Illusion of Specialization: Unveiling the Domain-Invariant Standing Committee in Mixture-of-Experts Models` (`arXiv:2601.03425`).

PX-005 asks a bounded experimental question:

Can standing-committee routing be observed under a frozen prompt-domain audit, and does the signal survive model-family and cross-architecture checks?

## 2. Audit Protocol

The audit is inference-only. There is no supervised fitting, no prompt-label training, and no threshold tuning after model selection.

| Component | Value |
|---|---:|
| Domains | `5` |
| Base prompts per domain | `12` |
| Style variants per base prompt | `8` |
| Total prompts per audit | `480` |
| Primary committee size | `32` |
| Sensitivity committee sizes | `16`, `32`, `64` |
| Bootstrap samples | `200` |

Domains are `cyber`, `code`, `math`, `policy`, and `writing`. Style variants include direct, concise, stepwise, risk-focused, evidence-focused, beginner, expert, and compact-summary prompts.

Frozen pass checks:

| Check | Threshold |
|---|---:|
| Router capture rate | `>= 0.95` |
| Primary mean pairwise Jaccard | `>= 0.25` |
| Primary bootstrap CI low | `>= 0.20` |
| All committee-size means | `>= 0.20` |

## 3. Models

PX-005 evaluates three model conditions:

| Model condition | Model | Purpose |
|---|---|---|
| Base OLMoE | `allenai/OLMoE-1B-7B-0924` | Initial frozen audit. |
| OLMoE-Instruct | `allenai/OLMoE-1B-7B-0924-Instruct` | Model-family external-validity check. |
| Qwen1.5-MoE | `Qwen/Qwen1.5-MoE-A2.7B` | Non-OLMoE cross-architecture check. |

The Qwen run used AWS `g5.xlarge` with 8-bit loading and CPU offload. The model-loading path changed for Qwen, but the prompt protocol, committee sizes, bootstrap reporting, and pass thresholds stayed frozen.

## 4. Results

### 4.1 Primary audit results

| Model | Decision | Router capture | Primary Jaccard | Bootstrap CI |
|---|---|---:|---:|---:|
| Base OLMoE | PASS | `480/480` | `0.4656` | `[0.4336, 0.4834]` |
| OLMoE-Instruct | PASS | `480/480` | `0.4591` | `[0.4320, 0.4796]` |
| Qwen1.5-MoE | PASS | `480/480` | `0.5826` | `[0.5552, 0.6281]` |

All three audits clear the frozen pass checks. The OLMoE-Instruct result shows that instruction tuning did not remove the signal inside the OLMoE family. The Qwen result is the key upgrade: it moves the experiment from an OLMoE-family result to a bounded cross-architecture result.

### 4.2 Committee-size sensitivity

| Model | Size 16 mean | Size 32 mean | Size 64 mean |
|---|---:|---:|---:|
| Base OLMoE | `0.4950` | `0.4656` | `0.5334` |
| OLMoE-Instruct | `0.5642` | `0.4591` | `0.5520` |
| Qwen1.5-MoE | `0.5354` | `0.5826` | `0.5652` |

The signal is not an artifact of a single committee size. Every tested model clears the committee-size sensitivity requirement at sizes `16`, `32`, and `64`.

### 4.3 Qwen cross-architecture gate

| Metric | Value |
|---|---:|
| Prompt count | `480` |
| Router-captured prompts | `480` |
| Router capture rate | `1.0000` |
| Primary committee size | `32` |
| Primary mean pairwise Jaccard | `0.5826` |
| Primary bootstrap CI low | `0.5552` |
| Primary bootstrap CI high | `0.6281` |
| Mean layer top-k mass | `0.3097` |
| Mean layer entropy | `3.3266` |

Qwen was also preceded by a small smoke gate that captured routers for `5/5` prompts. The full result above is the promoted evidence; the smoke result is retained as environment and observability provenance.

## 5. Interpretation

The observed pattern is consistent with a standing-committee account: a recurring set of high-mass routed expert slots appears across prompt domains and style variants. The result is stronger than a single-model trace because it appears in both OLMoE-family variants and in Qwen1.5-MoE under the same frozen audit protocol.

The result should not be described as proof that experts are causally responsible for domain behavior. It is a router-observability and committee-overlap result. Causal claims would require interventions such as expert ablation, routing patching, or domain-shift/fine-tuning experiments.

## 6. Supported Claim

Under a frozen 480-prompt prompt-domain audit, standing-committee routing structure appears stable in base OLMoE, OLMoE-Instruct, and Qwen1.5-MoE. This supports a bounded cross-architecture claim for recurring high-mass routed expert committees in the audited MoE models.

## 7. Claim Boundary

This result does not claim:

1. Universal standing-committee behavior across all MoE models.
2. That routed experts are causally specialized for domains.
3. Robustness under fine-tuning, domain shift, or adversarial prompt distributions.
4. That committee overlap alone explains model performance.
5. That all non-OLMoE architectures will reproduce the Qwen result.

The practical claim is narrower: router traces can reveal stable high-overlap expert committees across domains, and that signal survived one OLMoE-family check and one non-OLMoE cross-architecture check.

## 8. Reproducibility Record

| Artifact | Purpose |
|---|---|
| `MOE_STANDING_COMMITTEE_ROUTER_AUDIT_SYNTHESIS_20260623.md` | Base OLMoE audit synthesis. |
| `MOE_STANDING_COMMITTEE_OLMOE_INSTRUCT_AUDIT_SYNTHESIS_20260623.md` | OLMoE-Instruct external-validity synthesis. |
| `MOE_CROSS_ARCH_SOURCE_GATE_20260628.md` | Non-OLMoE source and feasibility gate. |
| `qwen15_router_smoke_20260628/MOE_QWEN15_ROUTER_SMOKE_20260628.md` | Qwen router-observability smoke report. |
| `qwen15_router_audit_20260628/MOE_QWEN15_ROUTER_AUDIT_20260628.md` | Full Qwen cross-architecture audit report. |
| `qwen15_router_audit_20260628/MOE_QWEN15_ROUTER_AUDIT_20260628.json` | Full Qwen prompt-level metrics and committee results. |
| `qwen15_router_audit_20260628/moe-qwen15-router-audit-20260628.log` | Raw AWS run log for the Qwen audit. |
| `../../configs/moe_standing_committee_router_audit_20260623.json` | Base OLMoE frozen audit config. |
| `../../configs/moe_standing_committee_router_audit_olmoe_instruct_20260623.json` | OLMoE-Instruct frozen audit config. |
| `../../configs/moe_qwen15_router_audit_20260628.json` | Qwen frozen audit config. |
| `../../cloud_jobs/moe_standing_committee_20260623/run_olmoe_router_audit.py` | OLMoE audit runner. |
| `../../cloud_jobs/moe_qwen15_router_audit_20260628/run_qwen_moe_router_audit.py` | Qwen audit runner. |

## 9. Conclusion

PX-005 is a publishable bounded-positive Praxis result. It demonstrates stable standing-committee routing under a frozen prompt-domain protocol across OLMoE base, OLMoE-Instruct, and Qwen1.5-MoE. The strongest next scientific extension is not another smoke test; it is either a second non-OLMoE replication or a causal/domain-shift intervention that tests whether these committees matter for behavior.
