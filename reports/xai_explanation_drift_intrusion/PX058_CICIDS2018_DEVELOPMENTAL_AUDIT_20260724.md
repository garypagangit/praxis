# PX-058 CIC-IDS-2018 Developmental Audit

## Disposition

The first CIC-IDS-2018 developmental run is **non-adjudicating and failed**.
It must not be described as a negative scientific result.

## Observed results

- Mean top-10 seed stability: 0.309 (threshold 0.50; failed)
- Mean full-rank seed stability: 0.428
- Drift–failure Spearman: -0.546 (threshold 0.40; failed)
- Balanced accuracy on both held-out days: approximately 0.50
- Seed-domain observations: 10

## Why it cannot adjudicate the hypothesis

1. The model had no useful balanced classification capability on either
   holdout, so explanation comparisons describe chance-level detectors.
2. The first shifted holdout (28 February) was incorrectly used as the
   explanation reference rather than an in-distribution validation split.
3. Only two holdouts were present. Repeated seeds do not create independent
   domain-shift replicates.
4. The run measured permutation importance only and lacked confidence and raw
   feature-drift baselines.

## Corrective action frozen before rerun

- Create a stratified in-distribution reference split from the training days.
- Require two classes in training and every holdout.
- Preserve seeds and thresholds.
- Add permutation, TreeSHAP, and LIME methods.
- Add confidence drift, standardized feature-mean drift, and identical replay.
- Keep CIC-IDS-2018 developmental; only CICIDS2017 Gate 2 may adjudicate H1/H2.

The failed output remains in
`reports/xai_explanation_drift_intrusion/cicids2018_developmental_pilot_20260724`
for auditability.
