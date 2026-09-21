# Lateral-movement protection: frozen development experiment

Research question: Can lower false-alarm operating points preserve lateral-movement detection?

This is a new, prospectively specified **development** experiment after the source dataset's earlier outcomes were known. It cannot establish independent confirmation or algorithmic novelty. The full paper will report success, failure, or infeasibility without changing these rules.

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

The tree workload uses at most two CPU workers, four threads each. AWS SSO was expired when checked; these small fitting sets do not require a GPU. No GPU result is implied.

`python -m experiments.apt_benchmark.lateral_protection_experiment.run --data <DATA.npz> --out <private-run> --prepare-only`

Run disjoint group indices with `--group-indices`, then use `--summarize-only` once workers have exited. The exact protocol is `protocol.json`; `specification.py` refuses changed settings. Private raw data, models, and predictions are excluded from Git. Published summaries will bind their hashes.

## External evidence

DEDALE (2026) is being qualified independently. Its published code currently indicates one lateral-movement execution. It may support a frozen external flow-level stress test, but does not meet the independent-execution requirement for a confirmatory noninferiority claim. Qualification must precede any model evaluation on its data.
