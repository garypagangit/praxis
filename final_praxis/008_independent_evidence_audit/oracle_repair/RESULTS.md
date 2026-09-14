# Offline oracle repair and replay

**Completed: the comparator repair, independent review and archived-output replay. Investment decision: HOLD on a paid Option 008 study. Keep this release as a small diagnostic fixture; do not adopt it as the primary Praxis benchmark.** The replay finds useful corrections, but too few tasks have sufficiently clear contracts, and the proposed defense has not been tested or established as novel.

The source-only task contract, comparator, independent controls, input manifests and both replay programs were committed and pushed as `66e125942898974a59550b15e900e7064687c855` before aggregate output scoring. No contract, comparator, eligibility or threshold changed after seeing replay scores. This is a retrospective measurement amendment, not a preregistered new-model experiment or a reproduction of the paper's headline results.

## Completed evidence

- All 103 independent synthetic comparator checks pass. They cover types, counts beyond floating-point precision, nested values, record identity, row order, duplicate membership, nulls, errors and paired columns. The first68/70 result and subsequent fixes are preserved.
- All 141 finite reference identities receive credit, and all 141 deliberately wrong controls are rejected. Reference 104 contains NaN and remains explicitly invalid. The original evaluator credited 111/142 identities.
- All 142 task/purpose/query/reference contracts are recorded. **40 are provisionally aligned, 61 have clear observable conflicts, and 41 are ambiguous.** These classifications came from source/clean-table review before output scoring. The 40-task result is a conditional selected-task diagnostic, not certified purpose success.
- All 53 synthetic query-semantic controls reproduce their declared outcomes: 28 matching controls and 25 expected discrepancies. All 284 raw/clean return-value controls are accounted for: 282 valid controls reproduce, while the two nonfinite controls for raw/clean ID 104 remain invalid comparisons. A matching query/reference control alone does not establish that the query answers the written purpose.
- The saved-answer replay accounts for 1,562 assigned file/task cells across 11 files: 1,509 present records and 53 missing records. It preserves upstream, typed and contract-aware diagnostics separately.
- The archived-table replay accounts for 852 table/task cells: 284 raw/clean controls and 568 archived model tables. Both control gates pass before model-table replay. The instrumented runner records swallowed exceptions and never falls back to raw tables for missing outputs.
- New model/API calls: **0**. New AWS compute jobs: **0**. Third-party data and answer text remain outside Git; the published package contains our code, synthetic fixtures, derived results, task IDs, hashes and receipts.

## Fresh replay of archived tables

These are current executions of reviewed queries against pinned archived CSVs. Group names are repository labels, not a new controlled comparison of model capability. The 40 provisionally aligned tasks were fixed before replay. Their raw tables match 9 references and miss 31; clean controls match 40/40.

| Archived group | Agreement on 40 provisional tasks | Raw-wrong tasks corrected /31 | Raw-correct tasks damaged /9 | Agreement on 141 finite references, all tasks |
|---|---:|---:|---:|---:|
| Raw tables | 9/40 | — | — | 12/141 |
| Clean controls | 40/40 | 31/31 | 0/9 | 141/141 |
| gemma2 | 19/40 | 10/31 | 0/9 | 44/141 |
| gemma2base | 9/40 | 0/31 | 0/9 | 15/141 |
| llama3.1 | 14/40 | 5/31 | 0/9 | 36/141 |
| mistral | 10/40 | 1/31 | 0/9 | 18/141 |

The all-task column measures agreement with the released executable observable; 102 tasks are excluded from purpose-aligned interpretation and reference 104 is invalid. All 142 assigned tasks remain in the per-cell reports. Neither the selected denominator nor agreement with released references establishes generalization. Tasks share six source-corpus groups, so no IID confidence interval or significance claim is made.

The Gemma archive supplies 10 useful correction examples and retains the 9 initially matching cases in this subset. That is a useful feasibility observation. **No specialist corruption, selectively disclosed evidence, adversarial revision or proposed verification policy was exercised.** Zero damage in this unperturbed replay is not evidence of a defense, and nine initially correct cases are a small preservation test bed.

## Errors and provenance remain visible

