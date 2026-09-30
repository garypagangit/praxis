# PX-085--091: warning-control experiments

[Results table](RESULTS.md) | [Interpretation](INTERPRETATION.md) | [Every arm, CSV](results/ALL_ARMS.csv) | [Frozen protocol](PROTOCOL.md) | [Registry](../REGISTRY.json)

| ID | Experiment | Status |
|---|---|---|
| PX-085 | Stage-conditioned warning-risk calibration | Complete exploratory replay; main warning failure remains |
| PX-086 | Recoverability audit and seed ensembles | Complete; mean loses warnings, union retains them with costs |
| PX-087 | Cost-ordered evidence and stopping | Complete; narrow simulated acquisition saving |
| PX-088 | Selective risk control and analyst capacity | Complete exploratory replay; see closeout |
| PX-089 | Chronological recalibration | Complete simulated-delay replay; see closeout |
| PX-090 | Constrained binary warning model | Complete expert-score adaptation; see closeout |
| PX-091 | Independent execution replication | Qualification complete; exact replication data-blocked |

## Execution

The full replay ran locally with two CPU workers in 31.59 seconds. A 95 MB S3 upload failed repeatedly, so AWS performed an independent aggregate audit through a compact SSM payload. Two AWS CPU processes recomputed metrics for 359 distinct confusion matrices representing all 2,625 result rows and checked the finite-rank rule. This was not a cloud full-data replay. No GPU acceleration or new model fitting occurred. [Execution adjustment](TRANSPORT_ADDENDUM.md).

The existing worker was stopped and shutdown verified. [Compute receipt](COMPUTE.json) records an approximately $0.295 conservative compute estimate, including startup, transfer troubleshooting and shutdown observation; this is not an invoice. The $0.75 incidental reserve is an allowance, not measured spending. An incomplete multipart upload was aborted. The shared data-loader was not changed.

## Evidence and limits

- [Local output audit](AUDIT.json): 2,439 result checks, 406 preparation checks, 54 comparisons with prior calibration decisions, and 14 mathematical/behavior checks.
- [AWS independent audit](AWS_AUDIT.json): two distinct worker processes and 4,683 metric/rank checks. The AWS payload contains aggregate matrices, not event rows.
- [Legacy estimator compatibility](PREDICTION_COMPATIBILITY.json): 24 exact sampled probability comparisons, 335 rows each, supplement the full prior calibration-decision and test-path comparisons.
- [Pareto comparisons](results/PARETO.json): cost, false alerts, and three warning recalls, evaluated per seed/condition/budget. F1 and exact-stage recall remain separate outcomes.
- Original aggregate output JSON files are losslessly stored as `.json.gz` in `results/`; hashes of their decompressed bytes are recorded in AUDIT.json. Raw events and large probability arrays remain private outside Git.

These are results on a previously exposed campaign. Movement has no calibration support. Chronological correlated flows do not establish exchangeability. No deployment risk guarantee, new theorem, confirmed novelty, or independent-campaign benefit is claimed. The source plan's mean-retention and cheapest-first optimality claims were disproved by counterexamples before replay.

## Reproduction

Run scripts from this directory or by file path, in an environment with numpy; preparation additionally requires the existing PX-081 data, models, LightGBM and joblib. `run.py --self-test` needs no datasets. `prepare.py --output <private-input-directory>` derives calibration predictions and verifies replay equivalence. `run.py --data <private-input-directory> --out <new-output-directory> --workers 2` executes the frozen scientific replay. `summarize.py` renders the current workspace's verified local/cloud artifacts. Cloud control requires explicit run settings and a fresh bounded allocation; the completed allocation must not be restarted.

## Subsequent closeout

[PX-088--091 results, audit and qualification](../closeout_20260930/README.md). The original frozen protocol and completed PX-085--087 outputs remain preserved.
