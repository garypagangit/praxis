# Final Praxis 003 final determination

**Negative. Discovery completed 2026-09-08.**

The pinned Qwen discovery produced all 400 cases and 3,200 real model rounds under protocol v2. The unchanged frozen cloud verifier passed. The supplemental local numerical replay reproduced all decisions; the exact local beta-quantile equality limitation is documented separately.

| Decision | Observed result | Frozen requirement | Outcome |
|---|---:|---:|---|
| Correctness non-inferiority | A4 34.50%; A1 54.25%; difference -19.75 percentage points; lower bound -25.00 points | Lower bound >= -2 points | FAIL |
| Round saving | 23.34%; 95% CI 21.13%-25.56% | >=20% | PASS |
| Token saving | 31.03%; 95% CI 28.28%-33.71% | >=20% | PASS |
| Degradation prevention | 39/97 cases, 40.21% | >=25% | PASS |
| Phenomenon | 100 adjacent degradation events in 97 cases | >=20 events | PASS |
| Early-stop harm | 34/400, 8.50%; one-sided 95% upper bound 11.16% | Observed <=2%; upper <=4% | FAIL |
| Review rate | 400/400, 100% | <=20% | FAIL |

A2 simple stability attained 56.50% correctness, compared with A4's 34.50%. A4 differed from A2 but did not demonstrate a useful safety-layer advantage. Cost savings are counterfactual sums through policy endpoints; full trace collection consumed all eight rounds. The result does not establish deployment safety or generalize beyond the generated authorization-triage corpus.

Canonical scientific run: `artifacts/discovery/qwen_20260908_v2/`.

Protocol SHA-256: `8e4ff9f6596b1433544eca2031c91c752f5d2d5919644b695dc1fbfc29f02983`.

Raw SHA-256: `13a97bf948a7baf5f55fe7929e0cf4b05fea3fefb2117b08e0795702ba79871c`.

Full report: [paper/PRAXIS_REPORT.md](paper/PRAXIS_REPORT.md).
