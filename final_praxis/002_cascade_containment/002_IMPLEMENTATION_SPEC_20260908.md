# Final Praxis 002 — Implementation Specification

Date: 2026-09-08
Status: **BUILD READY / model execution later**

## Inert workflow state

Use local JSON/SQLite only. No real SOC actions. Final actions are symbolic values such as `isolate_host:H7`, `disable_account:U3`, `collect_evidence:E9`, `no_action`, each checked against a frozen policy table.

## Required modules

```text
harness/
  workflow.py
  scenario_registry.py
  gates.py
  inject_errors.py
  generate_fixtures.py
  validate_fixtures.py
  run_workflow.py
  analyze_cascade.py
  independent_verify.py
configs/
  experiment.json
  policy.json
  scenarios.json
artifacts/
  fixtures/
  discovery/
  verification/
```

## Stage record

Every stage emits a structured record with `stage`, `input_evidence_ids`, `claims`, `proposed_action`, `provenance`, `policy_context`, and `parent_handoff_hash`. Analysis records the first-invalid stage and survival/correction status at each later stage.

## Deterministic gates

Gates may check only frozen machine-checkable properties: identifier existence, required-field completeness, evidence-reference support, provenance hash/lineage, action registry membership, and policy compatibility. They must not call an LLM for primary gate truth.

## Fixture gate

Minimum 144 fixtures. Validate every error family under each arm, matched clean behavior, exact first-invalid-stage attribution, propagation depth, final action validity, and deterministic replay.

## Scientific runner

Must fail closed until fixture marker and external model adapter exist. Synthetic agent outputs cannot substitute for discovery evidence.