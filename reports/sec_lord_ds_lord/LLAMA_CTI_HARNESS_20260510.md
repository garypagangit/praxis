# SEC-LoRD Llama CTI-MCQ Harness

Generated: 2026-05-10

## Decision

Gate result: `STOP - LLAMA DOMAIN SEEDING NEGATIVE`

Domain-seeded prompting reduced Llama CTI-MCQ accuracy under this gate.

## Model

- Model: `meta-llama/Llama-3.2-3B-Instruct`
- Rows: `500`
- Device: `cuda`

## Results

| Condition | Accuracy | Correct | Rows | Seconds / row |
|---|---:|---:|---:|---:|
| vanilla_prompt | 0.3820 | 191 | 500 | 0.048 |
| domain_seeded_prompt | 0.2380 | 119 | 500 | 0.065 |

## Next Gate

Do not proceed to extraction with this prompt strategy. Redesign seeding or task selection first.
