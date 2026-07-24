# PX-058 — Explanation Stability and Drift for Network Intrusion Detection

## Claim boundary

This experiment tests whether explanations from similarly accurate intrusion
detectors are stable across random seeds and whether explanation drift is an
early warning for held-out detection failure. It does not test whether an
explanation is causally correct or understandable to a human analyst.

The confirmatory dataset is CICIDS2017. CIC-IDS-2018 may be used only for
development and cannot adjudicate the confirmatory claim.

## Hypotheses

- **H1 — seed stability:** among models whose validation balanced accuracy is
  within 0.02, the mean pairwise top-k feature overlap is at least 0.50.
- **H2 — drift warning:** across predeclared day or attack-family holdouts,
  explanation drift has Spearman correlation of at least 0.40 with held-out
  balanced-error rate.
- **H3 — incremental warning:** explanation drift improves prediction of
  held-out error over confidence drift alone. This is reserved for the
  confirmatory gate and requires nested or held-out evaluation.

Failure of H1 is scientifically useful: it shows that accuracy-equivalent NID
models do not provide reproducible feature narratives. Failure of H2 rejects
explanation drift as a useful operational warning under the tested shifts.

## Frozen design

1. Remove identifiers, timestamps, infinities, constants, and post-outcome
   leakage fields before fitting.
2. Fit the same model family with seeds 11, 23, 37, 51, and 73.
3. Keep preprocessing and hyperparameters fixed across seeds.
4. Report balanced accuracy, AUROC when defined, and class support.
5. Compute explanations on the same frozen row sample for every seed.
6. Primary stability metric: pairwise Jaccard overlap of the top-k absolute
   global feature attributions.
7. Secondary stability metric: Spearman rank correlation over all features.
8. Primary drift metric: one minus top-k Jaccard overlap between reference and
   held-out global explanations.
9. Relate drift to held-out balanced-error across predeclared holdouts; never
   treat repeated rows from one holdout as independent replicates.

## Controls

- label-shuffled model;
- feature-name permutation check;
- identical-model/identical-data explanation replay;
- confidence drift baseline;
- raw feature-distribution drift baseline;
- accuracy-matched seed subset.

## Gates

- **Gate 0:** synthetic fixture proves that stable conditions produce stable
  ranks and engineered shifts increase drift. This is software validation only.
- **Gate 1:** CIC-IDS-2018 developmental pilot validates runtime, cleaning, and
  day-holdout behavior. It cannot support the paper claim.
- **Gate 2:** frozen CICIDS2017 day and attack-family evaluation adjudicates H1
  and H2.
- **Gate 3:** independent replication or a second public NID corpus evaluates
  transportability and H3.

No result is positive until the relevant non-fixture gate completes. Thresholds
must not be altered after inspecting Gate 2 outcomes.
