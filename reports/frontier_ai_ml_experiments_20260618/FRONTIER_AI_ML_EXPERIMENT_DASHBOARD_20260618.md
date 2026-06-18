# Frontier AI/ML Experiment Dashboard

Updated: 2026-06-18

Source brief: `C:\Users\garyp\Downloads\AI_ML_Praxis_Experiment_Templates.docx`.

Purpose: convert the attached block of five 2026 AI/ML experiment templates into a gated Praxis workstream. EXP01 now has a full preliminary AWS result; the other experiments remain queued behind their first gates. Each experiment below is framed with a thesis, gate state, evidence target, compute posture, and stop rule.

## Start Decision

We have completed the first full preliminary AWS run for **Experiment 01 - Cross-Model Transferability of Test-Time Compute Strategies**.

Current status: **EXP01 preliminary full-run result present, provisional / do not overclaim**. The split-readiness gate passed, then the AWS run evaluated `4` open 7B-class models across `160` public benchmark rows, `2` strategy classes, and budgets `K={1,2,4,8}`. Policy selection used GSM8K validation-policy rows only; final checks used a GSM8K in-domain test split plus a strict MATH-500 holdout that was not used for policy selection.

What the first run shows:

- The transfer matrix is complete for the configured model set: `32` rows.
- Best selected validation policy for `qwen2p5_7b_instruct` was majority vote `K=8`, with validation accuracy `0.8250`, in-domain test accuracy `0.7250`, and strict MATH-500 holdout accuracy `0.2250`.
- Other model-family results were much weaker under exact scoring: Qwen2.5-Math-7B selected majority vote `K=8` with strict holdout `0.0625`; DeepSeek-R1-Distill-Qwen-7B selected majority vote `K=8` with strict holdout `0.0000`; Mistral-7B selected single-sample `K=1` with strict holdout `0.0375`.
- Off-diagonal retention is measurable but not yet a clean scientific win: mean off-diagonal retention was `1.5920` in-domain and `1.3111` on strict holdout among non-null rows.
- The feature-engineered Optuna predictor completed but did not generalize: leave-one-target-family R2 `-14.9408`.
- Internal defense verdict: preliminary evidence suitable for a slide or committee update, not yet a Praxis-level claim. H1 still needs verifier/scorer best-of-N, and H3 still needs sequential refinement or a formal drop.

## Experiment Queue

| Priority | Experiment | Working title | Field area | Current posture | First gate | Main output |
|---:|---|---|---|---|---|---|
| 1 | EXP01 | Cross-Model Transferability of Test-Time Compute Strategies | Reasoning / inference efficiency | Preliminary full AWS result present; provisional | Add verifier best-of-N, sequential refinement or drop H3, and manual scoring audit | Transfer matrix, retention metric, negative predictor result, defense challenge |
| 2 | EXP02 | Step-Level Self-Jailbreak Detection and Training-Free Intervention | Reasoning-model safety | High-value but safety-sensitive | Build trace schema and label protocol; run no harmful generation until policy and dataset handling are explicit | Override detector, intervention frontier, safety-reasoning trade-off |
| 3 | EXP04 | Multi-Turn Hallucination Compounding and KG-Grounded Verification | Factuality / reliability | Strong second practical path | Build dialogue + atomic-claim schema and verify Wikidata/SPARQL access | Multi-turn hallucination benchmark and KG verifier |
| 4 | EXP03 | Instruction Diversity and Linguistic Generalisation in VLA Models | Embodied AI / robot foundation models | Promising but heavier setup | Verify OpenVLA/OXE/LIBERO environment and one short simulation eval | Instruction-diversity curve and cross-embodiment transfer result |
| 5 | EXP05 | Cross-Paradigm Visual Robustness of World-Model Agents | World models / model-based RL | High-ceiling, compute-heavy | Install stable-worldmodel and run one Crafter visual-wrapper smoke | Robustness leaderboard and augmentation remedy |

## EXP01 - Cross-Model Transferability of Test-Time Compute Strategies

**Thesis:** test-time compute scaling strategies are not fully model-agnostic; compute-optimal policies discovered on one model family may degrade when transferred to another family or scale.

**Research questions:** do source-optimal TTC strategies transfer zero-shot; which strategy class is most transferable; can cheap model signals predict degradation?

