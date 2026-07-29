# PX-063 Protocol 1.4 Preflight Defect Record

**Recorded:** 2026-07-26

**Disposition:** Protocol 1.4 invalidated before scientific inference; restart as Protocol 1.5

## What happened

Protocol 1.4 completed its sanitized source-integrity and synthetic fixture
gates. The subsequent preflight-only command stopped because
`source_expectations_schema_exact` was false. Gate 1 correctly recorded 14
source-expectation keys, including `pinned_parquet_sha256`; the deterministic
authenticator's frozen key set listed only 13 and omitted that key.

All other preflight checks were true. This was a metadata-authentication defect,
not a failed source-integrity result and not a verifier result.

## Scientific exposure

The failed preflight read only committed sanitized source and fixture artifacts
and replayed the inert synthetic fixture bank. It did not load TRACE rows, read
trajectory text, compute any TRACE decision, reserve a scientific output
directory, join gold labels to decisions, or write metrics or a determination.

## Corrective action

Protocol 1.5:

- adds `pinned_parquet_sha256` to the exact source-expectation schema;
- versions active source, fixture, decision-seal, report, and output paths to
  1.5;
- reruns Gates 0–3 from a clean pushed commit; and
- retains the Protocol 1.4 sanitized artifacts only as an auditable historical
  attempt.

No rule, parser behavior, fixture expectation, hypothesis, threshold, or
analysis formula changed in response to the failed preflight.
