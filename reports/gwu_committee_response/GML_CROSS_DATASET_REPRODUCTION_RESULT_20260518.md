# GML Cross-Dataset Reproduction Result

Date: 2026-05-18

## Run Location

- Local output: `runs/gml-cross-dataset-comparison-20260518/`
- Main report: `runs/gml-cross-dataset-comparison-20260518/GML_CROSS_DATASET_COMPARISON_REPORT.md`
- AWS S3 output: `s3://praxis-garypagan-272615233626-us-east-1/experiments/gml-cross-dataset/cloud_jobs/gml-cross-dataset-20260518/output/`
- AWS instance: `i-07178e293e8df2a60`, `g5.xlarge`, NVIDIA A10G
- SSM command: `6c54676a-d12c-4fa4-b96e-aa36b47ece72`
- Runtime: about 26 minutes

## Purpose

This was a fast cloud reproduction of the GML architecture comparison requested after the committee feedback. The run compares the same five GML model families on two datasets:

- `GCN-DGI`
- `GATv2`
- `RGCN`
- `GIN`
- `ST-GCN`

The classification target is now explicit: flow-node APT stage classification. Each graph node is a network flow record. The label is the APT stage assigned to that flow. Edges connect related flow records using same-source-IP, same-destination-IP, and KNN feature-neighbor links. R-GCN receives typed edge relations. ST-GCN receives temporal-neighbor links inside each split graph.

This is not host-node classification and not edge classification.

## Evaluation Protocol

| Dataset | Split protocol | Test support note |
|---|---|---|
| DAPT2020 | Network-aware hybrid temporal block split from the imported GML pipeline | Data Exfiltration has only `2` test examples after preprocessing, so DAPT cannot support a strong DE claim. |
| Unraveled | Held-out source-file split with zero source-file overlap between train, validation, and test | Stronger cross-check: evaluated test graph nodes include `2,187` Data Exfiltration examples after graph filtering. |

The run used a fixed fast reproduction budget: `8` supervised epochs, patience `3`, hidden dimension `128`, graph batch size `4`, graph KNN `5`, and DGI pretraining `2` epochs. This is sufficient for a same-run comparison, but it is not a final exhaustive hyperparameter search.

## Test Results

| Dataset | Best by Macro F1 | Macro F1 | Accuracy | ROC-AUC | PR-AUC | Key caveat |
|---|---|---:|---:|---:|---:|---|
| DAPT2020 | GCN-DGI | `0.5995` | `0.9053` | `0.8321` | `0.6566` | DE F1 was `0.0000` for every GML model; only `2` DE test examples. |
| Unraveled | GCN-DGI | `0.2859` | `0.7770` | `0.9242` | `0.4941` | DE F1 was `0.0000` for every GML model despite `2,187` DE test examples. |

## Full Test Ranking

| Dataset | Model | Accuracy | Macro F1 | Weighted F1 | ROC-AUC | PR-AUC | Recon F1 | Establish F1 | Lateral F1 | DE F1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DAPT2020 | GCN-DGI | `0.9053` | `0.5995` | `0.9048` | `0.8321` | `0.6566` | `0.8205` | `0.9398` | `0.2981` | `0.0000` |
| DAPT2020 | RGCN | `0.9246` | `0.5480` | `0.9106` | `0.8936` | `0.6606` | `0.8702` | `0.9175` | `0.0000` | `0.0000` |
| DAPT2020 | GIN | `0.8836` | `0.5408` | `0.8764` | `0.9302` | `0.6163` | `0.7901` | `0.6903` | `0.2830` | `0.0000` |
| DAPT2020 | GATv2 | `0.9168` | `0.5354` | `0.9039` | `0.8952` | `0.6140` | `0.8636` | `0.8613` | `0.0000` | `0.0000` |
| DAPT2020 | ST-GCN | `0.7831` | `0.2956` | `0.7586` | `0.7643` | `0.3776` | `0.5490` | `0.0000` | `0.0000` | `0.0000` |
| Unraveled | GCN-DGI | `0.7770` | `0.2859` | `0.6973` | `0.9242` | `0.4941` | `0.0000` | `0.0003` | `0.5087` | `0.0000` |
| Unraveled | RGCN | `0.7782` | `0.2692` | `0.7268` | `0.9231` | `0.5373` | `0.0006` | `0.0000` | `0.3744` | `0.0000` |
| Unraveled | GIN | `0.7462` | `0.2563` | `0.6490` | `0.8795` | `0.4378` | `0.0020` | `0.0000` | `0.4191` | `0.0000` |
| Unraveled | ST-GCN | `0.7281` | `0.1853` | `0.6186` | `0.8423` | `0.3731` | `0.0000` | `0.0000` | `0.0820` | `0.0000` |
| Unraveled | GATv2 | `0.7255` | `0.1749` | `0.6133` | `0.9013` | `0.4523` | `0.0013` | `0.0000` | `0.0320` | `0.0000` |

## Honest Answer

This reproduction helps answer several committee issues, but it does not rescue the original ST-GCN-centered thesis.

What it does show:

- The classification target can be made consistent as flow-node stage classification.
- The GML models were compared against each other in the same run.
- The comparison was run on two datasets, DAPT2020 and Unraveled.
- Per-stage metrics were captured, which prevents high accuracy from hiding minority-stage failure.
- ST-GCN is not the best model. It is weak on DAPT2020 and also weak on Unraveled.
- GCN-DGI had the best Macro F1 on both datasets in this reproduction.

What it does not show:

- It does not show a strong general APT detector.
- It does not show reliable Data Exfiltration detection. DE F1 was `0.0000` for every GML model on both datasets.
- It does not show that graph models beat strong tabular baselines.
- It does not support the old H3 that ST-GCN should outperform the other GML models.

The strongest defensible interpretation is therefore:

> Under a flow-node APT stage classification framing, the tested GML architectures show mixed and stage-dependent behavior across DAPT2020 and Unraveled. GCN-DGI produced the best Macro F1 in this fast reproduction, while ST-GCN was not supported. However, all models failed Data Exfiltration, and Unraveled exposed severe minority-stage generalization failures. The result is useful as a transparent architecture comparison and limitation study, not as an operational detection claim.

## Committee-Facing Use

This run directly addresses the request to recreate the GML comparison across APT stages and across more than one dataset. It should be presented as evidence of corrective work and methodological cleanup, not as a final positive finding.

Recommended phrasing:

> I reran the GML architecture comparison as a flow-node stage-classification experiment on both DAPT2020 and Unraveled. The rerun included GCN-DGI, GATv2, R-GCN, GIN, and ST-GCN with per-stage precision, recall, F1, support, ROC-AUC, and PR-AUC. The result confirms that the original ST-GCN-centered hypothesis should be removed: ST-GCN was among the weakest models. GCN-DGI had the best Macro F1 in the reproduction, but all GML models failed Data Exfiltration, including on Unraveled where DE support was much larger. I therefore cannot honestly claim operational usefulness from this GML line; the result is a bounded architecture comparison and limitation study.
