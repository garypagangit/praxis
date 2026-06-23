# AI/ML Praxis Idea Explorer Deconfliction

Date: 2026-06-22

Source document: `C:\Users\garyp\Documents\AI_ML_Praxis_Idea_Explorer.docx`

Extraction artifact: `tmp/docs/idea_explorer_20260622/AI_ML_Praxis_Idea_Explorer_extracted.md`

Layout note: the local machine does not have LibreOffice/Poppler available, so this review used `python-docx` text/table extraction rather than page-rendered DOCX visual review. The source document has 384 paragraphs, 41 tables, and no embedded images.

## Executive Decision

Do not start this as a 20-experiment batch.

The document is useful, but it overstates how many items are ready for Praxis-grade experimentation. Several ideas duplicate lanes we already tested and closed in the frontier batch. Others are high-novelty but require full pretraining, simulator readiness, clinical data handling, user studies, or open-ended evaluation that would be hard to defend quickly.

The honest move is to reduce the document to three near-term candidates and keep the rest as later-reading or source-gate material:

1. Start first: code citation poisoning / FalseCite-style benchmark for software artifacts.
2. Start second if source gate passes: MoE standing-committee routing audit.
3. Start third as a cheap controlled benchmark: synthetic ground-truth circuit recovery for interpretability tools.

Do not restart a broad frontier batch until these pass source/readiness gates.

## Deconfliction Against Current Portfolio

The current portfolio already has two positive paper tracks:

- Praxis 06: selective TTA for streaming APT stage detection.
- Praxis 07: retrieval-conditioned CTI compliance with ATT&CK relationship evidence.

The June frontier batch already tested adjacent new ideas and closed them without new publishable positives:

- Test-time compute transferability became a provisional harness, not a publishable result.
- Self-jailbreak detection found a signal but failed benign utility.
- VLA instruction diversity was blocked by public LIBERO metadata/simulator readiness.
- KG hallucination verification failed external promotion because response-only artifacts beat evidence features.
- World-model robustness remained an environment smoke, not a world-model agent result.

That means new ideas must avoid repeating:

- generic test-time compute/reasoning experiments without a strict promotion gate;
- broad hallucination verification where response-only baselines can win;
- robotics/VLA claims before simulator and language metadata are confirmed;
- world-model claims without a learned world-model agent;
- medical/clinical claims without very conservative scope and public labels.

## Source Verification Notes

Spot checks against primary arXiv pages confirm that several high-priority anchors exist:

- `2506.02338`: Long CoT Collection exists and reports a 100K long-CoT dataset plus 2-3x larger RLVR gains after initialization.
- `2602.05842`: RWML exists and evaluates self-supervised world-model learning on ALFWorld and tau-squared Bench.
- `2512.13059`: Open Deep Research Agent exists and describes an open long-form QA research agent with preference tuning.
- `2602.01031`: HalluHard exists and introduces a 950-seed multi-turn hallucination benchmark.
- `2602.11167`: the arXiv title is not "FalseCite" but the abstract does introduce FalseCite as the curated fabricated-citation dataset.
- `2601.03425`: Standing Committee in MoE exists and was revised as an ACL 2026 camera-ready version.
- `2512.18470`: SWE-EVO exists and reports a long-horizon coding-agent benchmark with 48 tasks.

Unverified items should get a source gate before any compute spend.

## Cluster-Level Review

| Cluster | Document items | Deconfliction | Decision |
|---|---|---|---|
| Reasoning / test-time compute | 1, 2 | Collides with prior EXP01 TTC harness. Full RLVR or latent-loop pretraining is too heavy. A small thought-budget gate is possible but not a fresh thesis lane. | Merge/defer. Do not start full training. |
| Agentic world models / coding agents | 3, 9, 10, 20 | Collides with EXP05 world-model limitation. SWE-EVO is more concrete than ALFWorld/MARL, but RWML-style repo-state modeling is a new research program. | Gate later. Start only with source/data readiness. |
| RAG / hallucination / evidence reliability | 4, 13, 14 | Strongest fit with Praxis 07 and EXP04 lessons. Must use strict external verification and response-only baselines. | Start item 14 first; consider 13 as follow-on. |
| Mechanistic interpretability / MoE | 7, 8, 15, 16 | Praxis 05 SAE failed on detector hidden states, but synthetic circuits and MoE routing audits avoid that exact failure. | Start 16 or 8 after source gate. |
| VLM/robotics/quantization | 11, 12 | Item 11 collides with failed VLA readiness. Item 12 adds federated medical complexity. | Defer. No robotics claim until simulator/data gate passes. |
| Generative 3D/video/audio | 5, 6, 17, 19 | Mostly outside current dissertation arc. Several require large training, partial/academic datasets, user studies, or multimodal infrastructure. | Hold/kill for this cycle. |
| Privacy/federated LoRA | 18 | Some relation to AI supply-chain LoRA trace work, but DP reasoning-chain quality relies on fragile evaluator metrics. | Defer; possible cheap gate only. |

## Item-Level Decision Matrix

