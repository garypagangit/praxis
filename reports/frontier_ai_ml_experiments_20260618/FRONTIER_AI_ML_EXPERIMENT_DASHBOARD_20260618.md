# Frontier AI/ML Experiment Dashboard

Updated: 2026-06-21

Source brief: `C:\Users\garyp\Downloads\AI_ML_Praxis_Experiment_Templates.docx`.

Purpose: convert the attached block of five 2026 AI/ML experiment templates into a gated Praxis workstream and close the batch with explicit final determinations. EXP01 has a full preliminary AWS result but is not being promoted. EXP02 has a schema pass plus two AWS guardrail gates; it produced a strong response-prefix signal but is not being promoted because utility controls fail. EXP03 is stopped/reframed because the public LIBERO path lacks language metadata and local simulator/model imports. EXP04 has a controlled KG positive but failed external verifier promotion. EXP05 now has an executable Crafter environment smoke but not a learned world-model result.

Open-first final batch decision: `reports/frontier_ai_ml_experiments_20260618/FRONTIER_FINAL_DETERMINATION_20260621.md`.

## Start Decision

We have completed the first full preliminary AWS run for **Experiment 01 - Cross-Model Transferability of Test-Time Compute Strategies**.

Current status: **EXP01 preliminary full-run result present, provisional / do not overclaim**. The split-readiness gate passed, then the AWS run evaluated `4` open 7B-class models across `160` public benchmark rows, `2` strategy classes, and budgets `K={1,2,4,8}`. Policy selection used GSM8K validation-policy rows only; final checks used a GSM8K in-domain test split plus a strict MATH-500 holdout that was not used for policy selection.

Current batch completed: **all five frontier experiments have final current-cycle determinations**. No experiment in this batch is promoted as a new publishable positive thesis result. The batch is preserved as a defensible audit trail of provisional, mixed, stopped, or environment-only results.

What the first run shows:

- The transfer matrix is complete for the configured model set: `32` rows.
- Best selected validation policy for `qwen2p5_7b_instruct` was majority vote `K=8`, with validation accuracy `0.8250`, in-domain test accuracy `0.7250`, and strict MATH-500 holdout accuracy `0.2250`.
- Other model-family results were much weaker under exact scoring: Qwen2.5-Math-7B selected majority vote `K=8` with strict holdout `0.0625`; DeepSeek-R1-Distill-Qwen-7B selected majority vote `K=8` with strict holdout `0.0000`; Mistral-7B selected single-sample `K=1` with strict holdout `0.0375`.
- Off-diagonal retention is measurable but not yet a clean scientific win: mean off-diagonal retention was `1.5920` in-domain and `1.3111` on strict holdout among non-null rows.
- The feature-engineered Optuna predictor completed but did not generalize: leave-one-target-family R2 `-14.9408`.
- Internal defense verdict: preliminary evidence suitable for a slide or committee update, not yet a Praxis-level claim. H1 still needs verifier/scorer best-of-N, and H3 still needs sequential refinement or a formal drop.
- EXP02 schema handling passed, and two AWS guardrail gates completed. The open guardian response-prefix run caught `38/38` unsafe held-out responses with average caught exposure `0.1310`, but blocked `12/66` safe responses and over-refused `87/100` benign prompt controls. Decision: preserve as a strong pilot, not a publication-ready thesis proof.
- EXP04 controlled KG smoke passed: `20` dialogues, `60` atomic claims, strict holdout `36` claims, KG evidence coverage `1.0000`, KG hallucination F1 `1.0000`, and turn-3 minus turn-1 hallucination rate `0.2500`. The AWS HaluEval NLI gate was mixed. The final HaluEval dialogue feature gate failed promotion: evidence+numeric strict holdout F1 `0.7215`, response-only F1 `0.7835`.
- EXP03 source/readiness gate passed, but the final LIBERO data gate stopped the claim: public `lerobot/libero_10` has `101,469` frames and `379` episodes, but no language/instruction columns and no task text metadata; local required imports were `0/5`.
- EXP05 source/wrapper gate passed, and the Crafter environment gate completed `25` clean/dev/held-out perturbation episodes. The thesis is not promoted because the agent was a deterministic observation-checksum policy, not a learned world-model, and no multi-paradigm or augmentation test ran.

