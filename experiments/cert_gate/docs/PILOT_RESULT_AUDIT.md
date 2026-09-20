# Exploratory score-only pilot: result audit

**Status: PASS for saved-artifact consistency and numerical recomputation.** Date: 2026-09-20. This is an **AI/code audit**, not the pending human label review. The harness author checked its outputs using separately written grouping, threshold, metric and resampling calculations, without importing the evaluated helpers. No model was refitted, no fresh model inference was performed and no threshold was changed.

## Verified evidence

- **Source and grouping:** Read the pinned 8,322-row source and reconstructed the feature whitelist, exact serialization, valid-IPv4 normalization and SHA-based role assignment. All 7,913 normalized groups match the private manifest. The four roles are group-disjoint. All 50 reserved human-review families, covering 74 rows, are excluded; three conflicting-label groups, covering six other rows, are excluded. The retained population is 7,860 representatives and 8,242 rows. Each representative is the lowest original source ordinal. These groups do not establish independent incidents or campaigns.
- **Fitting and calibration inputs:** The fit-content fingerprint matches exactly the 3,157 fitting representatives and their labels. Fit, selection and calibration score files contain precisely their assigned representatives and source labels. Calibration uses **727 attack-labeled representatives**, not 758 attack rows or a test-selected subset. The private model hash matches the frozen model artifact; fitting itself was not repeated.
- **Thresholds:** Independent full sorting gives the PAC-formula threshold **0.4234546585183297**, rank 725 of 727, with two strict calibration exceedances. The binomial value is 0.02366922590775486; allowing a third exceedance fails the registered 0.05 condition. The marginal-formula threshold is **0.12548790833048035**, rank 721, with expectation bound 7/728 under its assumptions. Both saved thresholds match the pre-test freeze. Strict `>` suppression and the score direction are consistent with the frozen scorer; classifier attack predictions use score `<0`.
- **Evaluation:** All 1,712 saved test-row scores, labels, source ordinals, group indices, representative positions and four decision arrays agree across the private artifacts. All primary/secondary suppression counts and classifier F1, TPR, FPR and precision recompute exactly. The primary test contains **1,614 representatives: 491 attack-labeled and 1,123 nonattack-labeled**.
- **Resampling and timing:** Independently reproduced every one of the **160,000 saved resampling values** using sampled group multiplicities and actual within-group row counts. All 16 percentile bands agree. Per-row latency summaries for every scored role also recompute from saved timing arrays. OS process-peak memory is a recorded run measurement, not an independently repeated hardware measurement.

## Recomputed primary result

| Fixed arm | Attack representatives suppressed / 491 | Nonattack representatives suppressed / 1,123 |
|---|---:|---:|
| Keep all | 0 | 0 |
| Ordinary zero-margin rule | 3 (0.6110%) | 1,099 (97.8629%) |
| PAC formula, score only | 1 (0.2037%) | 1,076 (95.8148%) |
| Marginal CRC formula | 2 (0.4073%) | 1,094 (97.4176%) |

The ordinary classifier's primary F1 is **0.9730807577**, TPR **0.9938900204**, and FPR **0.0213713268**. The PAC-formula arm retains two additional attack-labeled representatives compared with the ordinary zero-margin rule while retaining 23 additional nonattack representatives. This is an observed trade-off; these small paired differences do not establish statistical superiority or novelty.

For the PAC arm, the empirical group-resampling band is **94.6227%–96.9398%** for nonattack suppression and **0%–0.6383%** for attack suppression. These describe resampling from this observed group collection. They are not verified population or independent-incident confidence intervals, and their zero lower endpoint is not evidence of zero deployment risk.

## Freeze and artifact bindings

The five operative source/protocol hashes match committed source **`873dc0abae91339bf11dac9ccd50acf2ba4f4604`** and the reviewed files. All eight private artifact byte lengths and SHA-256 values match [RESULTS.json](../results/score_only_pilot_20260920/RESULTS.json), including the model, split manifest, four role-score files, test predictions and bootstrap draws.

The calibration-score file precedes the freeze file, which precedes the test-score file. The freeze records **16:15:18.271418 UTC**; the test-score file was written at **16:15:33.909070 UTC** and the final result records **16:15:40.386567 UTC**. This sequence corroborates the committed control flow, which writes the freeze before calling the test scorer. Local timestamps alone are not independent proof of every prior process action.

- [Final RESULTS.json](../results/score_only_pilot_20260920/RESULTS.json): SHA-256 `d1abb25f456c18b325d7819c7d5046ee9ed79b86ada6c7e66ef4a1c9e67de06c`.
- [CALIBRATION_FREEZE.json](../results/score_only_pilot_20260920/CALIBRATION_FREEZE.json): SHA-256 `401bcacc3657ba8b1bba6e01066f808675e7ce1894252a2ce84faa91f75762e6`.
- [Prospective PILOT_PROTOCOL.json](../PILOT_PROTOCOL.json): SHA-256 `cad970b7947385ce68665a5115d01500015f6ee0675df6604fcfa44a0b1fd67c`.
- Source dataset: SHA-256 `33f95305d1c42f8e615e4f94066119570859dee7eb086dff7c2273536c932ea3`; held-review audit: SHA-256 `1d5230afb42470405de91ad303da916606f285be5046456282ca4e0bc89a621a`.

## Interpretation and remaining limits

No arithmetic, split, threshold, prediction or artifact-binding defect was found. The pilot establishes useful **observed benchmark separation**, while a simple ordinary SVM rule already performs strongly. It does not complete the original two-dataset hypotheses, establish a novel method, reproduce an author experiment, validate adversarial robustness or authorize live suppression. Human label review, dataset terms, independent sampling units and full provenance/severity/incident-context requirements remain unresolved. The score-only experiment explicitly sets eligibility true; it does not validate the full evidence gate. Its formulas therefore must not be described as an achieved operational population-risk certificate.
