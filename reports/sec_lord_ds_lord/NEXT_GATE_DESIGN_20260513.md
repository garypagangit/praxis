# SEC-LoRD / DS-LoRD Next-Gate Design

Generated: 2026-05-13

Status: **current domain-seeded method stopped; redesign gate required**

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

## Required Metrics

| Metric | Threshold |
|---|---:|
| Retrieved-evidence strict accuracy vs vanilla | `>= +0.0300` absolute |
| Invalid response rate | `<= vanilla invalid rate` |
| Seeded negative-control result | reported, not hidden |
| Paired vanilla-only vs evidence-only wins | evidence-only wins must exceed vanilla-only wins |

## Compute Budget Cap

- Local or one small GPU/API batch.
- Max 500 questions per model for the gate.
- No extraction until the gate passes.

## Pass Decision

If retrieved evidence improves strict accuracy and reduces invalids, then design a separate extraction experiment. The extraction objective must not depend on broad prompt seeding improving accuracy.

## Fail Decision

If retrieved evidence still loses to vanilla, archive SEC-LoRD as negative for CTI-MCQ and pivot to a better-labeled task such as TTP linking or retrieval evaluation.