## Experiment Queue

| Priority | Experiment | Working title | Field area | Current posture | First gate | Main output |
|---:|---|---|---|---|---|---|
| 1 | EXP01 | Cross-Model Transferability of Test-Time Compute Strategies | Reasoning / inference efficiency | Preliminary full AWS result present; provisional | Add verifier best-of-N, sequential refinement or drop H3, and manual scoring audit | Transfer matrix, retention metric, negative predictor result, defense challenge |
| 2 | EXP02 | Step-Level Self-Jailbreak Detection and Training-Free Intervention | Reasoning-model safety | Schema PASS plus two AWS gates complete; response-prefix signal present, utility gate failed | Continue only with refusal-aware classifier/manual boundary labels, or move queue forward | Redacted guardrail pilot, open guardian early-detection result, over-refusal blocker |
| 3 | EXP04 | Multi-Turn Hallucination Compounding and KG-Grounded Verification | Factuality / reliability | Final failed promotion; response artifacts beat evidence features | Stop rescue runs for this cycle | Controlled KG positive plus external verifier failure |
| 4 | EXP03 | Instruction Diversity and Linguistic Generalisation in VLA Models | Embodied AI / robot foundation models | Final stop/reframe; public data lacks language metadata | Reopen only with instruction metadata and official simulator stack | LIBERO data/schema blocker |
| 5 | EXP05 | Cross-Paradigm Visual Robustness of World-Model Agents | World models / model-based RL | Environment smoke PASS; thesis not promoted | Reopen only with trained world-model baseline | Crafter clean/perturbed rollout smoke |

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

**Completed gates:** safety schema gate PASS on 2026-06-18. The gate produced a `100`-row redacted manifest from accessible public source/splits, with `65` unsafe-request rows, `35` benign-control rows, `30` strict behavior holdout rows, `30` benign-control holdout rows, `12` abstract trace-schema examples, `0` raw prompt text committed, and `0` model calls. The full AWS lightweight detector gate and the open Granite Guardian step gate then ran on AWS with redacted outputs only.

**AWS result:** lightweight detector failed promotion with prompt harmful recall `0.7400`, benign false-refusal `0.6900`, response-step recall `0.8158`, and safe-response block `0.1818`. The open guardian improved the response-prefix mechanism: prompt harmful recall `1.0000`, response-step unsafe recall `1.0000`, caught-unsafe exposure `0.1310`, and exposure reduction `0.8690`; however, prompt benign false-refusal was `0.8700` and safe-response block remained `0.1818`.

**Promotion gate:** category-holdout detector performance with ROC-AUC/PR-AUC confidence intervals plus false-refusal rate on benign twins. Current decision: not promoted until safe-response over-blocking is solved.

**Stop rule:** stop if override labels have poor human/judge agreement, target Cohen kappa `<0.60`, or if the intervention mainly over-refuses rather than reducing genuinely unsafe outputs.

**Protocol:** `reports/frontier_ai_ml_experiments_20260618/PRAXIS_EXP02_SELF_JAILBREAK_PROTOCOL_20260618.md`.

**Kickoff doc:** `reports/frontier_ai_ml_experiments_20260618/EXP02_SELF_JAILBREAK_KICKOFF_20260618.md`.

## EXP03 - Instruction Diversity and Linguistic Generalisation in VLA Models

**Thesis:** linguistic diversity in trajectory annotations is a binding constraint for VLA instruction generalisation; synthetic instruction variants can improve paraphrase robustness and cross-embodiment transfer without new robot data collection.

**Research questions:** how do variants per trajectory affect task success; where do returns saturate; does improvement transfer to an unseen embodiment?

**Hypotheses:** paraphrase robustness rises and saturates near five variants per trajectory; exact-task success stays roughly flat; cross-embodiment transfer improves.

