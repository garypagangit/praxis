# Option 008: independent evidence selection under specialist corruption

**Stage: offline oracle repair and archived-output replay completed; HOLD on paid inference. No primary Praxis selected.** This is a new candidate after closing the failed 004-007 implementations, including the MiCRo completion-format pilot. Its numbered branch is `Final-Praxis-008-Independent-Evidence-Audit`.

The research direction is an external specialist that supplies truthful but selectively chosen evidence for a harmful change. A verifier would choose its own checks from the original task and the proposed change. The open question is whether an actual acquisition policy can preserve correct outputs and still accept useful corrections at a fixed budget. This is more specific than asking whether another agent changes an answer, but specificity alone is not novelty.

[The literature reassessment](LITERATURE_REASSESSMENT.md) identifies close overlap. PBRC already discusses cherry-picked evidence and query-policy contracts; a new evidence gate or mandatory counter-query would not suffice. The June2026 data-cleaning debate paper already uses code-execution critics and evidence-backed revision. A prospective contribution must distinguish its acquisition policy, threat assumptions and task-success evidence from those works.

The AutoDCWorkflow source/data audit, oracle repair and archived-output replay are complete at source commit `082dcbf5304329ef1ff08f5830e4116256b00a59`. The repaired comparator passes 103 independent controls. Source review retains only 40 of 142 tasks as provisionally purpose aligned; 61 have clear conflicts and 41 are ambiguous. Archived Gemma tables match 19/40 references versus 9/40 for raw tables, supplying 10 useful corrections but no tested corruption defense. [Completed repair and replay](oracle_repair/RESULTS.md).

## Candidate research question and hypothesis

RQ: Under a fixed verification budget, can independently selected checks prevent harmful revisions caused by selectively presented valid evidence, while retaining corrections that require a useful specialist?

Candidate H1: A purpose- and edit-dependent acquisition policy reduces correct-to-wrong task outcomes relative to peer-selected evidence and fixed query contracts, without an unacceptable loss of wrong-to-correct outcomes, at matched tool/model budgets. Exact sample size, acceptable recovery loss and decision thresholds must be frozen in a separate prospective protocol before any new model processing. No significance or general guarantee is asserted here.

The clean tables and reference answers are evaluation-only oracles. They must not be supplied to the generator, specialist, verifier or acquisition policy. Partition future development/test work by source table, not individual purpose, and retain all assigned tasks. Do not tune against held-out model results or redefine upstream scores as corrected scores.

Required comparisons include an intact baseline, specialist bypass, grounded evidence gating, fixed task-based query contracts, matched-budget random independent checks, and the proposed policy. Separate honest criticism, misleading interpretation and selectively reported valid evidence. Measure task-purpose correctness and preserved data, rather than only valid column names or agent agreement. A useful intact specialist is a prerequisite. No benefits from buying extra calls should be mislabeled as a better policy.

## Current release check

The offline audit tests correct and wrong answers across actual answer types, row permutation/alignment, missing gold values and execution errors. It inventories purpose-to-table mappings and available saved outputs. Upstream behavior is preserved, and any corrected oracle must be independently checked before replaying saved outputs or running new models. An unreliable evaluator or missing baseline evidence returns HOLD, not permission to start a cloud experiment.

The initial [artifact audit](artifact_audit/README.md) remains preserved. Its integer, nested-value and record-control defects motivated the now completed repair. All 141 finite reference identities pass; reference104 remains invalid because it contains NaN. The replay accounts for all tasks, missing records, malformed CSVs and caught query errors; its 40-task subset is conditional rather than certified purpose success. No new model calls were made. Keep this release as a regression fixture and move the next base audit to [HumanEvalFix with HumanEval+ checks](oracle_repair/NEXT_BASE.md). This is a candidate base pending executable qualification, not a newly selected primary Praxis.
