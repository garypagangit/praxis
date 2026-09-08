# Final Praxis 001 — Implementation Specification

Date: 2026-09-08
Status: **Gate 2 build specification**

## Objective

Implement a fully inert, local, resettable environment that produces authoritative state snapshots and evaluates frozen postconditions independently of agent and judge text.

## Required modules

```text
final_praxis/001_outcome_state_verification/
  harness/
    models.py
    environment.py
    task_registry.py
    verifier.py
    judge.py
    generate_fixtures.py
    validate_fixtures.py
    run_discovery.py
    analyze_results.py
    independent_verify.py
  configs/
    tasks.json
    experiment.json
    judge_prompt.txt
  artifacts/
    fixtures/
    discovery/
    verification/
```

## State model

Use local JSON/SQLite-backed inert state only. No production accounts, real credentials, external service mutation, shell execution, or privileged operations.

Every run records:
- initial-state hash;
- task ID and instance ID;
- agent-visible request;
- ordered inert tool calls;
- final-state hash;
- completion claim;
- deterministic predicate vector;
- judge decision/confidence if available;
- verifier decision;
- latency/token/cost metadata.

## Verifier contract

Each task verifier returns structured output:

```json
{
  "goal_predicates": {"p1": true},
  "protected_invariants": {"i1": true},
  "goal_complete": true,
  "collateral_valid": true,
  "success": true,
  "reason_codes": []
}
```

No verifier may inspect the natural-language completion claim to determine ground truth.

## Judge contract

Primary judge receives only:
- task request;
- agent-visible transcript/tool observations;
- final textual claim.

It does not receive hidden expected-state metadata, verifier code, fixture family label, or deterministic verdict. Output is frozen structured JSON: `success` boolean, confidence if supported, concise reason.

## Fixture gate

Generate 140 fixtures from the frozen catalog. Required checks:
- exact 20×7 coverage;
- clean and alternate-valid fixtures accepted by deterministic verifier;
- incomplete/false/partial/collateral fixtures rejected;
- admitted failures rejected as task success but correctly marked claim-honest diagnostically;
- every predicate/invariant toggled at least once across fixtures;
- deterministic replay produces identical labels and hashes.

Any fixture failure blocks scientific generation.

## Scientific generation

After fixture freeze:
- generate exactly the preregistered 400 primary units, plus 40 admitted-failure controls if budget permits;
- use balanced task IDs and frozen condition allocation;
- do not select only interesting disagreements;
- preserve all raw units, including refusals and malformed attempts.

## Analysis

Primary output table must include FSAR, TSAR, APAR, CVMR for each evaluator, paired deltas/CI, per-task-family breakdown, per-agent-model breakdown, intervention/disagreement rate, latency/cost, exclusions, and all promotion-gate pass/fail states.

## Independent verification

`independent_verify.py` must read raw immutable artifacts rather than analysis summaries and recompute labels, denominators, metrics, hashes, and gate decisions. It must fail closed on missing units or duplicate instance IDs.

## Gate 2 completion definition

Implementation is ready for scientific execution only when:
1. all 140 fixture cases pass;
2. deterministic replay is stable;
3. config/task/verifier hashes are recorded;
4. primary judge structured-output parser passes fixture tests;
5. independent verifier reproduces fixture metrics exactly;
6. no scientific model outputs have been inspected.