**Datasets and tools:** Open X-Embodiment, Bridge V2, LIBERO, OpenVLA-7B, OpenVLA-OFT.

**First gate:** environment readiness. Install LIBERO/OpenVLA-OFT, load one Bridge/OXE subset, and run one official evaluation smoke before any LoRA sweep.

**Completed gates:** source/readiness gate PASS on 2026-06-19. The gate verified `4` GitHub repositories, `5` HF model checkpoints, and one public Dataset Viewer path: `lerobot/libero_10`. The final LIBERO data/simulator gate on 2026-06-21 stopped the current thesis path: public `lerobot/libero_10` has `101,469` frames, `379` episodes, and `10` task indices, but the available schema exposes only `observation.state`, `action`, `timestamp`, `frame_index`, `episode_index`, `index`, and `task_index`. There are no natural-language instruction columns or task text metadata, and required local imports `libero`, `robosuite`, `torch`, `transformers`, and `gymnasium` are unavailable.

**Final determination:** stop/reframe for this cycle. The public data supports data-loader work, not instruction-diversity VLA evaluation.

**Stop rule:** stop if the simulation/evaluation stack cannot reproduce baseline success within tolerance before augmentation.

## EXP04 - Multi-Turn Hallucination Compounding and KG-Grounded Verification

**Thesis:** hallucination compounds across conversational turns when later turns reference prior answers; a knowledge-graph-grounded verifier can measure and reduce this compounding more faithfully than single-turn checks.

**Research questions:** how does hallucination rate change with turn depth; does KG verification beat LLM-judge/NLI baselines; does verifier-in-the-loop correction reduce downstream hallucination?

**Hypotheses:** hallucination rate rises monotonically with depth on reference-carrying turns; KG verifier has higher detection F1; correction reduces hallucination at modest helpfulness cost.

**Datasets and tools:** HaluEval, HaluEval 2.0, HotpotQA, Natural Questions, FaithEval, Wikidata.

**First gate:** build 20 multi-turn dialogues and a claim-extraction/verification schema; verify that Wikidata entity linking and SPARQL evidence are usable on at least 80% of atomic claims in the smoke set.

**Completed gates:** controlled KG smoke PASS on 2026-06-19. It produced `20` dialogues and `60` atomic claims, with strict holdout `36` claims, KG evidence coverage `1.0000`, KG hallucination F1 `1.0000`, and turn-3 minus turn-1 hallucination rate `0.2500`. Wikidata SPARQL was under public rate-limit, so the gate used batched Wikidata entity API evidence as the KG backend. The AWS HaluEval NLI gate then ran on `roberta-large-mnli`, tuning on HaluEval QA and evaluating on HaluEval dialogue strict holdout. It was mixed: F1 `0.6878` CI `[0.6461, 0.7332]`, accuracy `0.5575`, lexical baseline F1 `0.6723`, delta `+0.0156`. The final HaluEval dialogue feature gate trained row-disjoint response/evidence/numeric baselines on `12,118` train examples, selected thresholds on `2,990` validation examples, tested on `2,970` examples, and evaluated `1,922` strict-holdout examples. Evidence+numeric F1 was `0.7215`, but response-only F1 was `0.7835`.

**Final determination:** do not promote as a positive. The current evidence-aware verifier loses to response artifacts on a sealed HaluEval holdout.

**Stop rule:** stop or reframe if entity linking leaves too many claims unverifiable, target unverifiable rate `>40%` on the smoke.

## EXP05 - Cross-Paradigm Visual Robustness of World-Model Agents

**Thesis:** world-model agent robustness to visual distribution shift depends on representation paradigm; a controlled platform can produce a robustness leaderboard and test an augmentation remedy.

**Research questions:** how much does each paradigm degrade under perturbation; which paradigm is most robust; can observation augmentation close the gap?

**Hypotheses:** diffusion world models retain more score under fine-grained perturbations; robustness relates to compression ratio; training-time observation augmentation improves retention with minimal clean-score cost.

