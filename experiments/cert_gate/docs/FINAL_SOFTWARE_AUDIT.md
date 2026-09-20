# Final software and statistical-scope audit

Review date: **2026-09-20**. This is an **AI-assisted code and artifact audit, not a human review or independent human sign-off**. Reviewed `FINAL_PROTOCOL.json`, `evidence_checker.py`, `generalization_benchmark.py`, their relevant tests, and the reused serialization/calibration helpers. The implementation review was completed before the new real-data benchmark fit; it used synthetic tests and did not inspect new real-data scores, model outputs or efficacy results at that stage. Any subsequent saved-result verification is recorded separately below.

## Review conclusion

No material split-leakage, calibration-denominator, matched-count threshold, component-bootstrap or practical-decision error was found in the reviewed runner. Its design supports the registered **post-pilot exploratory comparison**. It does not establish incident independence, operational certification, independent ground truth, novelty or APT-identification performance.

The initial Windows test run exposed an open `np.load` handle in the end-to-end test's temporary-file cleanup. The benchmark assertions had completed, but cleanup raised `WinError 32`. The owning engineer closed the handles; the independent rerun passed all six generalization tests. No benchmark code was changed by this reviewer.

## Checks and evidence

| Area | Reviewed behavior and interpretation |
|---|---|
| Full and evidence views | Both use explicit feature whitelists; labels and derived attack tags stay out of model text. The evidence view removes `rule_name` and `host`. It remains a projection of the same alert, not an independent source of raw evidence. |
| Duplicate control | Source families connect through full-view hashes or meaningful evidence-view hashes, using the shared IPv4 normalization. Empty evidence does not merge every missing record into one family. Family formation precedes exclusions and splitting. |
| Rule separation | The harder regime connects families through exact nonempty `rule_name` values before exclusions. Connected components remain in one role. Excluding review or mixed-label families does not recompute components and change remaining assignments. |
| Review isolation | All source rows in a duplicate family touching a reserved review case are excluded. Case IDs and source ordinals are verified against the pinned audit and source hashes. Bot review must not overwrite training labels. |
| Fitting and global freeze | Separate full/evidence SVMs fit only the fitting representatives, including vocabulary and IDF. Both regimes complete fitting, selection and calibration and save `GLOBAL_CALIBRATION_FREEZE.json` before any new test scores are computed. Committed operative bytes and protocol hashes are checked. |
| Calibration denominator | All attack calibration representatives are passed to each calibration. The gate also passes the eligibility mask; ineligible attack representatives remain in the denominator. The constructor retains its strict threshold and insufficient-sample keep-all behavior. |
| Test units | Each actual source row in a test family is scored. Primary metrics select the lowest-ordinal representative; secondary metrics use every scored row. Address-normalized family members are not assumed to receive identical scores. Neither target is automatically an incoming SOC alert population. |
| Utility matching | After gate calibration, selection-set benign cases determine the target count. The full-score comparator uses a strict threshold suppressing at most that count; zero target retains all, all target uses negative infinity, and ties can leave a reported shortfall. No test outcome selects the threshold. |
| Paired bootstrap | Whole split components are resampled, retaining their class composition and row multiplicities. Shared component IDs and deterministic draws pair arms and conditions. Missing class denominators produce undefined draws, which are counted. The runner reports gate-minus-baseline comparisons and neutral-minus-clean, directive-minus-clean, and directive-minus-neutral changes. Bands describe the finite empirical component sample. |
| Practical decision | The hard clean regime must first satisfy the registered attack/utility point thresholds. Then the same improvement route must beat both full-only and evidence-only calibrated comparators, with the required strict paired-band sign. Winning one route against one baseline and another route against the second is insufficient. |
| Artifact handling | Raw rows, models, per-record predictions and bootstrap draws stay private. Public outputs contain aggregate metrics and bindings. Existing output directories are rejected so earlier attempts remain intact. |

### Matched utility is selected before evaluation

