# Extracted Text: AI_ML_Praxis_Experiment_Templates.docx

AI/ML Praxis

Experiment Templates

Five experiment-ready research designs for the 2026 AI frontier

Each template includes: thesis, research questions, hypotheses, experimental design (Goal / Method / Rationale), dataset details with download locations and usage terms, data structure, setup steps, expected metrics, a literature review with APA references, anticipated results tables, and a reproduction-and-proof protocol.

Prepared June 2026   ·   5 experiments   ·   grounded in live-retrieved literature

How to use this document

These are not summaries — they are build-ready experiment plans. Run them top to bottom: Experiment 1 (test-time compute) and Experiment 2 (reasoning safety) are the strongest combination of field relevance and feasibility; Experiments 3 to 5 broaden into embodied AI, factuality, and world models. Every design is scoped to be reproducible on one to two GPUs and uses openly downloadable data.

A NOTE ON THE GMR BLOCK

Each experiment's design is written as Goal / Method / Rationale (GMR): what the experiment must establish, how it will be run, and why the contribution is defensible and durable rather than a transient leaderboard bump.

A NOTE ON THE PROOF PROTOCOL

Every experiment closes with four scientific-rigour components used consistently throughout: model verification via optima (selecting and verifying compute-optimal or threshold-optimal configurations, with bootstrap confidence intervals); feature analysis (ablations and probing to explain why a result holds, not just that it holds); strict hold-out (withholding whole categories, families, embodiments, domains, or perturbation types so generalisation is tested honestly); and validation-data discipline (disjoint dev / validation / test splits, fixed seeds, judge calibration against human annotation where relevant).

BEFORE FORMAL SUBMISSION

A small number of very recent preprints are cited by title where a stable author list was not yet available at retrieval time; confirm authorship and venue against the source listing before formal write-up. All expected-results tables contain illustrative target values that state the predicted direction and rough magnitude — they are hypotheses about outcomes, not measured results.

Experiment 1 — Cross-Model Transferability of Test-Time Compute Strategies

Field area:  Reasoning / Inference Efficiency

Why it stays relevant:  Test-time compute is the dominant performance lever of 2026. A transferability map is cheap, inference-only, and central to how every lab allocates inference budget.

Thesis

Test-time compute (TTC) scaling strategies are widely treated as model-agnostic, but their effectiveness is likely model-specific. This work characterises whether compute-optimal TTC policies discovered on one model family transfer to other families and scales, producing a transferability map plus a lightweight predictor of strategy degradation on unseen models.

Research questions

RQ1: Do compute-optimal TTC strategies (best-of-N, majority voting / self-consistency, sequential self-refinement, and budget allocation between policy and verifier) discovered on one model family retain effectiveness when transferred zero-shot to a different family or scale?

RQ2: Which class of TTC strategy is most transferable across models, and which is most model-specific?

RQ3: Can a lightweight predictor forecast a strategy's accuracy degradation on an unseen target model from cheap signals (base accuracy, output-distribution entropy, model scale)?

Hypotheses

H1: Verifier-based strategies (best-of-N with a reward or process model) transfer more robustly than verifier-free strategies (majority voting), because they depend less on the shape of the base model's answer distribution.

H2: Transfer degradation correlates with the divergence in base-model answer-distribution anti-concentration (entropy) between source and target.

H3: Sequential self-refinement strategies transfer worse than parallel strategies, because they hinge on model-specific instruction-following behaviour.

Experimental design (Goal / Method / Rationale)

Goal.  Quantify cross-model transferability of TTC strategies on reasoning benchmarks and fit a transfer-degradation predictor.

Method.  For each source model, sweep inference compute across four TTC strategy classes; identify the compute-optimal configuration per (model, budget); apply each source-optimal configuration zero-shot to every target model; measure accuracy retention. Fit a regression predicting retention from cheap model signals.

Rationale.  Snell et al. (2024) and Son et al. (2025) show TTC effectiveness varies by model and language, but no systematic cross-model transfer matrix with a predictive model exists. The artefact (a transfer matrix + predictor) retains value even as specific models age.

Datasets — download locations and usage

<!-- TABLE START -->
| Dataset | What it is | Download location | Usage / license |
| MATH | 12,500 competition math problems w/ step solutions | HuggingFace: hendrycks/competition_math | Open (MIT-style); free download |
| GSM8K | 8,500 grade-school word problems | HuggingFace: openai/gsm8k | Open (MIT) |
| MATH-500 | 500-problem evaluation subset of MATH | HuggingFace: HuggingFaceH4/MATH-500 | Open |
| AIME 2024/25 | Olympiad problems; OOD difficulty probe | HuggingFace / public archives | Open |
| HumanEval | 164 code problems; cross-domain check | HuggingFace: openai_humaneval | Open (MIT) |
<!-- TABLE END -->

Data structure