**Hypotheses:** verifier-based best-of-N transfers better than majority voting; retention degrades with answer-distribution entropy divergence; sequential self-refinement transfers worst.

**Datasets:** MATH, GSM8K, MATH-500, AIME 2024/25, HumanEval.

**Strategy classes:** best-of-N with verifier or reward model, majority voting/self-consistency, sequential self-refinement, and policy-verifier budget allocation.

**Completed gates:** the 50-row split-readiness gate passed with scoring-only labels separated from prompt-side manifests. The full preliminary AWS run completed on `2026-06-18` with four open models, `160` rows, `2,560` scored model/strategy rows, and `32` transfer rows.

**Promotion gate:** add verifier/scorer best-of-N, add sequential self-refinement or formally drop H3, manually audit exact-answer scoring agreement, and add bootstrap confidence intervals. Predictor family holdout currently gives a clearly explained negative: leave-one-target-family R2 `-14.9408`.

**Stop rule:** stop or narrow if answer extraction/scoring cannot reach `>=0.95` agreement on the smoke set, or if compute cost for the minimal off-diagonal matrix exceeds the agreed budget.

**Kickoff doc:** `reports/frontier_ai_ml_experiments_20260618/EXP01_TTC_TRANSFER_KICKOFF_20260618.md`.

## EXP02 - Step-Level Self-Jailbreak Detection and Training-Free Intervention

**Thesis:** self-jailbreak behavior occurs at a localizable reasoning-step boundary; a detector plus inference-time intervention can reduce unsafe final outputs without weight updates and with less reasoning degradation than fine-tuning.

**Research questions:** can override points be detected from traces; can intervention match Chain-of-Guardrail-like safety; what reasoning cost is paid?

**Hypotheses:** step detector F1 above `0.85`; intervention attack-success rate within five points of SFT; reasoning accuracy retained better than SFT.

**Datasets:** StrongREJECT, SORRY-Bench, WildJailBreak, JailbreakBench, MATH-500, GSM8K, GPQA.

**First gate:** create the trace/label schema and annotation rubric; validate that a small manually reviewed sample can identify override boundaries. Do not run large harmful-prompt generation until the data handling and evaluation plan are explicit.

**Promotion gate:** category-holdout detector performance with ROC-AUC/PR-AUC confidence intervals plus false-refusal rate on benign twins.

**Stop rule:** stop if override labels have poor human/judge agreement, target Cohen kappa `<0.60`, or if the intervention mainly over-refuses rather than reducing genuinely unsafe outputs.

## EXP03 - Instruction Diversity and Linguistic Generalisation in VLA Models

**Thesis:** linguistic diversity in trajectory annotations is a binding constraint for VLA instruction generalisation; synthetic instruction variants can improve paraphrase robustness and cross-embodiment transfer without new robot data collection.

**Research questions:** how do variants per trajectory affect task success; where do returns saturate; does improvement transfer to an unseen embodiment?

**Hypotheses:** paraphrase robustness rises and saturates near five variants per trajectory; exact-task success stays roughly flat; cross-embodiment transfer improves.

**Datasets and tools:** Open X-Embodiment, Bridge V2, LIBERO, OpenVLA-7B, OpenVLA-OFT.

**First gate:** environment readiness. Install LIBERO/OpenVLA-OFT, load one Bridge/OXE subset, and run one official evaluation smoke before any LoRA sweep.

**Promotion gate:** 0/1/5/10 variant sweep with three seeds, confidence intervals, held-out instruction templates, and one held-out embodiment.

**Stop rule:** stop if the simulation/evaluation stack cannot reproduce baseline success within tolerance before augmentation.

## EXP04 - Multi-Turn Hallucination Compounding and KG-Grounded Verification

**Thesis:** hallucination compounds across conversational turns when later turns reference prior answers; a knowledge-graph-grounded verifier can measure and reduce this compounding more faithfully than single-turn checks.

**Research questions:** how does hallucination rate change with turn depth; does KG verification beat LLM-judge/NLI baselines; does verifier-in-the-loop correction reduce downstream hallucination?

**Hypotheses:** hallucination rate rises monotonically with depth on reference-carrying turns; KG verifier has higher detection F1; correction reduces hallucination at modest helpfulness cost.

**Datasets and tools:** HaluEval, HaluEval 2.0, HotpotQA, Natural Questions, FaithEval, Wikidata.

