# Experiment 051 — Security-Utility Pareto for Agent Gates

**Status:** 🟢 Live-agent policy pass  
**Historical ID:** PX-051 / PX-051V

## In plain English
A security gate is useless if it blocks everything. This experiment asks whether we can block unsafe agent actions while still allowing useful work and avoiding review-all behavior.

## Problem
Security controls can look safe simply because they overblock legitimate actions.

## Approach
Evaluate the hardened policy as a security/utility operating point on live-agent tool-call traces.

## Data
Combined **288-row** Qwen/DeepSeek live-agent tool-call corpus produced by the PX-050U/PX-050V line.

## Result
Hardened invalid escape was **0.0000**, useful-work preservation was **1.0000**, and review rate was **0.0243**.

## Evidence
- [Live-agent policy refresh](../../reports/agentic_deployment_defense/px051v_live_agent_policy_refresh_20260705/PX051V_LIVE_AGENT_POLICY_REFRESH_20260705.md)
- [Original Pareto gate](../../reports/agentic_deployment_defense/px051_pareto_gate_20260705/PX051_SECURITY_UTILITY_PARETO_GATE_20260705.md)

[← Pagan Praxis dashboard](../../README.md)
