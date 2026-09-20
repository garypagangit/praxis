# Choosing cyberattack alerts using normal activity alone

This separately registered development experiment asks whether the stronger published MAGIC graph model can choose a useful alert threshold without consulting attack labels.

Train fresh models on normal graphs 0–2, choose the threshold on normal graph 3, then evaluate the fixed detector on test graph 0. Run all three declared seeds on both THEIA and CADETS. All six normal calibrations must finish and be frozen before any attack evaluation.

Every case must detect at least 50% of annotated malicious rows while flagging at most 2% of benchmark-negative rows. A failed case cannot be rescued by averaging results or choosing a different threshold.

See [the protocol](PROTOCOL.md) for the exact partitions, tie rule, evidence requirements, resource limits and interpretation. The earlier [published-model reproduction](../magic_compact/results/gpu_reproduction_20260920/REPORT.md) used test-label-selected thresholds; its strong scores motivated this practical test.

This study uses previously exposed development data and established methods. It does not by itself establish novelty, independent campaign generalization, actor identification or deployment readiness.

## Reproducibility

The registration binds the new runtime, both frozen parent runtimes, author source and input data. The worker saves full fit, calibration and test arrays, first/final checkpoints, every epoch record, threshold freezes and measured outcomes. An independent auditor checks the saved evidence without rerunning neural training.

The existing qualified AWS controller enforces the host deadline and verifies shutdown. Raw arrays, models, logs and cloud identifiers stay in the private evidence directory; sanitized reports and receipts are published here after completion.
