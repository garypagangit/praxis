# Experiment execution and API accounting

Counts distinguish assigned records, new provider results, and explicitly reused results. Pending V2 results are not interpreted as zeros.

| Version | Cohort | Split | Model | Assigned | Eligible | New results | Reused results | Valid reviews |
|---|---|---|---|---:|---:|---:|---:|---:|
| v1 | generated | development | mistral.devstral-2-123b | 450 | 370 | 370 | 0 | 370 |
| v1 | generated | development | qwen.qwen3-coder-next | 450 | 370 | 370 | 0 | 308 |
| v1 | generated | heldout | mistral.devstral-2-123b | 1520 | 0 | 0 | 0 | 0 |
| v1 | generated | heldout | qwen.qwen3-coder-next | 1520 | 0 | 0 | 0 | 0 |
| v1 | native | development | mistral.devstral-2-123b | 630 | 532 | 532 | 0 | 530 |
| v1 | native | development | qwen.qwen3-coder-next | 630 | 532 | 532 | 0 | 430 |
| v1 | native | heldout | mistral.devstral-2-123b | 2128 | 1694 | 1694 | 0 | 1694 |
| v1 | native | heldout | qwen.qwen3-coder-next | 2128 | 1694 | 0 | 0 | 0 |
| v1 | proposal | development | qwen.qwen3-coder-next | 82 | 68 | 68 | 0 | — |
| v1 | proposal | heldout | qwen.qwen3-coder-next | 246 | 202 | 0 | 0 | — |
| v2 | generated | development | mistral.devstral-2-123b | 450 | 370 | 0 | 370 | 370 |
| v2 | generated | development | qwen.qwen3-coder-next | 450 | 370 | 370 | 0 | 369 |
| v2 | generated | heldout | mistral.devstral-2-123b | 1520 | 1160 | 1160 | 0 | 1160 |
| v2 | generated | heldout | qwen.qwen3-coder-next | 1520 | 1160 | 1160 | 0 | 1158 |
| v2 | native | development | mistral.devstral-2-123b | 630 | 532 | 0 | 532 | 530 |
| v2 | native | development | qwen.qwen3-coder-next | 630 | 532 | 532 | 0 | 530 |
| v2 | native | heldout | mistral.devstral-2-123b | 2128 | 1694 | 0 | 1694 | 1694 |
| v2 | native | heldout | qwen.qwen3-coder-next | 2128 | 1694 | 1694 | 0 | 1691 |
| v2 | proposal | development | qwen.qwen3-coder-next | 82 | 68 | 0 | 68 | — |
| v2 | proposal | heldout | qwen.qwen3-coder-next | 246 | 202 | 202 | 0 | — |

| Version | Ledger attempts | Provider results | Synthetic controls | API estimate (USD) |
|---|---:|---:|---:|---:|
| v1 | 3566 | 3566 | 0 | 4.586249 |
| v2 | 5119 | 5119 | 1 | 7.276387 |

Combined API estimate for completed versions: **$11.862637**. This is not an invoice and excludes host/storage/transfer costs.

Exact status counts, token totals, lineage hashes, and unresolved reservations are in `EXECUTION_ACCOUNTING.json`.

- Assignments include invalid, ineligible, and gate-blocked placeholders; they are not all provider calls.
- Reuse is identified only by verified source/destination import hashes and the frozen model/cohort/split rule.
- Copied provider responses count once in combined distinct-response totals. Distinct configurations are not independent scientific replications.
- Costs sum each phase ledger once, including synthetic warmup and unresolved attempt reservations; imported records do not add a second charge.
- API estimates use recorded usage/rates and are not an AWS invoice. Host, storage, transfer, and tax costs are outside this tool.
