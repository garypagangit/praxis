# Can combined audit evidence identify tool-transfer periods?

This bounded diagnostic follows the [negative structured-loss follow-up](../results/robustness_v2/SUMMARY.md). It tests whether the observation unit was too narrow: one audit event can be unrelated to an attack that the author labels across a whole period and multiple hosts. Pooling does not establish that every event in the period is malicious.

## Frozen design

The [protocol](protocol.json), [independent AI/code review](PROTOCOL_REVIEW.md), and [source qualification](DATA_QUALIFICATION.md) were prepared before these new model fits. They define one target (T1105 tool transfer), one ten-second window width, one model seed, and no hyperparameter search. All five scenario families are already exposed development data. Leave-one-family-out fitting evaluates each family using models trained on the other four; the original fit/development/calibration/test names in qualification tables describe the previous experiment only.

The cohort contains 5,480 complete UTC bins: 264 positive, 4,319 other-annotation negatives, and 897 unknown. Empty bins remain, including 13 positives. All 83 published T1105 intervals overlap the included bins. The existing source slice was bounded by annotations; this is retrospective investigation within that slice, not continuous operational detection.

Each model ranks **every bin**, including unknowns, and reviews `ceil(10% * bins)` within each run. Main recall is over labeled positive bins, pooled within family and averaged equally across five families. Unknowns consume budget but are not called false positives. AP, ROC-AUC and known-only precision/F1 are conditional secondary scores. Source-interval coverage is separately labeled as a touch-of-overlapping-bin diagnostic.

| Arm | Evidence and purpose |
|---|---|
| Transfer-tool rule | Count distinct visible curl/wget/scp/sftp/tftp/rsync tokens; simple fixed control |
| Activity count | Rank by visible audit event count; check for activity-volume shortcuts |
| First-event logistic regression | One earliest source event from each bin; aggregation control |
| Pooled logistic regression | All visible defender audit events within the bin; primary model |
| Pooled ExtraTrees | Same pooled features, nonlinear model; secondary control |

Fit the three learned arms once per held-out family on clean, known-label windows. Evaluate both clean evidence and removal of EXECVE/PROCTITLE records without changing windows or labels. Surviving SYSCALL/PATH records can still contain program clues. No network or application source is added in this diagnostic.

## Decision and limits

The useful-signal gate requires primary clean macro-family recall of at least 40%, at least three times expected random-budget recall, and above chance in four of five families. Separate gates test pooling benefit, value over the simple tool rule, and a decline of at least ten recall points after record removal. These are practical development thresholds, not statistical guarantees. ExtraTrees cannot replace the primary after results are seen.

This experiment can justify a focused follow-up or retirement of the tested formulation. It cannot validate novelty, early warning, exact malicious-event recognition, real-world benign false-alert rates, or an independent confirmation. Family 4 has just one source target interval. More complex models cannot resolve that evidential limit.

## Literature and source

- [Landauer et al., CAM-LDS, IJIS 2026](https://doi.org/10.1007/s10207-026-01318-x); [pinned Zenodo release](https://zenodo.org/records/18861762), CC-BY 4.0; [pinned author label code](https://github.com/ait-aecid/attack-manifestations-interpretation/tree/44028d8bd40a4a1d8bbbc6ee33261d47cb433827).
- [Bilot et al., USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/bilot) supports including strong simple controls when evaluating provenance-based detection.
- [HunterAgent, May 2026 preprint](https://arxiv.org/abs/2605.29269) and [TGL-APT, August 2026 preprint](https://arxiv.org/abs/2608.19750) already address surviving evidence or fragmented attack investigation. Generic aggregation or an LLM substitution is not a novelty claim. Peer review of these two preprints was not independently established.

## Reproduction

Private data root below is an example. Raw logs, matrices, row-level predictions and fitted models are not published in Git.

```powershell
python -m experiments.apt_benchmark.window_diagnostic.features --source-root C:/w/apt_benchmark_data_20260920/camlds_v1 --output C:/w/apt_benchmark_data_20260920/window_diagnostic_v1/features --protocol experiments/apt_benchmark/window_diagnostic/protocol.json
python -m experiments.apt_benchmark.window_diagnostic.run --cache C:/w/apt_benchmark_data_20260920/window_diagnostic_v1/features --protocol experiments/apt_benchmark/window_diagnostic/protocol.json --output C:/w/apt_benchmark_data_20260920/window_diagnostic_v1/run1
```

Outputs are immutable; use a fresh destination for an explicit rerun. The feature manifest binds source, protocol, adapter and artifact hashes. The runner writes a pre-fit receipt and records disjoint training families, ordered train/test window hashes and saved-model hashes. An independent code audit must verify calculations before result publication; it is not a human label audit.
