# Next base audit: HumanEvalFix with HumanEval+ checks

**Decision: audit this base next without model calls. It is not yet a qualified benchmark or a new model experiment.** Keep the research direction and Option008 branch; retain the completed AutoDCWorkflow replay as a regression fixture and negative investment finding.

HumanEvalPack provides 164 Python tasks with canonical and human-inserted buggy code, bug categories, unit tests, separate example tests and task descriptions. That supplies paired correct/wrong starting variants before generating new model outputs. The six language versions share underlying tasks and must not be counted as 984 independent problems. [Official dataset](https://huggingface.co/datasets/bigcode/humanevalpack)

The OctoPack paper and official code describe HumanEvalFix and provide evaluation configurations, including repair from task descriptions or tests. Public model baselines exist, but their per-sample archives and useful correction behavior have not been verified in this workspace. [Paper](https://arxiv.org/abs/2308.07124), [implementation](https://github.com/bigcode-project/octopack)

EvalPlus supplies additional executable tests and records oracle corrections. Treat its strengthened outcome suite as a separately pinned measurement layer, not an infallible specification. Compatibility with the HumanEvalPack variants must be tested rather than assumed. Finite test passing cannot prove arbitrary-program correctness. [Official EvalPlus repository](https://github.com/evalplus/evalplus)

## Audit question and hypothesis

Audit RQ: After aligning exact task IDs, entry points and test versions, do the released canonical/buggy pairs provide reproducible cases where incorrect code passes some truthful checks but fails other reserved checks?

Audit hypothesis: A nonempty, explicitly enumerated set of compatible pairs will expose this selective-evidence mechanism. This is a base-qualification hypothesis, not the novel Praxis contribution. Report the full 164-task accounting; a nonempty set alone does not justify a sufficiently powered model experiment.

## Automated audit sequence

1. Pin and hash the dataset revision, paper evaluation code, HumanEval+ data and evaluator. Inventory all Python IDs, signatures, bug types, tests and examples. Keep original variants unchanged.
2. Run code in a bounded isolated execution environment with per-case time/memory limits and no credentials or external network. Record canonical and buggy outcomes on original and additional suites, retaining syntax errors, timeouts, incompatible IDs and oracle discrepancies.
3. Record per-test outcomes. Count incorrect variants with both genuinely passing witnesses and disjoint failing checks. Keep witness selection separate from reserved outcome evaluation. Tests and canonical answers designated evaluator-only must never enter a future critic/controller prompt.
4. Automatically review input hashes, coverage, outcome repeatability and discrepancies. Publish aggregate and per-task metadata; do not silently repair failed labels or remove tasks from denominators.
5. Before model inference, establish a useful honest repair baseline and compare the acquisition policy against existing regression-test selection, mutation testing, counterexample generation, fixed checking and randomly selected checks. Split by underlying problem across languages and variants.

The proposed later study would ask whether task- and edit-dependent independent checks reduce acceptance of harmful revisions supported by selectively disclosed valid tests, while retaining useful repairs at the same checking/model budget. Its novelty remains unestablished. A policy that simply runs more tests or uses known failing evaluation cases would not answer that research question. A new prospective protocol must freeze the policy, threat access, withheld outcomes, split, sample size, tradeoff thresholds and budget before paid inference.

This follow-on audit is planned, not executed. No model calls, new cloud jobs or HumanEval program executions were made during the completed AutoDCWorkflow repair/replay.
