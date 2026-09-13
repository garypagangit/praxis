# Option 008: independent evidence selection under specialist corruption

**Stage: HOLD after completed no-model artifact qualification. No primary Praxis selected.** This is a new candidate after closing the failed 004-007 implementations, including the MiCRo completion-format pilot. Its numbered branch is `Final-Praxis-008-Independent-Evidence-Audit`.

The research direction is an external specialist that supplies truthful but selectively chosen evidence for a harmful change. A verifier would choose its own checks from the original task and the proposed change. The open question is whether an actual acquisition policy can preserve correct outputs and still accept useful corrections at a fixed budget. This is more specific than asking whether another agent changes an answer, but specificity alone is not novelty.

[The literature reassessment](LITERATURE_REASSESSMENT.md) identifies close overlap. PBRC already discusses cherry-picked evidence and query-policy contracts; a new evidence gate or mandatory counter-query would not suffice. The June2026 data-cleaning debate paper already uses code-execution critics and evidence-backed revision. A prospective contribution must distinguish its acquisition policy, threat assumptions and task-success evidence from those works.

The immediate action is an offline source/data/evaluator audit of the original AutoDCWorkflow release at commit `082dcbf5304329ef1ff08f5830e4116256b00a59`. Public purpose definitions, raw/clean tables, saved outputs and deterministic evaluator code can be inspected without new model calls. The June debate paper's supplementary implementation has not been independently verified as publicly available; it is not represented as reproduced. The original repository's reuse terms also need clearer provenance before calling it a permissive release. Third-party source/data remain outside this branch; scripts fetch pinned sources for inspection and record hashes.

## Candidate research question and hypothesis

RQ: Under a fixed verification budget, can independently selected checks prevent harmful revisions caused by selectively presented valid evidence, while retaining corrections that require a useful specialist?

Candidate H1: A purpose- and edit-dependent acquisition policy reduces correct-to-wrong task outcomes relative to peer-selected evidence and fixed query contracts, without an unacceptable loss of wrong-to-correct outcomes, at matched tool/model budgets. Exact sample size, acceptable recovery loss and decision thresholds must be frozen in a separate prospective protocol before any new model processing. No significance or general guarantee is asserted here.

The clean tables and reference answers are evaluation-only oracles. They must not be supplied to the generator, specialist, verifier or acquisition policy. Partition future development/test work by source table, not individual purpose, and retain all assigned tasks. Do not tune against held-out model results or redefine upstream scores as corrected scores.

Required comparisons include an intact baseline, specialist bypass, grounded evidence gating, fixed task-based query contracts, matched-budget random independent checks, and the proposed policy. Separate honest criticism, misleading interpretation and selectively reported valid evidence. Measure task-purpose correctness and preserved data, rather than only valid column names or agent agreement. A useful intact specialist is a prerequisite. No benefits from buying extra calls should be mislabeled as a better policy.

## Current release check

The offline audit tests correct and wrong answers across actual answer types, row permutation/alignment, missing gold values and execution errors. It inventories purpose-to-table mappings and available saved outputs. Upstream behavior is preserved, and any corrected oracle must be independently checked before replaying saved outputs or running new models. An unreliable evaluator or missing baseline evidence returns HOLD, not permission to start a cloud experiment.

The [completed audit](artifact_audit/README.md) returns **HOLD**: only111/142 released reference answers receive credit against themselves; dictionary-value and row/null tests expose additional measurement limits. All142 raw/clean pairs are available, but saved-output coverage varies. These are findings about released functions and artifacts, not a reproduction or refutation of all paper results. See [NEXT_ACTION.md](NEXT_ACTION.md) for the exact repair prerequisite. The next paid study remains unregistered and unstarted until the baseline/evaluator and novelty conditions are met. This branch is a research candidate and reproducibility audit, not a claim that the proposed idea is publishable.
