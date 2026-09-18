# CTI checker: external benchmark validation

Specified September 18, 2026, before any generator answers on this dataset. This is a prospective test of a frozen selector on questions newly introduced to this project. It is not a new algorithm, a private test set, or a source-document-disjoint replication.

## Practical question

Can a checker learned from the previous CTI experiment decide when retrieved ATT&CK facts will help a different set of security questions? We test whether its gains survive the change of questions and whether it improves on a published relevance checker with the same evidence-use rate.

Every policy answers every question. The policy selects the generator's answer with retrieved evidence or its answer without evidence. Evidence-use rate is not abstention or answer coverage. Generating both answers enables a paired evaluation; a deployed policy would generate only its selected condition.

## Data fixed before generator inference

Use `XuanwuAI/SecEval`, revision `205dab7b0888a06f4b53ca7d9c7093e1326683e1`, file `questions.json`, SHA-256 `194c3a511104be422a678675a71d44315d0c0392b040745155aeebc321e692e0`. The actual pinned file has 2,189 rows. Retain all 1,247 rows with exactly four distinct displayed options and exactly one released A-D answer. Exclude the other 942 based only on this format rule. No generator result selects or removes a question.

The retained inventory contains 287 ATT&CK-source questions and 960 from other source families. Of the latter, 809 are from eight broad source families absent from the audited historical inventory; 151 are CWE. Source metadata is coarse: ATT&CK-source does not establish technique eligibility or independence from training source documents. Report this distinction explicitly.

Audit exact normalized questions and question-plus-unordered-options against 6,376 historical CTIBench, Athena and PX071 records. Also report word 1–2 gram TF-IDF nearest-question similarities. These checks cannot establish semantic independence or absence from model pretraining. The vocabulary used for this audit never enters a checker. Record all source hashes in `DATA_AUDIT.json`.

Use the unchanged query-only lexical retriever and pinned ATT&CK 19.1 corpus. Its query consists of the question and all displayed options; "query-only" excludes gold answers and source pointers. Retrieve six facts and verify all 1,247 retrieval results are unchanged after perturbing answer/source metadata. Generator and checker inputs exclude gold answers, eligibility labels, source metadata, original generator outputs, inherited option-support fields and source-pointer retrieval. Safe checker records contain only ID, question, displayed options and actual evidence text/kind/score. Keep released labels separately in `sealed_labels.jsonl`; this separation is an execution contract, not cryptographic concealment from the research team.

## Fixed checkers

Freeze the single deployment fit already exported from old CTIBench data: old SPLITS fold 0 is calibration (500 questions); folds 1–4 are training (2,000). This is a predetermined fit, not the best of several fits. Use the pilot's unchanged feature definitions, TF-IDF parameters, standardized dense features, Ridge alpha 10 and balanced logistic-regression C=1. Calibration searches and tie breaks are the old pilot's rule. No new labels, generator answers or outcome-based tuning enter training or calibration.

Run both published MiniLM relevance adaptations at revision `233902d25c440f23af6f7d6e94d2946bac0bee0a`: question-only and question-plus-all-displayed-options. Each policy uses the maximum of six fact scores. These are relevance baselines, not full CRAG implementations. Save all fact scores. Compare:

1. Always vanilla and always evidence.
2. Published relevance, question-only and option-inclusive, using their old calibrated thresholds.
3. Question-only source classifier.
4. Question-only utility regressor.
5. Primary candidate: evidence-aware utility regressor.

Use `deployment.joblib` SHA-256 `438fd2a5b81a559c03f192664c5882e8518c0a1056f45bdf295907aeee084db1` and thresholds recorded in `DEPLOYMENT_METADATA.json`. For each of the four checker comparators, also select exactly the candidate's total evidence count by descending score with ascending ID tie-breaks. This uses new scores but no labels/outcomes and equalizes evidence count, not compute cost. No tuning on new outcome subgroups.

## Generator settings and format qualification

Use original frozen prompt construction, verified byte-for-byte on all 2,500 old vanilla/evidence prompt pairs. Use unchanged generation helper SHA-256 `cd94f3da527c0e35ce2c408b2d03865d62cb195c608656eb11a08ccc187178f9`.

- Qwen/Qwen2.5-7B-Instruct, revision `a09a35458c702b33eeacc393d103063234e8bc28`.
- meta-llama/Llama-3.1-8B-Instruct, revision `0e9e39f249a16976918f6564b8830bc894c89659`.
- CUDA, float16, greedy decoding, batch size 2, input limit 4,096 and maximum eight generated tokens. Record actual library versions and hardware. Token counting must match generation's special-token behavior; reject oversized prompts rather than silently truncate.

