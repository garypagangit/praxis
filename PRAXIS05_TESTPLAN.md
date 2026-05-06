# Praxis 05 Test Plan: Sparse Autoencoders for APT Detection Interpretability

Version: 1.0. Phase A is a kill switch.

## 0. Honest Framing

Praxis 05 applies mechanistic-interpretability sparse autoencoders (SAEs) to hidden activations from provenance-graph APT detectors. The target detector is MAGIC. The study is high risk: recent SAE reliability work reports seed instability and weak probe advantages, so Phase A is explicitly designed to fail fast.

This project commits to Phase A first. Phase B and Phase C must not run until Phase A passes.

## 1. Pre-Registered Hypotheses

H1: A TopK SAE trained on MAGIC hidden states discovers semantically coherent features.

H2: A linear probe on SAE features matches or exceeds MAGIC native anomaly-score AUROC without losing more than 2 absolute F1 points.

H3: SAE features transfer across E3-CADETS, E3-THEIA, and E3-Trace.

## 2. Phase A Kill-Switch Criteria

Phase A trains 5 TopK SAEs on E3-CADETS MAGIC activations using seeds `13, 42, 137, 271, 1729`.

Pass thresholds:

- Reconstruction MSE ratio: SAE MSE must be `< 0.25` of mean-baseline MSE.
- Feature death rate: dead features must be `< 0.50`.
- Seed stability: top-100 feature overlap must be `> 0.30` average pairwise overlap.

Hard stop:

- If any criterion fails, do not proceed to Phase B.
- If MAGIC reproduction misses the published AUROC/F1 by more than 2 absolute points, stop before SAE training and write a replication-gap report.
- One PIDSMaker pivot is allowed if MAGIC hidden states are too small or degenerate. If PIDSMaker also fails, write the negative-result note.

## 3. Implementation Scope In This Repo

Implemented now:

- Phase A config, activation cache, hook utilities, SAE training wrapper, diagnostics, smoke test, and report scaffold.
- Real research backend expects `sae-lens==6.43.0` and external MAGIC activations.
- Local `torch_topk_smoke` backend exists only for CI/pipeline smoke tests. It is not the research SAE backend.

Not implemented until Phase A passes:

- Phase B top-activating subgraph interpretation.
- Phase B human annotation UI.
- Phase C probes and cross-dataset transfer.

## 4. Repeatable Phase A Commands

Setup:

```bash
bash scripts/praxis05_01_setup.sh
```

MAGIC reproduction:

```bash
export MAGIC_REPRO_COMMAND="<upstream MAGIC train/eval command for E3-CADETS>"
bash scripts/praxis05_02_reproduce_magic.sh
```

Activation extraction, using a pre-exported tensor or the synthetic smoke path:

```powershell
.\.venv\Scripts\python.exe scripts\praxis05_03_extract_activations.py --synthetic-smoke --output-dir runs\praxis05-smoke\activations
```

Train 5 Phase A SAEs:

```powershell
.\.venv\Scripts\python.exe scripts\praxis05_04_phase_a_train_saes.py --config configs\praxis05-sae-topk-k32-x16.json --cache-dir data\praxis05\activations\e3cadets --output-root runs\praxis05-phase-a
```

Run diagnostics:

```powershell
.\.venv\Scripts\python.exe scripts\praxis05_05_phase_a_diagnostics.py --phase-a-root runs\praxis05-phase-a --output results\praxis05\phase_a\diagnostics.json
```

Local smoke only:

```powershell
.\.venv\Scripts\python.exe scripts\praxis05_phase_a_smoke.py --output-root runs\praxis05-phase-a-smoke
```

## 5. Outcome Rules

- Phase A pass: ask before implementing Phase B.
- Phase A fail by reconstruction/death/stability: stop and write the negative result.
- Oracle/pivot to PIDSMaker: one attempt maximum.

