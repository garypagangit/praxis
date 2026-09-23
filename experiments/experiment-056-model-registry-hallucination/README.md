# Experiment 056 — Model-Registry Identifier Hallucination

**Status:** 🔵 Live pilot positive; full study pending  
**Historical ID:** PX-056

## In plain English
Coding models sometimes invent model or dataset names. This experiment checks those identifiers against real registries before code trusts them.

## Problem
Hallucinated Hugging Face or NVIDIA NGC identifiers can break model-loading and physical-AI workflows.

## Approach
Extract model/dataset/package identifiers from live code-model outputs and verify them against registry evidence.

## Data
Gate 2A used **3 open code models**, **378 outputs**, and **1,282 extracted identifiers**.

## Result
The pilot found nonexistent physical-model-registry identifiers in **2/33** verified model-registry rows and nonexistent package identifiers in **206/1,016** verified package rows. Deterministic gate blocks were 232 with **0 known-missing escapes**. This is feasibility/directional evidence, not the final H1-H4 result.

## Evidence
- [Gate 2A determination](../../reports/model_registry_hallucination/gate2a_live_pilot_20260721/px056-gate2a-live-pilot-20260721-202454/PX056_GATE2A_DETERMINATION_20260721.md)
- [Preregistration](../../reports/model_registry_hallucination/PX056_MODEL_REGISTRY_HALLUCINATION_PREREG_20260721.md)
- [Source gate](../../reports/model_registry_hallucination/source_gate_20260721/PX056_MODEL_REGISTRY_SOURCE_GATE_20260721.md)

[← Pagan Praxis dashboard](../../README.md)
