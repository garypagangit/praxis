# Independent read-only review of PX-082

Reviewed September 23, 2026 while the frozen experiment was running. This review did not change the protocol, run code, frozen hashes, input data, or model artifacts.

## Finding

No blocking implementation defect was found in the inspected split construction, sampling, metric calculation, or protocol alignment. This is a bounded source/data review, not certification of every experimental claim or a substitute for final saved-output audit.

The common-anchor comparison uses the same test identities for past-only and time-mixed training. Per-class fitting counts match. Current-feature fingerprints shared with the anchor are excluded from both primary fitting pools. The past-only chronology assertion checks the last fitting end against the earliest anchor start. Future training is explicitly allowed in the diagnostic arm. The secondary conventional random comparison changes the test population and therefore does not identify a pure temporal-leakage effect.

## Checks against actual prepared arrays

- 382,229 prepared rows and 382,229 unique source identity hashes.
- No non-finite current or historical input values.
- Every latest historical end precedes its current-flow start.
- Common anchor: 104,051 rows, consisting of 96,098 benign, 6,213 other-stage, 18 movement, and 1,722 exfiltration-labeled flows.

| Capture | Benign | Other stage | Movement | Exfiltration |
|---|---:|---:|---:|---:|
| 6 | 31,200 | 2,890 | 9 | 1,127 |
| 7 | 24,476 | 1,814 | 0 | 5 |
| 8 | 17,631 | 1,067 | 6 | 114 |
| 9 | 12,560 | 442 | 3 | 129 |
| 10 | 10,231 | 0 | 0 | 347 |

The movement comparison consequently rests on only 18 flow labels across three captures from one already examined campaign. Fitting seeds do not create independent attack episodes. Capture bootstrap intervals remain conditional descriptive intervals; they do not measure generalization to independent campaigns.

## Important interpretation boundary

In the `current_history` time-mixed arm, future fitting rows can contain historical aggregates derived from earlier anchor flows. Purging exact current-feature fingerprints does not remove those aggregate dependencies. The historical inputs are label-free and prior-only relative to each row, but the deliberate use of future training makes the overall evaluation inappropriate as a deployment forecast.

This is consistent with the experiment's diagnostic purpose. Describe the observed contrast as **protocol sensitivity under temporal mixing**, including changed fitting-distribution and historical-input dependencies. Do not describe it as an isolated effect of future labels or proof that exact-feature purging eliminates every form of train/test information dependence.

No claim of early warning, verified successful movement, or verified theft follows from these completed-flow author-stage labels. No numerical model conclusion was selected or tuned by this independent review.
