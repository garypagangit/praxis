# Final Praxis 001 refreshed fixture gate

2026-09-08: **PASS — infrastructure only**.

Protocol v2 adds four audit-binding tests, bringing the current total to **18 focused tests**. Exact output is in `artifacts/fixtures/SCIENTIFIC_INFRASTRUCTURE_TESTS_V2_20260908.txt`. The original 14-test output and marker below remain historical v1 evidence; the new tests reject manifest threshold/model/input-ledger tampering, check independent state/receipt reconstruction, and reject changed inference prompts/runtime.

The unchanged legacy fixture file replays all 140 expected labels. Fourteen new infrastructure tests additionally validate exact balanced allocation; all 400 controlled scientific-state constructions; every scientific goal and invariant under an independent failing mutation; true alternate assignment/set order; type and missing-field rejection; production/audit parser agreement; inert action execution; raw-file non-overwrite; and a known paired statistical example.

The fresh JSON marker records the actual fixture hash and test-output hash. The historical marker with a different fixture hash is retained as evidence of the repaired inconsistency. These test results are not scientific model outcomes and do not contribute to the discovery denominator.

Reproduce:

```text
python -m unittest final_praxis.001_outcome_state_verification.harness.test_scientific -v
```
