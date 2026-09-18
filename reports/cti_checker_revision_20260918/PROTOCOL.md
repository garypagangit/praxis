# CTI answer-change checker: bounded development test

September 18, 2026. This is a new development experiment using previously inspected data. It cannot replace the failed frozen external test or establish fresh confirmation.

## Question and proposed change

Can an independent semantic verifier recognize which evidence-supported answer changes are useful better than the previous utility regressor? The previous checker captured only 5/42 and 8/55 available corrections while introducing 9/6 errors. This motivates inspecting the content supporting each proposed answer change.

The first implementation uses the published `cross-encoder/nli-deberta-v3-xsmall`, pinned to revision `a150876415327c80daeff35ca6f68f5ed8cf5c24`. It scores each actual retrieved fact against the fixed hypothesis `The answer to the question "{question}" is "{option}".` This question-to-hypothesis construction is an unvalidated adaptation. Natural-language inference (NLI) distinguishes entailment, contradiction, and neutral evidence; its output is not automatically a calibrated probability that an MCQ answer is correct.

## Qualification comes first

Before any dataset scoring, require all eight fixed synthetic checks in `semantic_checker.py` to pass: four ordinary entailment/contradiction checks and four checks of the question/answer hypothesis bridge. The cases and rule are fixed before inference. If any fail, retain the failure and stop this adaptation without scoring SecEval or claiming efficacy. Any alternative implementation requires a separately named protocol amendment. No change to these cases or their expected labels is permitted to rescue the attempt.

## Data and information access

Use the previous CTIBench fold 0 (500 questions) only for selecting policy thresholds. The other 2,000 old questions are not a newly independent test set. The already observed 1,247 SecEval questions serve only as an exposed development diagnostic. Project question, displayed options, retrieved fact text/kind/score, and the union of answer options actually changed by either model. Never give the verifier source labels, answer keys, correctness flags, or future policy decisions. Gold labels and outcomes remain in separate evaluation records.

The generator answers are the complete archived vanilla and six-fact answers, using the original frozen parser. Identify disagreements using answer strings, not correctness. Where answers agree, either route has the same answer and the checker need not run. Invalid evidence answers are rejected; invalid baseline answers with valid alternatives remain eligible. Candidate outputs must cite actual fact indices and preserve their text hashes.

## Policy selection fixed before scoring

If qualification passes, score calibration disagreements first. For each generator, accept its evidence answer only when its maximum fact-entailment score reaches a minimum support threshold and exceeds the baseline answer's maximum entailment by a positive margin. Invalid baseline support is zero. Thresholds are shared across the generators.

Search the fixed support grid `[0, .25, .5, .75, .9]` and margin grid `[0, .1, .25, .5]`, using strict `new_support - old_support > margin`, plus an always-retain-baseline candidate. Select maximum mean net corrections across the two generators on all 500 calibration questions; ties prefer fewer induced errors, then fewer changes, then higher support and margin. Freeze the chosen policy before opening SecEval score outputs. No threshold search on SecEval.

Report baseline, always evidence, previous frozen utility checker, previous relevance checker, and the revised checker on all 1,247 questions. Preserve all published-label disagreements. Metrics include accuracy, recovered answers, induced errors, rejected useful corrections, and verifier/model cost. Because the revised design has already generated both answers, accepted changes do not measure retrieval cost or answer coverage. It is not an equal-cost comparison with a pre-generation checker. Any further matched-decision comparison must be labeled exploratory.

## Boundaries and completion

This first stage keeps retrieval fixed to isolate the checker. Improved multi-source retrieval and additional generator calls are not represented as completed by this diagnostic. Their implementation must follow review of actual mismatch causes and use a distinct prospective protocol. Complete the existing independent human-review workflow; the 50-item form is ready, but no human judgments have been supplied.

If the semantic bridge cannot pass qualification, report `STOPPED_UNQUALIFIED_SEMANTIC_ADAPTATION`, not a negative benchmark accuracy result. If the bridge passes, report complete development metrics without declaring success on an untouched test or changing the previous failed result. No new AWS compute is required for this bounded CPU stage.

Primary model documentation: https://huggingface.co/cross-encoder/nli-deberta-v3-xsmall. This adaptation is neither the complete CoRM-RAG, PAVE, nor SURE-RAG system, and does not establish algorithmic novelty.
