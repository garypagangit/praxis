# Option 006: prospective FP32 logic contribution qualification

Frozen before this follow-up model processing, 12 September 2026. This study tests a prerequisite for a new specialist-corruption containment method. It does not claim a new method or exact reproduction of an incompletely specified paper evaluation. The user's existing authorization covers execution below $1,000 per job; this job has a $75 total cap.

## Prospective precision follow-up

The predecessor run `fp006-logic-5075fe39d3` loaded all weights exactly but failed its frozen BF16 eager-versus-SDPA next-token equality on one of six fixed probes. Its largest backend logit difference was0.15625, within its magnitude bound; the discrete-token criterion still failed. It processed zero pilot or test questions. Preserve that failure and its automatic audit at the predecessor Git commit and sibling study folder. This is a separate protocol, not a relabeling of the BF16 result.

Change computation to float32 with CUDA matmul/cuDNN TF32 disabled. Keep the same untouched cohort, prompts, ablations, token cap, scientific decision thresholds and automatic review. Require all six cache/full and eager/SDPA next-token equalities, with a new prospectively fixed maximum absolute difference of0.001. No equality or magnitude threshold is loosened after this attempt. If FP32 fails, stop and preserve the numerical failure; do not automatically continue to study inference.

[PyTorch2.6 numerical-accuracy notes](https://docs.pytorch.org/docs/2.6/notes/numerical_accuracy.html) and [SDPA documentation](https://docs.pytorch.org/docs/2.6/generated/torch.nn.functional.scaled_dot_product_attention.html) support treating dtype/backend differences as a numerical qualification question. They do not guarantee our0.001 threshold. PRECISION_BASIS.md and RUNTIME_FP32_REVIEW.md record the rationale and memory accounting. Actual peak/free GPU memory is recorded. FP32 core weights plus maximum expected KV cache require about17.0GiB, leaving capacity for runtime overhead on the A10G.

The previous attempt is separately costed. This new job retains its own$75 total cap and8-hour host watchdog; no new scientific result was available when fixing this follow-up.

## Literature, question and hypothesis

The [MiCRo paper v3](https://arxiv.org/html/2506.13331v3) reports 34.7% GSM8K accuracy for MiCRo-Llama-1B and a reduction when its logic expert is ablated (Table 8, Figure 4, section 5.2). Its public checkpoint and source, and GSM8K public answer keys, make a useful-specialist qualification possible. LITERATURE.md records exact references, sample-size reasoning and undocumented paper settings. The paper already studies ablation and steering; those operations alone cannot be the Praxis novelty.

RQ: Under a fixed generation and scoring protocol, does the released MiCRo-Llama-1B provide useful math capability, and does removing its logic expert materially reduce that capability?

H1: Intact accuracy exceeds logic-ablation accuracy on paired questions. For every prespecified question, D_i = correct_intact_i - correct_logic_ablation_i; estimate mean(D_i). The practical continuation threshold is an observed loss of at least 10 percentage points, with a positive lower 95% paired bootstrap bound. This threshold is our decision rule, not a reported paper value.

H2, diagnostic: Logic removal loses more accuracy than social removal. Social ablation removes one nonlogic expert, providing a same-module-count diagnostic. It does not control for every difference in changed routes or general capacity and is not a primary gate.

H3, measurement: Any contribution must coexist with finite, correctly loaded computation, reset and cache checks, and useful completed intact generations. We report truncation and extraction separately and retain all assigned test questions.

## Fixed data and interventions

data.json contains 256 test questions selected by a deterministic hash ordering and 16 train questions for a technical pilot. data_receipt.json records the original GSM8K Git commit, exact source hashes and 40 excluded test identities used in previous option005/006 experiments. Also exclude normalized test questions present in train. No cohort selection uses model outputs or baseline correctness. The pilot runs all three conditions on all16 questions; its answers do not enter the test estimate and do not tune prompts, thresholds, model choice or generation length.

Every test question receives intact, permanent logic ablation and permanent social ablation: 768 test generations plus48 pilot generations. Condition order rotates with the fixed question position. Intact explicitly resets experts_ablate=[]; each cell starts with an independent empty KV cache. Ablation uses the author's actual raw-logit masking, not a prompt instruction or an altered router. No fault injection or new containment policy is tested here.

Use the exact checkpoint, tokenizer and author-code revisions in loader_settings.json and SOURCE_CONTRACT.md. Check every shard hash, all611 tensor names/shapes, F32 storage, strict loading, 4,485,154,816 parameters, and16 backbone groups/64 expert blocks. Load FP32 on an A10G with TF32 disabled. The source replacement changes the author's forced FlashAttention2 constructor default to SDPA. We do not claim universal backend equivalence.

## Generation and technical checks

protocol.json is the machine-readable authority. Render raw `Q: {question}\nA: Let's think step by step.` without chat wrapping, add BOS128000 exactly once, greedy batch1 with1,024 new tokens maximum. Stop on IDs128001 or128009, or first occurrence of `Q:`, `</s>`, `<|im_end|>`. The cap and special-token choices are explicitly ours because the paper does not disclose them. Stop text/EOS is removed before scoring; raw responses and token IDs are retained. No stochastic sampling, quantization, output repair or semantic judge is used.

Before pilot/test generation, two fixed short prompts in protocol.json are checked across all three arms. Require strict checkpoint loading, finite outputs, exact repeated full-forward/reset equality, identical next-token argmax for cached versus full and eager versus SDPA, and maximum absolute FP32 logit differences at most0.001 for those comparisons. This is an engineering acceptance threshold on fixed probes. Record cache route agreement and minimum router margin diagnostically. Require zero selected routes for the ablated expert and exact route-count accounting on every generated cell. Record prompt versus decode route totals separately; counts refer to processed input tokens.

A failed technical check stops the run before test inference. A failed or incomplete job is preserved and cannot pass. A mechanical repair requires a separately recorded code revision and must not use answer quality to change the scientific protocol. Outages may resume only identical cell identities, source, protocol and preregistration hashes, preserving completed cells. Runtime deadlines may still end a resumed job incompletely.

## Scoring, uncertainty and automatic decision

Primary scoring reproduces the pinned lm-evaluation-harness GSM8K flexible-extract regex and exact-match normalization in harness_task_receipt.json. Strict-match is secondary. No Decimal equivalence or answer-aware extraction is permitted: the harness can distinguish `4.0` from `4`. Truncated responses remain in the full-cohort metric with the same parser; separately report their rate, correctness without truncated outputs, strict final-answer extraction, and jointly nontruncated paired sensitivity. A regex-extracted number is not proof of completed reasoning.

The independent audit reconstructs scores from saved responses and golds, validates fixed cell IDs/hashes, uniqueness, completeness, route ablation and numerical evidence, and calculates paired correct-to-wrong and wrong-to-correct counts. Use10,000 paired-question bootstrap draws with seed20260912 and linearly interpolated2.5th/97.5th percentiles. Bootstrap uncertainty is over these questions, not model seeds or checkpoints. No repeated looks may extend or shrink the cohort. All256 questions and all768 test cells are needed for a continuation decision; partial summaries are descriptive only.

All gates must pass: all required technical/integrity checks; intact flexible accuracy>=0.25 (at least64/256); intact truncation<=0.10 (at most25/256); intact digit-containing flexible extraction>=0.90 (at least231/256); paired intact-minus-logic loss>=0.10 (at least26 net correct answers); and95% paired lower bound>0. There is no multiplicity-adjusted efficacy claim. The social comparison and strict parser diagnose specificity and measurement. A pass permits designing a new prospective containment experiment; a fail rejects this protocol as the immediate base and does not erase its results or prove the entire field unsuitable.

The256-question design improves approximate precision over128: near the paper's34.7% baseline the normal95% half-width is about5.8 points. For a true10-point paired effect and discordance0.2-0.3, approximate power against zero is84-96%, conditional on those assumptions. This does not imply that a true effect exactly at the practical10-point threshold is likely to pass the whole gate.

## Compute, durability and stop rules

Use the existing stopped g5.xlarge host, without taking over an active host. Verify its shutdown behavior is stop. Install an AWS scheduler stop before startup, for8 hours maximum. g5.xlarge pricing verified for this campaign is$1.006/hour (eight-hour compute bound$8.05); allow dependencies, storage and transfer within the conservative$75 total cap. Stop early on completion or technical failure. No new paid study starts automatically on a scientific failure.

A detached systemd job runs an independent supervisor for at most27,000 seconds; inference has a24,000-second limit. Atomic per-cell files and S3 synchronization allow the job to survive a local disconnection. The final automated audit writes machine-readable and Markdown decisions, including incomplete/failure status, with no manual review requirement. Shutdown follows final synchronization; the external watchdog is a backstop. Retain source/model pins, protocol, environment, execution receipts, raw outputs and negative findings. Do not upload credentials or publish third-party weight/tokenizer bundles to Git.
