# Execution history

Both GPU attempts are retained. The retry changed the launch working directory and used fresh cache/output directories. The Soup source, worker, protocol, dependency versions, inputs, reference path, assignments and numerical criteria were unchanged.

| Attempt | Observed outcome | Treatment |
|---|---|---|
| Initial shell launch, before worker installation/execution | The coordinator reported an SSM shell parse failure and changed the launcher to explicit bash. | Operational failure; no scientific assignments completed. The coordinator maintains the raw launch receipt. |
| GPU attempt 1 | Both BF16 and NF4 sharding calls rejected the output directory because it was outside `$HOME`, `$CWD` and `$TMPDIR`. All 16 positive assignments remained `not_completed`; zero of four negative controls and zero of nine timing blocks ran. Process exit was 1. | Incomplete qualification, retained without deletion or reclassification as a numerical failure. |
| GPU attempt 2, 2026-09-14 14:14:40–14:14:58 UTC from worker log | The coordinator launched the same code from the common `009` parent so new shard directories were under the current working directory. All assigned correctness controls and timing blocks completed. Process exit was 0. | Successful tiny-model instrumentation qualification; separate artifact reconciliation passed. |

Attempt 1's top-level `status: complete` means the worker finished enumerating its assignments. Its `qualification_pass: false`, `instrumentation_complete: false` and zero completion counters govern the result. It must not be counted as a successful experiment.

The two GPU receipts contain exactly identical `provenance` objects, and their `PIP_FREEZE.txt` files are byte-identical. Both name the original protocol SHA-256 `042559776af19736332c95664729a72876927544495f719639afbcd73264394b` and worker SHA-256 `541cfa76913aa877ead51858ec011f065ec83d98a62662da9259448dc60528c9`. Original source and frozen bundle files were not edited after this run.

The [lineage receipt](results/EXECUTION_LINEAGE.json) binds every copied artifact to its original bytes and both downloaded archive hashes. Attempt 1 remains under [results/attempt1](results/attempt1); successful artifacts are under [results/gpu](results/gpu). The raw safetensors contain compact random-model numerical outputs, gradients and adapter states, not the public Emotion dataset or pretrained model weights.