For an interior target `m` among `n` selection benign scores, the implemented ascending zero-based index `n-m-1` gives the largest strict-threshold count that does not exceed the target, allowing ties to reduce it. This comparator is not PAC-calibrated. Matching its selection-set count does not guarantee matching the gate's utility on test data or perturbed conditions. Report both achieved test operating points rather than describing every comparison as equal-utility performance.

### Calibration counts do not prove independence

The protocol's schema-only harder calibration counts distinguish attack representatives from attack-bearing rule components. The runner uses representatives for the nominal order-statistic sample size and explicitly disclaims operational certification. Duplicate and rule separation reduce identifiable overlap; they do not convert many alerts from one unknown incident into independent attacks. The statistical assumptions remain unresolved even if a nominal calibration certificate object is returned.

## Reporting limits raised before fitting

The final reviewed protocol incorporates the first two wording corrections below. The runner also labels the component definition separately for content and rule regimes.

1. **Exact rule names, not verified semantic families.** The harder split holds out connected components of exact rule names. It does not establish unseen attack families, organizations, time periods or campaigns. Describe it as unseen rule names/components unless a separate semantic taxonomy is supplied.
2. **Equal raw length, not equal model-feature length.** The neutral and directive notes have equal raw character lengths. Character-TFIDF collapses repeated whitespace, including padding. A synthetic check produced equal 129-character headers but 441 versus 435 character n-grams before vocabulary filtering. Treat the conditions as fixed lexical-sensitivity controls; they are not an exact match in model-input feature counts or an LLM prompt-injection test.
3. **Observed evidence is a presence check.** A status code or URI can satisfy `has_evidence`; that does not prove evidence sufficiency, maliciousness or benignness. Appended text can populate an empty header and change eligibility. The protocol and runner explicitly recompute and report those flips.
4. **Bootstrap scope.** With one or few relevant components, percentile bands may be unstable or undefined; zero observed events can yield degenerate zero-width bands. The practical gate is a prospectively fixed exploratory decision rule, not a simultaneous confidence guarantee across routes, arms, conditions and regimes.
5. **Prior data exposure.** This continuation reuses a corpus after the earlier pilot was observed. A positive result would motivate independent-data validation; it would not be untouched external confirmation.

## Automated audit remains separate

The 50-case Qwen process is explicitly automated, with a fixed prompt/model revision and private raw responses. Exact quotation checks validate that cited text is present, not that a model's reasoning is correct. A model's agreement with existing labels does not supply human review or independent ground truth.

The protocol promises a source-label by bot-decision confusion table. The originally frozen `auto_review.grade` provides decision counts and agreement rates without that cross-tabulation. Root will produce the promised confusion counts as a separate local aggregate from the already frozen answers and answer key; no inference prompt, model or frozen answer will be changed to add this report.

## Final verification record

- Evidence-checker suite: **6 tests passed**, covering view isolation, meaningful missingness, strict eligibility, dual-view grouping, copied perturbations and length matching in raw text.
- Generalization suite: **6 tests passed** on the final independent rerun. The corrected end-to-end fixture verifies both regimes' freeze before test scoring, all-attack calibration counts, held-case exclusion, individual row predictions, private artifact hashes, and a reported paired condition band against its saved draws.
- Independent synthetic inspection confirmed strict utility-matching orientation, all-attack calibration calls, global freeze order, identical resampling setup across conditions and same-route comparison against both baselines.
- No real-data model was trained or scored by this reviewer; no positive experiment result is asserted by this audit.
- Root's complete suite at committed source `abf8a18f7d32a31b43a44fed60e092e69e848f47`: **93 tests passed**, exit code 0, 17.861 seconds. The reviewer read the saved log and independently verified its SHA-256 against [TEST_RECEIPT.json](../results/final_verification_20260920/TEST_RECEIPT.json): `5338eb0e29750582b31447f239971f3d65d4dab6a2f421a3547f57df1c3c6ecd`. This confirms the recorded software check, not human validation or real-world efficacy.

### Reviewed file hashes

