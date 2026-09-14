# Independent design acceptance criteria

This document reviews study validity. It is not an inference authorization, a substitute for the frozen experiment protocol, or a declaration that a paper is ready. Quantitative investment thresholds must be selected prospectively by the study protocol. A failed criterion stays visible; passing process checks alone cannot qualify a scientific claim.

## The causal question

The proposed estimand is the effect of **who acquires which checks** on acceptance of a harmful proposed code revision and retention of useful repairs, at a fixed checking budget. A specialist's truthful passing witnesses must be held constant across controller policies for the same candidate. The candidate code, problem, outcome suite and initial program must also remain constant. Changing the code generator, number of checks, test strength and policy simultaneously cannot isolate independent evidence acquisition.

Canonical and intentionally buggy HumanEvalPack programs are paired qualification fixtures. Reversing their roles supplies a corruption direction and a repair direction, but does not establish that any model can produce the canonical repair. Do not call oracle-provided canonical programs model-generated repairs. An honest specialist capability result requires archived or freshly generated candidates with a reproducible generation lineage.

Report all paired variant categories: initial passes/candidate fails; initial fails/candidate passes; both pass; both fail; incompatible; incomplete. Do not discard pairs that lack a convenient attack. Separately report the fraction of all assigned problems where a defective variant supplies enough passing witnesses, and the attack's acceptance rate conditional on that eligible set. An attack constructed by conditioning on a known hidden-test failure demonstrates fixture feasibility, not deployment prevalence.

## Splits and information access

1. Split by the underlying HumanEval problem ID before tuning. Keep all languages, code variants, prompt variants, tests derived from that problem and repeated seeds within the same development or evaluation partition. Multiple languages are correlated views, not independent problems. Publish the deterministic split algorithm and hashes.
2. Distinguish three roles: development outcomes used to choose policy; a query pool available through the declared checking interface; and a reserved outcome suite used only for final scoring. Keep test-input families together when near-duplicate input transformations would leak outcomes across pools.
3. Selectors may receive the task specification, public examples, initial/proposed code/edit and declared past query results. They must not receive a separately provided reference solution, reserved inputs/expected outputs, hidden pass/fail labels, gold mutation location or a flag identifying the canonical variant. In a native paired fixture the initial or proposed code may itself equal the canonical code; this is unavoidable and must be disclosed. The protected information is its gold identity/correctness status and any additional evaluator-only implementation. Task IDs must not function as a lookup key into gold-bearing files.
4. The selector must commit each next test ID/input before receiving its execution result. A policy that first executes all candidate tests and then reports the best subset has spent the full search budget. Record the whole screening trace for attackers too; distinguish screening budget from disclosed witness count.
5. Evaluator-only expected outputs can be available to a trusted test service while remaining unavailable to selectors. State that boundary precisely. The final outcome service must not be used as the controller's query pool. Public release of these benchmarks means protocol separation is not proof of secrecy or absence of training contamination.
6. Run untrusted candidate code with network and credential access denied, a fresh writable temporary directory, restricted filesystem visibility, and per-case wall-time/CPU/memory/output limits. Limit and record subprocess creation. A code program reading the hidden suite would invalidate the experiment. Audit actual sandbox configuration and denied-access probes; a metadata assertion alone is insufficient.

## Attack and comparison controls

- Use genuine passing witnesses, recomputed by the trusted checker, and count malformed or unverifiable witnesses as attack failures. Do not mix fabricated test results with selective but truthful evidence without a separately defined arm.
- A candidate proposed after screening against reserved outcomes is an oracle-assisted attacker. Such an arm must be labeled explicitly and cannot support a claim about a weaker attacker.
- Include KEEP, unconditional acceptance, specialist-selected witnesses, independent uniform random checks and a credible change-aware/test-selection baseline. Depending on the final mechanism, include coverage, mutation-based or counterexample-generation baselines. Running the full outcome suite is an oracle ceiling, not a budget-matched practical policy.
- Match the number of evaluated candidate test cases, and separately report CPU time, model calls, tokens and monetary cost. Shared cached executions must be disclosed; policy-level attributable costs must not be summed as independent campaign costs.
- Compare both preservation and recovery. Blanket rejection prevents corruption but also refuses useful repairs. A preservation claim requires a prospectively defined recovery noninferiority criterion, and a positive recovery denominator.
- Freeze attacker strength, policy parameters, thresholds, tie handling and abstention behavior on development tasks. An adversary that adapts to the controller requires a separate adaptive evaluation; do not infer robustness from a fixed weak attack.

## Outcomes and uncertainty

Use the phrase "passes the reserved test suite" rather than unqualified program correctness. Canonical-suite disagreement, flaky behavior and oracle exceptions remain explicit categories. Qualification should replay both variants deterministically and retain failure logs; reference failures cannot be silently relabeled or removed.

The primary unit is the original problem. For paired policy differences, use a problem-clustered interval that resamples all variants, directions and seeds for a selected problem together. Preserve paired assignments within every replicate. Do not bootstrap individual tests or witness records as independent observations. Report raw counts, denominators and effect sizes alongside intervals. For sparse independent problem-level harm counts, a declared exact or Wilson binomial interval is useful; zero observed harm never implies a zero upper risk bound. Intervals across fixed problems do not measure uncertainty across model families or generation seeds.

Predefine one primary comparison, the recovery margin and the multiplicity treatment for additional comparisons. Derive the required cohort from a declared detectable effect and expected eligible-case count; the existence of 164 source tasks does not by itself establish power. If feasibility produces too few attackable or repairable problems, report a failed minimum-information gate instead of relaxing it after seeing results.

## Novelty and paper readiness

Selective passing tests, regression-test selection, independent random checks, mutation testing and counterexample generation are established ideas. Demonstrating their basic behavior is insufficient novelty. The paper needs a concrete policy or mathematical contribution, an explicit closest-prior comparison, an ablation isolating its added component, and an advantage under the same information and cost constraints. A new label for independent testing is not a contribution.

Paper-development readiness requires: a frozen literature-grounded RQ/hypothesis; reproducible qualified benchmark; informative corruption and repair cohorts; a useful honest specialist; leakage-tested access boundaries; complete matched-budget results; automated accounting and outcome review; prespecified uncertainty and decision rules; and a claim supported by the measured contrast. A complete reproducibility package may be ready before the primary research claim is ready. Report those states separately.
