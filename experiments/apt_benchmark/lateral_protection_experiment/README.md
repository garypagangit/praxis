# Lateral-movement protection: completed development experiment

Research question: Can lower false-alarm operating points preserve lateral-movement detection?

**Complete and independently audited, September 21, 2026.** All 19 groups and 152 final models completed. The primary screen is **INFEASIBLE: six of ten seeds had a feasible selected policy; four did not**. The source audit passed for all 152 cells. This prospectively specified **development** experiment used a source dataset whose earlier outcomes were already known; it establishes neither independent confirmation nor algorithmic novelty.

[Results and evidence receipts](../results/lateral_protection_v1/REPORT.md) · [empirical paper](paper/PRAXIS.md) · [Word](paper/PRAXIS.docx) · [PDF](paper/PRAXIS.pdf) · [preserved planning proposal](../lateral_protection_praxis/README.md).

## Completed results

| Benign fitting labels, with 160 attack labels | Feasible seeds | Frozen descriptive screen |
|---|---:|---|
| 1,024: primary | 6/10 | INFEASIBLE |
| 32: secondary | 0/3 | INFEASIBLE |
| 128: secondary | 1/3 | INFEASIBLE |
| 512: secondary | 1/3 | INFEASIBLE |

Among the **same six feasible primary seeds**, mean verification false-positive rate decreased from **0.7195% to 0.4800%**, but lateral-flow detection decreased from **88.19% to 84.49%**. That loss exceeds three percentage points and detection remains below 90%. These descriptive subset means cannot rescue the primary requirement that all ten seeds be feasible. Comparisons with ordinary controls must use the matching feasible subset; an ordinary-control mean over all ten seeds has a different denominator.

Lateral detection means flagging an author-labeled lateral flow as **any attack**. It does not measure exact stage naming, actor attribution, or early warning. Each verification run uses the same 14,965 benign and 72 lateral feature groups; fitting seeds are repeated models, not independent incidents. Forty new implementation and integrity tests passed for this study; this is not a cumulative historical test count.

## Fixed design

- Primary: ten original fitting seeds; identical 160 attack and 1,024 benign fitting rows per arm.
- Secondary: 32, 128, and 512 benign rows at the first three seeds; nested supports. No best-budget selection.
- Models: XGBoost and LightGBM. Twelve XGBoost and nine non-class-weight LightGBM grid candidates, drawn unchanged from the earlier wider baseline search.
- Weighting: natural frequency, equal class mass, equal class mass with lateral multipliers two and four. Mean weight is one. No double class weighting.
- Three fitting-only cross-validation folds choose each model's hyperparameters by unweighted six-class macro-F1. Imputation and weights are fitted separately within each fold.
- 19 groups of eight fitted cells = **152 final models** and **4,788 inner-fold fits**.

Exact fitting arithmetic: each group has four schemes times (12 + 9) grid candidates times three folds = 252 inner-fold fits. Across 19 groups this is 4,788 inner-fold fits, plus 152 final refits. Each arm has access to the same respective family grid.

## Selection and verification

The earlier calibration partition is deterministically divided within each class by hashed feature fingerprints. The first half is selection; the remainder is verification. The original test remains descriptive. Repartitioning exposed data does not make it untouched.

The score is `1 - p(NormalTraffic)`. An alert is emitted strictly when score exceeds threshold; ties cannot be split. A reference policy maximizes selection lateral detection under lateral recall >=90% and benign FPR <=1%. The candidate minimizes FPR while retaining at least max(90%, reference recall minus three percentage points), at the same FPR ceiling. Both receive the identical model and weighting library.

The threshold-only ablation applies the candidate objective to the reference detector alone. Ordinary controls use the fitting-CV-best natural tree, with its argmax decision and a benign-selection-only empirical 1% threshold. This threshold is not a confidence bound.

All eight fits and selection predictions finish before the group's policy lock is written. Only then are verification and test predictions generated. Models, probabilities, support rosters, locks, and receipts are hash-bound in private storage. Completed work resumes only after receipt validation. Partially written cells stop rather than being silently replaced.

## Primary descriptive decision

All ten primary seeds must have a feasible selection policy. On verification, the arithmetic mean across the ten fitting seeds must satisfy all four point-estimate conditions:

1. FPR reduction strictly greater than 20% relative to the lateral-sensitive reference.
2. Lateral recall loss strictly less than three percentage points.
3. Lateral recall at least 90%.
4. Benign FPR at most 1%.

Any infeasible seed is retained and makes the joint screen INFEASIBLE. Failed verification is retained without retuning. Test scores do not rescue a failed verification screen. Secondary screens are explicitly descriptive. Seeds are correlated fitting repetitions on the same flows, not independent incidents; no confidence guarantee is claimed.

## Resources and reproduction

The completed tree workload used at most two CPU workers, four threads each. AWS SSO was expired when checked; no GPU was used.

`python -m experiments.apt_benchmark.lateral_protection_experiment.run --data <DATA.npz> --out <private-run> --prepare-only`

Run disjoint group indices with `--group-indices`, then use `--summarize-only` once workers have exited. The exact protocol is `protocol.json`; `specification.py` refuses changed settings. Scientific source was frozen at `95d949276d754e6155b789b60779414ed88afcbd` before this study's fitting. Private raw data, models, and predictions are excluded from Git; the public result package contains aggregate evidence and hash receipts.

## External evidence

The [DEDALE qualification](dedale/QUALIFICATION.md) acquired 16 author-labeled CICFlowMeter tables, containing 10,362,133 raw flows and only four lateral flows from one PrintNightmare execution. The 73 source predictors were mapped before evaluation. The frozen day17 stress set contains all four lateral flows and 100,000 feature-deduplicated benign flows selected by hash; other attack stages were excluded. No target fitting, calibration, or threshold tuning occurred.

The fixed source seed, 20260921, had **no feasible candidate**. The external test therefore evaluated **ordinary controls only**:

| Source-fitted ordinary control | False positives / benign flows | Lateral flows detected |
|---|---:|---:|
| Argmax | 7,418/100,000 (7.418%) | 1/4 (25%) |
| Source-benign empirical 1% threshold | 24,511/100,000 (24.511%) | 4/4 (100%) |

The external calculation audit passed. A 1% source calibration target did not imply a 1% external false-positive rate. Four flows from one execution cannot establish independent protection or a reliable incident-level recall estimate, and the sampled prevalence makes precision/F1 unsuitable as deployment estimates. The test documents a transfer tradeoff; it does not validate the proposed candidate.
