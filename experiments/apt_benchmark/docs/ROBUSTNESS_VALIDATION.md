# Robustness suite validation

Validated September 20, 2026, before the full CasinoLimit model comparison.

- `python -m unittest discover -s experiments/apt_benchmark/tests -v`:
  **80 tests passed** in 17.963 seconds.
- A private synthetic end-to-end integration run compared the original and
  cached execution paths. All saved prediction arrays, target rosters,
  calibration thresholds and reported metrics were exactly equal. It also
  exercised an unsupported target. These synthetic scores are software checks,
  not research evidence and are not published as dataset performance.
- Cache tests compare every scheduled feature/observation view to the same
  causal Replay implementation, including lowercase source channels, unlabeled
  context, arbitrary row order, missing records and delays. Complete source
  hashes, protocol parameters, implementation hashes and sparse matrices are
  bound in the private cache manifest.
- Casino source tests cover exact onset joins, host aliases, source identity
  removal, incomplete-fragment linkage, conservative context filtering,
  immutable completed outputs, and byte-identical sequential/parallel event
  production. Appending a future identity record cannot change earlier features.
- The [Casino design audit](ROBUSTNESS_CASINO_DESIGN_AUDIT.md) documents the
  whole-file identity-vocabulary issue found and fixed before Casino fitting,
  as well as the source-doubt qualification and remaining label limitations.
- The [AIT result audit](../results/robustness_v1/ait/AUDIT.md) independently
  rejoined source annotations, recalculated all 68 comparisons and reproduced
  all four calibration thresholds without refitting.

These checks support implementation correctness within the declared contracts.
They do not certify the authors' labels, independent campaigns, operational
benign false-positive rates, or novelty. The original AIT run binds its own
pre-fit code at commit `174cbea`; the later cached path has a separate Casino
pre-fit receipt rather than silently changing the AIT evidence.
