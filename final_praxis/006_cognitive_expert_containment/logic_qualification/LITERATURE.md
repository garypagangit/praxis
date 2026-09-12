# MiCRo logic/GSM8K qualification: primary evidence and design

12 September 2026. Read-only literature/artifact review before this new model study. The user has authorized execution; this memo informs the protocol, not a permission request. This is capability and intervention qualification, with no novelty or containment-efficacy claim.

## What the paper establishes

[MiCRo v3, April 12, 2026](https://arxiv.org/html/2506.13331v3), Table 8, reports **34.7% +/-1.3 percentage points** for MiCRo-Llama-1B on GSM8K. Tables 7-8 and Appendix F specify 1,319 test questions, zero-shot CoT, exact match and the `gsm8k_cot_zeroshot` harness task. Figure 4/section 5.2 reports a substantial drop when the logic expert is removed and slight gains when social is removed. No precise ablation magnitude is recovered from the plot here. Language removal broadly damages tasks, so it is not a matched negative control for logic-specific usefulness. Social removal is the better prespecified nonlogic diagnostic.

The paper does **not** establish the benchmark harness commit, chat-template flag, generation cap, EOS override, inference precision or exact hardware invocation. The source availability and observed effect make a fresh qualification reasonable; they do not make an incompletely specified evaluation exactly reproducible. The paper already claims causal expert ablation and steering, so repeating that result establishes a prerequisite, not a new method.

## Prompt, decoding and scoring evidence

The [current pinned harness YAML](https://github.com/EleutherAI/lm-evaluation-harness/blob/ad8737ae7fad24cf64e50fc7fc31397bff586b9e/lm_eval/tasks/gsm8k/gsm8k-cot-zeroshot.yaml) has:

- Raw task text: `Q: {question}\nA: Let's think step by step.`
- Zero few-shot examples, deterministic generation (`do_sample: false`), one generation.
- Stop strings `Q:`, `</s>`, `<|im_end|>`; no task-level generation-token cap.
- Strict extraction using `The answer is ...`; flexible extraction uses the final numeric regex match. Target scoring removes the preceding GSM8K solution/`####` marker and specified punctuation. The pinned YAML bytes and SHA256 are in `harness_task_receipt.json`.

A harness wrapper may separately apply chat formatting, BOS/EOS and generation defaults. The YAML alone does not settle those options. Importantly, flexible extraction can find a number in unfinished reasoning; it does not certify an explicit final answer. Reproduce its extraction as a declared metric, and separately report explicit final-answer format, terminal numeric answers, missing extraction, truncation and empty output. Do not replace the frozen parser after observing failures or use answer-key information to choose a numeric span.

[Official generate.py](https://github.com/BKHMSI/mixture-of-cognitive-reasoners/blob/275a5e4b1369ff19c8e3f33f42f16bc5ef19e6d7/generate.py) provides different, generic demonstration behavior: it uses the configured chat template and assistant prefix, left padding, Llama pad ID 128004, BF16, FlashAttention2, deterministic decoding and stop strings `</s>`, `<|eot_id|>`, `<|im_start|>user`. The helper defaults to 1,024 new tokens; its CLI example passes 512. **Neither value is evidence of the published benchmark cap.** Loading BF16 with an explicitly reviewed SDPA portability change is source-supported engineering, not exact paper hardware replication.

Recommendation: freeze raw harness task text as the primary convention and declare a 1,024-new-token cap as our own design choice. Any chat-template sensitivity must be prospectively separate and receive no primary promotion based on results. A few disjoint training-split examples may test encoding, cache and stop behavior before test processing; keep their identities and outputs outside the qualification cohort. Do not tune a prompt on held-out qualification answers.

## Pinned public artifacts and loading contract

- [MiCRo code](https://github.com/BKHMSI/mixture-of-cognitive-reasoners/tree/275a5e4b1369ff19c8e3f33f42f16bc5ef19e6d7): commit `275a5e4b1369ff19c8e3f33f42f16bc5ef19e6d7`.
- [MiCRo-Llama-1B checkpoint](https://huggingface.co/bkhmsi/micro-llama-1b/tree/b9ea46bbfb2836552e963ea3ad322d9fb3b07179): revision `b9ea46bbfb2836552e963ea3ad322d9fb3b07179`, public/ungated. It has **4,485,154,816 total parameters**, serialized as 17,940,619,264 bytes of F32 tensors (about 17.94 GB), with approximately 8.97 GB of BF16 resident weights before runtime overhead; "1B" names the dense backbone.
- [Official architecture config](https://github.com/BKHMSI/mixture-of-cognitive-reasoners/blob/275a5e4b1369ff19c8e3f33f42f16bc5ef19e6d7/configs/config_micro_llama.yml) names base `meta-llama/Llama-3.2-1B`, tokenizer `meta-llama/Llama-3.2-1B-Instruct`, four experts and top-1 routing. It names `micro-llama`, whereas the public generation model map names `micro-llama-1b`; resolve that configuration alias explicitly rather than silently changing the architecture.
- [GSM8K](https://huggingface.co/datasets/openai/gsm8k/tree/740312add88f781978c0658806c59bc2815b9866): revision `740312add88f781978c0658806c59bc2815b9866`, `main` configuration. The [original MIT license](https://github.com/openai/grade-school-math/blob/3101c7d5072418e28b9008a6636bde82a006892c/LICENSE) is available. Preserve official split IDs and hashes. Exclude previously exposed campaign questions by normalized question identity; do not select by performance.

The model card lacks a derivative license declaration and the inspected code tree lacks LICENSE. Record these facts and applicable upstream Llama metadata; do not invent new legal restrictions or a grant. Keep third-party weights/code out of published branch artifacts. Verified base metadata pin: `meta-llama/Llama-3.2-1B` at `4e20de362430cd3b72f300e6b0f18e50e7166e08`; instruction tokenizer pin: `meta-llama/Llama-3.2-1B-Instruct` at `9213176726f574b556790deb65791e0c5aa438b6`. Both upstream cards declare `llama3.2`. The base/checkpoint config uses BOS 128000 and EOS 128001, while the instruction tokenizer uses EOS `<|eot_id|>` ID 128009 and has no native pad token. The official demo overrides pad to 128004. Freeze whether both end-of-text and end-of-turn IDs stop generation; do not silently inherit a conflicting default. The checkpoint has 16 physical backbone layers and 64 serialized expert/cache layers. Supplementary `SOURCE_CONTRACT.md` and loader receipts record exact file hashes and the constructor contract.

A valid load requires exact checkpoint-key/shape matching, four experts per physical layer, and no double expansion of `num_hidden_layers` by the custom constructor. The released router uses raw router values in active computation; preserve its math, expert ordering (logic, social, world, language), top-1 selection and ablation semantics. Routing counters are diagnostics. Validate finite outputs, cache/full-forward agreement within a predeclared BF16 tolerance, and intact-ablation-intact reset. Do not infer inactivity from unchanged answers if probabilities/routes changed, or correctness from route counts alone.

## Proposed research question and hypotheses

**RQ:** Under one fixed, reproducible generation protocol, does the published MiCRo-Llama-1B perform useful GSM8K answering, and does its logic expert make a practically meaningful paired contribution that social ablation does not reproduce?

- **H1 (primary contribution):** intact exact-answer accuracy exceeds permanent logic-ablation accuracy. Let `D_i = correct_intact_i - correct_logic_ablated_i`; estimate `delta = mean(D_i)` on every prespecified item.
- **H2 (specificity diagnostic):** logic removal loses more accuracy than social removal on the same questions. This comparison holds the number of available expert modules constant, but it does not match changed token-route counts or prove anatomical brain equivalence.
- **H3 (measurement):** the apparent contribution is not solely a loader, cache, missing-answer or truncation artifact. Preserve all outcomes, and report parser and completion diagnostics per arm; a jointly complete subset is a sensitivity, not an unbiased replacement for the full cohort.

A proposed practical continuation gate is intact accuracy at least 25%, observed logic-ablation loss at least ten points and a positive 95% paired confidence lower bound, with a working loader and sufficiently complete intact generation (for example, no more than 10% truncation). These are proposed engineering thresholds, not numbers claimed by the paper. Freeze exact thresholds and integer rounding in the actual preregistration. Social ablation should be included as a diagnostic; a broad impairment from both ablations weakens the domain-specific interpretation.

No requirement that 95% of answers contain a numeric regex should be mistaken for model capability. The flexible regex is permissive. Likewise, a low exact-match score does not automatically imply invalid generation. Count wrong, missing, truncated and technical errors separately; only technical errors justify a repair of the implementation.

## Sample size and precision

**Recommend 256 fixed paired test questions, with all three arms on the same cohort** (768 generations). Use a deterministic, outcome-independent sample after excluding all earlier exposed GSM8K IDs. If cost dictates 128, choose it before inference and acknowledge weaker precision; do not extend from 128 to 256 merely because the interim interval is unfavorable.

For intuition, if intact accuracy is 0.347, its approximate 95% binomial interval half-width is 8.25 points at n=128 versus 5.83 at n=256. For a paired ten-point effect, let `q = P(D != 0)` be the discordance probability. Then `Var(D) = q - delta^2` and `SE(delta_hat) = sqrt((q-delta^2)/n)`.

| Assumed discordance | n=128: 95% half-width / approximate power | n=256: 95% half-width / approximate power |
|---|---:|---:|
| q=0.20, true delta=0.10 | 7.55 points / 74% | 5.34 points / 96% |
| q=0.30, true delta=0.10 | 9.33 points / 56% | 6.60 points / 84% |

Power here is a normal approximation for a two-sided 5% test against delta=0, with assumed discordance, not a guarantee. It is not the probability of passing the complete continuation gate. If the true effect is exactly the minimum ten-point observed-effect threshold, the observed effect exceeds that threshold only about half the time. The experiment is therefore an informative qualification, not a highly powered proof that the true advantage is at least ten points.

Report paired correct-to-wrong and wrong-to-correct counts, the full paired difference, a prespecified paired-question bootstrap interval, and an exact McNemar test as a secondary check if desired. Resample question IDs jointly across all arms. Do not infer uncertainty across model seeds/checkpoints from question bootstrap. Avoid constructing the cohort only from intact successes: that would remove ablation recoveries and bias the contribution estimate.

A pass permits designing a new containment experiment with useful logic behavior to preserve. It does not validate the old failed social selector, show cross-fault transfer or establish a publishable mechanism. A failure is retained, and any changed checkpoint, prompt, budget or target task needs a new prospective study.
