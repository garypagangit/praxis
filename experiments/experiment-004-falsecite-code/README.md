# Experiment 004 — FalseCite-Code Software-Artifact Citation Poisoning

**Status:** 🟢 Bounded defense-positive  
**Historical ID:** PX-004

## In plain English
Coding assistants can confidently cite packages, versions, repositories, or tags that do not exist. This experiment checks those claims against real software metadata before trusting them.

## Problem
A fabricated software reference can look plausible enough for a code model to accept and act on.

## Approach
Compare a code model's trust decision with a deterministic verifier backed by public PyPI, NPM, and GitHub metadata.

## Data
A locked **80-claim** benchmark: 20 GitHub repositories, 20 GitHub tags, 20 NPM versions, and 20 PyPI versions, with valid and fabricated variants.

## Result
Qwen2.5-Coder-7B accepted fabricated citations at high rates in the unverified condition. The citation-aware verifier reduced strict-holdout fabricated trust to **0.0000** in the primary gates.

## Evidence
- [Final short paper](../../reports/falsecite_code/FALSECITE_CODE_SHORT_PAPER_20260628.md)
- [Dashboard](../../reports/falsecite_code/FALSECITE_CODE_DASHBOARD_20260625.html)

[← Pagan Praxis dashboard](../../README.md)
