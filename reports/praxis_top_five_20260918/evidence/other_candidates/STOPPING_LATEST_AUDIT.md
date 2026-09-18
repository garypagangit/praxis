# PX-057 experimental-state audit

**Audit date:** September 18, 2026. **Mode:** local evidence inspection and independent arithmetic over saved traces; no inference, cloud calls, or modification of historical evidence. This is an AI-assisted research audit, not human academic approval or a novelty determination.

## 1. Controlling result

The older 200-question slide is a valid description of the original Gate 2 discovery: adaptive and stability accuracy **182/200 = 91%**, fixed-eight **123/200 = 61.5%**, fixed-two and confidence-only **176/200 = 88%**, and **1/200 early-stop harms**. It is superseded as the current confirmation status by PX-057-F1's **CLOSED_FAIL_PRIMARY_CONFIRMATION** / **FAIL_PRIMARY_CONFIRMATION**. The August 26 closeout, finalized after all three shards completed, covers every **1,319 GSM8K questions and 10,552 question-round generations**. The historical 200 answer trajectories reproduced exactly. Reproduction does not rescue the failed confirmation. [F1 closeout manifest](../adaptive_stopping_overthinking/px057_f1_full_gsm8k_closeout_20260826/final_closeout/PX057_F1_FINAL_CLOSEOUT_MANIFEST.json)

The primary stratum excludes the original 200 questions: **1,119 questions**, including **500 previously exposed during H4 output collection** and **619 without that H4 exposure**. It is not an untouched new dataset. Both the original parser and the sealed, outcome-blinded **AI extraction review** had to pass every gate. The review covered 7,746 flagged responses, changed 1,850 extractions, and scored 1,376 ambiguous cases as empty. [Dual extraction adjudication](../adaptive_stopping_overthinking/px057_f1_full_gsm8k_closeout_20260826/final_closeout/final_dual_extraction_adjudication.json)

## 2. Exact baseline comparisons

All figures below use the same saved eight-round trajectories. “One-shot” means their first-round prefix under the original initial prompt and **256-token cap**; it is an additional descriptive count computed in this audit, not a tuned or equal-budget one-shot competitor. The other accuracy counts independently reproduce the saved summaries.

| Stratum / extraction | First round | Fixed two / confidence-only | Stability / adaptive | Fixed eight |
|---|---:|---:|---:|---:|
| Original 200, original parser | 106/200 (53.00%) | 176/200 (88.00%) | 182/200 (91.00%) | 123/200 (61.50%) |
| Primary 1,119, original parser | 563/1,119 (50.31%) | 944/1,119 (84.36%) | 976/1,119 (87.22%) | 682/1,119 (60.95%) |
| Primary 1,119, blinded extraction | 541/1,119 (48.35%) | 925/1,119 (82.66%) | 915/1,119 (81.77%) | 715/1,119 (63.90%) |
| Complete 1,319, original parser | 669/1,319 (50.72%) | 1,120/1,319 (84.91%) | 1,158/1,319 (87.79%) | 805/1,319 (61.03%) |
| Complete 1,319, blinded extraction | 642/1,319 (48.67%) | 1,094/1,319 (82.94%) | 1,084/1,319 (82.18%) | 842/1,319 (63.84%) |

Under the blinded primary analysis, **fixed-two exceeds adaptive by 10 correct answers** and has greater potential token saving: **76.58% versus 66.66%**. Under the original primary parser, adaptive exceeds fixed-two by 32 answers, at **63.88% versus 76.58%** saving. Consequently, success against forced round eight is insufficient to demonstrate value over a short baseline. These are generated-token prefix savings against round eight, not measured production latency, energy, total prompt-plus-output cost, or savings against one-shot.

## 3. What failed

| Analysis | Adaptive minus round-eight correct | Potential token saving | Overthinking prevented | Early-stop harms / allowed |
|---|---:|---:|---:|---:|
| Primary, original | +294 | 63.8822% | 326/383 (85.1175%) | **32 / 22** |
| Primary, blinded | +200 | 66.6567% | 275/352 (78.1250%) | **75 / 22** |
| Complete, original | +353 | 64.2764% | 386/450 (85.7778%) | **33 / 26** |
| Complete, blinded | +242 | 66.8790% | 326/414 (78.7440%) | **84 / 26** |

All four analyses passed the accuracy-count, >=20% saving, and >=25% prevention gates; **all failed the harm-count gate**. Primary accuracy noninferiority required a net count difference >=-11; the secondary limit was >=-13. Harm means round eight was correct and the policy-selected answer was wrong. Average gains do not offset this separate constraint. The primary harm rates are **2.8597% original / 6.7024% blinded**. The secondary rates are **2.5019% / 6.3685%**. Both the H4-exposed and never-H4-exposed strata also exceed 2% under both extraction methods. [Original adjudication](../adaptive_stopping_overthinking/px057_f1_full_gsm8k_closeout_20260826/merged_original/original_parser_adjudication.json)

