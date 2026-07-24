# New Praxis Experiment Build Order

Date: 2026-07-23

Status: pre-registration and staged implementation. No entry below is a positive result merely because its source, harness, or fixture gate passes.

## Numbering

| PX | Experiment | First scientific test | Readiness |
|---|---|---|---|
| PX-057 | Adaptive Stopping to Prevent LLM Overthinking | Stability/uncertainty stopping on frozen multi-step reasoning traces | Gate 0 harness built first |
| PX-058 | Explanation Stability and Drift for Network Intrusion Detection | Seed/split explanation stability and held-out drift prediction | Public CICIDS2017 path; build second |
| PX-059 | Uncertainty-Adaptive Speculative Decoding | Dynamic EAGLE draft depth under fixed hardware/output controls | Code/model source verification required |
| PX-060 | Robustness and Meaning of Learned Continuous Edge Directions | Missing/reversed/noisy-edge perturbation and direction stability | Public graph benchmarks; code verification required |
| PX-061 | Unequal Wavelet Noise and Adaptive Clipping for Private FL | Matched-epsilon comparison under non-IID clients | Public MNIST/Fashion-MNIST/CIFAR-10 |
| PX-062 | Provenance and Existence Gate for Coding-Agent Skills | Legitimate repo, nonexistent ID, and hash-mismatch inert canaries | GitHub-accessible; anchor artifact verification required |
| PX-063 | Deterministic Reward-Hack Verification on TRACE | Deterministic checks versus published judge baseline | Blocked until TRACE is fetched |
| PX-064 | Registry Verification as Environment Hardening in Tool-Use RL | Gated versus ungated exploit and task-success comparison | Blocked until RHB environments are verified |
| PX-065 | Provenance-Admission Gate for Agent Memory | Signed legitimate entries versus inert invalid-provenance canaries | Self-contained simulation after source verification |

Attached Plan #1 remains **PX-050**, because it describes the already-established package-verification core. It is not counted as a new contribution.

## Build order

1. PX-057: strongest combination of public benchmarks, measurable failure, moderate compute, and direct intervention.
2. PX-058: inexpensive public-data experiment with a clear missing construct: explanation stability rather than accuracy alone.
3. PX-059: strong systems result if EAGLE artifacts reproduce locally; hardware control is mandatory.
4. PX-060: public graph benchmarks and falsifiable robustness tests.
5. PX-061: public datasets and clear future-work extension, but privacy accounting raises implementation burden.
6. PX-062: live source surface and clean inert-canary design.
7. PX-063: conceptually simple once TRACE is local.
8. PX-065: self-contained but must be anchored to verified memory-lifecycle semantics.
9. PX-064: highest infrastructure and environment-reproduction burden.

## Common promotion contract

- Freeze hypotheses, controls, metrics, thresholds, and exclusions before non-fixture data.
- Separate source/readiness, harness validity, pilot, full scientific gate, replication, and publication packaging.
- Include the strongest cheap baseline before training or cloud spend.
- Report confidence intervals and denominators, not point estimates alone.
- Preserve negative results; do not move thresholds after inspection.
- Use inert defensive canaries only for the verification-gate family.

## Current action

PX-057 Gate 0 is the active build. Its fixture gate validates trace parsing and metric computation only. The first scientific result requires frozen model-generated traces from public reasoning benchmarks.
