# Experiment 003 — Retrieval-Conditioned CTI Compliance

**Status:** 🟢 Defense-ready narrow positive  
**Historical ID:** PX-003 / Praxis 07

## In plain English
Instead of asking an LLM a cyber-threat question and hoping it remembers the right facts, retrieve the specific ATT&CK evidence needed for that question first.

## Problem
Broad cybersecurity prompting can hurt strict answer compliance and does not guarantee grounding in the exact ATT&CK facts needed.

## Approach
Compare vanilla prompting, broad domain seeding, and question-specific ATT&CK relationship evidence under a strict answer parser.

## Data
CTIBench CTI-MCQ scaffold plus MITRE ATT&CK `enterprise-attack-12.0`. The locked evidence-addressable evaluation slice contains **106** questions.

## Result
On the 8B gate, vanilla accuracy was **0.642** and relationship-evidence accuracy was **0.915**. A 3B cross-model gate also passed. Technique-only evidence helped too, so the safe claim is retrieval-conditioned evidence—not pure relationship causality.

## Evidence
- [Result synthesis](../../reports/relationship_evidence_cti_compliance/PRAXIS07_RESULT_SYNTHESIS_20260517.md)
- [Ablation gate](../../reports/relationship_evidence_cti_compliance/SEC_LORD_RELATIONSHIP_EVIDENCE_ABLATION_GATE_20260517.md)
- [Paper package](../../paper/relationship_evidence_cti/)

[← Pagan Praxis dashboard](../../README.md)
