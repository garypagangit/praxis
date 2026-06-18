# DAPT2020 Soh-Style Baselines vs GML Apples-to-Apples Result

Date: 2026-05-19

## Purpose

This run addresses the committee's fair-comparison objection directly. The original GML praxis compared newly run GML results against traditional baseline numbers copied from Soh (2023), which was not a true head-to-head comparison.

I reran the DAPT2020 traditional baselines and the five GML families on the same rows, split, feature scaling, and stage labels.

## What Was Recreated

- Dataset: DAPT2020.
- Classification target: flow-stage classification.
- Labels: Benign, Reconnaissance, Establish Foothold, Lateral Movement, Data Exfiltration.
- Split: single stratified 80/20 train/test split.
- Leakage control: `StandardScaler` fit on training rows only, then applied to test rows.
- Traditional models: KNN, MLP, and a transparent Soh Bayesian-network proxy.
- GML models: GCN-DGI, GATv2, R-GCN, GIN, and ST-GCN.

Soh (2023) used PCA anomaly scoring, score calibration, and Bayesian-network classification, and also reported KNN and MLP comparisons. The exact executable Soh code and original random split are not available in this repo, so the Bayesian result here is marked as a proxy: PCA reconstruction error -> min-max anomaly score -> logistic/Platt-style attack calibration -> Gaussian Naive Bayes stage classifier. KNN and MLP are direct same-pipeline reruns.

## Split Support

| Split | Benign | Reconnaissance | Establish Foothold | Lateral Movement | Data Exfiltration |
|---|---:|---:|---:|---:|---:|
| Train | 50,969 | 9,527 | 6,883 | 1,961 | 12 |
| Test | 12,743 | 2,382 | 1,721 | 490 | 3 |

The Data Exfiltration support remains too small for a strong Data Exfiltration conclusion. This is the same structural dataset limitation identified elsewhere.

## Apples-to-Apples Test Results

| Family | Model | Accuracy | Macro F1 | Weighted F1 | ROC-AUC | PR-AUC | Recon F1 | Data Exfiltration F1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Traditional | KNN | 0.9261 | 0.6081 | 0.9204 | 0.8851 | 0.6582 | 0.8513 | 0.0000 |
| Traditional | MLP | 0.9210 | 0.6386 | 0.9193 | 0.9840 | 0.6960 | 0.8427 | 0.0000 |
| Traditional | Soh BN proxy | 0.3028 | 0.1798 | 0.3294 | 0.6663 | 0.2728 | 0.2863 | 0.0000 |
| GML | GIN | 0.8712 | 0.5895 | 0.8746 | 0.9309 | 0.6046 | 0.6767 | 0.0000 |
| GML | R-GCN | 0.8056 | 0.3190 | 0.7738 | 0.9513 | 0.5662 | 0.6093 | 0.0000 |
| GML | GCN-DGI | 0.8026 | 0.3097 | 0.7571 | 0.8843 | 0.4471 | 0.6376 | 0.0000 |
| GML | ST-GCN | 0.7322 | 0.1739 | 0.6247 | 0.7347 | 0.3560 | 0.0240 | 0.0000 |
| GML | GATv2 | 0.7349 | 0.1694 | 0.6226 | 0.8579 | 0.5191 | 0.0000 | 0.0000 |

## Key Per-Stage Findings

- MLP had the best macro F1 overall (`0.6386`), followed by KNN (`0.6081`) and GIN (`0.5895`).
- GIN was the strongest GML model under this same-procedure DAPT rerun.
- ST-GCN remained weak: Macro F1 `0.1739`, Reconnaissance F1 `0.0240`, and zero F1 on Establish Foothold, Lateral Movement, and Data Exfiltration.
- R-GCN had high ROC-AUC (`0.9513`) but weak hard-label stage performance, especially Establish Foothold F1 `0.0057` and Lateral Movement F1 `0.0434`.
- All models had Data Exfiltration F1 `0.0000`; the test split contains only `3` Data Exfiltration rows.

## Honest Conclusion

This run fixes the fair-comparison problem for the DAPT2020 surface: the traditional baselines and GML models were evaluated under the same pipeline rather than comparing fresh GML results to Soh's published table.

The result does not rescue the original ST-GCN-centered thesis. Under this rerun, ST-GCN is near the bottom of the GML family and far behind the same-pipeline MLP and KNN baselines. The strongest defensible GML conclusion is much narrower:

> On DAPT2020 flow-stage classification, a GIN graph formulation was the best GML head in this same-pipeline rerun, but traditional MLP/KNN baselines remained stronger on macro F1 and weighted F1. Data Exfiltration support is too small to support a strong operational APT-stage claim.

## Artifacts

- Full run report: `runs/dapt-soh-gml-apples-to-apples-20260519/SOH_GML_APPLES_TO_APPLES_REPORT.md`
- Metrics CSV: `runs/dapt-soh-gml-apples-to-apples-20260519/metrics_summary.csv`
- Per-stage CSV: `runs/dapt-soh-gml-apples-to-apples-20260519/per_stage_metrics.csv`
- Metadata: `runs/dapt-soh-gml-apples-to-apples-20260519/run_metadata.json`
- AWS log: `runs/dapt-soh-gml-apples-to-apples-20260519/aws_run.log`
- Reproduction script: `scripts/run_dapt_soh_gml_apples_to_apples.py`
