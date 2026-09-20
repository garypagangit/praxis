# Published MAGIC baseline qualification

Status: preparing a separately frozen development reproduction. See [protocol](PROTOCOL.md) for the two fixed cases, implementation caveats, resource gates and evaluation limits.

This work follows the completed negative [stability comparison](../normal_stability/results/gpu_stability_20260920/REPORT.md). It tests the original 64-dimensional edge-aware MAGIC model before proposing further checker changes. It does not change the completed study or claim a new algorithm.

The source-original run preserves observed masking-target aliasing and normalization behavior. Test-label-selected thresholds are labeled descriptive oracles. Results under the qualified newer runtime are not an exact historical-runtime reproduction.