Each benchmark item is {problem_id, problem_text, gold_answer, (MATH only) reference_solution}. During TTC you generate K candidate solutions per item and log a sampling record: {problem_id, model, strategy, budget_K, samples[], selected_answer, is_correct, tokens_used}. The unit of analysis for transfer is the (source_model, target_model, strategy, budget) cell.

Experiment setup steps

Install an inference server (vLLM) and load open models spanning families and scales: Qwen2.5-Instruct (7B/14B/32B), Llama-3.1 (8B/70B), DeepSeek-R1-Distill-Qwen (7B/14B).

Implement four strategy classes: (a) best-of-N with an open process reward model (e.g., Qwen2.5-Math-PRM), (b) majority voting / self-consistency, (c) sequential self-refinement, (d) policy↔verifier budget allocation.

Sweep compute budget K in {1,2,4,8,16,32,64,128} for every (model, strategy) pair on the dev split.

Select the compute-optimal configuration per (model, budget) cell by dev accuracy, recording the FLOP / token cost.

Cross-apply: run each source-optimal configuration zero-shot on every target model's test split. Compute retention = target_acc(source-optimal) / target_acc(target-optimal).

Fit a predictor (regularised regression / gradient boosting) mapping cheap signals (base accuracy, sampling entropy, model size) to retention; evaluate with held-out model families.

Estimated metrics

Coverage (probability of at least one correct sample) should rise roughly log-linearly with K, replicating Brown et al. (2024). Retention ratios are expected ~0.70-0.95 for verifier-based transfer and ~0.50-0.80 for majority voting, with sequential refinement lowest. Predictor target: R-squared > 0.6 on held-out families.

Literature review (APA)

The design builds directly on the following works:

Brown, B., Juravsky, J., Ehrlich, R., Clark, R., Le, Q. V., Re, C., & Mirhoseini, A. (2024). Large language monkeys: Scaling inference compute with repeated sampling. arXiv preprint arXiv:2407.21787.

Muennighoff, N., Yang, Z., Shi, W., Li, X. L., Fei-Fei, L., Hajishirzi, H., Zettlemoyer, L., Liang, P., Candes, E., & Hashimoto, T. (2025). s1: Simple test-time scaling. arXiv preprint arXiv:2501.19393.

Snell, C., Lee, J., Xu, K., & Kumar, A. (2024). Scaling LLM test-time compute optimally can be more effective than scaling model parameters. arXiv preprint arXiv:2408.03314.

Son, G., Hong, J., Ko, H., & Thorne, J. (2025). Linguistic generalizability of test-time scaling in mathematical reasoning. arXiv preprint arXiv:2502.17407.

Wu, Y., Sun, Z., Li, S., Welleck, S., & Yang, Y. (2024). Inference scaling laws: An empirical analysis of compute-optimal inference for problem-solving with language models. arXiv preprint arXiv:2408.00724.

Anticipated output metrics

Table 1.1 — Transfer matrix (retention %, source row applied to target column). Diagonal = 1.00 by construction.

<!-- TABLE START -->
| Source \ Target | Qwen-7B | Llama-8B | DeepSeek-7B | Qwen-32B |
| Qwen-7B | 1.00 | 0.82 | 0.79 | 0.88 |
| Llama-8B | 0.80 | 1.00 | 0.74 | 0.83 |
| DeepSeek-7B | 0.77 | 0.75 | 1.00 | 0.81 |
| Qwen-32B | 0.86 | 0.84 | 0.80 | 1.00 |
<!-- TABLE END -->

Expected: Expected: verifier-based cells (reported per strategy in the full matrix) cluster high; majority-voting cells show the widest spread, supporting H1.

Table 1.2 — Strategy transferability ranking (mean retention across all off-diagonal pairs).

<!-- TABLE START -->
| Strategy class | Mean retention | Std | Rank |
| Best-of-N (verifier) | 0.88 | 0.05 | 1 |
| Policy/verifier alloc. | 0.81 | 0.07 | 2 |
| Majority voting | 0.69 | 0.11 | 3 |
| Sequential refinement | 0.61 | 0.13 | 4 |
<!-- TABLE END -->

Expected: Expected ordering directly tests H1 and H3.

Reproduction and scientific proof

Model verification via optima.  Select compute-optimal configurations on the dev split only; verify each selected optimum lies on the accuracy-vs-FLOPs Pareto frontier. Report 95% bootstrap confidence intervals over problems for every retention figure so apparent differences are tested, not asserted.

Feature analysis.  Ablate predictor features (entropy, base accuracy, scale) and report permutation / SHAP importance to identify what drives transfer. Plot retention against source-target entropy divergence to test H2 directly.

Strict hold-out.  Strict family hold-out: train the predictor on Qwen + Llama cells and test on DeepSeek cells (an unseen family). Use AIME as an out-of-distribution difficulty hold-out never seen during budget tuning.

