# Frontier EXP02 Self-Jailbreak Guardrail AWS Job

This job runs the full redacted EXP02 guardrail experiment.

It trains/evaluates prompt and response-step detectors from public benchmark datasets, compares input/output/step guardrail metrics, and writes only redacted predictions and aggregate metrics. It does not run model generation and does not persist raw prompt or response text.

Default S3 base:

`s3://praxis-garypagan-272615233626-us-east-1/experiments/frontier-exp02-self-jailbreak/cloud_jobs/frontier-exp02-self-jailbreak-full-20260618/`
