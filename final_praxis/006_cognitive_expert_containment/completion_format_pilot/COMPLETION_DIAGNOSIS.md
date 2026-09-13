# Completed raw-format run: completion diagnosis

The completed run `fp006-logic-ec92d2561c` remains a failed qualification. Its useful-specialist signal is substantial: intact 80/256 versus logic ablation 13/256, paired difference 26.17 percentage points [20.31,32.03]. The only failed gate is intact truncation 48/256 (18.75%), above 10%. These results were published before this diagnosis and are not rescored or replaced.

A posthoc token-only diagnostic, blind to answer keys, examined each of the 768 test responses. For each response, examine its last 256 generated token IDs. At lags 1 through 64, calculate the fraction of comparable token pairs that match; report the maximum and its lag. Separately count duplicate sliding eight-token sequences across the full response. Thresholds below are descriptive choices after the experiment, not inferential gates.

| Arm | Capped | Capped with tail periodicity >=90% | Capped with duplicate 8-grams >=50% | Noncapped with tail periodicity >=90% |
|---|---:|---:|---:|---:|
| Intact | 48 | 37 | 40 | 0 |
| Logic ablated | 79 | 75 | 74 | 0 |
| Social ablated | 47 | 35 | 39 | 0 |

The first two capped intact responses by source ID repeatedly recompute the same monetary expressions. Most capped outputs exhibit repetition rather than merely long, varied solutions. This does not identify the causal source of every failure, but it gives little support for simply doubling the token budget.

The official generation helper and chat-masked training source support a single fixed chat-format check. That change is a new prospective protocol. The old 256 test questions cannot be reused to tune it. The new pilot uses 32 unused training questions and retains the original token cap, raw task text and numeric parser. It does not add repetition suppression or choose among multiple prompts after observing answers.

Only 2 of the 80 intact flexible-correct outputs were capped; 78/208 noncapped intact responses scored correctly. A jointly noncapped intact/logic subset has a 30.77-point gap, but this outcome-dependent subset is descriptive and does not replace the registered full-cohort estimate. Literal strict-format correctness was 2/256, with 8 strict extractions; that format-specific parser is not an independent semantic correctness adjudication.

[predecessor_response_diagnostics.json](predecessor_response_diagnostics.json) records every tested response identity/hash and diagnostic values. Original immutable evidence: [completed FP32 results](../logic_qualification_fp32/completed/RESULTS.md), [audit](../logic_qualification_fp32/completed/AUDIT.json), [artifact provenance](../logic_qualification_fp32/completed/ARTIFACTS.json). No additional model calls were made for this diagnosis.