| File | SHA-256 |
|---|---|
| `FINAL_PROTOCOL.json` | `50d35f060ac9490413540ea0026ff02f68e248e369080923582de125d5bbf38f` |
| `evidence_checker.py` | `88e6658565cd995aadaff7ef88136b5809ac9a9edb70f5d47c3b8e29f5f31db2` |
| `generalization_benchmark.py` | `31a34e7ca2da2c1fac9474d495e6b72974fd278b01fc80a83528c89f03e73137` |
| `tests/test_evidence_checker.py` | `b920b44337bed71c0901bd7559c918ce5e948ca7fa6c77cb3436d178b198bbf3` |
| `tests/test_generalization_benchmark.py` | `5b933b08c6c044444a6a3d3e444d65561ff6a8d9e425945794c15c3ac35215e2` |

## Independent verification of the saved real-data results

After the committed benchmark completed, the reviewer inspected its saved arrays and aggregates **without loading fitted models, refitting, rescoring, changing thresholds or changing the protocol**. The benchmark reports 268.293 seconds elapsed. The following checks passed:

- All **30 private artifact hashes** agree with the public receipt. All **7 operative source hashes** agree with both the current source files and their committed bytes at `abf8a18f7d32a31b43a44fed60e092e69e848f47`.
- All **48 saved prediction masks** agree with independently applied frozen thresholds and strict eligibility predicates: 8 arms, 3 conditions and 2 split regimes.
- All **96 metric tables** agree with direct counts from the saved predictions: primary representatives and secondary all rows for every arm/condition/regime. Representative positions, source ordinals, labels and component assignments are consistent across conditions.
- Independently computed binomial ranks, effective-score order statistics and observed calibration exceedances match the frozen calibration records. Content-family calibration uses **659 attack representatives**, ascending rank **657**, with **6 eligible** attack representatives for the checker. Exact-rule-component calibration uses **1,153 attack representatives**, rank **1,148**, with **27 eligible**. Ineligible cases remain in the attack denominator.
- Selected clean gate-minus-comparator and directive-minus-neutral paired bands agree with the saved shared bootstrap draws. The hard-clean primary utility bands were also recomputed from those draws. This verifies the reported arithmetic; it does not validate incident independence.
- Direct recomputation of the practical decision agrees with **`NO_GO_THIS_FIXED_CHECKER_COMPARISON`**. The point-value guard passes, but neither registered improvement route beats both required baselines.

### Main result: the added checker did not change the calibrated decisions

Hard clean test, with exact rule-name components held out:

| Arm | Attack representatives suppressed / 412 | Nonattack representatives suppressed / 1,696 | Nonattack suppression |
|---|---:|---:|---:|
| Full score, zero threshold | 6 | 1,661 | 97.94% |
| Evidence score, zero threshold | 8 | 1,657 | 97.70% |
| Calibrated full score | 0 | 1,610 | 94.93% |
| Calibrated evidence score | 0 | 1,615 | 95.22% |
| Calibrated cross-view checker | 0 | 1,610 | 94.93% |
| Full score, selection utility matched | 0 | 1,610 | 94.93% |
| Full score, marginal expectation calibration | 1 | 1,639 | 96.64% |

The full calibrated scorer and added checker make **identical decisions for every actual test row in all six conditions**: 1,711 rows in each content-family condition and 2,127 in each rule-component condition. There are **zero checker vetoes of full-score calibrated suppressions**. This is stronger than equality of aggregate counts, but is limited to these saved samples.

Their thresholds are also identical: `0.32506026430253027` for content families and `0.3140751279099605` for rule components. All calibration attacks at or above the full-score threshold remain checker-eligible: 3 in content families and 6 in rule components. Thus the eligibility filter leaves the relevant calibration order statistic unchanged, and every test item above that threshold also passes the checker. Eligibility excludes many other rows, but they were already retained by the calibrated full scorer.

In the clean content-family test, full-score calibration and the checker both suppress **1/432 attack representatives** and **1,086/1,120 nonattack representatives (96.96%)**. The evidence-only arm suppresses 1/432 attacks and 1,080/1,120 nonattacks. Neither split supplies a positive added-checker result.

### Component concentration and descriptive uncertainty

