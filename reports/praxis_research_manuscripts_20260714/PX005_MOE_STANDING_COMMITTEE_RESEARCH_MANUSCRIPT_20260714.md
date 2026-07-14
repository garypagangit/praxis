# Standing-Committee Routing Across Sparse Mixture-of-Experts Models

Research manuscript draft

Praxis ID: PX-005

Generated: 2026-07-14

Status: Bounded publishable positive

## Abstract

Sparse Mixture-of-Experts language models are often described as routing different domains to specialized expert subsets. PX-005 evaluates a narrower routing-observability claim: whether stable high-mass expert committees recur across prompt domains and style variants. Using a frozen 480-prompt audit across cyber, code, math, policy, and writing prompts, the experiment captures router traces for OLMoE base, OLMoE-Instruct, and Qwen1.5-MoE. All three audits pass frozen committee-overlap checks. OLMoE base captures 480/480 prompts with primary Jaccard 0.4656 and bootstrap CI [0.4336, 0.4834]. OLMoE-Instruct captures 480/480 prompts with primary Jaccard 0.4591 and CI [0.4320, 0.4796]. Qwen1.5-MoE captures 480/480 prompts with primary Jaccard 0.5826 and CI [0.5552, 0.6281]. The result supports a bounded standing-committee replication/extension under a frozen prompt-domain audit. It does not prove causal expert specialization or universal MoE behavior.

## 1. Introduction

MoE architectures route tokens through sparse expert subsets. A tempting interpretation is that domains naturally map to specialized experts. Recent router analyses complicate that assumption by showing recurring high-mass expert committees that persist across domains. PX-005 tests whether that phenomenon appears under a local frozen prompt-domain audit and whether it survives instruction tuning and a non-OLMoE architecture.

## 2. Prior Work

Switch Transformers established a practical sparse routing architecture for scaling language models with constant per-token compute. OLMoE extends this line with fully open MoE language models and release artifacts that make router analysis feasible. Qwen1.5-MoE provides a separate MoE architecture for cross-model checking.

The direct conceptual anchor is Wang et al.'s 2026 Standing Committee work. That paper questions the assumption that MoE routers produce clean domain specialization and introduces COMMITTEEAUDIT, a post hoc framework for analyzing expert groups rather than individual experts.

PX-005 should therefore not be positioned as the first discovery of standing committees. Its contribution is a frozen Praxis replication/extension across local prompt domains, OLMoE base, OLMoE-Instruct, and Qwen1.5-MoE.

## 3. Experimental Design Influences

Switch Transformer and OLMoE literature shaped the focus on router observability rather than output-only behavior.

The Standing Committee paper shaped the metric choice: analyze groups of high-mass experts using committee overlap, not single expert identities alone.

OLMoE's open release shaped the source-gate requirement: the experiment needed accessible model weights and router internals.

Qwen1.5-MoE shaped the cross-architecture gate: a non-OLMoE model was required before the result could be described as more than an OLMoE-family observation.

## 4. Research Questions

RQ1: Do stable high-overlap routed expert committees recur across prompt domains and style variants?

RQ2: Does the signal survive instruction tuning inside the OLMoE family?

RQ3: Does the signal appear in a non-OLMoE MoE architecture?

RQ4: Is the result sensitive to committee size?

## 5. Data and Methods

The audit is inference-only. It uses five domains, twelve base prompts per domain, and eight deterministic style variants per base prompt.

| Component | Value |
|---|---:|
| Domains | 5 |
| Base prompts per domain | 12 |
| Style variants per base prompt | 8 |
| Total prompts per audit | 480 |
| Primary committee size | 32 |
| Sensitivity committee sizes | 16, 32, 64 |
| Bootstrap samples | 200 |

Domains are cyber, code, math, policy, and writing. Style variants include direct, concise, stepwise, risk-focused, evidence-focused, beginner, expert, and compact-summary prompts.

Frozen pass checks:

| Check | Threshold |
|---|---:|
| Router capture rate | >= 0.95 |
| Primary mean pairwise Jaccard | >= 0.25 |
| Primary bootstrap CI low | >= 0.20 |
| All committee-size means | >= 0.20 |

## 6. Results

Primary audit results:

