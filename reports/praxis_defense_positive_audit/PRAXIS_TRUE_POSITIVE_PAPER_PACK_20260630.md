# Praxis True-Positive Paper Pack

Generated: 2026-07-01 UTC

## Paper 1: Safety-Gated Test-Time Adaptation for Streaming APT Detection

**PX ID:** PX-001

**Praxis thesis:** A streaming intrusion detector can use tightly gated, unlabeled test-time adaptation to recover weak early-stage attack detection while preserving high-risk destructive-event safety.

**Objective:** Test whether selective BatchNorm adaptation can improve Recon-stage F1 on an APT stage-classification stream without sacrificing destructive-event detection.

**Method:** Train the support-floor MLP on the Unraveled APT benchmark, select the TTA policy only on validation artifacts, freeze thresholds, then replay on held-out test streams across the original three seeds and a four-seed fixed-threshold extension. Audit override flows, stream-order sensitivity, DE safety, and feature-shift diagnostics.

**Results:** The fresh defense replay reproduced the locked result. Original locked seeds improved macro-F1 from `0.7685` to `0.8658`, Recon F1 from `0.0250` to `0.5050`, and preserved DE F1 at `0.9202`. Seven-seed fixed-extension runs improved macro-F1 from `0.7165` to `0.8341` and Recon F1 from `0.0615` to `0.5219`. The DE safety audit found `0` changed-from-DE rows.

**Finding:** PX-001 is a true defense-ready positive. It supports a narrow, useful claim about safety-gated TTA under the tested streaming APT setting.

**Claim boundary:** Do not claim universal external validity. DAPT2020 remains a negative TTA feasibility boundary.

**Evidence:** `runs/tta-defense-hardening-defense-audit-20260630/`, `reports/tta_streaming_apt/TTA_FUNCTIONING_CAPABILITY_REPORT_20260513.md`.

## Paper 2: Retrieval-Conditioned CTI Compliance with Source-Conflict Routing

**PX IDs:** PX-003 + PX-034

**Praxis thesis:** CTI question answering improves when models receive per-question ATT&CK evidence, and a source-conflict router can identify when evidence is decisive enough for direct answering.

**Objective:** Test whether relationship-level ATT&CK evidence improves strict CTI-MCQ compliance over vanilla prompting, broad seeding, technique-only evidence, empty evidence, and random facts on a locked evidence-addressable slice.

**Method:** Build a label-free evidence-addressable CTI-MCQ slice from MITRE ATT&CK relationship support. Evaluate strict `Answer: <A|B|C|D>` compliance on Llama-3.1-8B, Llama-3.2-3B, and Qwen2.5-7B. Add PX-034 source-conflict routing over the full 500-row CTI-MCQ set to classify rows as decisive, conflicting, ambiguous, weak, or unsupported.

**Results:** Llama-3.1-8B improved from `0.642` vanilla to `0.915` relationship evidence. Llama-3.2-3B improved from `0.547` to `0.887`. The new Qwen2.5-7B defense replication improved from `0.623` vanilla to `0.906` relationship evidence; technique-only evidence reached `0.726`, random facts `0.462`, empty evidence `0.594`, and broad seed `0.660`. Relationship evidence produced `35` evidence-only wins versus `5` vanilla-only wins. PX-034 found `106` decisive rows and routed the remaining rows away from direct confident answering.

**Finding:** PX-003/PX-034 is a true defense-ready positive. The cross-family replication makes this one of the strongest Praxis results.

**Claim boundary:** The mechanism is retrieval-conditioned evidence, not pure relationship causality. Technique-only evidence also helps, so relationship evidence should be described as the strongest tested condition.

**Evidence:** `reports/relationship_evidence_cti_compliance/PX003_QWEN25_7B_DEFENSE_REPLICATION_20260630.md`, `reports/relationship_evidence_cti_compliance/PRAXIS07_RESULT_SYNTHESIS_20260517.md`, `reports/relationship_evidence_cti_compliance/PX034_CTI_SOURCE_CONFLICT_GATE_20260630.md`.

