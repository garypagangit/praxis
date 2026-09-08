# Final Praxis 001 — Execution Checklist

## Gate 0: Novelty
- [ ] Build closest-work matrix.
- [ ] Verify outcome-state-vs-judge comparison is not already directly established.
- [ ] Record one-sentence novelty claim.
- [ ] Kill if only implementation packaging differs.

## Gate 1: Task and Ground Truth
- [ ] Define 3-5 inert task families.
- [ ] Define initial state and valid end states for every task.
- [ ] Encode alternate valid solution paths.
- [ ] Encode partial completion separately from failure.
- [ ] Unit-test deterministic postconditions.

## Gate 2: Baselines
- [ ] Freeze self-report arm.
- [ ] Freeze judge model/prompt/version.
- [ ] Add strongest cheap baseline where applicable.
- [ ] Define disagreement handling before execution.

## Gate 3: Preregistration
- [ ] Freeze H1-H4.
- [ ] Freeze sample size, seeds, models, metrics, CIs, exclusions.
- [ ] Freeze false-success and utility promotion thresholds.
- [ ] Hash protocol.

## Gate 4: Fixtures
- [ ] True success fixture.
- [ ] False claimed-success fixture.
- [ ] Partial-success fixture.
- [ ] Malformed-state fixture.
- [ ] Alternate-valid-path fixture.
- [ ] Independent metric recomputation passes.

## Gate 5: Discovery
- [ ] Run preflight hash/count checks.
- [ ] Execute frozen discovery set.
- [ ] Preserve raw outputs.
- [ ] Run independent verifier.

## Gate 6: Decision
- [ ] H1 evaluated on false-success acceptance.
- [ ] H2 evaluated on valid-success utility.
- [ ] H3 disagreement quantified.
- [ ] No post-hoc task filtering.
- [ ] Final classification and claim boundary written.

## Gate 7: Replication
- [ ] Freeze discovery result first.
- [ ] Second model only after freeze.
- [ ] No threshold retuning.
