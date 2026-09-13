# Offline measurement amendment v1

This is a retrospective artifact repair and replay, not a prospective model experiment or evidence for the candidate's hypothesis. No model inference or AWS compute is needed. The source remains LLM4DC commit `082dcbf5304329ef1ff08f5830e4116256b00a59`. Original artifacts and previous audit results are immutable.

Before aggregate model scores are calculated, freeze the task contract manifest, scorer, independent controls and replay rules in Git. Record the commit used in the execution receipt. Contracts are derived from task text, reviewed query code, reference answers and clean/raw tables; do not use model correctness to select tasks or scoring rules.

## Measures and denominators

1. Preserve the original evaluator's exact-accuracy and F1 outputs, including exceptions, for comparison. They describe released-code behavior and are not trusted task success.
2. Report strict typed agreement and task-contract-aware agreement with released reference answers as separate diagnostics. Reject nonfinite reference values as invalid rather than silently equating NaN or deleting the task. Report all 142 assigned tasks, valid-reference denominators and bounds that show unresolved references explicitly.
3. Report purpose-aligned agreement only on contract-reviewed eligible tasks, with the excluded IDs and reasons frozen independently of model scores. Eligibility is conditional on source inspection and clean-query consistency; it is not independent validation of the underlying real-world labels.
4. Preserve missing answer records, null answers, query errors, missing generated CSVs and uncertain historical answer-to-CSV linkage as different states. Do not substitute raw-table answers for missing model outputs. A complete saved-answer file does not establish complete generated-output coverage.
5. Include the released dirty-table answer file as a comparison, report paired dirty-to-output corrections and damage on eligible common tasks, and retain domain-level counts. Do not infer 142 independent source datasets or attach IID significance claims.
6. Reexecute reviewed query functions on the four complete archived CoT.response CSV groups plus raw/clean controls using the frozen runtime and contract. This creates a new reproducible table-to-answer trace; it does not certify the provenance of historical saved answers. Reject malformed tables and explicitly retain query errors, default-return ambiguity and missing files. Never import or execute the upstream pipeline's top-level model/API code. Report fresh archived-table results separately from saved-answer rescoring.

## Scoring contract

Booleans and strings retain their types. Identifier strings are literal: no case folding, trimming or JSON coercion. Finite integers and floats may represent the same number. Counts use exact equality. Tolerances for measured quantities must be explicit in each task's manifest. Nested dictionary values are checked, not just keys. Sequence/set/multiset rules are explicit; dictionaries of parallel lists preserve row associations. Nonfinite predictions fail against valid references. Missing outputs and execution failures are scored unsuccessful and counted separately.

Table preservation checks require an explicit unique record identity and declared schema. They allow row permutations with stable IDs, account for additions/deletions and compare nulls as values. Missing schema or ambiguous identity is an explicit failure, not a dropped task. These general controls do not claim that the released tables possess usable stable IDs; task-specific applicability must be recorded.

## Decision rules

The mechanical repair passes only if all valid reference identity controls pass, all declared wrong-answer controls fail, and the independent manually specified controls pass. A passing comparator does not repair a mismatched query or validate an answer's provenance.

The baseline remains HOLD if task/query/reference ambiguity, provenance gaps or an insufficient useful specialist baseline prevents a defensible purpose-success claim. Existing saved outputs may establish only a diagnostic prerequisite. No new paid study follows automatically: source-table splits, closest-prior distinction, useful specialist behavior, hypothesis, effect thresholds and budget require a separate prospective protocol.

Publish our code, derived findings, source hashes, task IDs and receipts. Keep third-party source, data, task wording, reference answers and model answer text outside Git. Reproduction reads a verified local cache populated by the prior pinned inventory script.
