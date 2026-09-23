# Experiment 052 — Provenance-Aware Tool-Boundary Monitoring

**Status:** 🟢 Live-agent provenance pass  
**Historical ID:** PX-052 / PX-052V

## In plain English
Before trusting an AI agent's tool argument, track where that argument came from.

## Problem
A tool call may contain an invalid or untrusted value even when the surrounding agent response looks reasonable.

## Approach
Preserve lineage from challenge/input to model output to final tool argument and flag invalid or untrusted arguments at the tool boundary.

## Data
The same **288-row** combined Qwen/DeepSeek live-agent tool-call trace corpus used by the agent-defense line.

## Result
Alert recall was **1.0000**, clean false-positive rate **0.0000**, and trace completeness **1.0000** on this corpus.

## Evidence
- [Live-agent provenance refresh](../../reports/agentic_deployment_defense/px052v_live_agent_provenance_refresh_20260705/PX052V_LIVE_AGENT_PROVENANCE_REFRESH_20260705.md)
- [Original provenance gate](../../reports/agentic_deployment_defense/px052_provenance_gate_20260705/PX052_PROVENANCE_TOOL_BOUNDARY_GATE_20260705.md)

[← Pagan Praxis dashboard](../../README.md)