| # | Idea | Honest decision | Reason |
|---:|---|---|---|
| 1 | Long CoT Collection / thought-budget oracle | Merge/defer | Useful as a small budget-control add-on to EXP01, but full RLVR training is not needed and would distract from paper packaging. |
| 2 | Ouro latent loop exit gating | Defer | High novelty, but architecture/pretraining heavy. Use released checkpoints only if a tiny source gate shows accessible loop-depth instrumentation. |
| 3 | RWML for multi-agent theory-of-mind | Defer | The document's spin is too broad. Keep only as a possible component for SWE-EVO repo-state modeling. |
| 4 | Open deep research agent for biomedical evidence synthesis | Merge/reframe | Good reproducibility, but biomedical claims are high-risk. Better reframe to CTI/source-conflict evidence synthesis using Praxis 07 assets. |
| 5 | GGS medical 3D generation | Kill for current cycle | Compute-heavy, clinical domain, and outside current claim stack. |
| 6 | HuGeDiff motion-conditioned avatars | Kill for current cycle | Needs 3D/motion generation plus user study. Low alignment with current thesis. |
| 7 | Circuit-aware reward training for longtail robustness | Defer | Interesting, but multimodal reward circuits would require new tooling and labels. |
| 8 | Synthetic ground-truth circuit benchmark | Start candidate | Cheap, controlled, and directly answers the interpretability benchmark gap. Better than reviving Praxis 05 SAE on weak detector states. |
| 9 | MAGRPO adversarial-collaborative MARL | Defer | Open-ended MARL plus medical/legal writing is evaluation-heavy. A no-training adversarial-pair prompt gate could be a later smoke. |
| 10 | Agentic RL survey / scientific discovery benchmark | Hold | Survey is a roadmap, not a specific experiment. Too broad without a narrow protocol. |
| 11 | SPEED-Q robotics VLM quantization | Defer | Quantization is reproducible, but robotics/VLA path is already blocked by simulator/language metadata. |
| 12 | TernaryCLIP federated hospital networks | Defer/kill | Federated medical setup adds privacy, dataset, and clinical validity burdens. |
| 13 | HalluHard scientific literature benchmark | Start candidate after 14 | Stronger than prior EXP04 if scoped as benchmark/verifier audit, but needs strict source-backed PubMed verification and response-only baselines. |
| 14 | FalseCite for code citation hallucination | Start first | Best near-term fit: open dataset style, strict external verification, code/package metadata checks, and clean deconfliction from Praxis 07. |
| 15 | FLAME-MoE routing transfer | Defer | Good training-trace idea, but cross-domain fine-tuning plus activation patching is heavier than needed. |
| 16 | MoE standing committee audit | Start second | Inference-only, current, published/accepted anchor, and has a clear falsifiable source gate. |
| 17 | Controllable video benchmark | Hold | Benchmark construction is plausible but far outside current portfolio and dataset-heavy. |
| 18 | DP-FedLoRA chain-of-thought degradation | Defer | Related to LoRA provenance, but CoT-quality scoring can be weak. Needs a tiny epsilon/accuracy smoke first. |
| 19 | SLAM-LLM low-resource audiovisual ASR | Hold | Accessible, but a full multimodal ASR track would be a thesis pivot, not a natural extension. |
| 20 | SWE-EVO plus repo-state world model | Gate later | Promising, but should start as a data/source gate only. Full RWML-style agent training is too large for immediate work. |

## Recommended Start Queue

### 1. Code Citation Poisoning and Software Artifact Verification

Working title: `FalseCite-Code: Citation Poisoning in Code-Assistance Prompts`

Why start:

- It is narrow, testable, and cheap relative to RL/vision/audio ideas.
- It naturally extends the verified FalseCite anchor into software artifacts.
- It avoids the EXP04 failure by requiring external package/repository metadata checks and response-only baselines.
- It fits the existing Praxis pattern: strict parser, locked dataset, no post-hoc threshold rescue.

First gate:

- Build 100-200 prompts with fabricated GitHub URLs, package versions, function signatures, and changelog citations.
- Include clean matched controls.
- Compare base prompt, retrieval-backed prompt, and citation-aware verifier.
- Score with strict metadata verification against PyPI/NPM/GitHub release records.
- Promote only if the verifier reduces fabricated-detail acceptance by at least 25 percent absolute without over-refusing clean prompts by more than 10 percent.

### 2. MoE Standing-Committee Routing Audit

Working title: `Standing Committee Routing Under Domain and Fine-Tuning Shift`

Why start:

- It is inference-first and can be source-gated before GPU spend.
- It is a cleaner interpretability path than reviving the failed Praxis 05 SAE detector track.
- It has a concrete mechanism claim: stable routed-expert coalitions versus domain-specialized experts.

First gate:

- Verify access to one open MoE model with exposed router logits or expert choices.
- Run 5 small domains with 200 prompts each.
- Measure expert coalition overlap, routing mass concentration, and whether committee experts persist under prompt/domain shift.
- No fine-tuning until the inference audit reproduces the standing-committee signal.

### 3. Synthetic Ground-Truth Circuit Recovery Benchmark

Working title: `Known-Circuit Recovery Benchmark for Activation Patching and SAEs`

Why start:

- It is cheap and defensible.
- It directly addresses the interpretability benchmark gap from the document.
- It creates a controlled positive/negative substrate before spending on real hidden-state claims.

First gate:

- Train tiny transformers on synthetic tasks with known algorithmic features.
- Compare activation patching, probing, and sparse autoencoder recovery against known ground-truth circuits.
- Promote only if recovery metrics are stable across seeds and beat random/probe-only baselines.

## Not Recommended As Immediate Starts

Do not start the generative 3D/video/audio tracks, robotics quantization, medical federated CLIP, or full RWML/MARL training now. They may be interesting, but they are not the fastest path to defensible Praxis output.

## Final Recommendation

Start exactly one new experiment from this document: `FalseCite-Code`.

Keep `MoE Standing Committee` and `Known-Circuit Recovery` as the next two source-gated candidates. Everything else should remain in a deferred idea bank until Praxis 06, Praxis 07, and the ATT&CK TTP retrieval section are in stronger submission shape.
