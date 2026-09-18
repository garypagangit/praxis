# CTI evidence-selection feasibility pilot

Specified September 18, 2026, before fitting selectors or inspecting their held-out predictions. This is a retrospective exploratory protocol, not a preregistered fresh replication. The original 2,500 questions and their aggregate outcomes are already known to this project.

## Question and scope

Can a small checker that sees the question and the actual retrieved evidence preserve useful CTI answer improvements while avoiding evidence-induced mistakes, and does it add value beyond a question-only selector or a published relevance model?

We run new checker inference and train new selectors locally. We replay archived answers from fixed Llama and Qwen generators. A selector chooses between each question's recorded vanilla and recorded query-only-evidence answer; it does not edit evidence or generate a new answer. Every policy answers every question. Evidence-use rate is not answer coverage or abstention.

No claim of a novel algorithm, superiority to CRAG/CoRM-RAG, fresh data, source-independent real-world generalization, or degree readiness follows from this pilot. Utility prediction is already represented in the literature, notably CoRM-RAG.

## Data and access

Use all 2,500 canonical CTIBench questions, with 1,578 technique-eligible and 922 mismatch questions. Each has archived answer pairs from both generators. The preparation script must verify joins, hashes, labels and published control totals. Keep the prior 500-item exposure indicator for a sensitivity report only; all 2,500 items have subsequently been used by this project.

Allowed checker features: question, all displayed option texts, and the actual query-only retrieved facts' text, kind and retrieval score. No correct option, answer correctness, source URL, eligibility, inherited source-pointer evidence, inherited option-support scores, or archived generator outputs enter feature computation. Training targets are explicitly separate. Source metadata is available only for splitting, the labeled source-classifier training target, and evaluation.

Group subtechniques with their parent ATT&CK technique. Other questions sharing a normalized source URL remain together, including the Manual group. Named document files are grouped after removing the `_partN.txt` suffix so parts of the same document cannot cross splits. Use StratifiedGroupKFold with five folds, shuffle=True and seed 20260918, stratified by eligibility. For outer test fold f, validation is fold (f+1) mod 5; the other three folds train. Every question is tested exactly once. Training/validation/test groups are disjoint for each fit. Fit vocabulary, scaling, regressors and source classifier on training rows only. The pretrained relevance scorer has no local outcome training.

## Frozen arms

1. Always vanilla and always evidence: fixed reference policies.
2. Published relevance: pinned cross-encoder/ms-marco-MiniLM-L6-v2 scores the question against each retrieved fact; the maximum fact score is the gate score. A second relevance arm includes all displayed options in the query text, allowing equal input access to the utility arms. This is an adaptation of a relevance model, not an implementation of CRAG. Both relevance arms enter the matched-use comparisons. The option-inclusive baseline was added during independent design review before any selector fitting or held-out result inspection; primary candidate features remain unchanged.
3. Question-only source classifier: word/character TF-IDF and balanced logistic regression, C=1, predicting training eligibility. This is a new grouped-fold baseline in the spirit of PX068, not its already-trained all-data model and not an exact reproduction of its calibration pipeline.
4. Question-only utility: Ridge(alpha=10, solver=lsqr) on word/character TF-IDF of question plus all options. Target is the mean of the two generators' paired correctness changes, bounded from -1 to 1.
5. **Primary candidate: evidence-aware utility.** Same question features and target, with additional standardized numerical features computed from actual retrieved facts: relevance score distribution, fact length/kinds, retrieval-score distribution, question/fact lexical overlap, displayed-option phrase/token support and discrimination, and explicit identifier overlap. This is a practical combination of known features and utility regression.

TF-IDF uses lowercase word 1-2 grams (max 20,000 features, min_df=2, sublinear_tf=True) and character-within-word 3-5 grams (max 30,000, min_df=2, sublinear_tf=True). Options are alphabetically serialized without gold labels. Dense features are standardized using training means and standard deviations. No outcome-driven feature additions or retries are permitted within this pilot.

For each arm/fold choose a threshold using validation scores only: consider 101 empirical score quantiles plus always/never; among thresholds with evidence use between 15% and 85% and mismatch net accuracy change at least -2 percentage points in each model, maximize mean paired utility across models, breaking ties toward lower evidence use. If none qualifies, choose never evidence and flag infeasible calibration. Eligible benefit is a final evaluation criterion, not an additional threshold-fitting constraint.

Also compare every learned baseline with the candidate at exactly the candidate's evidence count within each test fold, by taking the baseline's highest scores with deterministic ID tie-breaking. This uses test score ranks but no test outcomes. It isolates evidence-use rate; it does not equalize computational cost.

## Outcomes and decision criteria

Report both generators separately and their average, all questions and both eligibility strata. Count recovered wrong answers, evidence-induced mistakes, prevented mistakes and lost improvements. Report evidence use, correct-answer rate, and checker inference/training elapsed time; no invented cloud dollar savings.

Compute paired source-group bootstrap intervals (5,000 resamples, seed 20260918) with predictions fixed, preserving both model outcomes within each question. These are descriptive conditional intervals; shared cross-validation training dependence and public-benchmark exposure remain limitations. Report sensitivity excluding the historical 500 exposed IDs, without refitting or calling the remainder fresh.

The primary candidate has a useful bounded signal only if, for **each** generator:

- overall accuracy improves by at least 3 percentage points over vanilla;
- at least 50% of always-evidence's eligible net improvement survives;
- mismatch net loss is no worse than 2 percentage points, and its paired 95% interval lower bound exceeds -5 points.

An additional method-specific plausibility signal requires the candidate to beat **each** equal-evidence-use relevance (question-only and option-inclusive), question-only utility and source-classifier comparator by at least 1 percentage point in each generator, with a positive lower 95% bound for their paired average across the two generators. These are exploratory selection criteria, not multiplicity-adjusted confirmatory tests.

If only the first criteria pass, report that evidence selection looks useful but added value of this candidate is unproven. If they fail, report the failure without changing thresholds/features after seeing results. Preserve a negative outcome. A later method revision would require a separately labeled experiment.

## Resource and comparison boundary

Local CPU pilot, no paid cloud jobs. MiniLM is small enough for this machine. Published CRAG evaluator and CoRM-RAG critic checkpoints are available but substantially larger (approximately 2.8 GB and 5.21 GB); they are not run in this initial pilot. A positive result cannot establish superiority to them. A stronger-checker comparison and genuinely new source-disjoint questions are required before a practical-solution or novel-contribution claim.

## Frozen record and deliverables

Before fitting, write a manifest containing protocol/code/data hashes and split assignments. Save out-of-fold scores and decisions, per-arm metrics, paired comparisons, timing, runtime versions, the complete decision, and a plain-language report. Independent implementation review and checks of feature exclusion, group isolation and count reconstruction are required before interpreting the result.