| Group | Assigned tables | Caught query exceptions | Nonfinite returns | Null returns | Malformed CSVs |
|---|---:|---:|---:|---:|---:|
| Raw | 142 | 9 | 1 | 0 | 0 |
| Clean | 142 | 0 | 1 | 0 | 0 |
| gemma2 | 142 | 2 | 5 | 0 | 0 |
| gemma2base | 142 | 3 | 1 | 1 | 0 |
| llama3.1 | 142 | 6 | 1 | 0 | 2 |
| mistral | 142 | 3 | 7 | 1 | 0 |

Execution states and scoring states are different: invalid reference 104 takes precedence in scoring while its execution state is still recorded. Malformed Llama CSVs 150/154 remain assigned failures;150 is in the provisional subset. Exception instrumentation preserves successful-path operations and records every executed `except` handler; any handler event prevents task-success credit. No error is silently replaced with a successful empty answer.

The source inventory verified 1,543 files (15,932,184 bytes), including 1,235 archived generated CSVs across the inspected groups. Historical saved-answer bindings remain unverified: the active source script can write an unprefixed answer filename from ablation inputs, while notebooks suggest a different intended label. Saved-answer rescoring and fresh CSV replay are therefore separate outputs. Their aggregate reference-agreement counts happen to coincide for the four complete groups; individual answers do not all match. Fresh-to-saved strict agreement is 136/142 Gemma,141/142 Gemma-base,137/140 comparable Llama returns, and 135/142 Mistral. Nonfinite saved references count as invalid comparisons, not proven disagreements or evidence of historical source identity.

The provenance report separately records missing archived outputs, conditional raw fallback in upstream code and present files that equal raw cells. It does not infer which fallback actually produced an old answer. All third-party file hashes and the newly recomputed table-to-answer trace are retained for reproducibility.

## What to invest in next

Keep the research question about independently chosen checks against selectively presented valid evidence. Allocate the next effort to a cleaner public benchmark and a distinct acquisition policy, not more repair of this release or scaling its model calls. This is a research allocation decision, not a claim that AutoDCWorkflow's entire study is invalid.

The next candidate base is [HumanEvalFix with additional HumanEval+ checks](NEXT_BASE.md). Its public correct/buggy code pairs offer a concrete way to audit selective passing-test evidence before calling a critic model. This next base has been source-reviewed only; its executable compatibility and paired outcomes have not yet been qualified here.

Before another paid pilot, require a defensible task-success oracle, sufficient independently grouped correct and incorrect cases, an honest specialist that makes useful corrections, and a policy distinguishable from existing query contracts and code-executing evidence gates. Freeze the threat, source-group splits, matched-budget controls, effect thresholds and cost cap prospectively. Gold and clean tables remain evaluator-only. The current40 tasks can serve as regression fixtures; expanding or relabeling them would be a separate benchmark amendment.

Options 004–007 remain closed. Option 008 remains a candidate with a completed offline prerequisite and a HOLD on inference. No primary publishable Praxis or novel defense has qualified.

## Reproduction and evidence

Use Python3.11.9 and [requirements.txt](requirements.txt). Populate the verified public source cache using the prior [artifact-audit scripts](../artifact_audit/README.md), then follow [contract reproduction](contract/CONTRACT.md) and [provenance/reexecution instructions](provenance/README.md). Keep downloaded files and private answer outputs outside tracked publication folders. The programs enforce their frozen Git inputs and fail on hash mismatches.

```powershell
python replay.py --audit-root PATH_TO_ARTIFACT_AUDIT --output-dir OUTPUT_SAVED --frozen-commit 66e125942898974a59550b15e900e7064687c855
python provenance/reexecute_tables.py --audit-root PATH_TO_ARTIFACT_AUDIT --model-cache PATH_TO_MODEL_CACHE --private-controls PRIVATE_RAW_CLEAN_CONTROLS.json --output-dir OUTPUT_TABLES --private-output-dir PRIVATE_ANSWERS --frozen-commit 66e125942898974a59550b15e900e7064687c855
```

Evidence: [repair protocol](REPAIR_PROTOCOL.md), [contract manifest](contract/TASK_CONTRACTS.json), [independent review](validation/REVIEW.md), [saved-answer summary](completed/saved_answers/REPLAY_SUMMARY.json), [fresh archived-table summary](completed/archived_tables/TABLE_REPLAY_SUMMARY.json), [saved-answer receipt](completed/saved_answers/REPLAY_RECEIPT.json), [table-replay receipt](completed/archived_tables/TABLE_REPLAY_RECEIPT.json). Receipts bind the code, inputs, environment and outputs; they are not cloud billing receipts.