**Datasets and tools:** Atari 100K, Crafter/Craftax, ProcGen, DeepMind Control, stable-worldmodel.

**First gate:** install stable-worldmodel and run one Crafter agent evaluation under clean frames plus one perturbation wrapper.

**Completed gates:** source/wrapper gate PASS on 2026-06-19. It verified `4` repositories (`stable-worldmodel`, `crafter`, `craftax`, `dreamerv3`), `2` PyPI packages (`crafter`, `craftax`), and `4` frozen visual perturbation wrappers. Both held-out perturbations are explicit (`center_occlusion`, `salt_pepper`), all wrappers preserved `64x64x3` observation shape, and minimum mean absolute pixel delta was `0.0193`. The final Crafter rollout gate on 2026-06-21 completed `25` episodes across clean, dev perturbations, and held-out perturbations using a deterministic observation-checksum policy. Clean mean reward was `1.5000`; held-out `center_occlusion` mean reward was `2.7000`; held-out `salt_pepper` mean reward was `1.7000`.

**Final determination:** environment path passes, but the world-model thesis is not promoted. The run did not evaluate a learned world-model agent, multiple paradigms, or augmentation.

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
| `configs/frontier_exp02_self_jailbreak_schema_20260618.json` | EXP02 safety schema gate config. |
| `scripts/run_frontier_exp02_safety_schema_gate.py` | EXP02 metadata/redaction/schema gate runner. |
| `reports/frontier_ai_ml_experiments_20260618/PRAXIS_EXP02_SELF_JAILBREAK_PROTOCOL_20260618.md` | Formal Praxis protocol for EXP02 with RQ/H, lit review, GMR, splits, feature plan, and results gates. |
| `reports/frontier_ai_ml_experiments_20260618/EXP02_SELF_JAILBREAK_KICKOFF_20260618.md` | EXP02 kickoff and next trace-pilot plan. |
| `reports/frontier_ai_ml_experiments_20260618/EXP02_SCHEMA_GATE_SYNTHESIS_20260618.md` | Positive readiness synthesis for EXP02. |
| `runs/frontier-exp02-self-jailbreak-schema-20260618/EXP02_SCHEMA_GATE_RESULT_20260618.md` | EXP02 first-gate PASS report. |
| `configs/frontier_exp02_self_jailbreak_full_20260618.json` | Full lightweight EXP02 guardrail config. |
| `scripts/run_frontier_exp02_full_guardrail_experiment.py` | Full lightweight EXP02 prompt/response-step detector runner. |
| `cloud_jobs/frontier_exp02_self_jailbreak_20260618/` | AWS handoff for the lightweight full EXP02 gate. |
| `runs/frontier-exp02-self-jailbreak-full-20260618/EXP02_FULL_GUARDRAIL_RESULT_20260618.md` | Lightweight detector AWS result; mixed, not promoted. |
| `configs/frontier_exp02_guardian_step_20260618.json` | Open guardian response-prefix gate config. |
| `scripts/run_frontier_exp02_guardian_step_gate.py` | Granite Guardian prompt/response-prefix runner. |
| `cloud_jobs/frontier_exp02_guardian_step_20260618/` | AWS handoff for the open guardian step gate. |
| `runs/frontier-exp02-self-jailbreak-guardian-step-20260618/EXP02_GUARDIAN_STEP_RESULT_20260618.md` | Open guardian AWS result; strong early-detection signal, utility gate failed. |
| `reports/frontier_ai_ml_experiments_20260618/EXP02_FULL_GUARDRAIL_SYNTHESIS_20260618.md` | Combined EXP02 synthesis, RQ/H readout, and promotion decision. |
| `configs/frontier_exp04_kg_hallucination_smoke_20260619.json` | EXP04 controlled KG smoke gate config. |
| `scripts/run_frontier_exp04_kg_smoke_gate.py` | EXP04 controlled multi-turn KG verifier smoke runner. |
| `reports/frontier_ai_ml_experiments_20260618/PRAXIS_EXP04_KG_HALLUCINATION_PROTOCOL_20260619.md` | Formal Praxis protocol for EXP04. |
| `runs/frontier-exp04-kg-hallucination-smoke-20260619/EXP04_KG_SMOKE_GATE_RESULT_20260619.md` | EXP04 controlled KG smoke PASS report. |
| `configs/frontier_exp04_halueval_nli_full_20260619.json` | EXP04 dataset-backed HaluEval NLI gate config. |
| `scripts/run_frontier_exp04_halueval_nli_gate.py` | EXP04 HaluEval NLI strict-holdout verifier runner. |
| `cloud_jobs/frontier_exp04_halueval_nli_20260619/` | AWS handoff for the EXP04 HaluEval NLI gate. |
| `runs/frontier-exp04-halueval-nli-full-20260619/EXP04_HALUEVAL_NLI_GATE_RESULT_20260619.md` | AWS HaluEval NLI mixed result. |
| `configs/frontier_exp03_vla_source_gate_20260619.json` | EXP03 VLA source/readiness gate config. |
| `scripts/run_frontier_exp03_vla_source_gate.py` | EXP03 source and instruction-template manifest runner. |
| `reports/frontier_ai_ml_experiments_20260618/PRAXIS_EXP03_VLA_INSTRUCTION_DIVERSITY_PROTOCOL_20260619.md` | Formal Praxis protocol for EXP03. |
| `runs/frontier-exp03-vla-source-gate-20260619/EXP03_VLA_SOURCE_GATE_RESULT_20260619.md` | EXP03 source/readiness PASS report. |
| `configs/frontier_exp05_worldmodel_source_gate_20260619.json` | EXP05 source/wrapper gate config. |
| `scripts/run_frontier_exp05_worldmodel_source_gate.py` | EXP05 source and visual-perturbation wrapper runner. |
| `reports/frontier_ai_ml_experiments_20260618/PRAXIS_EXP05_WORLDMODEL_VISUAL_ROBUSTNESS_PROTOCOL_20260619.md` | Formal Praxis protocol for EXP05. |
| `runs/frontier-exp05-worldmodel-source-gate-20260619/EXP05_WORLDMODEL_SOURCE_GATE_RESULT_20260619.md` | EXP05 source/wrapper PASS report. |

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
| EXP02 Praxis protocol created | PASS | `reports/frontier_ai_ml_experiments_20260618/PRAXIS_EXP02_SELF_JAILBREAK_PROTOCOL_20260618.md`. |
| EXP02 safety schema gate | PASS | `runs/frontier-exp02-self-jailbreak-schema-20260618/EXP02_SCHEMA_GATE_RESULT_20260618.md`. |
| EXP02 raw unsafe text committed | PASS | `0` raw prompt/model-output text fields committed; manifest is hash/length/schema only. |
| EXP02 lightweight AWS guardrail gate | COMPLETE / MIXED | Response-step signal exists but prompt and safe-response utility checks fail. |
| EXP02 open guardian AWS gate | COMPLETE / MIXED | Response-step recall `1.0000` and exposure `0.1310`, but safe-response block `0.1818`. |
| EXP04 controlled KG smoke | PASS | `runs/frontier-exp04-kg-hallucination-smoke-20260619/EXP04_KG_SMOKE_GATE_RESULT_20260619.md`. |
| EXP04 AWS HaluEval NLI gate | COMPLETE / MIXED | Strict dialogue holdout F1 `0.6878`; not promoted. |
| EXP03 source/readiness gate | PASS / SIM PENDING | Source and instruction-template split ready; no simulator run yet. |
| EXP05 source/wrapper gate | PASS / AGENT PENDING | Source and perturbation wrappers ready; no agent rollout yet. |

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