**First gate:** build 20 multi-turn dialogues and a claim-extraction/verification schema; verify that Wikidata entity linking and SPARQL evidence are usable on at least 80% of atomic claims in the smoke set.

**Promotion gate:** domain-holdout verifier evaluation with human-calibrated labels and bootstrap confidence intervals for per-turn hallucination slopes.

**Stop rule:** stop or reframe if entity linking leaves too many claims unverifiable, target unverifiable rate `>40%` on the smoke.

## EXP05 - Cross-Paradigm Visual Robustness of World-Model Agents

**Thesis:** world-model agent robustness to visual distribution shift depends on representation paradigm; a controlled platform can produce a robustness leaderboard and test an augmentation remedy.

**Research questions:** how much does each paradigm degrade under perturbation; which paradigm is most robust; can observation augmentation close the gap?

**Hypotheses:** diffusion world models retain more score under fine-grained perturbations; robustness relates to compression ratio; training-time observation augmentation improves retention with minimal clean-score cost.

**Datasets and tools:** Atari 100K, Crafter/Craftax, ProcGen, DeepMind Control, stable-worldmodel.

**First gate:** install stable-worldmodel and run one Crafter agent evaluation under clean frames plus one perturbation wrapper.

**Promotion gate:** at least five seeds, interquartile mean and bootstrap confidence intervals, held-out perturbation type, and clean-score convergence checks.

**Stop rule:** stop if clean baseline scores cannot be reproduced within tolerance or visual wrappers change environment semantics rather than perception only.

## Shared Gating Rules

| Gate | Requirement |
|---|---|
| G0 - source integrity | Preserve the DOCX source and extracted text; do not treat illustrative expected-results tables as measured results. |
| G1 - smoke harness | Each experiment must first produce a small, reproducible smoke artifact with logs and a pass/fail decision. |
| G2 - validation discipline | Dev/tuning data must be separate from final test data; seed grid and thresholds must be fixed before formal evaluation. |
| G3 - holdout | Each experiment needs a strict holdout: model family, harm category, robot embodiment, factual domain, or perturbation type. |
| G4 - confidence | Report bootstrap confidence intervals or distributional RL metrics; no single-run headline claims. |
| G5 - claim boundary | Every result must state what it does not show. |

## Immediate File Map

| Artifact | Purpose |
|---|---|
| `tmp/docs/AI_ML_Praxis_Experiment_Templates_extracted.md` | Extracted text from the attached DOCX source. |
| `configs/frontier_ai_ml_experiment_registry_20260618.json` | Machine-readable registry for the five new experiments. |
| `configs/frontier_exp01_ttc_smoke_20260618.json` | Starter config for the first EXP01 smoke run. |
| `configs/frontier_exp01_ttc_full_20260618.json` | Full preliminary AWS config for four open 7B-class models, GSM8K/MATH-500 rows, and `K={1,2,4,8}`. |
| `cloud_jobs/frontier_exp01_ttc_transfer_20260618/` | AWS runner, requirements, and instance launch handoff for EXP01. |
| `reports/frontier_ai_ml_experiments_20260618/FRONTIER_AI_ML_EXPERIMENT_DASHBOARD_20260618.md` | Markdown dashboard and start-state source. |
| `reports/frontier_ai_ml_experiments_20260618/FRONTIER_AI_ML_EXPERIMENT_DASHBOARD_20260618.html` | Browser dashboard generated from the Markdown source. |
| `reports/frontier_ai_ml_experiments_20260618/PRAXIS_EXP01_TTC_TRANSFER_PROTOCOL_20260618.md` | Formal Praxis protocol for EXP01 with RQ/H, literature review, GMR, splits, feature engineering, Optuna discipline, and results gates. |
| `reports/frontier_ai_ml_experiments_20260618/EXP01_TTC_TRANSFER_KICKOFF_20260618.md` | First-experiment kickoff protocol and readiness checklist. |
| `runs/frontier-exp01-ttc-transfer-smoke-20260618/README.md` | Empty run folder handoff for the first smoke run outputs. |
| `runs/frontier-exp01-ttc-transfer-full-20260618/EXP01_FULL_AWS_RESULT_20260618.md` | Full preliminary AWS result with selected policies, accuracy table, transfer matrix, and predictor outcome. |
| `runs/frontier-exp01-ttc-transfer-full-20260618/EXP01_INTERNAL_DEFENSIBILITY_CHALLENGE_20260618.md` | Internal defense challenge and promotion blockers. |
| `reports/frontier_ai_ml_experiments_20260618/EXP01_FULL_RESULT_SYNTHESIS_20260618.md` | Compact Praxis-style synthesis of RQ/H readout, key results, and promotion blockers. |
| `scripts/run_frontier_exp01_ttc_split_gate.py` | Standard-library preliminary split-readiness gate for EXP01. |

