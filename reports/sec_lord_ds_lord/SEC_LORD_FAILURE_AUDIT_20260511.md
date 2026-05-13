# SEC-LoRD Llama Failure Audit

Generated: 2026-05-11

## Decision

Gate result: `CONFIRMED NEGATIVE - CURRENT DOMAIN SEEDING SHOULD STOP`

The original cloud reports were directionally correct but too generous: the parser treated fallback letters inside non-answer text, including the `a` in `assistant`, as answer `A`. A strict parser lowers absolute accuracy and confirms the same scientific decision: domain-seeded prompting makes both Llama models worse on this CTI-MCQ gate.

## Strict Reparse Summary

| Model | Vanilla strict acc | Seeded strict acc | Delta | Vanilla invalid | Seeded invalid |
|---|---:|---:|---:|---:|---:|
| Llama-3.2-3B-Instruct | 0.276 | 0.090 | -0.186 | 265 | 432 |
| Llama-3.1-8B-Instruct | 0.466 | 0.284 | -0.182 | 87 | 239 |

## Parser Artifact

The old parser used a fallback that searched for any `A/B/C/D` anywhere in the generated text. That means malformed outputs such as `assistant\n\nI'm ready` became `A`. The harness has now been patched to accept only an explicit answer letter or answer-prefixed letter near the beginning of the generated answer.

## Paired Outcomes

| Model | Both correct | Vanilla only | Seeded only | Both wrong |
|---|---:|---:|---:|---:|
| Llama-3.2-3B-Instruct | 37 | 101 | 8 | 354 |
| Llama-3.1-8B-Instruct | 127 | 106 | 15 | 252 |

## Interpretation

- This is not a defensible SEC-LoRD positive result.
- The best current Llama signal is plain 8B prompting, not domain seeding.
- The domain-seed prefix appears to increase non-answer/meta responses and answer-position bias.
- The honest next step is not extraction. It is redesigning seed injection and re-gating on answer-format compliance before any LoRD-style attack.

## Alternatives Worth Testing

1. Replace long seed lists with 1-3 retrieved ATT&CK facts tied to the specific question.
2. Put seed context in separate evidence snippets, then force `Answer: <letter>` with constrained decoding or post-hoc invalid rejection.
3. Move from CTI-MCQ to a domain where seeding should plausibly help extraction, such as AnnoCTR TTP linking with exact-match labels.
4. Treat vanilla 8B as a victim baseline and test extraction separately only if the attack objective no longer depends on prompt seeding improving accuracy.
