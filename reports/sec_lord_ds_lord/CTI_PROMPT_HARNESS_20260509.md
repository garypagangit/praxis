# SEC-LoRD CTI Prompt Harness

Generated: 2026-05-09

## Decision

Status: **NEEDS REAL MODEL - HEURISTIC SEEDING NOT SUFFICIENT**.

## Result

| Condition | Accuracy | Rows |
|---|---:|---:|
| `vanilla_length_heuristic` | `0.3860` | `500` |
| `domain_seed_overlap_heuristic` | `0.2880` | `500` |

## Interpretation

This harness validates the CTI-MCQ scoring path, but the heuristic prompt substitute is not enough to establish DS-LoRD value.

## Recommendation

Run the same harness with an actual small instruct model, then with approved Llama, before attempting extraction.
