# PX-093: Heterogeneous Warning Gates and False-Alert Accounting

[Findings and Plan B decision](FINDINGS.md) | [Results table](RESULTS.md) | [All 288 result rows](RESULTS.csv) | [Audit](AUDIT.json) | [Literature review](LITERATURE_AND_CLAIMS.md)

Complete. H1 passed by construction; H2 and H3 failed their joint criteria because warning recovery came with excessive false alerts under the frozen fixed-baseline guard. Both logistic-regression fits converged. The original PX-092 H3 remains failed.

This is the requested A6 heterogeneous-member extension, separately registered as PX-093. Commit `704ae24` froze the protocol, experiment code, independent audit, boundary tests, input hashes and software versions before either new fit. The existing current-only LightGBM was reused; two logistic-regression models were fitted locally. No cloud or model API was used.

## Evidence and reproduction

Four boundary tests passed before fitting. The independent audit passed 24,239 checks across 96 cells and 288 rows. It reproduced both LR models' full evaluation probabilities and all saved gate decisions. The compressed RESULTS.json.gz contains all members, confusion matrices, constituent metrics, row/label hashes and per-row artifact hashes. Raw data, models and decisions remain private at `C:/w/px093_heterogeneous_20260930` and the input paths in run.py.

Use the existing `C:/w/praxis_full_release_20260927_env/Scripts/python.exe` environment. Execution order: `run.py freeze`, commit the freeze, `run.py fit-unr` and `run.py fit-ait` in parallel, then `run.py replay`, `audit.py`, and `report.py`. Completed fit and replay outputs refuse overwrite. Reproduction needs a fresh output directory and a documented path amendment, preserving original artifacts. Decompress RESULTS.json.gz to RESULTS.json before auditing from a Git checkout. Training sources must also be available privately.

Report generation writes tables and preliminary findings; final editorial interpretation was added after review. Re-running report.py would overwrite those prose additions and attempts to register PX-093 again. The numerical experiment and audit sources were not edited after the freeze.

`OR_*`, overlap and mean-loss fields describe the model set and are repeated on its three aggregator rows. Individual-model arms may lose base warnings as well as recover others; added-warning counts are not their net gain. The full A6 arm contains every base member, so its added-warning counts are net gains. All costs are simulated acquisition units, with separate model counts; no analyst response or deployment safety was measured.
