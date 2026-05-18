# SEC-LoRD Relationship-Evidence Cloud Gate Ready

Generated: 2026-05-17

Status: **cloud GPU runner packaged; ablation runner ready**

## Bottom Line

SEC-LoRD has a frozen 106-row relationship-evidence model gate packaged for a GPU box. The local offline audit showed enough signal to justify one real model/API run, and the first three-condition cloud model gate later passed.

The cloud job now contains the prompt slice, complement-slice input, runner, requirements, and instance script needed to execute the next A2 complement audit or the later ablation gate without relying on ignored local `runs/` state.

The completed first model gate is recorded in `reports/sec_lord_ds_lord/SEC_LORD_RELATIONSHIP_EVIDENCE_MODEL_GATE_20260517.md`. The packaged prompt input has since been regenerated with `technique_only_evidence_prompt`, `random_facts_evidence_prompt`, and `empty_evidence_prompt` for the Praxis 07 ablation gate. Local slice-audit checks A1/A3/A4 are recorded in `reports/relationship_evidence_cti_compliance/SEC_LORD_RELATIONSHIP_EVIDENCE_SLICE_AUDIT_LOCAL_20260517.md`.

## Packaged Artifacts

- `cloud_jobs/sec_lord_relationship_evidence_20260517/input/evidence_addressable_prompts.jsonl`
- `cloud_jobs/sec_lord_relationship_evidence_20260517/input/complement_vanilla_prompts.jsonl`
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

## A2 Complement Audit Command

Run this before 3B cross-model or ablation:

```bash
INPUT_JSONL=complement_vanilla_prompts.jsonl \
CONDITIONS=vanilla \
OUTPUT_SUFFIX=slice-audit-complement-8b-vanilla \
MODEL_ID=meta-llama/Llama-3.1-8B-Instruct \
BATCH_SIZE=2 \
bash cloud_jobs/sec_lord_relationship_evidence_20260517/run_on_instance.sh
```

## Direct Python Command

```bash
python cloud_jobs/sec_lord_relationship_evidence_20260517/run_sec_lord_relationship_evidence_cloud.py \
  --model-id meta-llama/Llama-3.1-8B-Instruct \
  --input-jsonl cloud_jobs/sec_lord_relationship_evidence_20260517/input/evidence_addressable_prompts.jsonl \
  --output-dir runs/sec-lord-relationship-evidence-model-gate-20260517 \
  --batch-size 2 \
  --max-new-tokens 8 \
  --max-input-tokens 4096 \
  --conditions all
```

## Outputs

The runner writes:

- `predictions.jsonl`
- `summary.json`
- `report.md`

The instance script also syncs outputs to:

`s3://praxis-garypagan-272615233626-us-east-1/experiments/sec-lord-ds-lord/cloud_jobs/sec-lord-relationship-evidence-20260517/output/`

when AWS CLI access is available.

## Frozen Ablation Pass Gate

- Relationship-evidence strict accuracy beats vanilla by at least `+0.030`.
- Relationship-evidence strict accuracy beats technique-only retrieval by at least `+0.030`.
- Random-facts and empty-evidence controls do not reproduce the relationship-evidence lift.
- Relationship-evidence invalid rate is no worse than vanilla.
- Relationship-evidence-only paired wins exceed vanilla-only paired wins.
- Broad-seed negative control is reported.

No extraction experiment should run from this gate. If it passes, promote the result as relationship-evidence CTI task compliance and keep extraction separate.
