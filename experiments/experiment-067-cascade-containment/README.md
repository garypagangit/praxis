# Experiment 067 — Multi-Agent Cascade Containment

**Status:** 🔴 Negative — independently verified complete  
**Historical ID:** Final Praxis 002

## In plain English
If one AI agent passes bad information to another, can deterministic checkpoints stop that mistake before a downstream agent takes a bad action?

## Problem
Errors can propagate through triage → investigation → response chains. A system can look secure only because it blocks everything, so security and clean-task utility must be measured together.

## Approach
Compare four placements: no gates, final-action gate only, inter-agent handoff gates only, and handoff + final-action gates. Controlled errors were injected into structured handoffs and final symbolic actions were machine-checkable.

## Data
**60 model-independent base scenarios**, six error families with ten cases each. Clean and injected versions were replayed across four arms for **480 workflow units**. Qwen2.5-7B-Instruct filled the three logical roles; actions were simulated, not executed on real systems.

## Result
Ungated invalid-action escapes were **10/60 (16.7%)**; full containment reduced them to **0/60** and reduced propagation depth in all six error families. But clean end-to-end success was only **51/60 (85%)**, below the frozen **90%** utility floor. The final classification is therefore Negative.

## Why the negative matters
The deterministic boundaries clearly contained the measured bad actions, but the complete system did not preserve enough clean workflow utility to satisfy the preregistered claim.

## Evidence
- [Full Praxis report](../../final_praxis/002_cascade_containment/paper/PRAXIS_REPORT.md)
- [Final determination](../../final_praxis/002_cascade_containment/FINAL_DETERMINATION.md)
- [Independent verification](../../final_praxis/002_cascade_containment/INDEPENDENT_VERIFICATION.md)
- [Novelty review](../../final_praxis/002_cascade_containment/NOVELTY_REVIEW.md)

[← Pagan Praxis dashboard](../../README.md)
