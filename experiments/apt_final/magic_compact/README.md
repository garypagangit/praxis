# Finish the published graph-model test with exact duplicate compression

**Completed and audited.** Both 50-epoch dataset evaluations finished through the exact-compression runtime. Read the [reproduction report](results/gpu_reproduction_20260920/REPORT.md); thresholds use test labels. The separate [normal-only calibration study](../magic_calibrated/results/gpu_calibrated_20260920/REPORT.md) is also complete.

The uncompressed THEIA run completed its training-only qualification but could not fit full scoring into the fixed time budget. At that first-epoch qualification, its 1,279,199 reference rows contain 26,087 exact distinct vectors after standardization. Retaining integer counts permits a much smaller search while preserving the original mathematical reference distribution.

This [runtime amendment](PROTOCOL.md) keeps the [original registered science](../magic_reproduction/REGISTRATION.json) unchanged. It does not claim a novel detector. Each amended attempt trains from scratch and records the explicit scorer substitution separately.

Original data, source, model checkpoints and row-aligned embeddings remain private; source freezes, sanitized reports and independent audit receipts are published with the completed reproduction report.
