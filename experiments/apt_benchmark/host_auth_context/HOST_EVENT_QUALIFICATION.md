# Host-event qualification and the Windows clock exclusion

September 22, 2026. This decision was made before feature preparation or fitting. The original all-platform hypothesis remains untested.

## What is usable in this run

Eight Linux audit streams supply **286,953 distinct observed records**, of which **90,008** are authentication/session context records. Explicit audit Unix epochs provide recorded UTC event times. The predictor arrays contain host join keys, times, event-kind codes and hashed record identities, with no account names, commands, raw text or author attack annotations. The primary features use only prior source-host events and exclude equal/future recorded times.

This is recorded-time replay. Epoch syntax does not independently prove host synchronization to the network sensor, and ingestion delays are unavailable. Historical counts describe observed records, not complete telemetry or confirmed successful outgoing access.

## Why Windows was excluded

All six Security exports have independent embedded UTC clock-change timestamps sufficient to establish the export display offset (+7 hours to obtain recorded UTC). There are **147** such anchors. This establishes time representation, not clock correctness. The pilot interval includes backward clock changes of approximately 25,187 seconds on 10.1.1.15 and 25,201 seconds on the important exfiltration source 10.1.3.17. A single timezone offset cannot resolve these cross-clock joins.

A label-blind check sought Security 4624/4625 peer IP plus nonzero source-port matches against the eleven qualified flow captures for 10.1.3.17. None of 7,026 candidate logons supplied a usable nonzero source endpoint; **zero matches qualified**. No offset was selected using attack labels or model scores. No unverified piecewise correction was applied.

All **84,007 deduplicated Windows records** were therefore excluded from predictors, including the apparently more stable hosts. The parsed originals and clock evidence remain private; the published [qualification receipt](HOST_EVENT_QUALIFICATION.json) retains aggregate counts, source hashes and clock anchors. Missing Windows context is not interpreted as no authentication activity.

## Consequence for the question

| Author-stage rows | Fit | Calibration | Test |
|---|---:|---:|---:|
| Movement total | 27 | 0 | 35 |
| Movement with prior source audit records | 27 | 0 | 35 |
| Exfiltration total | 1,740 | 1,331 | 3,442 |
| Exfiltration with prior source audit records | 441 | 0 | 0 |

All 35 test movement rows have Linux source 10.1.3.8. All 3,442 test exfiltration rows have Windows source 10.1.3.17. The experiment can measure a limited Linux-authentication ablation and the cost of retaining movement alerts. It **cannot establish the benefit of earlier Windows authentication for exfiltration detection**. All fitting arms receive identical observed-log volume/timing and availability controls so the extra authentication-type fields are not compared against a baseline blind to logging differences.

## Reproduction

Run `python -m experiments.apt_benchmark.host_auth_context.host_events --source <author-host-logs> --out <fresh-event-dir> --linux-only`, then follow the frozen protocol and runner. The ungated parser output deliberately has `approved_for_event_time_replay: false`; the freezer rejects it. The Linux-only receipt is approved solely for the limited recorded-time replay described above.

The next full test requires independently aligned Windows timestamps or fresh, synchronized executions containing both movement and exfiltration across the same source hosts and role assignments. Destination action and marked-file receipt logs are also needed before replacing author-stage labels with confirmed movement/theft outcomes.
