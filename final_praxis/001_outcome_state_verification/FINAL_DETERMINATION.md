# Final Praxis 001 determination

**Negative**

Stage: discovery; independently audited units: 400.

| Evaluator | FSAR | TSAR | APAR | CVMR |
|---|---:|---:|---:|---:|
| det | 0/200 | 200/200 | 100/100 | 0/50 |
| judge | 7/200 | 19/200 | 10/100 | 3/50 |
| self_report | 50/200 | 117/200 | 60/100 | 30/50 |

Paired FSAR difference: 0.0350; frozen stratified bootstrap 95% CI: [0.015, 0.055].
Natural action execution successes before imposed stress: 236/400.

The primary corpus is a controlled state stress experiment. Its failure prevalence is imposed, not a natural agent failure rate. Deterministic accuracy on its own postcondition-defined labels is structural; empirical evidence concerns the learned judge and information availability.

Frozen gates:
- G1_integrity: PASS
- G2_utility: PASS
- G3_alternate: PASS
- G4_collateral: FAIL
- G5_nontrivial_judge_gap: FAIL
- G6_audit: PASS

Immutable source: `runs/discovery_20260908_v2/FINAL_DETERMINATION.md`. Full Praxis report: `paper/PRAXIS_REPORT.md`.