Validation data.  Disjoint dev (budget tuning) and test (final retention) splits per benchmark. Fix decoding seeds; report mean +/- std over 3 seeds. Pre-register the budget grid and optimum-selection rule before running the cross-application step.

Experiment 2 — Step-Level Self-Jailbreak Detection and Training-Free Intervention

Field area:  Reasoning-Model Safety

Why it stays relevant:  Reasoning-model safety is front-page after the Nature Communications autonomous-jailbreak result. There is a published baseline (Chain-of-Guardrail) to beat, and an inference-time fix is cheaper and reasoning-preserving.

Thesis

Self-jailbreak — where a reasoning model recognises harm and then overrides itself during reasoning — occurs at an identifiable point in the chain of thought. A step-level detector plus a minimal inference-time intervention can prevent unsafe outputs at far lower cost than full safety fine-tuning, and without degrading reasoning quality.

Research questions

RQ1: Can the override point in a self-jailbreak trajectory be detected reliably at the sentence / reasoning-step level from the trace alone?

RQ2: Does a minimal inference-time intervention at the detected override point reduce attack success rate as effectively as full supervised fine-tuning (Chain-of-Guardrail)?

RQ3: What is the reasoning-performance cost of detector + intervention versus CoG fine-tuning?

Hypotheses

H1: Self-jailbreak override points are detectable above 0.85 F1 by a lightweight classifier over reasoning-step representations.

H2: Inference-time intervention reduces attack success rate to within 5 points of full CoG fine-tuning while requiring no weight updates.

H3: Detector + intervention preserves reasoning-benchmark accuracy better than CoG fine-tuning, which incurs a measurable reasoning cost.

Experimental design (Goal / Method / Rationale)

Goal.  Build a step-level self-jailbreak detector and a training-free intervention, and compare both safety and reasoning cost against the Chain-of-Guardrail baseline.

Method.  Generate reasoning traces on harmful prompts; label the override sentence with an LLM judge validated by human annotation; train a classifier on reasoning-step representations; intervene at detected override points by re-injecting the model's own earlier risk assessment and forcing re-evaluation; measure attack success rate and reasoning accuracy.

Rationale.  The Chain-of-Guardrail work shows the model knows the query is harmful but overrides it mid-reasoning, and corrects this at training time. If the override is localisable, an inference-time fix is cheaper and avoids the safety-reasoning trade-off that training-time methods suffer.

Datasets — download locations and usage

<!-- TABLE START -->
| Dataset | What it is | Download location | Usage / license |
| StrongREJECT | 313 harmful prompts, 6 misuse categories, with autograder | GitHub: alexandrasouly/strongreject | Open; research use |
| SORRY-Bench | 440 prompts across 44 fine-grained categories | HuggingFace: sorry-bench | Open |
| WildJailBreak | 2,213-item adversarial evaluation split | HuggingFace: allenai/wildjailbreak | Open (AI2) |
| JailbreakBench | Standardised jailbreak behaviours + labels | jailbreakbench.github.io | Open |
| MATH-500 / GSM8K / GPQA | Reasoning-preservation evaluation | HuggingFace | Open |
<!-- TABLE END -->

Data structure

Each trace is {prompt, harm_category, reasoning_steps[sentence], step_labels[safe | override], final_answer, harmfulness_score(1-5)}. The detector consumes per-step hidden states or sentence embeddings; the supervised label is the override boundary index. A separate over-refusal set pairs each harmful prompt with a benign twin (same topic, permissible request) to measure false refusals.

Experiment setup steps

Load open reasoning models: Qwen3-8B and a DeepSeek-R1-Distill variant. Fix the thinking-token budget (e.g., 500-4000) per developer recommendation.

Generate reasoning traces on the harmful-prompt benchmarks; segment each trace into sentences / reasoning steps.

Label override sentences with a strong LLM judge; hand-annotate 250 traces (~8,000 sentences) to validate the judge via Cohen's kappa.

Train a lightweight detector (logistic regression or a small transformer) on step representations to predict the override boundary.

Implement the intervention: on detected override, re-inject the model's own earlier risk recognition and force a safety re-evaluation before the final answer.

Reproduce Chain-of-Guardrail as the baseline via supervised fine-tuning (LlamaFactory, ~14,000 corrected traces) in both Safety Recomposition and Safety Backtrack variants.

Evaluate attack success rate with the StrongREJECT autograder, reasoning accuracy on MATH-500 / GSM8K / GPQA, and false-refusal rate on the benign-twin set.

Estimated metrics

Detector F1 ~0.85-0.92 with ROC-AUC reported. Attack success rate should fall from a base ~40-70% (per benchmark) to under ~15% with intervention. Reasoning accuracy change within +/- 1-2 points (versus a larger drop for naive safety prompting). Intervention adds roughly 5-10% inference overhead versus the one-off cost of full SFT.

