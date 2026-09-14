# PX-068 technical incident 03 — frozen schema appendix is not estimable

## Event

After independent complete-evidence review and explicit `PX068_ANALYSIS_APPROVED_V3`, the frozen deferred analyzer was invoked once with the exact v3 manifest, primary truth and assignments, both model-family primary prediction files, all three sensitivity artifacts, and 20,000 bootstrap replicates.

All ten guarded analyzer/freeze/truth/assignment/prediction SHA-256 checks passed before execution. After 525.8 seconds, the analyzer stopped while entering the descriptive schema-sensitivity appendix:

```text
ValueError: Invalid truth label for athena_ckt_1384
```

The failure occurred in `schema_sensitivity_appendix()` when it called the shared `policy_rows()` routine. No analysis output directory or result file was created. Primary calculations had occurred only in process memory; no primary outcome or gate result was printed, written, selected, or inspected.

## Root cause

The frozen prospective protocol explicitly records source ID 1384 as the one AthenaBench record whose canonical and updated answer values are both malformed. It was prospectively excluded from every 2,997-row primary metric before router fitting or model inference, but retained among the three exposed records for a descriptive sensitivity appendix.

The frozen analyzer nevertheless applies the primary A–E scoring precondition to all three appendix rows. Because source 1384 has no valid A–E truth label, a three-row accuracy comparison is mathematically undefined as frozen. This is a protocol/analyzer interface defect, not a model-inference failure and not a failed confirmatory gate.

## Preservation actions

- No row was silently dropped.
- No answer was imputed or reconstructed.
- No analyzer code, parser, assignment, threshold, model output, estimand, multiplicity rule, or gate was changed.
- No alternate bootstrap count was used.
- No second analysis was started without a separately recorded recovery authorization.
- All sealed prediction hashes remain those listed in `PX068_DOWNLOADED_ARTIFACT_HASHES_V3_20260801.sha256`.

## Scientifically conservative recovery proposed

Run the same frozen analyzer on the unchanged 2,997-row primary corpus only, using its already-frozen required arguments and 20,000 replicates. Preserve and report the full confirmatory gate family. Mark the three-row descriptive appendix `NOT_ESTIMABLE_AS_FROZEN`; do not replace it with a two-row post-hoc subset and do not fabricate a label for source 1384.

This recovery requires an explicit `PX068_PRIMARY_ONLY_RECOVERY_APPROVED_V3` record before execution.
