# PX-003/PX-034 Full-Bucket Downstream Gate

Purpose: run Qwen2.5-7B across all 500 CTI-MCQ source-conflict rows, not only the 106 decisive rows, then join predictions back to PX-034 buckets. This directly tests whether the source-conflict router predicts downstream answerability.

## Inputs

Build the full-bucket prompt file locally:

```powershell
python scripts\build_cti_full_bucket_prompt_file.py --output-jsonl runs\px003-px034-full-bucket-downstream-qwen-20260705\input\full_bucket_prompts.jsonl
```

Upload code and input:

```powershell
aws s3 sync cloud_jobs\cti_full_bucket_downstream_20260705 s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/cti_full_bucket_downstream_20260705/code --profile praxis-build --region us-east-1
aws s3 cp cloud_jobs\sec_lord_relationship_evidence_20260517\run_sec_lord_relationship_evidence_cloud.py s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/cti_full_bucket_downstream_20260705/code/run_sec_lord_relationship_evidence_cloud.py --profile praxis-build --region us-east-1
aws s3 cp runs\px003-px034-full-bucket-downstream-qwen-20260705\input\full_bucket_prompts.jsonl s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/cti_full_bucket_downstream_20260705/input/full_bucket_prompts.jsonl --profile praxis-build --region us-east-1
```

## Output Analysis

After the AWS run finishes, download `predictions.jsonl` and run:

```powershell
python scripts\analyze_cti_bucket_downstream_accuracy.py --bucket-csv runs\cti-source-conflict-gate-20260630\cti_source_conflict_rows.csv --predictions-jsonl reports\relationship_evidence_cti_compliance\full_bucket_downstream_qwen_20260705\predictions.jsonl --output-dir reports\relationship_evidence_cti_compliance\full_bucket_downstream_qwen_20260705
```

