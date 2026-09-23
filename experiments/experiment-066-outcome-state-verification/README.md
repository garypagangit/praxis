# Experiment 066 — Outcome-State Verification

**Status:** 🔴 Negative — independently verified complete  
**Historical ID:** Final Praxis 001

## In plain English
An AI agent can say “done” even when the actual environment does not match the requested outcome. This experiment compared an LLM judge with authoritative state checks.

## Problem
A fluent completion message is not proof that the requested state transition happened or that unrelated state was preserved.

## Approach
A Qwen2.5-7B agent generated actions and completion assessments. A distinct Mistral-7B judge evaluated the transcript, while a deterministic verifier checked authoritative final state.

## Data
A controlled inert corpus of **400 task instances**, based on **20 JSON-state task templates** in four families. Half of the imposed final states were invalid. This is an experimental stress distribution, not a natural agent-error prevalence estimate.

## Result
The learned judge accepted **7/200 (3.5%)** invalid states; the deterministic verifier accepted **0/200**. The preregistered experiment was nevertheless **Negative** because the required non-trivial judge gap and collateral gates failed. The judge also accepted only 19/200 valid states and 205/400 responses violated the frozen schema.

## Why the negative matters
The expected large false-success gap did not appear under this judge/protocol. The result also shows that low false-success acceptance alone does not establish a useful judge if valid-task acceptance and schema compliance are poor.

## Evidence
- [Full Praxis report](../../final_praxis/001_outcome_state_verification/paper/PRAXIS_REPORT.md)
- [Final determination](../../final_praxis/001_outcome_state_verification/FINAL_DETERMINATION.md)
- [Independent verification](../../final_praxis/001_outcome_state_verification/INDEPENDENT_VERIFICATION.md)
- [Novelty gate](../../final_praxis/001_outcome_state_verification/001_NOVELTY_GATE_20260908.md)

[← Pagan Praxis dashboard](../../README.md)
