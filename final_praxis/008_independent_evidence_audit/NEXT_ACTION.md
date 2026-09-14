# Next: audit paired code variants and their executable outcome tests

The AutoDCWorkflow oracle repair and archived-output replay are complete. All 103 independent comparator controls pass, and 141 finite reference identity/wrong-answer pairs pass. The full 142-task source review retains 40 provisional purpose-aligned tasks, with 61 clear conflicts and 41 ambiguities. Fresh archived Gemma tables match 19/40 versus raw 9/40, giving 10 corrections and zero damage among the nine initially matching cases. No corruption defense was tested. [Completed results](oracle_repair/RESULTS.md).

**Decision: keep this release as a regression fixture; do not fund a full study on it.** Option008 remains HOLD on paid inference. Options004?007 remain closed, and no primary Praxis has qualified. The requested automatic review is complete; no manual review task is pending.

The next base is HumanEvalFix with a separately pinned HumanEval+ outcome suite. [Source review, audit RQ/hypothesis and exact sequence](oracle_repair/NEXT_BASE.md). The public paired canonical/buggy variants offer a way to test whether misleadingly selected passing checks can hide genuine defects. This is a candidate base, not an assumed reliable oracle or an established novel contribution.

Next actions are to pin the releases, align all 164 Python task IDs/signatures, execute canonical and buggy variants in bounded isolation, and automatically report original/expanded test outcomes and selective-witness feasibility. Retain incompatibilities and timeouts in the denominator. Freeze witness and reserved-outcome roles before critic models; evaluator gold and held-out failing tests cannot be supplied to the policy.

Only after this audit, an honest repair baseline and a close-prior comparison are resolved should a new inference protocol specify the acquisition policy, threat, source-problem split, matched budgets, sample size, recovery/harm thresholds and cost cap. Novelty against test selection, mutation testing and counterexample generation remains unverified. The next executable base audit is planned; it was not performed as part of the completed AutoDCWorkflow replay.
