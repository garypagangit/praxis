# SecAlertBench exploratory score-only design review

Review date: **2026-09-20**. This review inspected source code, labels, schemas and content-group counts only. **No model was fitted, no scores were produced, and no performance results were inspected.** The proposed study is an alert-classification and suppression-feasibility pilot, not an APT-identification experiment.

## Decision and scope

The acquired processed SecAlertBench release can support a narrowly described, exploratory score-only benchmark after the root protocol explicitly releases that scope. It cannot establish the original full-predicate gate, independent incident sampling, or an operational 95%/1% certificate. Research-use terms and the human review remain unresolved facts to disclose; this memo does not resolve them. See [dataset access review](DATASET_ACCESS_REVIEW.md), [statistical contract](STATISTICAL_CONTRACT.md), and the [pinned author artifact](https://github.com/Dxsssu/SecAlertBench/tree/42a84889fda912ca432c994924a1ccd4b9df6274).

A pre-fit grouping audit found address variants that exact model-text hashes would place in different roles. The primary grouping rule now masks valid IPv4 spellings **for grouping only**. Model input remains the original evidence. This change was made before any model outcomes were available.

## Freeze the existing scorer

Use the existing `LinearSVMScorer(seed=20260920)` in [scorers.py](../scorers.py): character TF-IDF with 3–5 character n-grams, `max_features=50000`, `min_df=2`, sublinear term frequency and lowercase preprocessing; `LinearSVC(C=1, class_weight="balanced", max_iter=10000)`. Fit both the vocabulary/IDF and SVM on fitting representatives only. Higher returned scores mean more benign because the scorer negates the attack-class decision margin.

The feature whitelist is `rule_name`, `proto`, `method`, `host`, `uri`, `parameter`, `req_header`, `req_body`, `rsp_header`, `rsp_body`, and `rsp_status`. `Label`, `attack_type`, `kill_chain_all`, randomized top-level addresses/ports and unrecognized fields are excluded. Group keys use this same whitelist, so derived target fields cannot keep otherwise duplicate model inputs in different groups.

`rule_name` is an alert-system feature, not independently verified behavioral ground truth. A positive result could depend on rule or source-template shortcuts. Without enterprise IDs, times or independent campaigns, this split does not test transfer to a new enterprise, time period, rule family or APT. A future rule-held-out or source-held-out study needs its own frozen design; it should not be selected after seeing this pilot's score.

## Deterministic grouping contract

[feature_grouping.py](../feature_grouping.py) exports:

- `exact_feature_sha(alert)`: SHA-256 of UTF-8 `serialize_features(alert)`.
- `feature_group_sha(alert)`: SHA-256 of that same serialized text after valid IPv4-looking substrings become the literal `<ipv4>`.
- `GROUPING_VERSION = "serialized-features-valid-ipv4-v1"`.

Candidate substrings use this exact regular expression:

```text
(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])
```

Each match must also pass `ipaddress.IPv4Address`; otherwise it is unchanged. Digit/dot boundaries prevent replacement of four octets inside a longer dot-separated numeric sequence. Adjacent letters are permitted. Thus `v1.2.3.4` can be grouped with `v5.6.7.8`: a syntactically valid IPv4 spelling may actually be a software version. This is intentional conservative grouping, not a claim that every address-looking substring was randomized by the author.

There is no lowercasing, whitespace rewrite, port masking, hostname masking, IPv6 masking, label lookup or fitted transformation in the grouping helper. Actual host, URI and payload evidence supplied to the SVM is unchanged. The helper therefore prevents the detected address-variant split overlaps without deleting possible security evidence from the model. It does not identify all semantic duplicates or prove incident independence.

Five focused tests cover address variants, unchanged model evidence, exclusion of derived targets from keys, invalid octets/numeric boundaries, version-like spellings, and preservation of other evidence/ports. All five passed before fitting.

## Exclusions and four fixed roles

1. Verify the pinned corpus hash below and reconstruct the existing 50 review case IDs using the registered audit salt. The IDs were checked against `human_review_v2/REVIEW_CASES.json`; no reviewer answers were read or invented.
2. Build the normalized groups over all 8,322 records. Exclude every group with conflicting dataset labels. Do not repair labels, vote on a preferred label, or retain the easier member.
3. Reserve every group containing any of the 50 human-review records. Remove the entire group from all model roles. This reserves 74 rows, not merely the 50 displayed cases.
4. For each remaining group, choose the lowest original source-row ordinal as its representative. This choice is deterministic and independent of model outcomes.
5. Compute `h = int(SHA256(f"20260920|{group_sha}"), 16)`. Assign fit when `100*h < 40*2**256`; development below `50*2**256`; calibration below `80*2**256`; otherwise locked test. Use integer comparisons. Do not reroll the seed, stratify retrospectively or reassign groups to obtain better results.

The full-corpus label-consistency exclusion is a declared benchmark curation step. It narrows the analyzed population to groups with consistent released labels; it is not a deployable way to determine which future alerts have reliable labels. Mixed labels after conservative address masking are not necessarily annotation errors: a changed destination can matter to the true outcome even when the remaining text matches.

### Schema-only counts under this exact design

| Role | Feature groups / representatives | Source rows | Attack representatives | Attack rows |
|---|---:|---:|---:|---:|
| Fit | 3,157 | 3,336 | 937 | 979 |
| Development | 734 | 744 | 218 | 226 |
| Calibration | 2,355 | 2,450 | 727 | 758 |
| Locked test | 1,614 | 1,712 | 491 | 516 |
| Reserved human-review groups | 50 | 74 | 11 | 14 |
| Excluded mixed-label groups | 3 | 6 | Not an evaluation target | 3 |

There are **7,913 normalized groups**, versus 7,946 exact serialized-feature groups. The 727 attack calibration representatives exceed the algorithm's numerical minimum of 299. They are **not 727 verified independent attacks**. Representative selection also changes the target from an alert-volume-weighted population to a fixed set of distinct feature groups. Different original texts within one normalized group can receive different scores; this is why the representative and all-row analyses must be labeled separately.

## Evaluation boundaries

Primary metrics use one representative per test group. Secondary metrics use all rows in those same test groups with the same frozen scorer and threshold. Neither analysis can be relabeled as an independently sampled deployment estimate. The unused human-review groups must not enter training, threshold choice, test results or early stopping.

Keep the SVM recipe fixed. Development may support recorded diagnostics, but must not be used to choose a favorable model, grouping rule, seed or reported result. If a later development decision changes the recipe, register it before using calibration or test outcomes. Vocabulary fitting, normalization fitting, class weighting and model fitting must not use calibration/test records.

Compare the frozen score-only rules prospectively: keep-all, the frozen SVM cutoff, the named marginal order-statistic formula, and the nominal tolerance-bound threshold. Report the marginal and tolerance constructions separately. Calling the latter algorithm does not establish its IID or correct-label assumptions on SecAlertBench. Avoid a certified-risk claim, PAC pass/fail conclusion, or best-arm selection from the observed test metrics. Real P1–P4 eligibility is unavailable and must not be invented or replaced by `eligible=True` while retaining a full-gate claim.

Report all attack and non-attack numerators/denominators, useful non-attack suppression, all-alert suppression, classification precision/recall/F1 where applicable, and the actual thresholds. A test miss fraction over 1% does not directly test the 95% theorem; zero observed misses do not prove zero risk. Any 10,000-resample feature-group bootstrap is descriptive sensitivity within the observed benchmark groups. It cannot repair unknown campaign dependence, certify population risk, or provide meaningful positive precision for zero observed misses. Preserve paired arms in every resample and declare handling of resamples with empty denominators.

## PCAP-derived data does not automatically clear the remaining hurdles

PCAP can supply packet evidence and event times. It does not by itself supply authoritative user identity, a justified severity/eligible-rule policy, complete decision-time incident context, independently established alert labels, or hundreds of independent attack campaigns. Many Suricata alerts generated from one capture remain dependent. A constructed PCAP benchmark can be useful after defining its narrower evidence contract and label joins, but alert volume alone cannot qualify it for the original full-gate certification claim. The original dataset review records which PCAP artifacts were actually acquired and which were only linked.

## Pinned review inputs

- SecAlertBench processed JSON: `33f95305d1c42f8e615e4f94066119570859dee7eb086dff7c2273536c932ea3`.
- Inspected `scorers.py`: `0690da7844bd7b5db3d48279a366bcd083f8a7c75b8645193f94b639d7c8c039`.
- New `feature_grouping.py`: `094e28a6ae23d8774a0774eb07067d2199f1adff2dc0ecdbd945283c3381dcc9`.
- New `test_feature_grouping.py`: `ce1f5c9eeeac3630115853197c870966f9ee2d72d7c8e8789c6a0050c31bd7c4`.
- Private `human_review_v2/REVIEW_CASES.json`: `a93e4923c7348e18edbfcccf439017b20b9bb33b4d35304ecf48f29ed39c5122`.

The corpus remains at `C:/w/cert_gate_data_20260920/access_review/SecAlertBench/0x02. Processed SecAlertBench Dataset/secalertbench.json`; review cases remain private. No dataset rows, model predictions or human findings are reproduced in this memo.
