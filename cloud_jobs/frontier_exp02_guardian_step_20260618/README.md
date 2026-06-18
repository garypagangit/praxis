# Frontier EXP02 Guardian Step AWS Job

This job runs the second EXP02 gate with an open-source guardian judge.

It evaluates prompt and response-prefix safety detection on public benchmark data and writes only redacted predictions and aggregate metrics. It does not generate new harmful model completions and does not persist raw prompt or response text.

Default S3 base:

`s3://praxis-garypagan-272615233626-us-east-1/experiments/frontier-exp02-self-jailbreak/cloud_jobs/frontier-exp02-guardian-step-20260618/`
