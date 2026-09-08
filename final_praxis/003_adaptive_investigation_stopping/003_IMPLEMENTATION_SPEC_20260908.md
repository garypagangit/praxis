# Final Praxis 003 — Implementation Specification

Date: 2026-09-08
Status: **BUILD READY / externally compute-dependent for scientific evidence**

## Required modules

```text
harness/
  cases.py
  trace_schema.py
  policies.py
  review_gate.py
  generate_fixtures.py
  validate_fixtures.py
  run_traces.py
  evaluate_policies.py
  independent_verify.py
configs/
  experiment.json
  case_manifest.json
artifacts/
  fixtures/
  discovery/
  verification/
```

## Trace schema

Each of 8 rounds stores case ID, round, evidence IDs exposed, normalized disposition, raw response, correctness against hidden frozen label, token count, confidence proxy if preregistered, and policy decision (`STOP|CONTINUE|REVIEW`).

## Mechanical policy rules

A2 answer stability: earliest stop after identical normalized disposition on two consecutive rounds.

A4 safety-gated adaptive: apply A2 only if no frozen review trigger is active. Review triggers are computed from machine-readable case/evidence metadata and latest disposition history; no post-hoc manual override.

## Fixture gate

At minimum 80 synthetic traces covering: stable-correct, stable-wrong, correct-to-wrong, wrong-to-correct, oscillation, protected-class review, low-evidence review, and refusal/abstain. Validate policy decisions, harm calculation, prevention calculation, review denominator and deterministic replay.

## Scientific runner

Must fail closed without fixture marker, frozen 400-case manifest, real model adapter and immutable evidence schedule. Synthetic traces are fixture evidence only and cannot promote the experiment.