# PX-003/PX-034 Summary Export

## Experiment

Title: Retrieval-Conditioned CTI Compliance with Source-Conflict Routing

Praxis IDs: PX-003 plus PX-034 merged as the source-conflict router add-on

Status: Final positive. Defense ready.

## Executive Summary

PX-003/PX-034 tested whether cyber threat intelligence question answering improves when the model is given per-question ATT&CK relationship evidence, and whether a router can separate decisive evidence cases from conflicted or weak-support cases. The result is one of the strongest positive experiments in the portfolio: relationship evidence improved strict CTI multiple-choice compliance across Llama and Qwen families, and the source-conflict router gives a defensible way to present high-confidence direct-answer cases versus review cases.

## Thesis

CTI question answering improves when a model receives per-question ATT&CK evidence, and a source-conflict router can identify when evidence is decisive enough for direct answering.

## Objective

Test whether relationship-level ATT&CK evidence improves strict CTI-MCQ compliance over vanilla prompting, broad seeding, technique-only evidence, empty evidence, and random facts on a locked evidence-addressable slice.

## What Was Tested

PX-003 built a label-free evidence-addressable CTI-MCQ slice from MITRE ATT&CK relationship support. The evaluation required strict `Answer: <A|B|C|D>` compliance. PX-034 added source-conflict routing, classifying rows into decisive, conflicting high-support, ambiguous, weak single-source, and unsupported buckets.

## Key Results

Cross-model decisive-slice results:

| Model | Vanilla accuracy | Relationship-evidence accuracy | Delta |
|---|---:|---:|---:|
| Llama-3.1-8B-Instruct | 0.642 | 0.915 | +0.274 |
| Llama-3.2-3B-Instruct | 0.547 | 0.887 | +0.340 |
| Qwen2.5-7B-Instruct | 0.623 | 0.906 | +0.283 |

Qwen2.5-7B ablation:

| Condition | Accuracy |
|---|---:|
| Relationship evidence | 0.906 |
| Technique-only evidence | 0.726 |
| Broad seed | 0.660 |
| Vanilla | 0.623 |
| Empty evidence | 0.594 |
| Random facts | 0.462 |

PX-034 source-conflict buckets over 500 CTI-MCQ rows:

| Bucket | Rows |
|---|---:|
| Decisive | 106 |
| Conflicting high-support | 179 |
| Ambiguous multi-source | 28 |
| Weak single-source | 37 |
| Unsupported | 150 |

Full-bucket Qwen follow-up:

| Bucket | Vanilla accuracy | Relationship-evidence accuracy | Delta |
|---|---:|---:|---:|
| Ambiguous multi-source | 0.5357 | 0.7143 | +0.1786 |
| Conflicting high-support | 0.5307 | 0.8101 | +0.2793 |
| Decisive | 0.6226 | 0.9057 | +0.2830 |
| Unsupported | 0.6933 | 0.7733 | +0.0800 |
| Weak single-source | 0.7297 | 0.9189 | +0.1892 |
| Full 500-row table | 0.6140 | 0.8220 | +0.2080 |

## What It Proves

PX-003/PX-034 proves that per-question ATT&CK relationship evidence improves strict CTI-MCQ compliance across model families on the locked decisive slice. The full-bucket audit shows the benefit is not limited to the decisive rows, but the router remains useful as source-support risk stratification.

## What It Does Not Prove

It does not prove universal CTI question answering, a general deep-research agent, a hard answerability oracle, or pure causal relationship evidence. Technique-only evidence also helps, and non-decisive buckets can still answer well under forced-choice conditions.

## Defense Use

Use PX-003/PX-034 as a major Praxis result after PX-001 and PX-050. The clean defense statement is: retrieved ATT&CK relationship evidence improves strict CTI compliance, and source-conflict routing provides a principled confidence/risk layer.

## Evidence Links

- `reports/praxis_final_positive_reports_20260701/PX003_PX034_FINAL_REPORT_CTI_EVIDENCE_ROUTING.md`
- `reports/relationship_evidence_cti_compliance/PX003_QWEN25_7B_DEFENSE_REPLICATION_20260630.md`
- `reports/relationship_evidence_cti_compliance/PX034_CTI_SOURCE_CONFLICT_GATE_20260630.md`
- `reports/relationship_evidence_cti_compliance/full_bucket_downstream_qwen_20260705/PX003_PX034_FULL_BUCKET_DOWNSTREAM_ACCURACY_AUDIT.md`
- `reports/relationship_evidence_cti_compliance/PRAXIS07_RESULT_SYNTHESIS_20260517.md`
- `reports/relationship_evidence_cti_compliance/qwen25_7b_defense_20260630/summary.json`
- `scripts/analyze_cti_source_conflict_gate.py`
- `scripts/analyze_cti_bucket_downstream_accuracy.py`

