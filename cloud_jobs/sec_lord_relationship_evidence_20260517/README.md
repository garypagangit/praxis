# SEC-LoRD Relationship-Evidence Cloud Gate

Generated: 2026-05-17

This cloud job runs the frozen SEC-LoRD relationship-evidence model gate on the
106-row no-label evidence-addressable CTI-MCQ slice.

## Inputs

- `input/evidence_addressable_prompts.jsonl`

Each row contains:

- `vanilla_strict_prompt`
- `technique_only_evidence_prompt`
- `relationship_evidence_prompt`
- `broad_seed_negative_control_prompt`
- `expected_output`

## Local/GPU Command

```bash
bash cloud_jobs/sec_lord_relationship_evidence_20260517/run_on_instance.sh
```

Useful overrides:

```bash
MODEL_ID=meta-llama/Llama-3.1-8B-Instruct \
BATCH_SIZE=2 \
HF_TOKEN=... \
bash cloud_jobs/sec_lord_relationship_evidence_20260517/run_on_instance.sh
```

## Pass Gate

- Relationship-evidence strict accuracy beats vanilla by at least `+0.030`.
- Relationship-evidence strict accuracy beats technique-only retrieval by at least `+0.030`.
- Relationship-evidence invalid rate is no worse than vanilla.
- Relationship-evidence-only paired wins exceed vanilla-only paired wins.
- Broad-seed negative control is reported and cannot be hidden.

No extraction experiment should run from this gate. If this ablation gate passes, promote the result as relationship-evidence CTI task compliance and keep extraction separate.
