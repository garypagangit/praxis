# Frontier EXP01 TTC Transfer Cloud Job

This job runs the first full open-model AWS test for EXP01.

It loads one model at a time, evaluates `single_sample` and `majority_vote` over `K={1,2,4,8}`, writes raw generation logs, computes the source-to-target retention matrix, runs a constrained predictor/Optuna analysis if available, and emits an internal defensibility challenge.

Default S3 base:

`s3://praxis-garypagan-272615233626-us-east-1/experiments/frontier-exp01-ttc-transfer/cloud_jobs/frontier-exp01-ttc-transfer-20260618/`