## Ready-To-Start Checklist

| Item | Status | Note |
|---|---|---|
| Source DOCX extracted | PASS | 245 paragraphs and 73 table rows extracted. |
| Experiment queue created | PASS | Five experiments ordered by feasibility and impact. |
| First experiment selected | PASS | EXP01 TTC transferability. |
| EXP01 Praxis protocol created | PASS | `reports/frontier_ai_ml_experiments_20260618/PRAXIS_EXP01_TTC_TRANSFER_PROTOCOL_20260618.md`. |
| EXP01 preliminary split gate | PASS | `runs/frontier-exp01-ttc-transfer-smoke-20260618/PRELIMINARY_SPLIT_READINESS_20260618.md`. |
| EXP01 full AWS run | PASS / PROVISIONAL | `runs/frontier-exp01-ttc-transfer-full-20260618/EXP01_FULL_AWS_RESULT_20260618.md`. |
| EXP01 internal defensibility challenge | PASS / DO NOT OVERCLAIM | `runs/frontier-exp01-ttc-transfer-full-20260618/EXP01_INTERNAL_DEFENSIBILITY_CHALLENGE_20260618.md`. |
| AWS profile available | PASS | Use `--profile praxis-build` when cloud compute is needed. |
| GitHub connection available | PASS | Previous smoke confirmed push capability. |
| First action defined | COMPLETE | Build and run preliminary EXP01 harness on AWS. |
| EXP01 starter config created | PASS | `configs/frontier_exp01_ttc_smoke_20260618.json`. |
| EXP01 run folder created | PASS | `runs/frontier-exp01-ttc-transfer-smoke-20260618/`. |

## EXP01 Preliminary Split Result

| Item | Value |
|---|---:|
| GSM8K total rows visible through Dataset Viewer | `1,319` |
| MATH-500 total rows visible through Dataset Viewer | `500` |
| Smoke rows sampled | `50` |
| Validation-policy rows | `12` |
| In-domain test rows | `13` |
| Strict MATH-500 holdout rows | `25` |
| Model calls made | `0` |

This is a readiness result, not a model-performance result. The next defensible result must come from frozen JSONL generation logs, scoring logs, and a retention table.

## EXP01 Full Preliminary AWS Result

| Item | Value |
|---|---:|
| Open models evaluated | `4` |
| Public benchmark rows | `160` |
| Score rows | `2,560` |
| Transfer rows | `32` |
| Strict holdout rows | `80` |
| Best Qwen2.5-7B validation policy | `majority_vote K=8` |
| Qwen2.5-7B validation accuracy | `0.8250` |
| Qwen2.5-7B in-domain test accuracy | `0.7250` |
| Qwen2.5-7B strict MATH-500 holdout accuracy | `0.2250` |
| Mean off-diagonal retention, in-domain | `1.5920` |
| Mean off-diagonal retention, strict holdout | `1.3111` |
| Predictor status | `COMPLETE` |
| Leave-one-target-family predictor R2 | `-14.9408` |
| Defense verdict | `PROVISIONAL / DO NOT OVERCLAIM` |

The AWS run produced results, but the claim boundary is narrow. The defensible statement is that the current harness can measure cross-model TTC policy transfer under strict split discipline. It does not yet prove that TTC strategies are transferable in a strong general sense, because verifier-based best-of-N and sequential refinement remain untested, exact-answer scoring needs audit, and the transfer predictor failed to generalize across held-out target families.

## Next Action

Continue EXP01 with a promotion gate, not another rescue run:

1. Add a verifier/scorer best-of-N arm for H1 using the same frozen split discipline.
2. Add sequential self-refinement or formally drop H3 from the EXP01 claim.
3. Manually audit a random sample of exact-answer scoring and report agreement.
4. Add bootstrap confidence intervals for accuracy and retention.
5. Convert the result into a short Praxis section only after the promotion gate clarifies whether this is a positive transferability result, a negative predictor result, or a methods artifact.
