# Experiment 068 — Adaptive Cyber Investigation Stopping

**Status:** 🔴 Negative — independently verified complete  
**Historical ID:** Final Praxis 003

## In plain English
A security AI may reach the right answer and then reason itself away from it. This experiment tested whether a safety-gated stopping rule could stop at the right time.

## Problem
Comparing only final accuracy and token cost hides two important events: preventing a correct answer from degrading, and stopping too early before later evidence would correct a wrong answer.

## Approach
Each case produced an eight-round staged-evidence trace. Fixed-short, fixed-long, answer-stability, and safety-gated stability policies were evaluated on the same traces with explicit harm and review gates.

## Data
A frozen generated corpus of **400 inert security authorization cases** with eight rounds each, producing **3,200 real inference records**. Labels came from an explicit authorization rule. This is controlled generated data, not a sample of real SOC incidents.

## Result
The safety-gated policy achieved **34.5% correctness**, **31.03% token saving**, and prevented some degradation, but early-stop harm was **34/400 (8.5%)** with a one-sided 95% upper bound of **11.16%**. Every case required review. Fixed-long correctness was **54.25%**. Mandatory safety and utility gates failed.

## Why the negative matters
Stopping saved compute and sometimes prevented degradation, but the safety mechanism harmed too many cases and reviewed everything. That is exactly the kind of failure the preregistered safety gates were designed to expose.

## Evidence
- [Full Praxis report](../../final_praxis/003_adaptive_investigation_stopping/paper/PRAXIS_REPORT.md)
- [Final determination](../../final_praxis/003_adaptive_investigation_stopping/FINAL_DETERMINATION.md)
- [Independent verification](../../final_praxis/003_adaptive_investigation_stopping/INDEPENDENT_VERIFICATION.md)

[← Pagan Praxis dashboard](../../README.md)
