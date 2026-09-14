# Selective Disclosure of Executed Tests in Language-Model Code Revision

Working subtitle: **A preregistered study of harmful revisions, useful repairs and independent verification.**

## Abstract draft

An execution record can be accurate while its disclosure is selective. We study
whether a specialist's choice of genuine test observations changes a language
model's decision to replace an existing program, and whether independently
acquired tests improve that decision. Using pinned HumanEvalPack and HumanEvalPlus
data, we qualify 135 native code pairs and retain 101 source problems for heldout
comparisons. The supplier acquires up to 16 observations and discloses at most two;
uniform disclosure is compared with a policy that withholds failures and selects
passing observations when available. A separately preregistered schema-constrained
Qwen configuration accepts 12 of 101 harmful native revisions under selected
disclosure versus four under uniform disclosure: an increase of 7.92 percentage
points (95% task-bootstrap interval 2.97–13.86; Holm-adjusted p=.015625). Devstral's
corresponding contrast is not supported. A proposed input- and edit-conditioned
hybrid verification policy fails its harm-reduction criterion for both models.
The disclosure effect is not observed in the secondary cohort of 34 harmful
model-generated revisions. Complete assignment accounting, pinned data, raw
provenance and reproducible analyses support an empirical characterization of
selective disclosure and its limits. The results do not isolate the pairing
heuristic, establish a new defense, or imply universal semantic correctness.

## Research questions and outcomes

| Question | Registered hypothesis or scope | Observed answer |
|---|---|---|
| RQ1: Does selective disclosure increase harmful-revision acceptance at fixed supplier access and maximum display? | H1: selected minus uniform testimony, reviewer-only decisions, heldout native replicate zero. | Supported for the schema-constrained Qwen configuration: +7.92 points. Devstral: +1.98 points, adjusted p=.75, unsupported. |
| RQ2: Does hybrid independent acquisition reduce harmful acceptance without unacceptable loss of useful repairs? | H2: uniform minus hybrid, enforced decisions, with usefulness and static-edit requirements. | Unsupported for both models. Qwen: 3/101 uniform versus 4/101 hybrid; Devstral: zero under both. |
| RQ3: Does the pattern extend to model-generated proposals? | Secondary intent-specific comparisons; preserve independent source-task counts. | No observed H1 contrast in 34 harmful generated revisions; this cohort is below the 40-task recommendation threshold. |

Both primary Qwen H1 arms have 101 valid completed observations. Of eight
selected-only harmful acceptances, seven involve withholding a failing uniform
record; two show no selected test records. Treat this as an exploratory mechanism
description. The confirmatory treatment is the complete disclosure policy,
including filtering and possible omission, rather than an isolated similarity
heuristic. Do not present all eight changes as persuasion by passing examples.

## Chapter plan and evidence map

1. **Problem and scope.** Explain why truthful observations may still mislead when
   their acquisition or disclosure is controlled by another actor. Define
   harmful and useful revisions using the finite reserved test suite. State the
   observed contribution and the unsuccessful intervention at the outset.
2. **Literature and research gap.** Begin with
   [OctoPack/HumanEvalPack](https://arxiv.org/abs/2308.07124) and
   [EvalPlus](https://arxiv.org/abs/2305.01210) as the reproducible base. Compare
   [belief-revision query contracts](https://arxiv.org/html/2604.15558v1#S9.SS2),
   [critic-induced corruption](https://arxiv.org/html/2606.02866v1#S7), and
   established differential/regression testing. Use
   [the closest-prior matrix](../literature/CLOSE_PRIOR_MATRIX.md); do not claim
   discovery of cherry-picking or novelty from adding a verifier.
3. **Method and reproducibility.** Use
   [the complete methods](METHODS_AND_WRITING_PLAN.md), both source freezes,
   qualification exclusions, supplier/independent/reserved pools, exact policy
   equations, all-assigned denominators and the four-test Holm family. Describe
   V1's formatting failure and V2's prospective schema extension. Devstral reuse
   is exact reuse, not a fresh replication or extra sample size.
4. **Results.** Lead with the four primary contrasts and
   [the main figure](figures/schema_extension_v2/primary_effects.png). Then show
   all native arms, useful repairs, generated transfer, offline acquisition and
   format/assignment/cost flow. Separate reviewer judgments from the common
   authenticated-failure veto. Source all numbers from
   [the detailed interpretation](RESULTS_AND_INVESTMENT.md) and immutable result
   JSONs, preserving failed and inconclusive comparisons.
5. **Discussion, limitations and conclusions.** Discuss selective withholding,
   the one-configuration positive result, lack of demonstrated transfer, failed
   hybrid gains and the limited number of informative generated harms. Public
   benchmark training exposure, finite test oracles, deliberate bugs, weak
   correspondence to natural agent errors and managed model revisions limit
   generalization. Appendix the earlier closed studies without pooling them.

## Future work justified by these results

An independently registered follow-up could separate passing-result filtering,
display count and geometric pairing, using a uniform-passing comparator and
matched record counts. It would need fresh confirmatory source problems and a
qualified, sufficiently large harmful generated cohort. Stronger coverage or
differential-testing baselines would be required for a broader acquisition-policy
claim. These are future research questions, not unrun conditions silently added
to the present study or a reason to search this heldout set for favorable weights.

The current investment is manuscript development around the measured disclosure
effect and its boundaries. The hybrid candidate remains an unsuccessful
intervention. Paper-development readiness is recorded separately in
`PAPER_READINESS.md`; it does not certify institutional or publication acceptance.