## EXP02 Positive Readiness Result

| Item | Value |
|---|---:|
| Gate status | `PASS` |
| Accessible source/splits | `3` |
| Redacted manifest rows | `100` |
| Unsafe request rows | `65` |
| Benign control rows | `35` |
| Strict behavior holdout rows | `30` |
| Benign control holdout rows | `30` |
| Synthetic abstract trace examples | `12` |
| Raw prompt text committed | `0` |
| Model calls made | `0` |

This is a positive readiness result. It proves EXP02 can proceed safely with strict holdout roles, benign controls, a trace-label taxonomy, and intervention actions. It does not yet prove detector or intervention effectiveness.

## EXP02 AWS Guardrail Results

| Item | Lightweight detector | Open guardian step judge |
|---|---:|---:|
| Prompt harmful recall | `0.7400` | `1.0000` |
| Prompt benign false-refusal | `0.6900` | `0.8700` |
| Response-step unsafe recall | `0.8158` | `1.0000` |
| Safe-response block rate | `0.1818` | `0.1818` |
| Caught unsafe exposure fraction | `0.2370` | `0.1310` |
| Exposure reduction vs output-only | `0.7630` | `0.8690` |
| Promotion decision | Mixed / not promoted | Mixed / not promoted |

The useful signal is real: open guardian response-prefix monitoring caught all unsafe held-out responses very early. The thesis is not proven because both prompt-level and response-level utility controls over-block safe/benign examples. Preserve this as a strong pilot and continue EXP02 only if the next gate directly targets refusal-aware safe-response preservation.

