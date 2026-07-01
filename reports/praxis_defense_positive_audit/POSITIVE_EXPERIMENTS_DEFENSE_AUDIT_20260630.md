# Praxis Positive Experiments Defense Audit

Generated: 2026-07-01 UTC

## Executive Decision

The seven previously listed positives are not all equally defensible. After rerunning or adding the necessary hard checks, the true positive set is:

1. **PX-001 Safety-Gated TTA for Streaming APT Detection** - true defense-ready positive.
2. **PX-003 Retrieval-Conditioned CTI Compliance + PX-034 source-conflict router** - true defense-ready positive.
3. **PX-004 FalseCite-Code Software-Artifact Citation Poisoning** - true bounded defense-positive.
4. **PX-005 MoE Standing-Committee Router Audit** - true bounded publishable positive, but not a causal expert-specialization result.

The demoted positives are:

1. **PX-002 ATT&CK TTP-Set Profile Retrieval** - useful lookup artifact, not a defense pillar.
2. **PX-010 Synthetic Ground-Truth Circuit Recovery** - methods-positive at toy levels, but not defense-ready after the trained mini-transformer bridge failed.
3. **PX-034 Open Deep Research Agent framing** - not separate; merge into PX-003 as a source-conflict/router add-on.

## Defense Classification Table

| PX | Experiment | Defense classification | Fresh audit result | What it proves | Defense action |
|---|---|---|---|---|---|
| PX-001 | Safety-Gated TTA for Streaming APT Detection | **True defense-ready positive** | Fresh 7-seed replay preserved the May result: locked hybrid macro-F1 `0.8658` vs frozen `0.7685`; Recon F1 `0.5050` vs `0.0250`; DE F1 `0.9202`; changed-from-DE count `0`. | A locked, validation-selected selective TTA policy can rescue Recon-stage performance in streaming APT detection while preserving destructive-event safety under the tested Unraveled slice. | Use as lead Praxis defense result. |
| PX-003 / PX-034 | Retrieval-Conditioned CTI Compliance plus source-conflict router | **True defense-ready positive** | New Qwen2.5-7B run: vanilla `0.623`, relationship evidence `0.906`, technique-only `0.726`, random facts `0.462`, empty evidence `0.594`, broad seed `0.660`; relationship-only wins `35` vs vanilla-only `5`. | Per-question ATT&CK evidence retrieval improves strict CTI-MCQ compliance across Llama and Qwen model families; PX-034 identifies the decisive evidence slice and routes non-decisive rows to abstain/review. | Use as second major Praxis result; keep mechanism conservative. |
| PX-004 | FalseCite-Code Software-Artifact Citation Poisoning | **True bounded defense-positive** | Fresh authenticated metadata refresh passed: `80` claims, `15` strict holdout, external verifier accuracy `1.000`, invalid recall `1.000`, API error rate `0.000`. Existing model gates show strict fabricated trust reduced to `0.0000`. | Fabricated software-artifact citations can be accepted by code-tuned models, and an external metadata verifier can suppress fabricated-citation trust on the locked benchmark. | Include as practical verifier/guardrail paper. |
| PX-005 | MoE Standing-Committee Router Audit | **True bounded publishable positive** | Existing frozen audits pass across OLMoE base, OLMoE-Instruct, and Qwen1.5-MoE. Qwen: `480/480` router capture, primary Jaccard `0.5826`, CI `[0.5552, 0.6281]`. | Stable high-overlap routed expert committees appear across prompt domains and style perturbations in the audited MoE models. | Include as AI-industry/interpretability result, but do not claim causal specialization. |
| PX-002 | ATT&CK TTP-Set Profile Retrieval | **Demoted to diagnostic lookup artifact** | New anti-tautology audit: standard overlap top-5 `0.960`, but leave-query-out overlap top-5 `0.000`; SVD leave-query-out top-5 only `0.299`. | The original win is mostly profile overlap lookup when query techniques remain available in the candidate profile. | Keep as supporting CTI retrieval utility only. Do not use as defense pillar. |
| PX-010 | Synthetic Ground-Truth Circuit Recovery | **Demoted to methods-positive / not defense-ready** | New trained mini-transformer bridge failed: holdout accuracy `0.9988`, attention target accuracy `0.9268`, but source-patch AP `0.8000`, precision@K `0.7000`, stable seed fraction `0.4000`. | The harness works on simpler synthetic gates, but the stronger trained transformer-style bridge does not stably recover the true attention-source components. | Keep as an honest methods artifact; next work requires a stronger transformer/real activation corpus. |
| PX-034 | Open Deep Research Agent with Preference Tuning framing | **Merged into PX-003** | Source-conflict router: `106` decisive rows, `179` high-support conflicting, `28` ambiguous, `37` weak single-source, `150` unsupported. | A local CTI source-conflict router can identify when retrieved evidence is decisive enough for direct answering. | Present only as PX-003 router add-on, not as broad open deep research agent. |

## Main Defense Thesis After Audit

The strongest Praxis defense story is no longer "we ran many AI-paper-inspired experiments and seven were positive." The defensible story is sharper:

Praxis Research surveyed 2025-2026 AI research directions, extracted future-work opportunities, and converted them into falsifiable experiments. Most candidates failed or narrowed. Four survived as bounded, evidence-backed positives. The strongest through-line is **safe evidence conditioning and verification for cyber/AI systems**:

- PX-001: safe adaptation under streaming security distribution shift.
- PX-003/PX-034: evidence-conditioned CTI answering with source-conflict routing.
- PX-004: external verification against software-artifact citation poisoning.
- PX-005: router observability for MoE systems, useful as an interpretability/AI-systems result.

## What Should Be Defended

Defend PX-001, PX-003/PX-034, and PX-004 as the main Praxis defense package. Use PX-005 as a publishable supporting AI-industry experiment. Use PX-002 and PX-010 as evidence of disciplined falsification: they were promising, but the stronger tests demoted them.

## Artifact Links

| Artifact | Purpose |
|---|---|
| `../tta_streaming_apt/TTA_FUNCTIONING_CAPABILITY_REPORT_20260513.md` | PX-001 locked functioning report. |
| `../../runs/tta-defense-hardening-defense-audit-20260630/PRAXIS06_TTA_DEFENSE_HARDENING_REPORT_20260513.md` | PX-001 fresh 7-seed defense replay. |
| `../relationship_evidence_cti_compliance/PX003_QWEN25_7B_DEFENSE_REPLICATION_20260630.md` | PX-003 Qwen2.5-7B cross-family replication. |
| `../relationship_evidence_cti_compliance/PX034_CTI_SOURCE_CONFLICT_GATE_20260630.md` | PX-034 source-conflict/router add-on. |
| `../falsecite_code/defense_refresh_20260630/FALSECITE_CODE_SOURCE_VERIFIER_GATE_20260623.md` | PX-004 authenticated metadata freshness audit. |
| `../moe_standing_committee/MOE_STANDING_COMMITTEE_SHORT_PAPER_20260628.md` | PX-005 bounded short paper. |
| `../gnn_attribution_ttp_graph_embeddings/PX002_TTP_RETRIEVAL_DEFENSE_AUDIT_20260630.md` | PX-002 anti-tautology demotion audit. |
| `../synthetic_circuit_recovery/TRAINED_MINI_TRANSFORMER_CIRCUIT_BRIDGE_20260630.md` | PX-010 stronger bridge failure. |
