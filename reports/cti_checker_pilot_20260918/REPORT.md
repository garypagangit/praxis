# CTI checker pilot: completed experiment

September 18, 2026.

## Decision

Selective evidence use met the practical pilot criteria, but this checker did not establish an advantage over every simpler comparator. The application has a signal; the proposed method is not yet a defensible improvement.

**Recorded status:** `USEFUL_SELECTION_SIGNAL_ADDED_VALUE_UNPROVEN`.

For this completed run, the practical recommendation is to carry the published relevance model with a locally calibrated cutoff and the frozen candidate into a fresh CTI test. The simpler relevance approach already preserves substantial benefit and limits mismatch loss to about one percentage point. Further complexity is not justified by a clear advantage in this pilot. See [NEXT_STEPS.md](NEXT_STEPS.md).

## What was actually run

The experiment used all 2,500 archived CTI questions and both fixed generators. New neural checker inference scored 15,000 retrieved facts twice: once with the question and once with the question plus all answer choices. New selectors were trained in five source-separated splits, with 1,500 training, 500 validation and 500 test questions per fit. Every question received exactly one held-out selector decision.

The selector decides whether to use the existing with-evidence or without-evidence answer. It does not produce new generator answers, remove individual facts, refuse to answer, or verify every logical condition in a security recommendation. All policies answer every question.

Correctness uses the released multiple-choice labels and the original frozen answer parser. Invalid outputs remain wrong in every denominator. These scores do not establish open-ended answer quality, analyst productivity or independently verified ground truth.

The candidate predicts whether evidence will help from question text, all choices and 38 numerical features of the actual retrieved evidence. It learns from correctness changes on training questions only. It never receives the test answer label, known source, source category, or inherited source-aware option scores.

## Overall accuracy

| Policy | Evidence used | Llama accuracy | Qwen accuracy |
|---|---:|---:|---:|
| No extra evidence | 0.00% | 64.72% | 62.84% |
| Always use evidence | 100.00% | 70.68% | 65.16% |
| Published relevance: question | 46.24% | 75.72% | 72.00% |
| Published relevance: question + choices | 42.44% | 76.04% | 71.76% |
| Question-only source selector | 61.24% | 76.16% | 71.60% |
| Question-only benefit selector | 51.32% | 75.56% | 71.92% |
| Proposed evidence-aware benefit selector | 41.16% | 76.96% | 72.48% |

These percentages share a denominator of 2,500 questions per model. The two model outcomes are paired observations, not 5,000 independent questions.

## Useful benefit and mismatch harm

The eligible group contains 1,578 ATT&CK-technique questions; the mismatch group contains 922 questions outside that source category. Category membership is an evaluation stratum, not a human judgment that every retrieved fact is applicable or inapplicable.

| Model / group | Always-evidence change | Candidate change [95% interval] |
|---|---:|---:|
| Llama / eligible | +18.19 pp | +19.20 pp [+16.92, +21.50] |
| Llama / mismatch | -14.97 pp | +0.33 pp [-0.33, +0.97] |
| Qwen / eligible | +13.88 pp | +15.27 pp [+13.19, +17.48] |
| Qwen / mismatch | -17.46 pp | +0.00 pp [-0.87, +0.83] |

Intervals use 5,000 paired resamples of source groups, holding fitted predictions fixed. They describe this retrospective result; they do not resolve cross-validation training dependence, project exposure or benchmark contamination.

## Did the added evidence features earn their complexity?

Every comparison below uses evidence on exactly 1029 questions (41.16%), with counts matched separately in each test fold. Positive differences favor the proposed checker. Computational costs are not equalized.

| Matched-use comparator | Llama difference | Qwen difference | Paired model-average difference [95% interval] |
|---|---:|---:|---:|
| Published relevance: question | +0.80 pp | +0.08 pp | +0.44 pp [-0.19, +1.10] |
| Published relevance: question + choices | +0.96 pp | +0.32 pp | +0.64 pp [+0.02, +1.29] |
| Question-only source selector | +4.52 pp | +4.24 pp | +4.38 pp [+3.29, +5.51] |
| Question-only benefit selector | +1.32 pp | +1.28 pp | +1.30 pp [+0.59, +2.04] |

## Prespecified checks

| Check | Llama | Qwen |
|---|---|---|
| Overall improvement at least 3 points | PASS | PASS |
| At least half the eligible benefit retained | PASS | PASS |
| Mismatch net loss no worse than 2 points | PASS | PASS |
| Mismatch interval lower bound above -5 points | PASS | PASS |

**Core criteria:** PASS. **Added value versus every matched comparator:** FAIL.

The added-value rule requires at least a one-point gain in each model against every comparator and a positive interval lower bound for the paired model average. These are exploratory decision rules, not multiplicity-adjusted confirmatory significance tests.

## Remaining mistakes and lost improvements

| Model | Evidence-induced mistakes retained | Such mistakes prevented | Helpful changes retained | Helpful changes lost |
|---|---:|---:|---:|---:|
| Llama | 42 | 247 | 348 | 90 |
| Qwen | 72 | 319 | 313 | 136 |

Preventing some mistakes is not enough: the same policy can discard helpful evidence. These counts are based on paired archived answers, not human judgments of evidence quality.

## Exposure sensitivity

Excluding the historical 500 development items leaves 2,000 questions. This is a sensitivity analysis without refitting. Those 2,000 questions were also later used by the project, so they are not a fresh confirmation sample.

| Model | Candidate gain over vanilla on remaining 2,000 |
|---|---:|
| Llama | +10.05 pp [+7.99, +12.13] |
| Qwen | +7.75 pp [+6.16, +9.43] |

## Cost and verification

- Local CPU relevance inference: 377.7 seconds for question-only and 510.0 seconds for question plus choices.
- All five selector fits and associated preprocessing/calibration: 6.2 seconds.
- Truncated pairs: 0 / 15,000 and 0 / 15,000.
- No paid cloud jobs were launched. These are local batch timings, not production latency or dollar-savings estimates.
- The candidate requires the neural relevance scores. Question-only selectors avoid that extra inference.
- Learning benefit requires paired generator outcomes for training; this pilot reused archived outcomes.
- Independent automated audit status: `PASS_PRE_AND_POST_FIT_AUDIT`. Details are in [REVIEW.json](REVIEW.json).

## What this establishes and what it leaves open

This is an executed test of a new selection policy over old model responses. The same corpus, generators and historical benchmark are reused. Source-separated splitting reduces direct source overlap but does not demonstrate transfer to a new benchmark or model.

The published comparator is [MiniLM](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2), a general relevance model. Full CRAG and the released CoRM-RAG critic were not run here. [CoRM-RAG](https://arxiv.org/html/2605.01302v1) already learns evidence utility, so that general idea cannot be claimed as a new algorithm. See [BASELINES.md](BASELINES.md) for the available checkpoints and resource limitations.

Academic originality, independent source/answer review and performance on new questions remain unresolved. Human review has not been performed. The diagnostic review packet provides a way to examine concrete failures; its examples are deliberately selected and cannot estimate population error rates.

## Reproduction and artifacts

[Protocol](PROTOCOL.md) · [frozen hashes](FREEZE.json) · [results](RESULTS.json) · [run instructions](README.md) · [human review packet](HUMAN_REVIEW.md)
