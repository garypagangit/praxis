# Praxis 05 Phase A Status

Status: scaffold complete; real Phase A not yet run.

## What Is Built

- `PRAXIS05_TESTPLAN.md` records the Phase A kill switch and pass/fail thresholds.
- `configs/praxis05-sae-topk-k32-x16.json` freezes the real Phase A SAE settings:
  - TopK SAE
  - `k = 32`
  - `expansion_factor = 16`
  - `n_features = 4096`
  - seeds `[13, 42, 137, 271, 1729]`
  - kill-switch thresholds: MSE ratio `< 0.25`, death rate `< 0.50`, seed stability `> 0.30`
- `src/praxis/praxis05/` contains Phase A activation caching, MAGIC hook utilities, SAE training wrappers, and diagnostics.
- `scripts/praxis05_01_setup.sh` and `scripts/praxis05_02_reproduce_magic.sh` prepare the external MAGIC/PIDSMaker path and enforce the replication gate.
- `scripts/praxis05_03_extract_activations.py`, `scripts/praxis05_04_phase_a_train_saes.py`, and `scripts/praxis05_05_phase_a_diagnostics.py` implement the Phase A command sequence.

## Local Smoke Check

The local smoke pipeline uses `backend = torch_topk_smoke` on synthetic activations. This is only a CI and wiring check. It is not the research SAE backend and must not be reported as a Praxis 5 result.

Smoke command:

```powershell
.\.venv\Scripts\python.exe scripts\praxis05_phase_a_smoke.py --output-root runs\praxis05-phase-a-smoke
```

Smoke output:

- Status: `PASS`
- MSE ratio: `0.3643` against smoke threshold `0.95`
- Feature death rate: `0.3125` against smoke threshold `1.0`
- Seed stability: `0.8500` against smoke threshold `0.0`

## What Is Still Required

1. Install the pinned Praxis 5 dependency file:

   ```bash
   python -m pip install -r requirements-praxis05.txt
   ```

2. Clone and pin MAGIC/PIDSMaker:

   ```bash
   bash scripts/praxis05_01_setup.sh
   ```

3. Reproduce MAGIC on E3-CADETS and verify AUROC/F1 within 2 absolute points of the paper.

4. Extract real MAGIC penultimate activations for benign E3-CADETS training data.

5. Train the 5 real SAELens TopK SAEs.

6. Run `scripts/praxis05_05_phase_a_diagnostics.py`.

Phase B remains intentionally unimplemented until Phase A passes.