**Measurement mechanism matters.** Independent inspection finds **49/75 primary blinded harms**, and **58/84 complete blinded harms**, select an empty extracted answer. The frozen rule permits consecutive empty strings to count as stability. Original-parser harms select empty answers in **0/32 primary and 0/33 complete cases**. These are post hoc descriptive counts. Removing the empty-answer trigger changes subsequent stopping decisions; it is invalid to subtract these counts and declare a repaired policy successful.

**The first-round baseline is severely constrained.** Raw evidence contains **7,689/10,552 rounds reaching 256 generated tokens (72.87%)**, including **833/1,319 first rounds (63.15%)**. These counts mean `generated_tokens == 256`; they do not independently establish that every such response was semantically unfinished. The one-shot comparison cannot establish superiority over adequately budgeted one-shot reasoning.

## 4. Confidence is not answer certainty

The fixed policy uses `min_step=2`, `patience=2`, and `confidence_threshold=0.05`. Its confidence is `exp(clip(mean(finite generated-token transition log probabilities), -20, 0))`: a clipped geometric mean of selected-token probabilities, not a calibrated probability that the extracted numeric answer is correct. The replay excludes nonfinite entries and uses `math.fsum`; all inspected F1 transition log probabilities were finite.

The minimum stored confidence is **0.2904678208524977** over all 10,552 rounds, well above 0.05. Independent per-question replay confirms **identical selected rounds**, not merely equal aggregate accuracy, for adaptive versus stability on all 1,319 traces under both extractions; confidence-only selects round two throughout. Thus the confidence condition contributes **zero changed decisions** here. It cannot support incremental benefit from confidence, calibrated uncertainty, or a claim that confidence identifies harmful reconsideration.

A recorded Windows/Linux one-ULP replay difference affected 65 rounds, but threshold margin was at least 0.2404678, and the compatibility audit confirmed decision invariance without rewriting stored evidence. [Confidence compatibility audit](../adaptive_stopping_overthinking/px057_f1_full_gsm8k_closeout_20260826/PX057_F1_CONFIDENCE_COMPAT_INDEPENDENT_REVIEW.json)

## 5. H4 and H5 already constrain a follow-up

**H4 LTT transfer:** the controlling completion audit is **PROTOCOL_INVALID**, because the mandatory independent pre-data code-review evidence was absent. An earlier adjudicator's `VALID_NEGATIVE` covered implemented statistical/provenance checks but missed that requirement. The retained observations are descriptive, not a completed valid risk certificate or transfer confirmation. [H4 completion audit](../adaptive_stopping_overthinking/h4_20260725/completion_audit_20260727.json)

There were 500 calibration questions per cell (1,500 traces / 12,000 generations). The first fixed-sequence candidate (`min_step=4`, `patience=2`, `tau=0.20`) had **40/500 harms (8%)** for Llama/GSM8K, **35/500 (7%)** for Qwen/ARC, and **28/500 (5.6%)** for Llama/ARC. No cell obtained a certified prefix or selected policy; holdout was correctly not run. This does not establish that every later policy fails: the fixed sequence stopped at the first failed candidate.

Every H4 confidence value exceeded the grid maximum 0.20 (cell minima 0.585984, 0.491244, 0.487014). The nominal 30-policy grid collapsed to six distinct stopping behaviors. H4's confidence-component result was **INCONCLUSIVE**. Blank/token-capped extractions accounted for 33/40, 22/35, and 26/28 first-policy harms. These diagnostics were already documented in the H4 final determination; they are not a new discovery of this audit.

**The development repair intended to enable H5 already failed:** the `m4-k2-valid-v1` candidate used 500 already exposed Llama/GSM8K questions and is **FAIL - H5 NO-GO**, not confirmation. **Fresh H5 calibration/holdout was not run.** Accuracy was **178/500 (35.6%) versus 165/500 (33.0%)** at round eight, with **4/500 harms (0.8%)**, but saving **17.7281%** missed 25%, valid-schema rate **57.3%** missed 95%, and only **2/7 mechanism sentinels** met the required condition: **3/6 checks passed**. [Development evaluation](../adaptive_stopping_overthinking/h5_development_pilot_20260727/cell1_llama31_gsm8k/development_evaluation.json)

The exact r2 intervention was a **compound protocol repair**, not just a nonempty-answer predicate: native chat serialization; eight greedy rounds capped at **96 new tokens** each; exactly three lines (`Check:` with 1–40 words, `Final answer:` with a full numeric match, then `<END>`); explicit EOS/EOT/end-marker termination; a strict requirement to finish before the cap; and reconsideration using **only the preceding strict-valid answer**, otherwise `NO_VALID_PRIOR_ANSWER`. Invalid rounds reset context. The rule required two consecutive valid stable answers from round four, used no confidence condition, and compared against **strictly valid round eight with no fallback**. Therefore r2 does not isolate the causal effect of validity, chat serialization, shorter outputs, or answer-only context. Its failure does not prove a later evidence-based acceptance/veto mechanism impossible.

