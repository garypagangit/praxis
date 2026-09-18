# Decision after the executed CTI checker pilot

## Plain-language answer

Yes, choosing when to use extra security information is a plausible practical direction. This experiment supplies a working retrospective example. It also shows that an existing relevance model, combined with a cutoff learned from development examples, already handles most of the observed problem.

The proposed checker improved Llama/Qwen accuracy to 76.96%/72.48%. At the same evidence-use rate, the existing relevance model reached 76.16%/72.40%. The proposed improvement averaged 0.44 percentage points, with a conditional 95% interval from -0.19 to +1.10 points. That does not establish a reliable extra advantage across the two models. This pilot's explicit added-value criterion failed.

**Continue the applied CTI investigation. Hold the claim that this custom checker is a new, better method.** No further feature or threshold search was performed after this result.

## Next experiment worth doing

1. Keep the published relevance gate and this candidate unchanged as the main comparison. Include no-evidence and always-evidence controls. Choose a single final deployment fit using development data only; do not pick the best of the five test folds.
2. Use newly acquired or independently authored CTI questions whose source-document families were not used in this project. Log source dates, provenance and known exposure. Group whole documents and related technique families before any split. Public availability does not guarantee absence from model pretraining.
3. Obtain independent review of answer keys and whether the retrieved facts actually support the question. The included HUMAN_REVIEW.md makes a small diagnostic review possible now; it is not the fresh test set. Actual human review is still pending.
4. Qualify answer scoring before the new generator run. Keep malformed outputs in the denominator and separate formatting failures from substantive errors. The previous Athena router run's answer-format problems cannot be repaired by calling its archived results fresh confirmation.
5. Use the same retrieval corpus, question/option access, generator settings and evaluation items across policies. Threshold selection must use a separate development set. Run the held-out test once and preserve all outputs, including failures.
6. Plan the number of independent source groups from a paired power/precision calculation. The tiny observed custom-versus-relevance difference may require many more questions than this pilot. A small fresh sample can test large benefit and mismatch harm, but cannot automatically certify a sub-percentage-point advantage.
7. Record net accuracy, individual harmful and helpful changes, evidence use, useful-answer retention, invalid outputs and end-to-end cost. A result that only rejects more evidence or sees extra metadata does not establish a better checker.

If a claim of methodological improvement is pursued, add the released CoRM-RAG evidence critic and an appropriate CRAG evaluator adaptation after resource qualification. The [baseline record](BASELINES.md) contains their official artifacts. This pilot did not run them. A stronger comparator is a necessary next comparison for a superiority claim, not an obstacle to reporting the useful bounded result already obtained.

## Human work and how to accomplish it

- **Cybersecurity review:** give a reviewer HUMAN_REVIEW.md without REVIEW_SAMPLE_KEY.json. Have them record supported options, missing conditions, authoritative references and uncertainty. Save the completed packet under a new filename and record actual reviewer/date; do not replace blank fields with AI guesses.
- **Praxis scope:** give the adviser REPORT.md and the prior pursuit-decision memo. Ask whether the controlled applied evidence-selection workflow and fresh evaluation provide the required original contribution, or whether a demonstrated method improvement is required. No faculty decision is recorded here.

These tasks are follow-up requirements for stronger scientific/academic claims. The authorized feasibility pilot itself is complete, its outputs are preserved, and its independent automated audit passed.