Literature review (APA)

The design builds directly on the following works:

Hagendorff, T., Derner, E., & Oliver, N. (2026). Large reasoning models are autonomous jailbreak agents. Nature Communications. https://doi.org/10.1038/s41467-026-69010-1

Self-jailbreaking: Language models can reason themselves out of safety alignment after benign reasoning training. (2025). arXiv preprint arXiv:2510.20956.

Souly, A., Lu, Q., Bowen, D., et al. (2024). A StrongREJECT for empty jailbreaks. arXiv preprint arXiv:2402.10260.

When models outthink their safety: Unveiling and mitigating self-jailbreak in large reasoning models with chain-of-guardrails. (2026). arXiv preprint arXiv:2510.21285.

Lin, S., Hilton, J., & Evans, O. (2022). TruthfulQA: Measuring how models mimic human falsehoods. In Proceedings of ACL 2022.

Anticipated output metrics

Table 2.1 — Attack success rate (%) by method and benchmark (lower is better).

<!-- TABLE START -->
| Method | StrongREJECT | SORRY-Bench | WildJailBreak |
| Base model (no defence) | 58 | 49 | 63 |
| CoG: Safety Recomposition | 14 | 11 | 18 |
| CoG: Safety Backtrack | 12 | 10 | 16 |
| Detector + intervention (ours) | 13 | 11 | 17 |
<!-- TABLE END -->

Expected: Expected: ours lands within ~5 points of CoG without weight updates, supporting H2.

Table 2.2 — Reasoning accuracy (%) retained and detector quality.

<!-- TABLE START -->
| Method | MATH-500 | GSM8K | Detector F1 |
| Base model | 68 | 91 | - |
| CoG (SFT) | 65 | 89 | - |
| Detector + intervention | 67 | 90 | 0.89 |
<!-- TABLE END -->

Expected: Expected: ours preserves reasoning better than SFT, supporting H3.

Reproduction and scientific proof

Model verification via optima.  Tune the detector decision threshold on a dev split; select the operating point by Youden's J from the ROC curve and report ROC-AUC and PR-AUC with bootstrap confidence intervals. Report the safety-reasoning trade-off as a frontier, not a single point.

Feature analysis.  Run per-layer probing classifiers to locate where the override decision is represented, and analyse attention to the linguistic pivot ('but actually...', 'it should be fine because...'). This connects to mechanistic reward-model interpretability and is itself a publishable finding.

Strict hold-out.  Category hold-out: train the detector on 5 of 6 StrongREJECT misuse categories and test on the held-out category, measuring generalisation to unseen harm types. Use WildJailBreak as an out-of-distribution attack-style hold-out.

