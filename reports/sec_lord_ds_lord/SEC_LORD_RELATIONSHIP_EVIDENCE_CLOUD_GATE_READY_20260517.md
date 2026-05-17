# SEC-LoRD Relationship-Evidence Cloud Gate Ready

Generated: 2026-05-17

Status: **cloud GPU runner packaged; model gate completed separately**

## Bottom Line

SEC-LoRD has a frozen 106-row relationship-evidence model gate ready for a GPU box. The local offline audit showed enough signal to justify one real model/API run, but it did not promote the claim.

The cloud job now contains the prompt slice, runner, requirements, and instance script needed to execute the gate without relying on ignored local `runs/` state.

The model gate was later run successfully. See `reports/sec_lord_ds_lord/SEC_LORD_RELATIONSHIP_EVIDENCE_MODEL_GATE_20260517.md`.

## Packaged Artifacts

- `cloud_jobs/sec_lord_relationship_evidence_20260517/input/evidence_addressable_prompts.jsonl`
- `cloud_jobs/sec_lord_relationship_evidence_20260517/run_sec_lord_relationship_evidence_cloud.py`
- `cloud_jobs/sec_lord_relationship_evidence_20260517/run_on_instance.sh`
- `cloud_jobs/sec_lord_relationship_evidence_20260517/requirements.txt`
- `cloud_jobs/sec_lord_relationship_evidence_20260517/README.md`

## Run Command

From a GPU machine with the repo checked out:

```bash
export HF_TOKEN=<hugging-face-token-with-llama-access>
MODEL_ID=meta-llama/Llama-3.1-8B-Instruct \
BATCH_SIZE=2 \
bash cloud_jobs/sec_lord_relationship_evidence_20260517/run_on_instance.sh
```

If the AWS secret `praxis/huggingface/token` is available to the instance role, `HF_TOKEN` can be omitted.

## Direct Python Command

```bash
python cloud_jobs/sec_lord_relationship_evidence_20260517/run_sec_lord_relationship_evidence_cloud.py \
  --model-id meta-llama/Llama-3.1-8B-Instruct \
  --input-jsonl cloud_jobs/sec_lord_relationship_evidence_20260517/input/evidence_addressable_prompts.jsonl \
  --output-dir runs/sec-lord-relationship-evidence-model-gate-20260517 \
  --batch-size 2 \
  --max-new-tokens 8 \
  --max-input-tokens 4096
```

## Outputs

The runner writes:

- `predictions.jsonl`
- `summary.json`
- `report.md`

The instance script also syncs outputs to:

`s3://praxis-garypagan-272615233626-us-east-1/experiments/sec-lord-ds-lord/cloud_jobs/sec-lord-relationship-evidence-20260517/output/`

when AWS CLI access is available.

## Frozen Pass Gate

- Relationship-evidence strict accuracy beats vanilla by at least `+0.030`.
- Relationship-evidence invalid rate is no worse than vanilla.
- Relationship-evidence-only paired wins exceed vanilla-only paired wins.
- Broad-seed negative control is reported.

No extraction experiment should run unless this model gate passes.
