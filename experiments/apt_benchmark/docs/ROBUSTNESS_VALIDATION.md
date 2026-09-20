# Robustness suite validation

Validated September 20, 2026, before the full CasinoLimit model comparison.

- `python -m unittest discover -s experiments/apt_benchmark/tests -v`:
  **88 tests passed** in 24.852 seconds after the faster history lookup was integrated.
- A private synthetic end-to-end integration run compared the original and
  cached execution paths. All saved prediction arrays, target rosters,
  calibration thresholds and reported metrics were exactly equal. It also
  exercised an unsupported target. These synthetic scores are software checks,
  not research evidence and are not published as dataset performance.
- A second synthetic end-to-end check compared the faster streamed path with
  the original uncached model run. Prediction arrays, thresholds, metrics and
  unsupported-target handling were exactly equal. Its independent result audit
  passed all 40 reported comparisons and reproduced eight calibration thresholds.
- Eight added FastReplay tests cover dense histories, all declared loss/delay
  conditions, multiple/tied entity keys, missing linkage and long runs of hidden
  recent events. The optimization uses an ordinary lazy heap merge to avoid
  sorting every candidate; it is an implementation improvement, not a new
  attack-recognition method. The original Replay remains the comparison reference.
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

## Completed Casino run

The corrected adapter completed all 114 executions, producing 3,758,674 retained
events and 8,240 eligible targets. Every one of the 4,896,255 annotated audit IDs
matched a source record. Streamed feature preparation completed and bound its
source/protocol/code/matrix hashes. Twelve models were fitted without a
convergence failure; all 204 condition/model/seed results completed.

The [Casino calculation audit](../results/robustness_v1/casino/AUDIT.md) passed
all result rows, pooled and per run, at both operating points, and reproduced
twelve calibration thresholds. Root executed the independently implemented
auditor after the reviewer agent hit its account usage limit. This did not
change the frozen experiment or substitute a human review. The [combined
summary](../results/robustness_v1/SUMMARY.md) reports positive and negative
findings and the full comparisons preserve every declared condition.