Before any new test inference, both models must each return 16 parsable outputs on eight old qualification questions in two conditions. Select the first four numeric IDs from each old eligibility stratum without consulting answer correctness. Qualification checks response format only. Freeze the resulting IDs and input hashes. If either model fails, stop before fresh inference and report the failure. A changed format or parser requires a separately named protocol, never silent repair of this attempt.

Then obtain both conditions for all 1,247 questions in both models: 4,988 fresh outputs plus 32 qualification outputs. Record raw output, parsed answer, validity, rendered-prompt hash, model revision and timing. The original parser defines validity. Invalid fresh outputs are incorrect, never dropped or retried. The test is complete only when the full unique inventory, expected hashes and successful runtime receipt match. Timeouts/partial outputs cannot support a complete benchmark result. There is no implicit outcome-driven rerun.

## Analysis and decisions fixed before answers

Report accuracy, paired change from vanilla, evidence-use count/rate, recovered answers, evidence-induced errors, prevented errors and lost improvements. Separate each model, their mean, all questions, ATT&CK-source questions, other-source questions and the 809 questions from previously absent broad families. Report individual source-family results as descriptive diagnostics.

Use 5,000 paired question bootstrap resamples, seed 20260918, preserving the two model outcomes together. Condition on the observed coarse-source counts by resampling within source family. ATT&CK has no finer released document grouping; do not call these source-cluster intervals or infer independence of source documents. Intervals condition on this benchmark, frozen policy and released labels. Report 95% percentile intervals and do not interpret exploratory comparisons as multiplicity-adjusted confirmation.

Retain the pilot's conservative practical-benefit thresholds as an external transport diagnostic. For each model, the candidate must:

- improve overall accuracy over vanilla by at least three percentage points;
- improve ATT&CK-source accuracy and retain at least half of always-evidence's ATT&CK-source net gain when that gain is positive;
- lose no more than two percentage points on other-source questions, with a paired 95% interval lower bound strictly above minus five points.

If always-evidence has no positive ATT&CK-source benefit, the benefit-retention condition fails: do not claim preserved useful benefit from avoiding a harmful intervention. The new broad source split differs from the old technique-eligibility split, so this is a deliberately stringent transport test, not an exact eligibility replication.

Additional method-specific plausibility requires the candidate to exceed **each** of the four matched-evidence-count checkers by at least one percentage point in **each** generator, and each comparison's mean across generators must have a positive lower 95% bound. These criteria were not met in the original pilot. Passing here would justify follow-up, not establish algorithmic novelty or superiority to full CRAG or CoRM-RAG.

Classify complete outcomes as `EXTERNAL_USEFUL_SIGNAL_AND_ADDED_VALUE`, `EXTERNAL_USEFUL_SIGNAL_ADDED_VALUE_UNPROVEN`, or `EXTERNAL_TRANSPORT_CRITERIA_NOT_MET`. Always publish constituent results: failing a combined gate does not mean every practical effect is zero. An incomplete run is `EXTERNAL_INCOMPLETE` with no full-result classification.

## Human review and limitations

SecEval is an older public benchmark whose authors describe GPT-4-generated/calibrated questions and labels. Treat released-answer accuracy as benchmark agreement, not independently verified security truth. Its source era differs from ATT&CK 19.1. Do not overwrite disputed labels after observing model errors. Shared ATT&CK/CWE sources and model pretraining exposure remain possible.

Prepare a blinded human review packet before outcome inspection: five questions per source family selected by deterministic SHA-256 rank of `20260918|ID` (50 total across ten families). Include question/options/evidence, omit released label and model decisions. Two security reviewers independently supply answer, supporting source, evidence applicability and ambiguity; an adjudicator resolves disagreements. Record reviewer identity/date, original independent decisions and adjudication. No human review is claimed until completed. A model-produced review is not a human sign-off. This packet is a targeted quality diagnostic, not an unbiased population accuracy estimate.

Stronger published checker comparisons and independently reviewed, source-document-disjoint applied questions remain necessary before a defensible final Praxis contribution claim. Current work tests feasibility of transporting a practical evidence-use policy.

## Freeze and resource record

Before paid inference, commit this protocol, the runtime manifest and exact runtime files in an isolated Git worktree. Bind checker artifacts, safe inputs, labels and analysis code by a separate scientific hash record; only label-free generator prompts go to the GPU worker. Record the bounded operational plan separately in `CLOUD_LAUNCHER.md` and the committed runtime freeze. Verify AWS account, existing designated host state and automatic shutdown before starting. Preserve results and verify STOPPED after the attempt.

Dataset/code attribution: [SecEval repository](https://github.com/XuanwuAI/SecEval), [pinned dataset](https://huggingface.co/datasets/XuanwuAI/SecEval/tree/205dab7b0888a06f4b53ca7d9c7093e1326683e1). Dataset license: CC BY-NC-SA 4.0; code license is separate.