## Paper 3: FalseCite-Code External Verification for Software-Artifact Citation Poisoning

**PX ID:** PX-004

**Praxis thesis:** Code assistants can be induced to trust fabricated software-artifact citations, but external metadata verification can suppress this failure mode on a locked benchmark.

**Objective:** Build a balanced software-artifact citation benchmark and test whether code-tuned models accept fabricated PyPI, NPM, GitHub repository, and GitHub tag citations; then test whether a deterministic external verifier reduces fabricated trust.

**Method:** Construct an 80-claim benchmark from public package/repository metadata with artifact-keyed train/validation/strict-holdout splits. Evaluate source/verifier readiness, audit-mode model trust, generation-mode model trust, and boundary models. Refresh the metadata gate with authenticated GitHub access during the defense audit.

**Results:** The fresh authenticated metadata refresh passed with `80` claims, `15` strict-holdout claims, API error rate `0.000`, verifier accuracy `1.000`, and invalid recall `1.000`. Qwen2.5-Coder-7B accepted fabricated strict-holdout citations at `0.8571` in audit mode and `0.8333` in verbose generation mode. The external verifier reduced strict fabricated trust to `0.0000` in the primary gates.

**Finding:** PX-004 is a true bounded defense-positive. It is practical, reproducible, and directly relevant to code-assistant safety.

**Claim boundary:** Do not claim universal hallucination prevention or universal model vulnerability. The supported claim is software-artifact citation verification on the locked benchmark and tested model/prompt conditions.

**Evidence:** `reports/falsecite_code/FALSECITE_CODE_SHORT_PAPER_20260628.md`, `reports/falsecite_code/defense_refresh_20260630/FALSECITE_CODE_SOURCE_VERIFIER_GATE_20260623.md`.

## Paper 4: Standing-Committee Routing in Sparse Mixture-of-Experts Models

**PX ID:** PX-005

**Praxis thesis:** Sparse MoE routers can exhibit stable high-mass standing committees across prompt domains and style variants, challenging simple domain-specialization assumptions.

**Objective:** Test whether high-overlap routed expert committees recur across cyber, code, math, policy, and writing prompts under deterministic style perturbations.

**Method:** Run a frozen 480-prompt audit with five domains, twelve base prompts per domain, and eight style variants. Measure router capture, committee overlap at sizes `16`, `32`, and `64`, bootstrap confidence intervals, and cross-architecture replication on OLMoE base, OLMoE-Instruct, and Qwen1.5-MoE.

**Results:** OLMoE base passed with primary Jaccard `0.4656` and CI `[0.4336, 0.4834]`. OLMoE-Instruct passed with primary Jaccard `0.4591` and CI `[0.4320, 0.4796]`. Qwen1.5-MoE passed with `480/480` router capture, primary Jaccard `0.5826`, and CI `[0.5552, 0.6281]`.

**Finding:** PX-005 is a true bounded publishable positive. It should be presented as a router-observability result, not as proof of causal expert specialization.

**Claim boundary:** No causal expert-ablation, fine-tuning-shift, or behavior-intervention claim is supported yet. The next scientific step is a causal/domain-shift intervention or another non-OLMoE architecture.

**Evidence:** `reports/moe_standing_committee/MOE_STANDING_COMMITTEE_SHORT_PAPER_20260628.md`, `reports/moe_standing_committee/qwen15_router_audit_20260628/MOE_QWEN15_ROUTER_AUDIT_20260628.md`.

## Defense Narrative

The strongest Praxis defense package should lead with PX-001, PX-003/PX-034, and PX-004. These three form a coherent cyber/AI safety thesis around safe adaptation, evidence conditioning, and external verification. PX-005 is an additional publishable AI-systems result and a strong industry-relevant artifact, but it should not be forced into the same cyber-defense mechanism story.
