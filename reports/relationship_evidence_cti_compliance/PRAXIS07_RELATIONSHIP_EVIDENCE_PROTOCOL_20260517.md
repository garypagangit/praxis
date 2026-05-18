# Praxis 07 Protocol: Relationship-Evidence Retrieval For CTI Task Compliance

Generated: 2026-05-17

Status: **protocol executed; package as bounded result**

## Experiment ID

`relationship-evidence-cti-compliance`

## Hypothesis

For CTI multiple-choice questions whose answers are supported by ATT&CK evidence, a frozen instruction-tuned LLM prompted with question-ranked ATT&CK evidence will achieve higher strict answer compliance than the same LLM under vanilla prompting and broad CTI seed prompting. Relationship evidence is expected to outperform technique-only retrieval, but the mechanism claim is decided by ablation rather than assumed.

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
| Full slice audit report | `reports/relationship_evidence_cti_compliance/SEC_LORD_RELATIONSHIP_EVIDENCE_SLICE_AUDIT_20260517.md` |
| 3B cross-model report | `reports/relationship_evidence_cti_compliance/SEC_LORD_RELATIONSHIP_EVIDENCE_CROSS_MODEL_GATE_3B_20260517.md` |
| 8B ablation report | `reports/relationship_evidence_cti_compliance/SEC_LORD_RELATIONSHIP_EVIDENCE_ABLATION_GATE_20260517.md` |
| Result synthesis | `reports/relationship_evidence_cti_compliance/PRAXIS07_RESULT_SYNTHESIS_20260517.md` |

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

## Promotion Gates And Outcomes

The result may be promoted as a thesis/paper claim with the following outcomes:

| Gate | Outcome |
|---|---|
| Relationship evidence beats vanilla | PASS at 8B (`+0.274`) and 3B (`+0.340`) |
| Relationship evidence beats technique-only | PASS at 8B (`+0.151`) |
| Random/empty controls do not reproduce lift | PASS for accuracy; random-facts has higher invalid rate |
| Relationship-evidence invalid rate no worse than vanilla | PASS (`0.000` vs `0.000`) |
| Evidence-only paired wins exceed vanilla-only wins | PASS at 8B (`33 > 4`) and 3B (`40 > 4`) |
| Broad seed reported | PASS |
| Retrieval and slice construction frozen before scoring | PASS for local A1/A3/A4; A2 is soft pass |
| At least one replication | PASS on Llama-3.2-3B |

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

## Cloud Gates Run

| Gate | Model | Output suffix | SSM command |
|---|---|---|---|
| A2 complement vanilla | `meta-llama/Llama-3.1-8B-Instruct` | `slice-audit-complement-8b-vanilla` | `8fc60aa2-dd59-4db7-b434-ac6365a3b8f1` |
| 3B cross-model | `meta-llama/Llama-3.2-3B-Instruct` | `cross-model-3b` | `2c6db5c9-c15c-4818-886b-252fe76a3757` |
| 8B ablation | `meta-llama/Llama-3.1-8B-Instruct` | `ablation-8b` | `13ebd008-4482-44f1-b012-b3646f85c297` |

## Decision Rules

| Outcome | Decision |
|---|---|
| Relationship evidence beats vanilla and technique-only, with no invalid-rate regression | Promote to Praxis 07 paper/thesis section. |
| Relationship evidence beats vanilla but not technique-only | Reframe as retrieval helps, relationship structure not proven. |
| Technique-only ties relationship evidence | Keep as ATT&CK retrieval result, drop relationship-specific thesis. |
| Broad seed wins | Reopen prompt-design analysis, but do not claim relationship evidence. |
| Any result depends on dropping invalid outputs | Do not promote. |

## Current Recommendation

Stop cloud experimentation for this result chain and package the bounded finding. The safe paper title is **Retrieval-Conditioned CTI Compliance: A Protocol-Specific Result**. Relationship evidence can be described as the strongest tested evidence condition, but not as a fully isolated causal mechanism.