The harder clean test contains **36 rule components**, including **33 with attacks** and only **9 with nonattacks**. All three calibrated arms suppress zero attacks in each of the 33 attack-bearing components. One component contains **286/412 attack representatives (69.42%)**; neither the 412 rows nor the 33 components are verified independent incidents. Zero observed misses and degenerate zero-event bootstrap bands do not establish zero population risk.

One benign component contains **1,486/1,696 nonattack representatives (87.62%)**, all suppressed by the three calibrated arms. Their high pooled utility is strongly influenced by this large component. Below are the independently counted benign-bearing components; indices refer to the private saved component ordering, without exposing rule text.

| Component index | Nonattack representatives | Full calibration / checker suppressed | Evidence calibration suppressed |
|---|---:|---:|---:|
| 4 | 23 | 0 | 0 |
| 7 | 15 | 10 | 9 |
| 10 | 22 | 1 | 1 |
| 14 | 20 | 20 | 20 |
| 15 | 23 | 14 | 14 |
| 17 | 14 | 1 | 1 |
| 21 | 15 | 0 | 6 |
| 28 | 1,486 | 1,486 | 1,486 |
| 29 | 78 | 78 | 78 |

An equally weighted average across those nine benign-bearing components is **48.80%** for full calibration/checker and **52.51%** for evidence calibration; individual component rates range from **0% to 100%**. These averages are **post-result descriptive diagnostics**, not substitutes for the registered primary metric. They explain why whole-component resampling gives a wide primary utility band: **22.12%–99.10%** for full calibration/checker and **26.67%–99.15%** for evidence calibration. These are empirical percentile bands, not verified population confidence intervals.

The paired hard-clean checker-minus-full bands are exactly `[0, 0]` for attack suppression and utility because the underlying decisions coincide. Against evidence calibration, the utility difference is **−0.295 percentage points**, with a paired empirical band of **−8.80 to +1.09 percentage points**. No added-checker advantage is demonstrated.

For context, zero-threshold full-score attack errors occur in components 2 (**1/3**), 15 (**3/7**) and 19 (**2/5**). Evidence zero-threshold adds component 12 (**2/5**) to those same counts. The marginal-expectation arm suppresses one attack in component 15 (**1/7**). These are observed component-specific fractions, not incident-level error estimates.

### Verified result bindings

| Saved public artifact | SHA-256 |
|---|---|
| [RESULTS.json](../results/final_generalization_20260920/RESULTS.json) | `cee168e755fc38547993afdc810c1e44f768ec451bc6a6aec6d7caf86ed4c71b` |
| [GLOBAL_CALIBRATION_FREEZE.json](../results/final_generalization_20260920/GLOBAL_CALIBRATION_FREEZE.json) | `bb613d448d1e9904c8c8ccec22d6ca2376e324eca50b452e91ba1f9d9623a04d` |

**Final audit conclusion:** the saved experiment is internally consistent and the fixed added checker has a negative result against the registered strong comparators. This closes the proposed benefit claim for this specific checker comparison. It does not prove that every checker will fail, establish operational certification, or provide an APT-attribution result.

## Subsequent design audit: qualify the programmed no-go verdict

The earlier audit established that the software correctly implemented and reported the frozen criterion. A subsequent review identified a flaw in that criterion's attainable range. Against the evidence-only baseline, route B requires `1615/1696 + 0.05 = 1.002240566`, above the maximum possible benign-suppression rate of one. Route A requires an attack-suppression rate no greater than `0 - 0.01 = -0.01`. Because one route must beat both baselines, neither route can pass, even for a perfect checker on this observed test.

Root and the benchmark reviewer independently confirmed this arithmetic. It is a scientific criterion-design problem, not an inconsistency between the implementation and its specification. The no-go flag cannot independently support rejection of the hypothesis. The actual identical per-row decisions still establish no added measured benefit for this specific checker on these data. The original independent-raw-evidence gate was not evaluated for efficacy, so that broader hypothesis remains unresolved. Frozen artifacts are preserved; no new criterion is used to relabel this run positive.
