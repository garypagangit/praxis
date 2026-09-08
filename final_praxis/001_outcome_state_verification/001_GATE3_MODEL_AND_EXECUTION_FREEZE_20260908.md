# Final Praxis 001 — Gate 3 Model and Execution Freeze

Date: 2026-09-08
Status: **FROZEN / execution blocked until compute adapter is available**

## Discovery agent model

Primary agent: `Qwen/Qwen2.5-7B-Instruct`.

Reason: this exact open model is already used repeatedly in the Praxis repository and existing cloud GPU patterns support reproducible local/cloud execution. Model identity must be recorded by resolved revision/hash at run time.

Replication agent: `mistralai/Mistral-7B-Instruct-v0.3`, only after the discovery result is frozen. Replication cannot alter discovery thresholds.

## Primary judge

Primary judge must be a model **different from the discovery agent** and frozen before the end-to-end pilot. It receives task request, agent-visible transcript/tool observations, and final completion claim only. It never receives hidden expected-state metadata, fixture class, verifier implementation, or deterministic verdict.

Because this chat/GitHub connector does not expose an executable LLM inference endpoint or the repository's cloud credentials, the exact judge endpoint cannot be truthfully executed here. The runner therefore remains fail-closed until an external compute adapter is supplied.

## Generation settings

Discovery agent:
- deterministic/low-variance decoding: temperature `0.0` where supported;
- one completion per scientific unit;
- maximum output/tool-step budget frozen in config before pilot;
- no retries for semantic mistakes; provider/infrastructure retry only with identical request ID lineage;
- preserve refusals and malformed outputs as outcomes.

Judge:
- temperature `0.0` where supported;
- structured JSON decision required;
- one primary judgment per unit;
- no majority-vote rescue in discovery.

## Scientific allocation

Frozen primary set: 400 units.
- 20 tasks × 20 units/task.
- 200 valid-success target conditions: 100 clean, 100 alternate-valid.
- 200 invalid-success target conditions: 50 incomplete, 50 false-success, 50 partial, 50 collateral-damage.

Optional control: 40 admitted-failure units (2/task).

Condition allocation must be generated from a fixed seed before model inference and stored before outputs are produced.

## Gate 3 pilot

The first executable model pilot is infrastructure-only and must use **no more than 2 tasks per state family and 1 unit per selected condition**, capped at 16 agent units. It may validate:
- model loading/inference;
- tool-call serialization;
- state reset;
- transcript capture;
- judge structured output parsing;
- artifact persistence;
- independent recomputation.

It may **not** alter scientific hypotheses, task definitions, sample size, FSAR/TSAR/APAR/CVMR thresholds, or condition allocation based on observed scientific direction.

## Hard stop

Do not label Final Praxis 001 scientifically complete until:
1. a real agent adapter executes the frozen model;
2. a distinct real judge adapter executes the frozen judge protocol;
3. Gate 3 pilot passes;
4. 400-unit discovery executes;
5. independent verification recomputes all primary metrics;
6. promotion/kill rules are applied without threshold changes.

Current status is therefore **BLOCKED ON EXTERNAL MODEL COMPUTE, not a scientific result**.