## EXP04 Results

| Item | Controlled KG smoke | AWS HaluEval NLI gate | HaluEval dialogue feature gate |
|---|---:|---:|---:|
| Status | PASS | MIXED | FAILED PROMOTION |
| Rows | `60` atomic claims | `400` strict holdout examples | `1,922` strict holdout examples |
| Strict holdout | `36` claims | HaluEval dialogue | Row-disjoint HaluEval dialogue |
| Main F1 | `1.0000` | `0.6878` | `0.7215` evidence+numeric |
| Baseline F1 | `0.0000` always-supported | `0.6723` lexical | `0.7835` response-only |
| Delta | `+1.0000` | `+0.0156` | `-0.0620` vs response-only |
| Main limitation | Controlled templates | Weak external-holdout lift | Evidence features lose to artifacts |

EXP04 is closed for this cycle. The controlled KG measurement works, but the external HaluEval verifier is not strong enough for a positive publication claim.

## EXP03 Final Data Gate

| Item | Value |
|---|---:|
| Accessible GitHub repositories | `4` |
| Accessible HF models | `5` |
| Public HF datasets | `1` |
| Instruction manifest rows | `48` |
| Held-out template rows | `16` |
| Mean heldout/base token Jaccard | `0.6264` |
| Public LIBERO frames | `101,469` |
| Public LIBERO episodes | `379` |
| Public LIBERO task indices | `10` |
| Language columns in public data | `0` |
| Task text metadata columns | `0` |
| Required local simulator/model imports | `0/5` |

EXP03 is stopped/reframed for this cycle. The public data is real, but it is not sufficient to test instruction-diversity VLA generalisation.

## EXP05 Final Rollout Gate

| Item | Value |
|---|---:|
| Accessible repositories | `4` |
| Accessible PyPI packages | `2` |
| Perturbation wrappers | `4` |
| Held-out perturbations | `2` |
| Shape failures | `0` |
| Minimum mean absolute pixel delta | `0.0193` |
| Crafter episodes completed | `25` |
| Clean mean reward | `1.5000` |
| Held-out center occlusion reward | `2.7000` |
| Held-out salt-pepper reward | `1.7000` |
| Learned world-model agent | `False` |
| Multiple paradigms | `False` |

EXP05 has an executable environment smoke but remains parked as a thesis claim. The measured agent is a deterministic observation-checksum policy, not a learned world-model.

## Next Action

Recommended decision:

1. Close this frontier batch for the current cycle.
2. Do not start more rescue runs on EXP03-EXP05 unless new external assets are added: instruction metadata and simulator stack for EXP03, a learned world-model baseline for EXP05, or a stronger evidence mechanism for EXP04.
3. Preserve EXP01-EXP05 as a defensible experiment audit trail and negative/control evidence.
4. Return publication effort to the stronger Praxis 06 TTA and Praxis 07 CTI-compliance packages.
