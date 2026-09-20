# GPU experiment operational closeout

Status: **ALL_ATTEMPTS_VERIFIED_STOPPED**.

| Attempt | Execution outcome | Verified stopped | Compute estimate |
|---|---|---|---|
| 1 | bounded worker timeout with partial science | Yes | $0.838406 |
| 2 | bootstrap storage failure before worker | Yes | $0.077288 |
| 3 | bootstrap free space guard before worker | Yes | $0.080216 |
| 4 | worker completed | Yes | $0.634597 |

**Estimated compute for verified closed attempts: $1.630507.**
This is elapsed-time arithmetic, not an invoice. It includes startup and stopping-observation time and excludes storage, transfer and other services. The $5 incidental allowance per attempt is a budget reserve, not measured spending.

Attempt 1 is the sole source of reusable encoder and normal-cache checkpoints. Later attempts preserve the original scientific settings and rebuild all banks, calibration, normal metrics and attack replay. Attempt 2 failed during bootstrap; a startup mount/path change remains an unconfirmed explanation. Attempt 3 was rejected before science because root storage had less than the required 10 GiB free. Earlier evidence and source freezes are retained.

The accompanying JSON binds each available execution/controller receipt, source freeze, input bundle and collected output archive by SHA-256. Stop requests alone are insufficient: closure is supported by the controller's observed stopped state, final receipt and matching elapsed-time record. Cloud account, host, storage, role and command identifiers remain private.

A timeout or bootstrap failure does not establish scientific no-go. Scientific results, completeness checks and independent result audit belong in the research report; this operational closeout does not infer detector performance.