The exact historical sources are `configs/px057_h5_development_pilot_20260727.json` (SHA-256 `8ce6d5051bae861707f8801396036948e7faa291c553863e54ef9a61f3d99595`) and `reports/adaptive_stopping_overthinking/PX057_H5_DEVELOPMENT_PILOT_DETERMINATION_20260727.md`, both readable at Git revision `720d9e76a6142aae95ad1c31153d9ac38499fbb0`. The local evaluation's `/mechanism_selection_gate` and `/one_look_primary_policy` contain the decisive values. The later August 16 status and August 27 final paper retain this NO-GO; F1 does not replace it with a successful H5 result.

**Do not pitch as new or established:** simple two-answer stability; the existing confidence threshold or calibrated confidence benefit; generic H4-style risk-controlled policy selection; native chat plus a bounded check/answer/end schema; valid/nonempty-answer stability by itself; a last-valid-answer fallback as though it had never been proposed (the H4 determination already proposed it); or the 91% discovery result as the latest confirmation. A materially different follow-up must specify its incremental mechanism and compare it with these existing approaches.

## 6. What existing traces permit

The F1 raw archive retains **prompt, response, question/source identity, gold answer, extracted answer/correctness, generated token IDs, token count, chosen-token transition log probabilities, confidence, and response/token-binding hashes** for every round. It contains **2,369,390 generated tokens**. This audit checked all 1,319 unique IDs, rounds 1–8, saved correctness against the selected-row gold answer under both extractions, and equal token-ID/logprob/count lengths for all 10,552 raw records.

Without inference, these traces permit descriptive prefix-policy replay; answer-change/recovery and stability analyses; token-cap, empty-answer, and extraction sensitivity; selected-token likelihood proxies (including answer-span proxies if spans and tokenizer mapping are explicitly validated); and comparisons with fixed rounds and descriptive oracle ceilings. Gold labels may score outcomes but cannot enter deployable stopping features. New policy selection on these already inspected traces is development, requiring a separate frozen confirmation.

They **do not** contain full-vocabulary logits, so exact distributional entropy, alternative-token margins, counterfactual token probabilities, fresh verifier responses, alternate prompts, or altered continuation branches cannot be recovered from the saved chosen-token scores. Observational replay cannot establish gains from a policy that intervenes in how later rounds are generated. Token caps and blank-stability events identify protocol/measurement confounds; these counts alone do not prove that truncation caused a wrong answer, that a blank response concealed a correct intended answer, or that changing the interface would repair reasoning. A follow-up needs a substantive distinction beyond confidence thresholds, validity filtering, or generic risk-controlled stopping, plus competitive short/one-shot baselines and prospective harm limits. Literature comparison and the final candidate choice are outside this local audit.

## 7. Source identity and reproducibility note

The current working tree retains the result files but omits some historical F1/H4 source files. Those were read directly, without checkout or edits, using `git show 720d9e76a6142aae95ad1c31153d9ac38499fbb0:<path>`:

- `configs/px057_f1_full_gsm8k_qwen_prereg_20260818.json`: SHA-256 `0dbda2b21087870f36cf91db46cd7d45205a17c33a430ed39fb598536324c22b` (matches archived config binding).
- `scripts/px057_f1_common.py`: SHA-256 `dcef1bef1d238e10043c8e45d03f9b8573a305b98ce9e80e75bd7c502741427e`; confidence function at line 311.
- `configs/px057_h4_ltt_transfer_20260725.json` and `reports/adaptive_stopping_overthinking/PX057_H4_FINAL_DETERMINATION_20260727.md` (the latter SHA-256 `ce066726cd43b66db36e06d9c075661ba40ebacd22ecc3f302a56b9e7d65f4b3`).

Key local file hashes, independently observed on this audit:

| Evidence under the F1 closeout directory | SHA-256 |
|---|---|
| `final_closeout/PX057_F1_FINAL_CLOSEOUT_MANIFEST.json` | `f4cd0f02ae62f1dbedfdb3b7d935c6be4d9cb901b6452ef5888adfa8a7b55412` |
| `final_closeout/final_dual_extraction_adjudication.json` | `e0c71fbb6812dc22dca2eb33401ed3fc548a919cda4b9ce3af6e1db60c631724` |
| `merged_original/selected_rows.jsonl` | `71637458a718d84de51d0a7661dd71d65657f9512b021cdd6f772e3c978758b3` |
| `merged_original/reasoning_traces_original_parser.jsonl` | `a14093fce67c4a2d97d04054a5643c2819cb7ffe460f211cc570646e5801e6f4` |
| `final_closeout/reasoning_traces_blinded_review.jsonl` | `e9d9cc6a8c200f6908a411be90e0dc395e6836b552e9a82826e0f589bae89b3d` |
| `merged_original/raw_generations_private.jsonl` | `21c02c1b1c4873ee083f3c8c800c25c8b4bfbfe9d84f0dcb286a538d90a1cd21` |

Frozen claims are available at `/analysis/original_parser/{primary_1119,complete_1319_secondary}/metrics` and `/analysis/blinded_flagged_extraction/{primary_1119,complete_1319_secondary}/metrics` in the closeout manifest. Additional first-round, blank-harm, and token-cap counts above are explicitly September 18 descriptive calculations, not newly registered outcomes. No new bootstrap intervals, inference, scientific gate changes, or certificate claims were produced.
