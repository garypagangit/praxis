# Experiment 001 — Safety-Gated TTA for Streaming APT Detection

**Status:** 🟢 Defense-ready positive  
**Historical ID:** PX-001 / Praxis 06

## In plain English
APT detectors can lose rare attack stages when the source of incoming data changes. This experiment asks whether the detector can adapt at test time **without labels**, while a safety gate prevents the adaptation from damaging a high-consequence Data Exfiltration class.

## Problem
A model that works on one source/day can fail after distribution shift, especially on rare stages such as Reconnaissance.

## Approach
A frozen MLP is paired with BatchNorm test-time adaptation and a conservative validation-selected `recon_guarded` override policy.

## Data
Unraveled network-flow telemetry using a held-out source-file split with no source overlap between train, validation, and test.

## Result
Macro F1 improved from **0.7685 to 0.8658**. Reconnaissance F1 improved from **0.0250 to 0.5050**. Data Exfiltration F1 was preserved/improved, and only **4.7%** of predictions were overridden.

## What this supports
Selective no-label adaptation can recover a shifted rare APT stage under this frozen protocol while preserving the protected class.

## Evidence
- [Paper-ready final report](../../reports/tta_streaming_apt/PRAXIS06_PAPER_READY_FINAL_REPORT_20260513.md)
- [Defense hardening addendum](../../reports/tta_streaming_apt/PRAXIS06_DEFENSE_HARDENING_ADDENDUM_20260513.md)
- [Paper assets](../../paper/praxis06_tta/)

[← Pagan Praxis dashboard](../../README.md)
