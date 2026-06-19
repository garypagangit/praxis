# Frontier EXP04 HaluEval NLI AWS Job

This job runs the dataset-backed EXP04 verifier gate.

It evaluates an open NLI model on HaluEval QA validation and HaluEval dialogue strict holdout, compares against a lexical baseline, and writes only redacted predictions plus aggregate metrics. It does not generate model answers.

Default S3 base:

`s3://praxis-garypagan-272615233626-us-east-1/experiments/frontier-exp04-kg-hallucination/cloud_jobs/frontier-exp04-halueval-nli-20260619/`
