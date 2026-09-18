# CTI decision after the external test

September 18, 2026. This decision incorporates the completed external run and supersedes the earlier pursuit recommendation only for the readiness of this checker version.

## In plain language

The problem is real: an AI can read a true security fact that does not apply to the question, then change a correct answer into a wrong one. We tested a checker that decides whether to give the AI those extra facts.

**This checker is not ready to support a claim that we have solved that problem.** On 1,247 different public security questions, it finished almost where the AI started:

| Model | Answer without extra facts | Answer selected by our checker | Change |
|---|---:|---:|---:|
| Llama 3.1 8B | 86.53% | 86.21% | -0.32 percentage points |
| Qwen 2.5 7B | 87.09% | 87.25% | +0.16 percentage points |

Both uncertainty intervals include zero. The average change is -0.08 percentage points, with a 95% interval from -0.52 to +0.36. The checker also failed the preset added-value criteria against all four simpler comparisons at the same evidence-use count.

## What did work, and what did not

Always adding retrieved facts reduced overall accuracy to 84.20% and 85.24%. The checker avoided most of that damage by giving facts to only 85 of 1,247 questions. But it also rejected many useful facts. Compared with always adding evidence, it prevented 62 and 72 errors while losing 37 and 47 potential corrections, for Llama and Qwen respectively.

For questions from ATT&CK sources, always adding evidence helped by +2.09 and +2.79 points. The checker retained only +0.70 points in each model, below the preset requirement to retain half the benefit. It passed the specified other-source loss limits; that does not mean it caused no harm.

The earlier 2,500-question pilot remains a positive result in its original setting: +12.24 and +9.64 points over answering without facts. Its added value over a simpler relevance checker was already unproven. The new test shows that this frozen version did not carry those gains to SecEval. It does not establish that every possible checker must fail.

## Praxis judgment

**Keep the CTI problem and the complete evidence record; do not promote this checker version as a successful new method or a confirmed top-three solution.** The evidence currently supports a bounded finding about when retrieved security facts help or harm and a failed attempt to select them automatically.

There is also a separate originality issue: learning whether evidence will help already appears in [CoRM-RAG](https://arxiv.org/html/2605.01302v1). This study did not implement full CoRM-RAG, CRAG, or Ahlert head-to-head. A generic “better checker” claim remains insufficient; this negative external result does not resolve the literature question in either direction.

## Next steps, in order

1. **Complete the prepared human review.** Two independent security reviewers assess the 50 blinded questions and the applicability of the retrieved facts. A third reviewer adjudicates disagreements. This checks whether ambiguous questions, released-answer errors, source-version differences, or missing conditions deserve investigation. No cause is established yet. Use the [review handoff](REVIEW_HANDOFF.md); no human judgments have been completed.
2. **Make the academic scope decision with the evidence in hand.** Show the adviser the earlier positive pilot, this external failure, and the prior-work overlap. Ask whether the controlled failure analysis and resulting engineering guidance are sufficient for the proposed applied contribution, or what specific additional capability must be demonstrated. This is a degree-scope decision, not a missing technical approval to run this completed experiment.
3. **Only pursue a revised method if the review identifies a concrete, testable gap.** Define which required condition the evidence checker misses, compare a proposed fix with strong published approaches under equal information access, and freeze the decision rules before testing on a separate untouched set. Any tuning on SecEval now makes it development data for that revision; it cannot serve as fresh confirmation again.

Do not spend on another unchanged run or lower the success thresholds after seeing these results. No new technique is claimed as novel in this closeout.

## Evidence

- [Full results and limitations](REPORT.md), [machine-readable results](RESULTS.json), and [independent reconstruction audit](INDEPENDENT_RESULTS_AUDIT.json).
- [Earlier pilot](../cti_checker_pilot_20260918/REPORT.md) and [prior-work assessment](../cti_checker_gap_review_20260918/RESEARCH_GAP.md).
- [AWS run and recovery](OPERATIONS.md). The single GPU run completed; the host was verified stopped. Estimated compute is about $0.59, not an invoice.

