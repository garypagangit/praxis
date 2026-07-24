# PX-058 Gate 2 Method Amendment

Date: 2026-07-24

## Timing and evidence isolation

The first CICIDS2017 process was stopped before it wrote `results.json`,
`domain_metrics.csv`, or any metric output. No confirmatory outcome was
inspected before this amendment. Its empty stdout/stderr logs are retained.

## Defects found by preregistration-to-code review

1. The first implementation calculated H1 across every seed even though the
   preregistration defines H1 among accuracy-equivalent models.
2. The first implementation correlated 25 seed-by-holdout rows for H2, even
   though the preregistration explicitly says repeated seed rows from one
   holdout are not independent replicates.

Either defect would make the confirmatory adjudication invalid.

## Frozen correction

- Define the accuracy-matched subset as seeds whose reference balanced accuracy
  is no more than 0.02 below the best seed.
- Calculate H1 stability only across that subset.
- Average balanced error, explanation drift, confidence drift, and feature
  drift across seeds within each named holdout.
- Calculate the H2 Spearman correlation across the five independent holdout
  aggregates, not across repeated seed observations.
- Preserve the original H1 threshold of 0.50 and H2 threshold of 0.40.
- Require all three preregistered explanation methods to pass a hypothesis for
  a method-consensus positive claim. Also report every method separately so a
  mixed result is not collapsed into an unsupported positive or negative.
- Require at least two accuracy-matched seeds, all 15 seed/method reference
  records, all 75 seed/method/holdout records, five independent holdouts per
  method, and deterministic replay rank correlation of at least 0.99.

The corrected run writes to
`cicids2017_gate2_confirmatory_corrected_20260724` so it cannot be confused
with the stopped process.

## Runtime repair before outcome production

The corrected process later stopped before writing any result because a frozen
3,000-row explanation sample contained only class 0. Scikit-learn's string
`neg_log_loss` scorer infers labels from that sampled `y` and raises when only
one label is present. The repaired scorer computes the same negative binary
log-loss while explicitly supplying labels `[0, 1]`. The explanation sample,
metric, seeds, models, thresholds, and all outcome-bearing settings are
unchanged. No Gate 2 metric was available or inspected before this repair.

## Execution-only parallelism amendment

The repaired process was later stopped before producing `results.json` after
monitoring showed that `n_jobs: 1` restricted the 300-tree forest and its
prediction calls to one CPU core. `n_jobs` was changed to `-1` to use all
available local cores. This is an execution-scheduling setting for the same
scikit-learn estimator; the estimator family, tree count, depth, random seeds,
data, explanation samples, methods, metrics, and thresholds are unchanged. No
confirmatory metric was produced or inspected before this execution-only
amendment.

## Post-run adjudicator correction

The completed raw result contains 90 domain records: three methods by five
seeds by the five preregistered holdouts plus the reference-validation domain.
The first independent adjudicator expected 75 records and therefore returned
`INVALID_INCOMPLETE`. The runner's convenience summary also correlated H2 over
six domain aggregates, including reference validation, which is not an
independent held-out shift.

The corrected adjudicator verifies all 90 stored records, then independently
recomputes H2 from only the five named holdouts in the frozen configuration,
averaging the five seed repetitions within each holdout. H1 remains computed
from the frozen accuracy-matched seed subset. No raw output, sample, metric,
threshold, or model result is changed.
