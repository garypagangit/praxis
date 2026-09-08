# Final Praxis 003 — Execution Checklist

## Gate 0: Protocol Feasibility
- [ ] Calculate required calibration/review sample size.
- [ ] Define the harm-rate safety denominator and confidence method.
- [ ] Confirm the planned corpus can satisfy the required denominator.
- [ ] Stop if the safety claim cannot be statistically supported with feasible compute.

## Gate 1: Independence Audit
- [ ] List every historical stopping policy/threshold previously inspected.
- [ ] Document how the new policy is selected independently of prior descriptive outcomes.
- [ ] Do not choose the policy because it would have passed an earlier invalid run.
- [ ] If independence cannot be defended, redesign before execution.

## Gate 2: Novelty
- [ ] Position directly against REFRAIN and related stopping work.
- [ ] Verify novelty is security-investigation termination + safety decomposition, not generic early stopping.
- [ ] Search for direct security-triage stopping experiments.
- [ ] Kill if the same construct and safety protocol are already directly evaluated.

## Gate 3: Corpus and Evidence Schedule
- [ ] Freeze cyber-triage corpus and ground truth.
- [ ] Freeze staged evidence order.
- [ ] Define case families/stages.
- [ ] Prevent uncontrolled browsing/new evidence during discovery.
- [ ] Hash corpus/split/schedule.

## Gate 4: Arms and Safety Gate
- [ ] Freeze fixed-short arm.
- [ ] Freeze fixed-long arm.
- [ ] Freeze answer-stability arm.
- [ ] Freeze uncertainty arm only if independently justified.
- [ ] Freeze adaptive safety-gated arm.
- [ ] Implement review/harm gate in code and unit-test it.

## Gate 5: Preregistration
- [ ] Freeze H1-H5.
- [ ] Freeze non-inferiority/equivalence margin.
- [ ] Freeze minimum compute saving.
- [ ] Freeze degradation-prevention threshold.
- [ ] Freeze harm ceiling.
- [ ] Freeze review semantics, sample size, seeds, models, exclusions, CIs.
- [ ] Hash protocol.

## Gate 6: Fixtures
- [ ] Always-correct trajectory fixture.
- [ ] Correct-to-wrong degradation fixture.
- [ ] Wrong-to-correct improvement fixture.
- [ ] Early-stop harm fixture.
- [ ] Review/abstain fixture.
- [ ] Mechanical gate fails when safety denominator/review requirement is missing.

## Gate 7: Discovery
- [ ] Run preflight protocol/corpus/model/count checks.
- [ ] Execute frozen evidence trajectories.
- [ ] Preserve all round-level outputs.
- [ ] Do not inspect and retune stopping thresholds mid-run.
- [ ] Run independent verifier.

## Gate 8: Decision
- [ ] H1 correctness/utility evaluated.
- [ ] H2 cost reduction evaluated.
- [ ] H3 correct-to-wrong prevention evaluated.
- [ ] H4 harm ceiling evaluated with required denominator.
- [ ] H5 security-domain phenomenon established.
- [ ] Compare adaptive policy against simple answer stability.
- [ ] If mandatory review/safety gate missed: classify Protocol Invalid or Negative.
- [ ] Write final claim boundary without importing historical PX-057 descriptive numbers.
