# Necessary chronological cutoff support audit

This is a start-time count diagnostic on previously exposed data. No model was fitted, no cutoff selected, and no timestamp repaired.

To retain at least two fitting rows and one test row for every native class, with `fit_start < cutoff <= test_start`, a cutoff must be greater than every class's second-earliest start and no greater than every class's latest start. Thus the start-only interval is `(max(second-earliest), min(latest)]`. Empty or reversed bounds rule out every such single cutoff. Duration and duplicate constraints can only narrow support.

| Dataset | Lower, exclusive | Binding class(es) | Upper, inclusive | Binding class(es) | Start-only interval |
|---|---|---|---|---|---|
| SCVIC-APT-2021 | 2015-10-21T10:21:12 | DataExfiltration | 2015-10-21T22:56:16 | LateralMovement | Nonempty; not split qualification |
| DAPT2020 | 2019-07-19T16:38:37 | Data Exfiltration | 2019-07-17T19:24:55 | Reconnaissance | Empty; no all-class single cutoff |

## Native-class bounds

### SCVIC-APT-2021

| Native class | Rows | Second-earliest start | Latest start |
|---|---:|---|---|
| DataExfiltration | 527 | 2015-10-21T10:21:12 | 2015-10-21T23:01:02 |
| InitialCompromise | 73 | 2015-10-21T09:57:54 | 2015-10-21T22:59:00 |
| LateralMovement | 729 | 2015-10-21T10:05:56 | 2015-10-21T22:56:16 |
| NormalTraffic | 254836 | 1970-01-17T12:29:00 | 2015-10-21T23:59:00 |
| Pivoting | 2122 | 2015-10-21T10:05:51 | 2015-10-21T23:01:08 |
| Reconnaissance | 833 | 2015-10-21T10:00:22 | 2015-10-21T23:00:15 |

### DAPT2020

| Native class | Rows | Second-earliest start | Latest start |
|---|---:|---|---|
| Benign | 63712 | 2019-07-15T13:45:38 | 2019-07-19T22:29:23 |
| Data Exfiltration | 15 | 2019-07-19T16:38:37 | 2019-07-19T22:25:32 |
| Establish Foothold | 8604 | 2019-07-17T14:45:46 | 2019-07-19T18:44:55 |
| Lateral Movement | 2451 | 2019-07-18T12:47:14 | 2019-07-18T21:32:11 |
| Reconnaissance | 11909 | 2019-07-16T12:12:20 | 2019-07-17T19:24:55 |

## Interpretation limits

- SCVIC timestamps remain unqualified physical chronology, including all anomalous 1970 rows. This result concerns its recorded time field only.
- DAPT uses flow starts. A qualified completed-flow or arrival-time split is stricter and requires separate checks.
- Nonempty support does not establish independence, useful statistical power, or a deployment-valid split. Empty support is a count-level impossibility under the stated single-cutoff rule.
- Native labels, every input row and tied timestamps are preserved. There is no label dropping, clock repair, favorable-window search, resampling, or fitting.
- Additional fitting/calibration/test partitions impose further constraints. This two-side necessary condition does not certify those partitions.

Frozen algorithm commit: `ea9956c`. Detailed file hashes and exact integer bounds: [SUPPORT_CUTOFF_AUDIT.json](SUPPORT_CUTOFF_AUDIT.json).
