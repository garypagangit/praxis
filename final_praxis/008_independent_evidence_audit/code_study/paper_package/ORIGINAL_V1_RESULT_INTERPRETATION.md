# Original V1 result interpretation — retained technical stop and negative policy screen

**V1 does not establish the proposed hybrid policy as a successful primary-Praxis method.** Devstral's heldout native study completed, with a small unsupported testimony-selection effect and no harmful-acceptance advantage for hybrid over uniform verification. Qwen failed its development-format gates; its heldout review and proposal assignments were not executed. The separately frozen V2 configuration remains a separate prospective extension whose outcomes are not assessed here.

The coordinator released V1 scientific artifacts for this interpretation only after V2 was frozen and pushed at `43b7d26`, with extension-freeze SHA256 `9fbc377a01caa82665b4248fc542c18d8b94ebb521732de554936ab919808bc7`. The original core remains frozen at `162d2ab`. This document neither changes V2 nor selects a new experiment from the V1 results.

## Reproduction and experiment flow

The unchanged frozen `analysis.analyze` and `offline_analysis.analyze` were rerun on all archived aggregate and expected-assignment records. **Both complete statistical payloads reproduce exactly**, including every 5,000-draw bootstrap field, configuration, diagnostic and gate. Only the top-level attached `provenance` object was omitted from the comparison. All nine archived payload hashes and every frozen source hash matched before execution and remained unchanged afterward. This verifies deterministic reproduction by the same implementation, not independently authored algorithm validity or population confidence-interval coverage. Raw-request/evidence provenance and the separate arithmetic/manual controls remain distinct audit evidence. [Reanalysis receipt](../postrun_review/completed_original_v1/REANALYSIS_RECEIPT.json)

The archive accounts for **9,456 review assignments**, **328 generated proposal assignments**, **656 native/generated proposal directions**, and **131,200 offline rows** from 164 source tasks. There are no missing review-record identities. Of 5,192 eligible review assignments, 3,498 received completed model responses and 1,694 were not run because of development gates. The 4,264 ineligible review assignments remain explicit placeholders. “Completed response” does not imply valid JSON or a completed scientific cohort. [Flow and costs](C:/Users/garyp/OneDrive/Documents/codex/reports/praxis_20260914_code_study/study/public_results/FLOW_AND_COSTS.json)

| Development gate | Qwen | Devstral |
|---|---:|---:|
| Native reviews | 430/532 valid, **80.83%; failed** | 530/532 valid, **99.62%; passed** |
| Generated reviews | 308/370 valid, **83.24%; failed** | 370/370 valid, **100%; passed** |

The released native Qwen diagnosis identifies 102 malformed JSON responses after normal `end_turn`, motivating V2's prospective schema constraint. V1 preserves these invalid responses. Devstral subsequently completed all 1,694 eligible native-heldout review assignments with valid responses, including the planned stability repeats. Qwen's corresponding 1,694 assignments are **not-run placeholders**.

The frozen machine report retains all-assigned operational zeros and structurally pairable Qwen rows, including `analysis_eligible=true` for its paired estimands. That field describes the paired arithmetic, not technical qualification or actual model observation. The paper must label Qwen's heldout H1/H2 as **not measured because of the failed gate**. Its zero contrasts, CI[0,0] and p=1 are not evidence of refusal, safety, noninferiority or a scientific null. The full unchanged four-test family remains in the archive; no favorable family is substituted.

## Devstral native heldout findings

The primary analysis contains **101 source tasks per native direction**, using acquisition replicate zero. Both directions come from the same 101 source problems. All entries below have 101 valid assigned responses; counts are conditional on the relevant reserved-outcome direction. Repeated calls are not additional source tasks.

| Arm | Harmful revisions accepted, reviewer-only | Harmful revisions accepted, enforced | Useful revisions accepted, enforced |
|---|---:|---:|---:|
| No witness | 2/101 | 2/101 | 96/101 |
| Uniform witness | 1/101 | 1/101 | 97/101 |
| Selected passing witness | 3/101 | 3/101 | 98/101 |
| Selected witness + uniform independent tests | 0/101 | 0/101 | 95/101 |
| Selected witness + static edit tests | 0/101 | 0/101 | 94/101 |
| Selected witness + complement tests | 0/101 | 0/101 | 95/101 |
| Selected witness + hybrid tests | 0/101 | 0/101 | 95/101 |

**H1:** selected versus uniform testimony increased reviewer-only harmful acceptance by **2/101 = 1.98 percentage points**, with registered bootstrap CI **[0, 4.95] points**, exact one-sided p=**0.25**, and Holm-four adjusted p=**1.0**. Paired cells were one acceptance under both arms, two selected-only acceptances, zero uniform-only acceptances and 98 acceptances under neither. This does not support H1 at the registered criterion. It also does not demonstrate an absence of evidence-selection effects. Only 60/101 harmful proposals had two available passing witnesses; the other 41 remain in the primary maximum-two-witness policy estimate, so the effect cannot isolate clustering or equal display count.

