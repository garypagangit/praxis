# SEC-LoRD / DS-LoRD Next-Gate Design

Generated: 2026-05-13

Status: **current domain-seeded method stopped; relationship-evidence gate ready**

## Current Decision

Strict parser audit confirmed that domain-seeded prompting hurts CTI-MCQ performance:

| Model | Vanilla strict acc | Seeded strict acc | Delta |
|---|---:|---:|---:|
| Llama-3.2-3B-Instruct | `0.276` | `0.090` | `-0.186` |
| Llama-3.1-8B-Instruct | `0.466` | `0.284` | `-0.182` |

No LoRD-style extraction should run while the seed strategy reduces task compliance.

## New Method

Replace broad domain prompt stuffing with question-specific evidence conditioning:

1. Retrieve 1-3 short ATT&CK/CTI facts tied to the current question.
2. Put evidence in a separate `Evidence:` block.
3. Force a strict answer format:

```text
Answer: <A|B|C|D>
```

4. Reject or mark invalid any response without that exact form.
5. Compare:
   - vanilla strict prompt,
   - retrieved-evidence prompt,
   - broad domain-seeded prompt as negative control.

## Evaluation Dataset

- Same CTI-MCQ set used in the strict audit.
- Optional second gate: AnnoCTR TTP linking exact match if labels are available.

## 2026-05-14 Gate Readiness Update

The retrieved-evidence prompt set is now built:

| Item | Value |
|---|---:|
| CTI-MCQ rows | `500` |
| Rows with exact ATT&CK technique fact | `500` |
| Rows with evidence snippets | `500` |
| Evidence coverage | `1.000` |

Artifacts:

- `runs/sec-lord-retrieved-evidence-gate-20260514/retrieved_evidence_prompts.jsonl`
- `reports/sec_lord_ds_lord/SEC_LORD_RETRIEVED_EVIDENCE_GATE_READY_20260514.md`

This does not change the status of the current method. SEC-LoRD remains negative until a model run shows retrieved evidence beats vanilla under strict parsing.

## 2026-05-16 Relationship-Evidence Update

The first retrieved-evidence gate was too shallow: it used short technique facts and missed many CTI-MCQ rows that ask about mitigations, data sources, procedure examples, commands, tools, or groups. A stronger gate is now built with ATT&CK `enterprise-attack-12.0` relationship evidence:

| Item | Value |
|---|---:|
| CTI-MCQ rows | `500` |
| Rows with retrieved relationship evidence | `486` |
| No-label evidence-addressable rows | `106` |
| Evidence-pointer audit accuracy on addressable rows | `0.811` |
| Previous 8B vanilla strict accuracy on same rows | `0.538` |
| Previous 8B broad-seed strict accuracy on same rows | `0.245` |

Artifacts:

- `runs/sec-lord-relationship-evidence-gate-20260516/relationship_evidence_prompts.jsonl`
- `runs/sec-lord-relationship-evidence-gate-20260516/evidence_addressable_prompts.jsonl`
- `reports/sec_lord_ds_lord/SEC_LORD_RELATIONSHIP_EVIDENCE_GATE_20260516.md`

The evidence-addressable slice is selected without labels: include a row only when exactly one answer option has strong lexical support from retrieved evidence. Labels are used afterward only for audit. This is the recommended SEC-LoRD rescue path.

## Required Metrics

| Metric | Threshold |
|---|---:|
| Relationship-evidence strict accuracy vs vanilla | `>= +0.0300` absolute |
| Invalid response rate | `<= vanilla invalid rate` |
| Seeded negative-control result | reported, not hidden |
| Paired vanilla-only vs evidence-only wins | evidence-only wins must exceed vanilla-only wins |

## Compute Budget Cap

- Local or one small GPU/API batch.
- Max 500 questions per model for the gate.
- No extraction until the gate passes.

## Pass Decision

If relationship evidence improves strict accuracy and reduces invalids, then design a separate extraction experiment. The extraction objective must not depend on broad prompt seeding improving accuracy.

## Fail Decision

If relationship evidence still loses to vanilla on the 106-row evidence-addressable slice, archive SEC-LoRD as negative for CTI-MCQ and pivot to a better-labeled task such as TTP linking or retrieval evaluation.
