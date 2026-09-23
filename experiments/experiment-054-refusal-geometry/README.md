# Experiment 054 — Refusal Geometry Across Recurrent Depth

**Status:** 🟢 Defense-ready bounded characterization positive  
**Historical ID:** PX-054

## In plain English
When a recurrent model reasons at different depths, does the internal direction associated with refusal remain recognizable?

## Problem
If safety-related internal representations move unpredictably with depth, depth-dependent analysis becomes hard to interpret.

## Approach
Measure refusal-direction geometry across recurrent depths using a safe prompt set and bounded characterization protocol.

## Data
AWS Huginn scale gate: **120 prompts**, depths **[4, 8, 16, 32, 64]**, producing **600/600** captured activation rows.

## Result
Cross-depth stability was **0.9257** with bootstrap CI **[0.9067, 0.9273]**; benign-control FPR was **0.0000** and worst refusal TPR **0.9750**.

## Claim boundary
Characterization only. This is not refusal-removal, jailbreak optimization, or a deployed safety-defense claim.

## Evidence
- [Final manuscript](../../reports/refusal_geometry_recurrent_depth/px054_final_manuscript_20260706/PX054_FINAL_MANUSCRIPT_20260706.md)
- [Final defense package](../../reports/refusal_geometry_recurrent_depth/px054_final_defense_package_export_20260706/PX054_FINAL_DEFENSE_PACKAGE_EXPORT_20260706.md)
- [Scale gate](../../reports/refusal_geometry_recurrent_depth/scale_gate_20260705/PX054_REFUSAL_GEOMETRY_SCALE_GATE_20260705.md)

[← Pagan Praxis dashboard](../../README.md)
