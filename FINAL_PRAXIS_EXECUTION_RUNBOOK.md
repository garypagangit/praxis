# Final Praxis Execution Runbook

This document is the operating instruction set for Final Praxis 001-003. The goal is to prevent exploratory convenience from changing the scientific question after results are visible.

## Rule 0 — Proposal Files Are Immutable Evidence

Once a preregistration is frozen, do not rewrite it to match outcomes. Amendments require a new dated file explaining what changed and whether the change occurred before or after result inspection.

## Phase 1 — Novelty Kill/Go

For each experiment:

1. Search 2024-2026 literature and code for the closest direct experimental work.
2. Maintain a table with: paper, year, venue/status, task, intervention, ground truth, metrics, and exact overlap.
3. Write one sentence: **"Prior work does X; Final Praxis N uniquely tests Y under Z."**
4. Ask the kill question: if Y is only a renamed architecture/component already measured elsewhere, stop.
5. Record `NOVELTY_GATE_PASS` or `NOVELTY_GATE_FAIL` with date and sources.

Do not begin full implementation before this gate passes. Fixture code may be built only to test feasibility.

## Phase 2 — Preregistration

Create `PREREGISTRATION_v1.md` in the experiment folder containing:

- research question;
- threat/failure model;
- hypotheses;
- frozen dataset/task source and hash or generator commit;
- discovery model(s) and exact version;
- arms and baselines;
- unit of analysis;
- inclusion/exclusion rules;
- primary and secondary metrics;
- confidence interval/statistical method;
- promotion thresholds;
- kill thresholds;
- planned sample size and its justification;
- seed list;
- maximum allowed infrastructure retries;
- what counts as protocol invalid.

Hash the preregistration and save the hash in `FROZEN_PROTOCOL.json`.

## Phase 3 — Harness and Fixture Gate

Build the smallest deterministic fixture suite capable of testing every result path:

- true positive/success;
- true negative/failure;
- malformed output;
- ambiguous/partial state where applicable;
- clean utility case;
- intervention/review case.

Requirements:

- tests pass locally/CI;
- metrics are independently recomputable from raw artifacts;
- no scientific result is inferred from fixture performance;
- log schema includes experiment ID, protocol hash, model identity, task ID, seed, arm, timestamp, and raw outcome pointers.

Create `FIXTURE_GATE.md` with PASS/FAIL and exact test counts.

## Phase 4 — Frozen Pilot

The pilot exists to find broken infrastructure, not to optimize the hypothesis.

- Use a small preregistered sample.
- Do not adjust scientific thresholds after viewing pilot outcomes.
- Allowed changes are parser bugs, unavailable model substitution documented before rerun, or deterministic harness corrections.
- Every correction gets an amendment file.

If the pilot reveals that the phenomenon is absent, classify it honestly rather than searching task variants until it appears.

## Phase 5 — Discovery Run

Before launch, run a preflight script that verifies:

- protocol hash;
- dataset/task hash;
- model/version;
- arm configuration;
- seed list;
- expected task count;
- exclusion rules;
- output destination is empty/new.

Then execute the frozen run. Preserve raw outputs. Never overwrite a completed run directory.

## Phase 6 — Independent Verification

Use a separate verifier script/process to:

- confirm hashes and model identity;
- verify unique task IDs and denominators;
- detect duplicate/missing outputs;
- recompute primary metrics from raw records;
- check exclusions against preregistered rules;
- compute confidence intervals/statistical tests;
- compare every gate to its frozen threshold.

The verifier outputs `FINAL_DETERMINATION.md` without reading a desired classification from the experiment code.

## Phase 7 — Classification

Allowed final labels:

- **Strong Bounded Positive**
- **Bounded Positive**
- **Mixed**
- **Negative**
- **Protocol Invalid**
- **Blocked**

Rules:

- Missing a mandatory safety/review/sample-size gate cannot be promoted by strong descriptive performance.
- A negative result remains a completed experiment.
- A mixed result must identify exactly which preregistered hypotheses passed and failed.
- Do not re-run with changed thresholds under the same experiment identity.

## Phase 8 — Replication

Replication starts only after the discovery result is frozen.

- second model and/or second domain;
- no discovery-threshold changes;
- report agreement and disagreement separately;
- external-validity failure narrows the claim; it does not erase the original bounded discovery result.

## Phase 9 — Paper/Defense Package

Each completed Final Praxis folder should end with:

- `README.md` — stable experiment charter;
- `NOVELTY_REVIEW.md`;
- `PREREGISTRATION_v1.md` and amendments;
- `FROZEN_PROTOCOL.json`;
- `FIXTURE_GATE.md`;
- `runs/<run-id>/raw/` and summary artifacts;
- `INDEPENDENT_VERIFICATION.md`;
- `FINAL_DETERMINATION.md`;
- `CLAIM_BOUNDARY.md`;
- `paper/` with abstract, methods, results tables/figures, limitations, references;
- reproducibility instructions.

## Recommended Build Sequence

### Final Praxis 001

1. novelty table;
2. task/postcondition taxonomy;
3. verifier schema;
4. judge baseline freeze;
5. fixture corpus;
6. preregistration;
7. discovery run;
8. second-model replication.

### Final Praxis 002

1. aggressive novelty review first;
2. freeze workflow/state machine;
3. define deterministic gates and error families;
4. create clean/error matched task pairs;
5. run a no-model state-machine fixture;
6. preregister arms and cascade metrics;
7. discovery run;
8. replication only if cascade phenomenon is measurable.

### Final Praxis 003

1. calculate calibration/review sample requirement before build commitment;
2. audit policy-selection independence from old descriptive runs;
3. choose and freeze cyber-triage corpus/evidence schedule;
4. implement mechanical review gate and test it on fixtures;
5. preregister all policies/thresholds;
6. discovery run;
7. do not classify unless the planned safety denominator is met.

## Resource Discipline

Prioritize experiments by information gained per compute dollar:

1. Final Praxis 001 first because ground truth and falsification are clean.
2. Final Praxis 002 second after novelty survives; build cost is higher.
3. Final Praxis 003 only after its calibration/protocol gate clears.

Do not run expensive cloud work merely because capacity is available. Every cloud job should map to a frozen hypothesis and decision gate.
