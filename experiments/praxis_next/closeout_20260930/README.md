# Open-item closeout: PX-088–091

[Results and interpretation](RESULTS.md) | [All 1,770 arms](results/ALL_ARMS.csv) | [Audit](AUDIT.json) | [Frozen protocol](PROTOCOL.md) | [Data and literature qualification](QUALIFICATION.md)

PX-088 and PX-089 are completed exploratory replays. PX-090 is completed as an explicitly adapted expert-score constraint experiment, with six new CPU fits. PX-091 qualification is complete; exact independent replication remains blocked by data requirements. Novelty remains unconfirmed.

Source and inputs were frozen in commit `cc5bde7` before execution. Three local jobs ran concurrently; individual elapsed times were 3.41, 10.78 and 5.89 seconds. No new cloud allocation or model API was used. The earlier AWS worker was already stopped. Local execution avoided repeating the previous large-upload failure.

Six pre-run boundary tests passed. The post-run audit independently checked 1,890 confusion matrices, queue accounting and reconstructed label availability: 51,982 checks passed. This arithmetic audit does not independently reproduce training or establish external validity. Lossless aggregate JSON outputs are included as gzip files; decompressed hashes are in AUDIT.json. Event data, probability arrays and six saved models remain in private local storage.

## Reproduction

Run `test_closeout.py` using unittest. With the private inputs at the paths in `common.py`, run `deferral.py`, `recalibration.py` and `constrained.py` concurrently into a fresh private output directory. Existing output files are protected against overwrite. `audit_report.py` verifies the freeze and publishes aggregate outputs. `source_check.py` records bounded public metadata checks. All data were previously exposed development data.
