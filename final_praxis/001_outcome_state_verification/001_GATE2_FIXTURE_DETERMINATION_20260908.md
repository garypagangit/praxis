# Final Praxis 001 — Gate 2 Fixture Determination

Date: 2026-09-08
Status: **PASS — fixture/verifier infrastructure**

## Result

The executable inert harness was implemented and tested against the frozen 20-task catalog.

- Task templates: 20
- Task families: 4
- Required fixture classes per task: 7
- Total fixtures: 140
- Fixture validation: **140/140 PASS**
- Deterministic regeneration hash: `fab1d1fc72946935d58db7875744a192996fd7eee08ea3b9d9900de38b68a3ec`
- Repeated generation produced the same SHA-256 digest.

## What passed

1. Every task/template × fixture-family combination exists exactly once.
2. Clean and alternate-valid states pass deterministic verification.
3. Incomplete, false-success, partial-success, collateral-damage, and admitted-failure states do not pass task-success verification.
4. Goal predicates and protected invariants are exercised by passing and failing fixtures as required.
5. Deterministic replay reproduces stored verifier decisions.
6. The scientific runner is fail-closed and requires a fixture-gate marker before it can proceed.

## Important boundary

This is an **infrastructure pass only**. It is not scientific evidence and does not count toward Final Praxis 001 H1-H4.

No natural scientific agent outputs have been used to tune thresholds. The frozen discovery design remains 400 primary units plus optional admitted-failure controls.

## Next gate

Gate 3 preparation:

- freeze the discovery agent model(s), model versions, temperatures/sampling parameters, and tool interface;
- freeze the primary judge model and structured prompt;
- build agent and judge adapters that write immutable JSONL records;
- generate a small infrastructure-only pilot to confirm end-to-end serialization and provider behavior without changing scientific thresholds;
- then execute the frozen 400-unit discovery corpus.

Any change to scientific promotion thresholds after natural discovery outcomes are viewed makes the run Protocol Invalid.