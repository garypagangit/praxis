# OpTC Window Gate

Generated: 2026-05-15

Status: **superseded by expanded OpTC gate**

This report path was used by the reusable window-builder wrapper while constructing targeted OpTC host/day slices. The single-slice window-factory output is no longer the decision artifact.

## Current Decision Artifact

Use `reports/provenance_architecture/OPTC_CROSS_HOST_GATE_20260515.md`.

That expanded gate combines:

- Three red-team host/day slices: `sysclient0501` day 2, `sysclient0201` day 1, and `sysclient0051` day 3.
- Three clean benign baselines for the same host groups from `benign/20-23Sep19`.
- `717` usable non-gray windows and `108` excluded gray-buffer windows.

## Decision

The OpTC window-label path is ready as a label/data artifact. Detector promotion is blocked because host/day holdout fails even though pooled/random sanity is strong.

## Claim Guard

Do not use this per-slice wrapper report to claim a detector. Use it only as evidence that the window factory can build OpTC feature tables. The detector decision lives in the expanded cross-host gate.