| Model | Decision | Router capture | Primary Jaccard | Bootstrap CI |
|---|---|---:|---:|---:|
| OLMoE base | PASS | 480/480 | 0.4656 | [0.4336, 0.4834] |
| OLMoE-Instruct | PASS | 480/480 | 0.4591 | [0.4320, 0.4796] |
| Qwen1.5-MoE | PASS | 480/480 | 0.5826 | [0.5552, 0.6281] |

Committee-size sensitivity:

| Model | Size 16 mean | Size 32 mean | Size 64 mean |
|---|---:|---:|---:|
| OLMoE base | 0.4950 | 0.4656 | 0.5334 |
| OLMoE-Instruct | 0.5642 | 0.4591 | 0.5520 |
| Qwen1.5-MoE | 0.5354 | 0.5826 | 0.5652 |

Qwen cross-architecture gate:

| Metric | Value |
|---|---:|
| Prompt count | 480 |
| Router-captured prompts | 480 |
| Router capture rate | 1.0000 |
| Primary committee size | 32 |
| Primary mean pairwise Jaccard | 0.5826 |
| Primary bootstrap CI low | 0.5552 |
| Primary bootstrap CI high | 0.6281 |
| Mean layer top-k mass | 0.3097 |
| Mean layer entropy | 3.3266 |

## 7. Discussion

PX-005 shows stable high-overlap routed committees under the frozen audit. The result is stronger than a single-model observation because it appears in OLMoE base, OLMoE-Instruct, and Qwen1.5-MoE. The signal is also not an artifact of committee size because sensitivity checks pass at sizes 16, 32, and 64.

The claim remains observational. Committee overlap does not prove expert causality, domain specialization, or behavioral control. Causal follow-up would require expert ablation, routing patching, domain-shift tests, or fine-tuning interventions.

## 8. Threats to Validity

The prompt suite is fixed and synthetic. The measured committees are high-mass router structures, not proof of task performance. Qwen provides one non-OLMoE check, not universal cross-architecture validity. The experiment does not test whether committee membership causes domain behavior.

## 9. Conclusion

PX-005 is a bounded publishable MoE interpretability result. It replicates and extends standing-committee analysis under a frozen Praxis audit and demonstrates router instrumentation across multiple MoE models. Its best defense posture is conservative: stable routed committees appear in these audited models under this protocol.

## Repository Artifacts

- `reports/moe_standing_committee/MOE_STANDING_COMMITTEE_SHORT_PAPER_20260628.md`
- `reports/moe_standing_committee/router_audit_20260623/MOE_STANDING_COMMITTEE_ROUTER_AUDIT_20260623.md`
- `reports/moe_standing_committee/router_audit_olmoe_instruct_20260623/MOE_STANDING_COMMITTEE_ROUTER_AUDIT_OLMOE_INSTRUCT_20260623.md`
- `reports/moe_standing_committee/qwen15_router_audit_20260628/MOE_QWEN15_ROUTER_AUDIT_20260628.md`
- `cloud_jobs/moe_standing_committee_20260623/run_olmoe_router_audit.py`
- `cloud_jobs/moe_qwen15_router_audit_20260628/run_qwen_moe_router_audit.py`
- `configs/moe_standing_committee_router_audit_20260623.json`
- `configs/moe_qwen15_router_audit_20260628.json`

## References

Fedus, W., Zoph, B., & Shazeer, N. (2021). Switch Transformers: Scaling to trillion parameter models with simple and efficient sparsity. arXiv. https://arxiv.org/abs/2101.03961

Muennighoff, N., Soldaini, L., Groeneveld, D., Lo, K., Morrison, J., Min, S., Shi, W., Walsh, P., Tafjord, O., Lambert, N., Gu, Y., Arora, S., Bhagia, A., Schwenk, D., Wadden, D., Wettig, A., Hui, B., Dettmers, T., Kiela, D., ... Hajishirzi, H. (2024). OLMoE: Open Mixture-of-Experts language models. arXiv. https://arxiv.org/abs/2409.02060

Qwen Team. (2024). Qwen2 technical report. arXiv. https://arxiv.org/abs/2407.10671

Wang, Y., Xu, Y., Shen, N., Su, J., Huang, J., & Zhu, Z. (2026). The illusion of specialization: Unveiling the domain-invariant "Standing Committee" in Mixture-of-Experts models. arXiv. https://arxiv.org/abs/2601.03425