Validation data.  Validate the LLM judge against human annotation (Cohen's kappa) before trusting any labels. Always report false-refusal rate on benign twins so the intervention is not just refusing everything. Fix seeds; report mean +/- std.

Experiment 3 — Instruction Diversity and Linguistic Generalisation in Vision-Language-Action Models

Field area:  Embodied AI / Robot Foundation Models

Why it stays relevant:  Robot foundation models attract heavy industry investment, OpenVLA is a recognised open baseline, the gap is author-acknowledged, and the whole study runs on a single GPU through LoRA and simulation.

Thesis

Linguistic diversity of training annotations, not raw trajectory count, is the binding constraint on VLA instruction generalisation. Synthetically augmenting low-annotation robot datasets with LLM-generated instruction variants improves zero-shot paraphrase robustness and cross-embodiment transfer, with no new robot-data collection.

Research questions

RQ1: How does instruction diversity (variants per trajectory) affect task success and robustness to unseen instruction phrasings?

RQ2: Is there a point of diminishing returns in synthetic instruction augmentation?

RQ3: Does improved linguistic generalisation transfer to an unseen robot embodiment in zero-shot evaluation?

Hypotheses

H1: Paraphrase-robustness success rate increases with instruction diversity up to a saturation point (around 5 variants per trajectory).

H2: Top-1 exact-instruction accuracy stays roughly flat while paraphrase / tolerance accuracy rises, mirroring the synthetic-augmentation finding.

H3: Linguistic augmentation improves zero-shot cross-embodiment transfer success by a measurable margin over the non-augmented baseline.

Experimental design (Goal / Method / Rationale)

Goal.  Quantify the instruction-diversity to generalisation relationship and its cross-embodiment effect for an open VLA model.

Method.  Fine-tune OpenVLA-OFT on a Bridge V2 subset with 0 / 1 / 5 / 10 synthetic instruction variants per trajectory, generated by an open LLM from the action sequence and scene image; evaluate on LIBERO simulation suites and on a held-out embodiment from Open X-Embodiment.

Rationale.  Large Open X-Embodiment subsets lack natural-language annotations, and OpenVLA names language grounding and flexible inputs as future work. The diversity-to-generalisation relationship is assumed but unmeasured.

Datasets — download locations and usage

<!-- TABLE START -->
| Dataset | What it is | Download location | Usage / license |
| Open X-Embodiment | 970,000 episodes across 22+ robot embodiments | Download script in openvla/openvla repo | Open (mixed licenses; per-dataset) |
| Bridge V2 | ~60,000 manipulation demonstrations | rail-berkeley / OXE mixture | Open |
| LIBERO | Simulation suites: Spatial, Object, Goal, Long | github.com/Lifelong-Robot-Learning/LIBERO | Open |
| OpenVLA weights | 7B VLA checkpoint (DINOv2 + SigLIP + Llama-2) | HuggingFace: openvla/openvla-7b | Open |
| OpenVLA-OFT recipe | Optimised fine-tuning; faster inference, multi-image | OpenVLA project site | Open |
<!-- TABLE END -->

Data structure

Each trajectory is {frames (third-person RGB sequence), actions (7-DoF end-effector deltas + gripper state), language_instruction (possibly empty)}. The augmented record adds instruction_variants[] generated at distinct abstraction levels (concrete object reference, spatial reference, abstract goal). The held-out paraphrase test set contains unseen phrasings of seen tasks.

Experiment setup steps

Download OpenVLA-7B and a Bridge V2 / OXE subset; install and configure the LIBERO simulation suite.

Generate instruction variants with an open LLM (Qwen2.5-7B or Llama-3.1-8B) conditioned on an action summary plus an initial-frame caption, at 3 abstraction levels.

LoRA fine-tune four OpenVLA-OFT variants (0 / 1 / 5 / 10 variants per trajectory) on a single RTX 4090 or 2x A100.

Evaluate task success on LIBERO suites using the official 100-episodes-per-task protocol.

Build a paraphrase test set (held-out phrasings of seen tasks) and measure paraphrase-robustness success.

Evaluate the best model zero-shot on a different OXE embodiment to measure cross-embodiment transfer.

Estimated metrics

Baseline OpenVLA-OFT LIBERO success is roughly 70-90% by suite. Expected paraphrase-robustness gain of several points with augmentation, a diminishing-returns curve saturating near 5 variants, and a measurable zero-shot cross-embodiment improvement for the augmented model.

Literature review (APA)

The design builds directly on the following works:

Collaboration, Open X-Embodiment. (2023). Open X-Embodiment: Robotic learning datasets and RT-X models. arXiv preprint arXiv:2310.08864.

Enhancing linguistic generalization of VLA: Fine-tuning OpenVLA via synthetic instruction augmentation. (2026). arXiv preprint arXiv:2603.16044.

Kim, M. J., Pertsch, K., Karamcheti, S., Xiao, T., Balakrishna, A., Nair, S., Rafailov, R., Foster, E. P., Sanketi, P. R., Vuong, Q., Kollar, T., Burchfiel, B., Tedrake, R., Sadigh, D., Levine, S., Liang, P., & Finn, C. (2025). OpenVLA: An open-source vision-language-action model. In Proceedings of the 8th Conference on Robot Learning (PMLR 270).

Lin, S., Hilton, J., & Evans, O. (2022). TruthfulQA: Measuring how models mimic human falsehoods. In Proceedings of ACL 2022.

Snell, C., Lee, J., Xu, K., & Kumar, A. (2024). Scaling LLM test-time compute optimally can be more effective than scaling model parameters. arXiv preprint arXiv:2408.03314.

Anticipated output metrics

Table 3.1 — LIBERO success rate (%) by augmentation level and suite.

<!-- TABLE START -->
| Variants / traj. | Spatial | Object | Goal | Paraphrase set |
| 0 (baseline) | 84 | 88 | 79 | 61 |
| 1 | 85 | 88 | 80 | 69 |
| 5 | 86 | 89 | 81 | 78 |
| 10 | 86 | 89 | 81 | 79 |
<!-- TABLE END -->

Expected: Expected: exact-task suites roughly flat (H2); paraphrase set rises then saturates near 5 variants (H1).

Table 3.2 — Zero-shot cross-embodiment transfer success (%).

<!-- TABLE START -->
| Model | Seen embodiment | Unseen embodiment | Transfer gap |
| OpenVLA-OFT baseline | 82 | 41 | -41 |
| + instruction augmentation | 83 | 52 | -31 |
<!-- TABLE END -->

Expected: Expected: augmentation narrows the embodiment transfer gap, supporting H3.

Reproduction and scientific proof

Model verification via optima.  Report success over at least 3 seeds with confidence intervals and per-task learning curves. Fit the diversity-to-success curve and locate the saturation optimum quantitatively rather than by eye.

Feature analysis.  Ablate by instruction abstraction level to identify which kinds of variants help most, and analyse language-token grounding (attention over instruction tokens) to explain why augmentation aids paraphrase robustness.

Strict hold-out.  Hold out an entire LIBERO suite and an entire robot embodiment for zero-shot evaluation. Hold out instruction templates so the paraphrase test set is genuinely unseen, not a rephrasing of a template the model trained on.

Validation data.  Use the official LIBERO evaluation protocol (100 episodes per task). Disjoint train / validation / test trajectory splits; fixed seeds; report mean +/- std across seeds.

Experiment 4 — Multi-Turn Hallucination Compounding and Knowledge-Graph-Grounded Verification

Field area:  Factuality / Reliability

Why it stays relevant:  Factuality is the number-one barrier to LLM deployment and is perennially cited. Existing benchmarks are largely single-turn; a multi-turn compounding study with a traceable, KG-grounded verifier is buildable and practical.

Thesis

LLM hallucination compounds across conversational turns in ways single-turn benchmarks miss. A domain-grounded, knowledge-graph-anchored verifier can both measure multi-turn hallucination more faithfully and reduce it more effectively than single-turn faithfulness checks.

Research questions

RQ1: How does hallucination rate evolve across turns in multi-turn factual dialogue, and does it compound when earlier answers are referenced?

RQ2: Does a knowledge-graph-grounded verifier detect multi-turn hallucinations more accurately than a single-turn LLM judge or an NLI-based detector?

RQ3: Does verifier-in-the-loop intervention reduce downstream hallucination without materially hurting helpfulness?

Hypotheses

H1: Hallucination rate increases with turn depth, with a steeper rise when a turn references content from earlier hallucinated answers.

H2: Knowledge-graph-grounded verification achieves higher detection F1 than LLM-judge and NLI baselines on multi-turn claims.

H3: Verifier-in-the-loop intervention reduces the hallucination rate at a modest, quantified helpfulness cost.

Experimental design (Goal / Method / Rationale)

Goal.  Build a multi-turn hallucination benchmark and a knowledge-graph-grounded verifier; measure compounding across turns and the effect of verifier-in-the-loop correction.

Method.  Construct multi-turn dialogues from a factual QA base with follow-ups that deliberately reference prior answers; generate model responses; extract atomic claims; verify each against Wikidata via entity linking and SPARQL; validate labels with human annotation; measure per-turn hallucination and test correction.

Rationale.  HaluEval and HalluLens are largely single-turn and FaithEval is single-context RAG; multi-turn compounding is under-measured, and knowledge-graph grounding gives traceable, auditable verification.

Datasets — download locations and usage

<!-- TABLE START -->
| Dataset | What it is | Download location | Usage / license |
| HaluEval | 35,000 samples (HotpotQA, OpenDialKG, CNN/DM) | HuggingFace: pminervini/HaluEval | Open |
| HaluEval 2.0 | 8,770 questions across 5 domains | Authors' release | Open |
| HotpotQA | Multi-hop QA; supports referencing follow-ups | HuggingFace: hotpot_qa | Open (CC BY-SA) |
| Natural Questions | Open-domain factual QA | HuggingFace: natural_questions | Open |
| FaithEval | Faithfulness under unanswerable / contradictory context | HuggingFace / project repo | Open |
| Wikidata | Knowledge graph for claim grounding | Wikidata dump / SPARQL endpoint | Open (CC0) |
<!-- TABLE END -->

Data structure

A dialogue is {turns:[{user_utterance, model_response, atomic_claims[], claim_labels[supported | unsupported | unverifiable], kg_evidence[triples]}]}. Dialogues are built from a base QA item by appending 3-6 follow-up turns, a subset of which explicitly reference entities or facts from the previous model answer (to expose compounding).

Experiment setup steps

Select a factual QA base (HotpotQA / Natural Questions) and generate multi-turn dialogues (3-6 turns) with follow-ups referencing prior turns.

Run target models (open: Qwen2.5, Llama-3.1 / 3.3; optionally a frontier API model) to produce responses for each turn.

Extract atomic claims from each response with a claim-extraction model.

Verify each claim against Wikidata via entity linking + SPARQL; mark supported / unsupported / unverifiable, retaining the evidence triples.

Human-annotate a validation subset to calibrate the verifier (Cohen's kappa).

Compute per-turn hallucination rate; compare KG verifier against an LLM-judge baseline and an NLI baseline.

Implement verifier-in-the-loop correction (append retrieved evidence or re-ask) and measure hallucination reduction and helpfulness (pairwise win-rate).

Estimated metrics

Per-turn hallucination rate is expected to rise from turn 1 to turn 5, more sharply on reference-carrying turns. The KG verifier should beat the LLM-judge baseline by roughly 5-10 F1 on multi-turn claims. Verifier-in-the-loop is expected to cut hallucination by ~20-40% relative, with a small helpfulness cost.

Literature review (APA)

The design builds directly on the following works:

HalluLens: LLM hallucination benchmark. (2025). arXiv preprint arXiv:2504.17550.

Li, J., Cheng, X., Zhao, W. X., Nie, J.-Y., & Wen, J.-R. (2023). HaluEval: A large-scale hallucination evaluation benchmark for large language models. In Proceedings of EMNLP 2023.

Lin, S., Hilton, J., & Evans, O. (2022). TruthfulQA: Measuring how models mimic human falsehoods. In Proceedings of ACL 2022.

Ming, Y., et al. (2025). FaithEval: Can your language model stay faithful to context, even if 'the moon is made of marshmallows'. In Proceedings of ICLR 2025.

MultiHal: Multilingual dataset for knowledge-graph grounded evaluation of LLM hallucinations. (2025). arXiv preprint arXiv:2505.14101.

Anticipated output metrics

Table 4.1 — Hallucination rate (%) by turn depth and model (reference-carrying turns).

<!-- TABLE START -->
| Model | Turn 1 | Turn 3 | Turn 5 | Slope |
| Qwen2.5-7B | 9 | 17 | 26 | steep |
| Llama-3.1-8B | 11 | 19 | 28 | steep |
| Frontier API | 5 | 9 | 15 | moderate |
<!-- TABLE END -->

Expected: Expected: monotonic rise with depth (H1); steeper on reference-carrying turns than independent turns.

Table 4.2 — Verifier detection quality and intervention effect.

<!-- TABLE START -->
| Verifier / setting | Precision | Recall | F1 |
| NLI baseline | 0.71 | 0.66 | 0.68 |
| LLM-judge baseline | 0.78 | 0.74 | 0.76 |
| KG-grounded (ours) | 0.85 | 0.82 | 0.83 |
<!-- TABLE END -->

Expected: Expected: KG grounding beats LLM-judge, supporting H2. A second panel reports hallucination reduction and helpfulness delta after verifier-in-the-loop.

Reproduction and scientific proof

Model verification via optima.  Tune the verifier decision threshold on a dev split by PR-AUC and report the chosen operating point; provide bootstrap confidence intervals on detection F1 and on every per-turn rate.

Feature analysis.  Build an error taxonomy (entity-level, relational, sentence-level) and analyse which turn positions and reference types drive compounding, so the finding is mechanistic rather than a single aggregate number.

Strict hold-out.  Domain hold-out: calibrate the verifier on four HaluEval 2.0 domains and test on the fifth. Hold out an entire model family to test that the verifier generalises beyond the models used to build the benchmark.

Validation data.  Validate verifier labels against human annotation (Cohen's kappa) on the held-out subset. Report a false-positive / over-correction rate so the intervention is not penalising correct statements. Fixed seeds; mean +/- std.

Experiment 5 — Cross-Paradigm Visual Robustness of World-Model Agents

Field area:  World Models / Model-Based RL

Why it stays relevant:  World models are intensely hot after Genie 3 and the Waymo World Model. A reproducible-research robustness study uses a three-week-old open platform, runs on a single GPU, and yields a leaderboard nobody has published yet.

Thesis

World-model agents differ systematically in robustness to visual distribution shift depending on their representation paradigm (latent, diffusion, or transformer-token). A controlled robustness study across paradigms, built on the stable-worldmodel platform, yields a robustness leaderboard and identifies which design choices confer visual robustness.

Research questions

RQ1: How much does each world-model paradigm degrade under graded visual perturbations applied at test time?

RQ2: Which paradigm is most robust, and does robustness correlate with representation-compression ratio?

RQ3: Can a lightweight remedy (training-time observation augmentation) close the robustness gap with minimal clean-performance cost?

Hypotheses

H1: Diffusion-based world models (DIAMOND) preserve visual detail and degrade less under fine-grained perturbations than aggressively compressed latent models (DreamerV3).

H2: Robustness correlates inversely with latent-compression ratio across paradigms.

H3: Training-time observation augmentation improves test-time robustness across paradigms with minimal clean-performance cost.

Experimental design (Goal / Method / Rationale)

Goal.  Produce a cross-paradigm visual-robustness benchmark for world-model agents and test an augmentation remedy.

Method.  Train the platform's world-model baselines (DreamerV3, IRIS / Delta-IRIS, DIAMOND, plus goal-conditioned-RL baselines) on Crafter and Atari 100K; evaluate each under graded visual wrappers (colour shift, occlusion, noise, blur); measure normalised-score retention; add training-time observation augmentation and re-evaluate.

Rationale.  World-model agents are benchmarked almost entirely on clean frames. The new stable-worldmodel platform ships visual wrappers that enable controlled perturbation even when simulator internals are inaccessible, and no systematic cross-paradigm robustness study exists.

Datasets — download locations and usage

<!-- TABLE START -->
| Dataset | What it is | Download location | Usage / license |
| Atari 100K | 26 games, 100K interactions (~2h human play) | Arcade Learning Environment (ALE) | Open |
| Crafter / Craftax | Procedurally generated survival environment | github.com/danijar/crafter ; Craftax (JAX) | Open |
| ProcGen | Procedurally generated levels; generalisation | openai/procgen | Open |
| DeepMind Control | Continuous-control suite (optional) | google-deepmind/dm_control | Open (Apache 2.0) |
| stable-worldmodel | Baselines + visual wrappers + Hydra configs | arXiv 2605.21800 release | Open |
<!-- TABLE END -->

Data structure

An environment interaction is {observation (RGB frame), action, reward, done}. The world model is trained on a replay buffer of these transitions and the policy is trained 'in imagination' inside the learned model. At evaluation, a visual wrapper rewrites the rendered frame before it reaches the agent; per-episode return is logged under each perturbation severity.

Experiment setup steps

Install stable-worldmodel with its Hydra-configured training entry point and the visual-wrapper layer.

Train each world-model baseline on Crafter and Atari 100K on a single GPU (DreamerV3 on an A100; DIAMOND profiled on an RTX 4090).

Define graded perturbation severities for each wrapper type (colour shift, occlusion, noise, blur).

Evaluate every trained agent under each perturbation at each severity, over at least 5 seeds, using a fixed evaluation-episode count.

Compute human-normalised-score retention = perturbed score / clean score per paradigm and perturbation.

Add training-time observation augmentation, re-train, and re-evaluate to measure the remedy.

Estimated metrics

Clean human-normalised scores should match published baselines (DIAMOND reports the highest mean among world-model baselines on Atari 100K). Under fine-grained perturbation, diffusion-based models are expected to retain more score than heavily compressed latent models; global shifts may reverse this. Augmentation is expected to recover a substantial fraction of lost score.

Literature review (APA)

The design builds directly on the following works:

Alonso, E., Jelley, A., Micheli, V., Kanervisto, A., Storkey, A., Pearce, T., & Fleuret, F. (2024). Diffusion for world modeling: Visual details matter in Atari. In Advances in Neural Information Processing Systems 37.

Hafner, D., Pasukonis, J., Ba, J., & Lillicrap, T. (2025). Mastering diverse control tasks through world models. Nature.

Micheli, V., Alonso, E., & Fleuret, F. (2023). Transformers are sample-efficient world models. In Proceedings of ICLR 2023.

stable-worldmodel: A platform for reproducible world modeling research and evaluation. (2026). arXiv preprint arXiv:2605.21800.

Agarwal, R., Schwarzer, M., Castro, P. S., Courville, A., & Bellemare, M. G. (2021). Deep reinforcement learning at the edge of the statistical precipice. In Advances in Neural Information Processing Systems 34.

Anticipated output metrics

Table 5.1 — Score retention (% of clean) under each perturbation, by paradigm (Crafter).

<!-- TABLE START -->
| Paradigm | Colour shift | Occlusion | Noise | Blur |
| DreamerV3 (latent) | 71 | 58 | 64 | 55 |
| IRIS / Delta-IRIS (token) | 74 | 61 | 68 | 60 |
| DIAMOND (diffusion) | 82 | 66 | 77 | 69 |
<!-- TABLE END -->

Expected: Expected: diffusion retains most score under fine-grained perturbation (H1); ordering correlates with compression (H2).

Table 5.2 — Effect of training-time observation augmentation (mean retention across perturbations).

<!-- TABLE START -->
| Paradigm | No augmentation | + augmentation | Clean-score cost |
| DreamerV3 | 62 | 78 | -1 |
| DIAMOND | 73 | 85 | -2 |
<!-- TABLE END -->

Expected: Expected: augmentation closes much of the gap with negligible clean-performance cost (H3).

Reproduction and scientific proof

Model verification via optima.  Reinforcement-learning results are high-variance: report at least 5 seeds and use distributional metrics (interquartile mean and bootstrap confidence intervals) following Agarwal et al. (2021), not bare means. Verify each agent's training converged via return curves before any robustness claim.

Feature analysis.  Probe the learned latent for perturbation invariance, and visualise world-model rollouts under perturbation to test whether the model still 'imagines' the environment correctly. Plot robustness against compression ratio to test H2.

Strict hold-out.  Perturbation hold-out: train the augmentation on a subset of perturbation types (noise + colour) and test on a held-out type (occlusion), so the result reflects genuine robustness rather than memorised augmentations. Hold out games / levels for generalisation.

Validation data.  Use a standardised evaluation protocol (fixed number of evaluation episodes), fixed seeds, and report distributional metrics rather than single-run scores. Pre-register perturbation severities.

<!-- Extracted 245 paragraphs and 73 table rows. -->