# Independent startup output review

Date: 2026-09-20. Scope: read-only recomputation of synthetic qualification and G0 artifacts; no model fitting, real-data scoring, human judgment or live suppression. The calibration module's author independently recomputed the separate runner's outputs; this is a software evidence check, not an external human scientific review.

## Findings

**Numerical checks passed.** All 40,000 nontrivial thresholds were reproduced from the registered random seed using full sorting instead of the runner's partition operation. Every saved population risk equals `1-threshold`; all ranks, allowed exceedances, violation counts, means and pointwise exact binomial confidence intervals match. The continuous order-statistic Beta distribution independently gives the reported binomial failure probabilities.

| Attack calibration units | Rank | Observed population-risk violations / 10,000 | Exact failure probability |
|---:|---:|---:|---:|
| 299 | 299 | 520 / 10,000 = 5.20% | 4.953626% |
| 500 | 499 | 389 / 10,000 = 3.89% | 3.975474% |
| 1,000 | 996 | 295 / 10,000 = 2.95% | 2.868640% |
| 2,000 | 1,988 | 374 / 10,000 = 3.74% | 3.830768% |

At n=299 the pointwise 95% Monte Carlo interval is **[4.772935%, 5.653387%]**, containing the exact 4.953626%. Under that exact probability, observing at least 520 violations has probability about 13.33%. The observed 5.20% is therefore compatible with simulation variation; it neither refutes the theorem nor empirically establishes a violation probability below 5%. These intervals concern simulation uncertainty, not the finite attack-test fractions criticized in the original proposal. They are not simultaneous intervals across all sample sizes.

**One reporting error was corrected and the replacement receipt verified.** For n=100, 200, 250 and 298, the saved zero-risk arrays and infinite thresholds are correct analytical keep-all results. The original receipt incorrectly calls them 10,000 independent calibration samples and supplies a Monte Carlo interval. Only one randomized API check per size was actually executed. The v2 receipt correctly labels these as analytical keep-all cases, reports zero Monte Carlo repetitions, and removes empirical frequencies/intervals. All 16 saved array entries are exactly identical across the original and v2 attempts; the complete NPZ byte hash is also unchanged. All 40,000 nontrivial simulation results and counterexample quantities are unchanged. The original result and source freeze remain preserved. The amendment changes reporting, not the calibration rule or synthetic draws.

**G0 recount and evidence checks passed; the experiment remains on hold.** Independently read source bytes give 8,322 rows: 2,496 labeled Attack and 5,826 labeled Non-Attack, 241 rule names, 7,946 content groups after the specified exclusions, 376 excess rows and one mixed-label content group. The source lacks user, rule_id, timestamp, severity and incident/campaign identifiers required by this contract. Missing independent raw-event evidence and complete cluster context cannot be converted into passed predicates. Zero full-predicate eligibility is a feasibility result, not useful suppression or scorer efficacy. The 2,496 attack-labeled rows do not establish 2,496 independent attack calibration units.

The 50 selected review cases, salted hash ordering and private answer key match the source exactly. Displayed alert contents match the source after the documented field exclusions. All three final private review-file hashes match. Human review remains **PENDING**; the packet does not independently establish true labels or meet the missing raw-provenance requirement. The G0 receipt's conclusions are appropriately limited.

**A blinding issue was corrected before human review.** The original packet hid `Label` but retained the derived `attack_type` and `kill_chain_all` annotations. The final G0 v2 packet excludes those fields and the `ground_truth`, `true_label` and `expected` aliases, case-insensitively. Independent inspection of both `REVIEW_CASES.json` and the HTML's embedded JSON payload confirms all six excluded names are absent and the two payloads match. All 50 case IDs and ordering are unchanged; the answer key is byte-identical. G0 population counts, eligibility outcomes and interpretation are unchanged. Use the v2 packet for human review; the original remains preserved as superseded evidence.

## Audited bindings

- Final qualification [v2 RESULTS.json](../results/qualification_20260920_v2/RESULTS.json): SHA-256 `a5df362b9fa34c369426001e7cc703ce9b8d489c3ffbccbad57717aba10bfef8`. All three source hashes match the current reviewed files and source committed as `8b06410` before this execution. The simulation NPZ is byte-identical to the original below.
- Original qualification [RESULTS.json](../results/qualification_20260920/RESULTS.json): SHA-256 `c532b4a4002d7940af768e8dd3c747e23148b8706d162a41b2021756f354c627`.
- Original simulation NPZ: SHA-256 `1788153cee81ba03278d6ca098315ceb644246a87a8bc3fb89f4d74320606a7e`; array contents independently replayed. Its three source hashes match committed source `99280f4`.
- Final G0 [v2 ELIGIBILITY_AND_REVIEW.json](../results/g0_20260920_v2/ELIGIBILITY_AND_REVIEW.json): SHA-256 `1d5230afb42470405de91ad303da916606f285be5046456282ca4e0bc89a621a`; both source hashes match current files and committed source `ec4c3e7`. The revised `g0_audit.py` hash is `a10f6a2d9e0260161674ca09efb43b4ea208081e3919aea9324f24cfe346a79a`. All three final private packet files match this receipt's lengths and SHA-256 values.
- Original G0 [ELIGIBILITY_AND_REVIEW.json](../results/g0_20260920/ELIGIBILITY_AND_REVIEW.json): SHA-256 `59e69b1c6349e3c547ff02a4be66b6d2b8925f6273c0ed9332effe68bba55d7b`; source hashes match the preserved `af4c62d` source.
- Both registration hashes match `7428a13f6ccb0387c4fc2635b9337283d5e598ab23afe3351b1a707f33fc4dae`; the acquired source-data hash matches the G0 receipt and dataset manifest.

**Final review: PASS for synthetic-output correctness and G0 receipt accuracy.** No blocking arithmetic defect or unresolved output-reporting error was found. Real-data efficacy remains blocked by the documented G0 requirements, independently of successful synthetic qualification. Neither qualification attempt fitted a model or scored a real alert.
