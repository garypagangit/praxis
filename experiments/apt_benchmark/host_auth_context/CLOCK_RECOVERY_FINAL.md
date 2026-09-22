# Final Windows clock recovery review

September 22, 2026. Read-only follow-up after the completed Linux-only experiment.

## Decision

**The available UNRAVELED Windows exports do not qualify for recovery of the complete pilot timeline.** The displayed timezone is recoverable. The underlying clock discontinuity on the principal exfiltration source is not fully recoverable from the available evidence. Keep the existing Windows exclusion and the completed Linux-only results unchanged.

This is a closed limitation of the currently inspected artifacts, not a claim that recovery would be impossible if original event files or independently timestamped collector records became available. No corrected Windows event array was created, and no additional fitting was performed.

## What this final check established

The existing [qualification](HOST_EVENT_QUALIFICATION.md) already established 147 Security-event UTC anchors and zero eligible source-endpoint matches from the main Windows host. This review added full inspection of five System/eventviewer exports, all eleven local Filebeat files, and a search of the released collection/automation tools for Windows clock configuration.

| Evidence route | Direct observation | What it establishes |
|---|---|---|
| Security time-change messages | The prior audit found 147 event-4616 UTC anchors across six exports. | Displayed local time needs seven hours added to obtain the host's recorded UTC representation. |
| System/eventviewer time-change messages | This review found 571 UTC-anchor occurrences across five exports; every inferred display offset was also seven hours. | Independently corroborates the representation in another log channel. These are not 571 independent clock experiments: channels and user/automation exports overlap. |
| Main source System log | 36,663 records, 133 UTC anchors, and 38 timestamp increases within its otherwise reverse-ordered export. | Record order exposes discontinuities; sorting by displayed timestamps would hide them. |
| Time-service messages | Synchronization and valid-time-data messages surround the principal rollback, with `time.windows.com` named. | Supports a synchronization event at that point; does not supply a trustworthy timestamp for every earlier Security record. |
| Local Filebeat files | Eleven Linux-named files totaling 72,359,506 bytes. Full-text checks found zero `@timestamp`, `winlog`, `event.created`, `event.ingested`, or Windows Security-provider markers. No file is a Windows-host stream. | No matching Windows collector stream or independently timestamped receipt record was established. Marker absence is a bounded artifact observation, not a claim about unreleased raw data. |
| Released tooling | The clock-related configuration found is the Linux `ntp.j2` template and Linux NTP playbooks; no usable Windows clock-correction manifest was found. | A generic synchronization configuration does not reconstruct the Windows host's actual clock history. |

Microsoft defines the Security event's `New Time` as UTC. This supports decoding the field, not assuming the host clock was always correct. [Microsoft event 4616 documentation](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4616).

## The unresolved seven-hour discontinuity

For laboratory host **10.1.3.17**, both Security exports and its System export contain this change:

- Recorded previous time: **2021-07-03 03:39:10.5404615 UTC**.
- Recorded new time: **2021-07-02 20:39:09.3253744 UTC**.
- Change: **−25,201.215087 seconds**, approximately seven hours backward.
- The System message attributes the change to an application or system component.

In reverse export order, the relevant nearby System records are:

| Zero-based parsed record position | Event | Display time converted to recorded UTC |
|---:|---|---|
| 3311 | Time-Service 35; synchronization statement | July 2, 20:39:09 |
| 3312 | Kernel-General 1; the large backward correction | July 2, 20:39:09 |
| 3314 | Time-Service 37; valid-time-data statement | July 3, 03:38:56 |

This is evidence that the correction happened, not merely a timezone-display issue. The later synchronization statement and the earlier, seven-hours-ahead timestamp cannot both be treated as already aligned observations by applying a single display offset.

No corresponding forward seven-hour change marker identifies exactly when the preceding affected segment began. Earlier small corrections and synchronization messages are present, but they do not independently timestamp every intervening Security record. The inspected exports also contain no `EventRecordID`/`Event Record ID` markers that would provide a durable cross-export record sequence. Thus neither subtracting seven hours from an arbitrary earlier span nor masking only a small interval around the rollback establishes correct cross-stream ordering.

The principal host's System log has other historical backward corrections, including another approximately seven-hour change on June 15. Several older exact clock-change timestamps also occur in other hosts' exports, consistent with shared historical system provenance; those occurrences must not be treated as independent confirmations of the pilot's network time.

## Why another simple workaround is insufficient

1. **Timezone conversion alone:** adding seven hours corrects how the export displays time; it does not repair a host clock that was itself wrong.
2. **A seven-hour subtraction before the correction:** the beginning and duration of the affected segment are unqualified. Applying this to the whole preceding stream could move correctly timed events into the wrong history window.
3. **A small exclusion window around the correction:** events before that window may still have incorrect clocks. This does not solve the earlier-history problem.
4. **Using the apparent post-synchronization tail:** that is evidence for a narrower segment, not a repair of fitting, calibration, and the entire evaluation period. It would require a separately defined experiment and explicit residual timing uncertainty. This review does not approve that segment for a new model run.
5. **Optimizing an offset against stage scores:** this would use outcomes to manufacture the join and was not performed.

The previous label-blind peer-address/nonzero-port check also remains unsuccessful: no usable matching endpoint was available from the relevant 4624/4625 records. No alternative independent Windows-to-network transaction match was established in this bounded review.

## Consequence for the research claim

The existing Linux audit context remains a limited recorded-time experiment. All 3,442 exfiltration test flows originate from the excluded Windows host, so those results cannot show that earlier Windows authentication improves exfiltration detection. The limitation must stay next to any broader host-context claim.

For the intended movement-versus-exfiltration test, the concrete next evidence source is a separately collected, synchronized execution with an independent receiver clock and verified action outcomes. That is a new experiment, not a retroactive fix or a positive result supplied by this review.

## Reproduction and evidence bindings

[clock_recovery.py](clock_recovery.py) reads existing source files and writes a fresh metadata receipt. It uses the frozen record parser without changing it. Example:

```text
python -m experiments.apt_benchmark.host_auth_context.clock_recovery --source <author-host-logs> --out <fresh-review-json>
```

Private receipt: `C:/w/apt_benchmark_data_20260920/host_auth_context_v1/CLOCK_RECOVERY_FINAL.json`.

- Receipt SHA-256: `877b6bf07c0c75d26d5a7fa531ef9953b70a526b6128e67fd1863a972941c612`.
- Review helper SHA-256: `446c55e5c9b3772603a50f7f431091f1d2362074bee41d64f70245a60aa372b5`.
- Reused frozen parser SHA-256: `9d401c3beecc7d306bf6dd271d900fd1902afe148212022405ffd8b0d7bc47c1`.
- Principal System source SHA-256: `19381d1ebbe0acf2ffa8573b4c41243204c3437b84a353c662598f458d7e6391`.

The receipt records hashes for every inspected System and Filebeat file, aggregate counts, clock-change timestamps and limited synchronization metadata. It contains no account names, passwords, commands or model outcomes. Existing protocols, prepared arrays, fitted models and published results were not modified.