**H2:** uniform and hybrid independent verification each had **0/101 harmful acceptances**, producing a zero paired difference, CI[0,0], and exact/adjusted p=1.0. Static edit and complement also had zero harmful acceptances. There is no observed hybrid advantage to explain in this primary model endpoint, and the empirical zero interval is not a guarantee against future harm. Reviewer-only acceptance was also zero in those arms, so the observed outcome is not exclusively an enforced-veto artifact.

Uniform and hybrid each accepted **95/101 useful repairs**. Their useful-repair difference was zero with CI **[-2.97, 2.97] points**: 94 were accepted under both, one under uniform only, one under hybrid only, and five under neither. Thus the registered useful noninferiority numerical criterion passed without an all-zero individual paired contrast. This cannot rescue the policy gate: harm reduction failed the five-point margin and H2 test, and hybrid had no directional harmful-acceptance benefit over static edit. **The bounded policy recommendation is false.** [Original model results](C:/Users/garyp/OneDrive/Documents/codex/reports/praxis_20260914_code_study/study/public_results/MODEL_RESULTS.json)

## Offline acquisition result

At k=8, the heldout native harmful characterization includes 101 tasks with 20 acquisition replicates each. Means and uncertainty use source tasks; the 2,020 policy rows are repeated measurements. The selected tests detected a failure in 1,743/2,020 uniform conditions and 1,767/2,020 hybrid conditions. Positive reductions below favor hybrid.

| Comparator minus hybrid miss rate | Task-average reduction, percentage points | Registered bootstrap CI, percentage points |
|---|---:|---:|
| Uniform | 1.188 | approximately [0, 2.475] |
| Static edit | 0.792 | [0.248, 1.337] |
| Fixed hash order | 4.307 | [0.693, 8.317] |
| Complement | 0.050 | [-0.198, 0.347] |

The exact uniform lower bound is `-5.49615358725325e-19` in rate units, a floating-point quantity at zero; the unchanged gate correctly does not count it as positive. The uniform comparison also falls well below the registered five-percentage-point practical margin. Pairing, all 20 seeds, detection observations, task adequacy and matched logical budgets are complete for this primary offline stratum. The better directional result against static edit does not replace the failed uniform criterion. **The bounded offline recommendation is false.** These offline comparisons are finite-pool characterization, not additional model persuasion tests, new independent tasks or evidence of superiority over full coverage/differential-testing systems. [Acquisition results](C:/Users/garyp/OneDrive/Documents/codex/reports/praxis_20260914_code_study/study/public_results/ACQUISITION_RESULTS.json)

## Generated scope, resources and paper consequence

Of 328 assigned generated proposals, 66 were admitted, two were invalid, 58 ineligible and **202 eligible heldout proposals were not run** under the Qwen development gate. The 66 admitted proposals belong to development and yield nine harmful, 32 useful and 25 other reserved-outcome transitions. They can support descriptive development accounting; they cannot establish heldout generated transfer. Deliberate corruptions remain explicitly prompted mutants, not naturally occurring model errors.

The V1 ledger reports **$4.5862494 estimated API usage** across 3,566 successful provider attempts, including review and proposal generation. This is not an AWS invoice or a total-cloud cost. V2 has a separate additional ledger and reuses defined V1 records without charging them again as new API calls. No current host-stop or V2 completion claim is made here. [Original cost flow](C:/Users/garyp/OneDrive/Documents/codex/reports/praxis_20260914_code_study/study/public_results/FLOW_AND_COSTS.json)

For the paper, V1 supplies a reproducible technical qualification history, a negative Devstral policy screen with a capable useful-repair baseline, and a modest offline selection comparison. It does **not** establish the proposed positive defense contribution or two-model heldout replication. The complete project decision remains pending the separately frozen V2 result and independent artifact review. Reused Devstral native observations in V2 will be the same evidence, not a new replication.

The primary base and closest-prior citations are already available in [Methods §2](METHODS_AND_WRITING_PLAN.md), the [literature matrix](../literature/CLOSE_PRIOR_MATRIX.md) and the paper's [claim-boundary table](CLAIM_BOUNDARIES.md). PBRC already identifies selectively acquired valid evidence; executable critics, patch checking and code-aware test selection are established. The contribution must therefore be an empirically supported, carefully delimited characterization/process comparison. Finite reserved tests and public benchmark exposure remain material limitations; successful artifact reproduction alone certifies neither novelty nor general correctness.
