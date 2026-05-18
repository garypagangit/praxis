# Praxis 07 Protocol: Relationship-Evidence Retrieval For CTI Task Compliance

Generated: 2026-05-17

Status: **protocol draft**

## Experiment ID

`relationship-evidence-cti-compliance`

## Hypothesis

For CTI multiple-choice questions whose answers are supported by ATT&CK relationship evidence, a frozen instruction-tuned LLM prompted with question-ranked relationship evidence will achieve higher strict answer compliance than the same LLM under vanilla prompting, broad CTI seed prompting, and technique-only retrieval.

## Primary Dataset And Artifacts

| Item | Path |
|---|---|
| Frozen prompt slice | `cloud_jobs/sec_lord_relationship_evidence_20260517/input/evidence_addressable_prompts.jsonl` |
| Relationship evidence builder | `scripts/build_sec_lord_relationship_evidence_gate.py` |
| Offline support audit | `scripts/run_sec_lord_relationship_evidence_offline_gate.py` |
| Slice leakage audit | `scripts/audit_sec_lord_relationship_evidence_slice.py` |
| Cloud model runner | `cloud_jobs/sec_lord_relationship_evidence_20260517/run_sec_lord_relationship_evidence_cloud.py` |
| Complement-slice cloud input | `cloud_jobs/sec_lord_relationship_evidence_20260517/input/complement_vanilla_prompts.jsonl` |
| First model-gate report | `reports/sec_lord_ds_lord/SEC_LORD_RELATIONSHIP_EVIDENCE_MODEL_GATE_20260517.md` |
| First model-gate JSON | `reports/sec_lord_ds_lord/SEC_LORD_RELATIONSHIP_EVIDENCE_MODEL_GATE_20260517.json` |
| Local slice audit report | `reports/relationship_evidence_cti_compliance/SEC_LORD_RELATIONSHIP_EVIDENCE_SLICE_AUDIT_LOCAL_20260517.md` |

## Conditions

| Condition | Purpose |
|---|---|
| `vanilla` | Strong plain prompt baseline with strict answer format. |
| `broad_seed` | Negative control for the old SEC-LoRD broad prompt-seeding method. |
| `technique_only_evidence` | Required ablation to test whether relationship evidence is better than short technique facts. |
| `random_facts` | Negative control for irrelevant ATT&CK relationship facts with the same evidence-block structure. |
| `empty_evidence` | Negative control for the evidence-block header without answer-bearing content. |
| `relationship_evidence` | Main treatment: question-ranked ATT&CK mitigations, detections/data sources, tactics, software/group procedure examples, and technique metadata. |

The prompt builder and cloud runner now support the full ablation set plus the broad-seed legacy control. The pre-registered sequence says to run the slice audit before cross-model or ablation work.

## Metrics

| Metric | Definition |
|---|---|
| Strict accuracy | Exact parsed answer letter equals the expected option. |
| Invalid rate | The model fails to emit exactly one parseable `A`, `B`, `C`, or `D` answer. |
| Accuracy delta | Treatment strict accuracy minus vanilla strict accuracy. |
| Paired wins | Per-row comparison: evidence-only wins vs vanilla-only wins. |
| Negative-control visibility | Broad-seed result must be reported in the same table. |

## Promotion Gates

The result may be promoted as a thesis/paper claim only if all criteria hold:

- `relationship_evidence - vanilla >= +0.030` strict accuracy.
- `relationship_evidence - technique_only_evidence >= +0.030` strict accuracy.
- Random-facts and empty-evidence controls do not reproduce the relationship-evidence lift.
- Relationship-evidence invalid rate is no worse than vanilla.
- Relationship-evidence-only paired wins exceed vanilla-only paired wins.
- Broad seed is reported, even if negative.
- Retrieval and slice construction are frozen before model scoring.
- At least one replication is run: either another model or the diagnostic `130`-row addressable slice.

## Current First Gate

This is already passed for the three-condition gate:

| Model | Slice | Vanilla | Relationship evidence | Broad seed | Delta |
|---|---:|---:|---:|---:|---:|
| `meta-llama/Llama-3.1-8B-Instruct` | `106` rows | `0.642` | `0.915` | `0.642` | `+0.274` |

Paired outcome: `33` relationship-evidence-only wins vs `4` vanilla-only wins.

This is enough to justify the new Praxis 07 experiment. It is not enough by itself to claim general CTI RAG superiority.

## Leakage And Confounding Controls

- The primary slice is no-label evidence-addressable: it was selected from retrieval support, not from relationship-evidence model outcomes.
- The broad-seed negative control remains reported to prevent hiding the old failed method.
- The expected answer should only be used for final scoring and support auditing, not prompt construction.
- ATT&CK snapshot version must remain fixed for a given run.
- Prompt templates must be committed before model scoring.
- Invalid outputs are failures, not dropped rows.
- Runs should record model ID, device, decoding settings, and seconds per row.

## Next Cloud Gate

Name: `relationship-evidence-slice-audit-a2-20260518`

Purpose: run the complement-slice vanilla check before spending budget on cross-model or ablation runs.

Recommended command shape:

```powershell
aws sso login --profile praxis-build
aws sts get-caller-identity --profile praxis-build
```

On the GPU host:

```bash
INPUT_JSONL=complement_vanilla_prompts.jsonl \
CONDITIONS=vanilla \
OUTPUT_SUFFIX=slice-audit-complement-8b-vanilla \
MODEL_ID=meta-llama/Llama-3.1-8B-Instruct \
BATCH_SIZE=2 \
bash cloud_jobs/sec_lord_relationship_evidence_20260517/run_on_instance.sh
```

For PowerShell users, environment variables must be set separately:

```powershell
$env:MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"
$env:BATCH_SIZE = "2"
$env:INPUT_JSONL = "complement_vanilla_prompts.jsonl"
$env:CONDITIONS = "vanilla"
$env:OUTPUT_SUFFIX = "slice-audit-complement-8b-vanilla"
bash cloud_jobs/sec_lord_relationship_evidence_20260517/run_on_instance.sh
```

## Decision Rules

| Outcome | Decision |
|---|---|
| Relationship evidence beats vanilla and technique-only, with no invalid-rate regression | Promote to Praxis 07 paper/thesis section. |
| Relationship evidence beats vanilla but not technique-only | Reframe as retrieval helps, relationship structure not proven. |
| Technique-only ties relationship evidence | Keep as ATT&CK retrieval result, drop relationship-specific thesis. |
| Broad seed wins | Reopen prompt-design analysis, but do not claim relationship evidence. |
| Any result depends on dropping invalid outputs | Do not promote. |

## Current Recommendation

Proceed, but in the pre-registered order. Local A1/A3/A4 slice-audit checks pass. The next cloud work is A2 complement-slice vanilla, then 3B cross-model, then the five-arm ablation.
