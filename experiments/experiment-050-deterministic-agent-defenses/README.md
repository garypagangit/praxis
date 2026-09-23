# Experiment 050 — Deterministic Tool-Boundary Agent Defenses

**Status:** 🟢 Lead bounded positive  
**Historical ID:** PX-050

## In plain English
If a coding agent invents a package name, do not let the agent's confidence decide whether installation is safe. Check the package and command deterministically at the tool boundary.

## Problem
Package hallucinations can become executable install commands.

## Approach
Parse proposed package-manager commands, reject unsafe command composition and remote/file specifications, and verify package names against a frozen valid-package set before execution.

## Data
Fixed fixtures, live Qwen and DeepSeek generations, parser-stress mutations, StarCoder2 held-out repair runs, and two-model dry-run live-agent tool-call corpora.

## Result
Across the measured positive corpora, the hardened gate produced **zero observed invalid-package escapes** while preserving high valid-command utility. Some raw held-out StarCoder2 promotion gates failed and are retained as boundary evidence.

## Evidence
- [Final manuscript](../../reports/agentic_deployment_defense/px050_final_manuscript_20260705/PX050_FINAL_MANUSCRIPT_20260705.md)
- [Final defense package](../../reports/agentic_deployment_defense/px050_final_defense_package_export_20260705/PX050_FINAL_DEFENSE_PACKAGE_EXPORT_20260705.md)
- [Two-model live-agent determination](../../reports/agentic_deployment_defense/px050_live_agent_two_model_determination_20260705/PX050_LIVE_AGENT_TWO_MODEL_FINAL_DETERMINATION_20260705.md)

[← Pagan Praxis dashboard](../../README.md)
