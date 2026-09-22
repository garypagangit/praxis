# Can earlier host logs improve the movement-versus-exfiltration experiment?

**Bounded local inspection, September 22, 2026. No model fitting.**

**Yes: there is a concrete source-side authentication-context experiment to qualify next.** The local UNRAVELED copy contains Linux authentication/audit records and Windows Security events for the two important source hosts. However, host logs for the private-service destination are absent from this local collection, and process/archive/file-read evidence has not yet been established. The next step is a small time-and-event join audit, followed by a frozen feature comparison if that audit succeeds.

This would remain a previously exposed, single-campaign development study. It would not supply a new independent campaign, confirmed successful data theft, or proof that generic host context is novel.

## 1. Inventory: actual local files

The inspected directory is the existing author checkout's `data/host-logs/`. File counts and sizes are filesystem metadata, not parsed event totals.

| Log family | Files | Bytes | Directly inspected format |
|---|---:|---:|---|
| Linux audit | 8 | 79,634,951 | `LogEvent, Activity, Stage, DefenderResponse, Signature`; audit event text embedded in `LogEvent` |
| Linux auth | 8 | 11,461,434 | Same five-column author wrapper; authentication/session messages in `LogEvent` |
| Filebeat | 11 | 72,359,506 | Same author wrapper in sampled files |
| Syslog | 9 | 219,010,283 | Same author wrapper in sampled files |
| Windows | 23 | 329,868,307 | Sampled files begin with `Level, Date and Time, Source, Event ID, Task Category`; multiline event content and annotations require their own parser qualification |
| **Total** | **59** | **712,334,481** | Approximately 712 MB; no full host-log scan performed |

The Linux audit/auth inventory covers eight hosts in the corporate subnets. The Windows inventory covers three hosts, including **10.1.3.17**. Its seven files include user/automation Security, Application and Administrative views plus a System view. **No local host-log filename corresponds to a 10.1.5.* private-service host.** The author [network and host-log description](https://gitlab.com/asu22/unraveled/-/blob/d2ea90055d82fa448ab20588a13e3ec8bfd74816/README.md) also distinguishes network capture from host-log availability. Do not assume a flow destination has endpoint telemetry merely because its traffic was observed.

## 2. Exact endpoint relevance to the current pilot

A read-only pass over the **11 already qualified pilot flow files** counted endpoint pairs using the stable observable prefix and rightmost stage annotations specified in [PILOT_INPUTS.json](PILOT_INPUTS.json). No new split or predictor was chosen.

| Partition | Author stage | Source → destination | Flow rows |
|---|---|---|---:|
| Fit | Lateral Movement | 10.1.3.8 → 10.1.5.21 | 27 |
| Test | Lateral Movement | 10.1.3.8 → 10.1.5.21 | 35 |
| Fit | Data Exfiltration | 10.1.3.8 → 10.8.10.84 | 441 |
| Fit | Data Exfiltration | 10.1.3.17 → 10.8.10.84 | 1,299 |
| Calibration | Data Exfiltration | 10.1.3.17 → 10.8.10.84 | 1,331 |
| Test | Data Exfiltration | 10.1.3.17 → 10.8.10.84 | 2,341 |
| Test | Data Exfiltration | 10.1.3.17 → 10.1.5.21 | 1,101 |

The IPs above are addresses in the published laboratory dataset, retained here only to explain telemetry coverage. Literal addresses and known victim identities must not become primary predictive features.

- **10.1.3.8:** local Linux audit and auth files exist. Source-side authentication activity can potentially be linked to its flow history.
- **10.1.3.17:** Windows Security and other event files exist. Source-side logon and credential-use context can potentially be linked to its later flow history.
- **10.1.5.21:** no matching local endpoint file. Successful destination authentication, database reads and destination-side file operations are therefore not currently available from these host-log files.
- **10.8.10.84:** no matching local endpoint file. Network observations alone do not establish that a remote receiver accepted stolen data.

The pilot's lateral-associated flows are annotated **Remote System Discovery** in the qualified source inputs. Preserve that distinction: a successful-login feature could help characterize an earlier host state, but the target remains an author stage-associated flow. It is not automatically a successful remote-login outcome.

## 3. What the bounded samples actually show

The review inspected file headers and small prefixes, then at most 128,000 bytes from each end of four focused files. These are presence checks, not exhaustive coverage or event counts.

| Focused file/view | Observed signals | Timing evidence and limitation |
|---|---|---|
| 10.1.3.8 auth | Accepted authentication and session-open messages in the sampled prefix | Sampled endpoints contain June 13–16 and July 2–11 date strings. Traditional auth timestamps omit an explicit year/timezone. Gaps and June 21–July 4 completeness remain unverified. |
| 10.1.3.8 audit | `USER_AUTH`, `USER_CMD`, account/session events and explicit `res=success` records | Sampled embedded audit epochs extend from May 25–26 to July 9–11, 2021, interpreted as UTC epoch times. These endpoints do not prove uninterrupted capture. |
| 10.1.3.17 Security, user view | Event IDs 4624, 4625 and 4648; annotated content also exists in the sampled text | Prefix is July 17; tail is June 25. Export ordering is descending and exported timezone is not established. Earlier June fit coverage must not be assumed. |
| 10.1.3.17 Security, automation view | Same event IDs in the sampled ends | Similar June 25–July 17 sampled dates. User/automation exports may overlap; event identity deduplication is required. |

Microsoft documents [4624 as successful logon](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4624), [4625 as failed logon](https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/event-4625), and [4648 as an attempt using explicit credentials](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4648). **4648 alone is not proof of successful authentication.** Event 4624 records a session on the computer accessed; finding it on a flow's source host does not establish a successful outgoing login to the flow's destination. Local/interactive/service logons must also be distinguished from remote network logons before a feature is called lateral authentication.

The bounded focused samples did **not** establish Linux `SYSCALL`/`EXECVE`/`PATH` coverage or Windows process-creation/file-access events 4688/4663. This is absence from the sample, not evidence that the complete files lack them. No archive creation, database read, successful upload receipt, or exfiltration outcome has been qualified. Do not promise those features yet.

## 4. The most useful next task: a small host-to-flow join audit

Before additional training, produce a private event inventory for the two source hosts and the existing June 21–July 4 pilot interval:

1. **Qualify record parsing.** Windows message bodies are multiline, and the Linux wrappers may contain embedded commas. Preserve original record boundaries. Verify that annotation columns are not shifted or copied into event features. Never treat a filename ending in `labeled` as a sufficient schema specification.
2. **Normalize clocks from evidence.** Keep raw time, timezone assumption, parsed UTC and any collection time separately. Use Linux audit epochs where present. For Windows and auth exports, confirm configured timezone against author collection configuration or multiple independently matching network/session events. Do not choose a time offset because it improves stage scores.
3. **Verify capture coverage and overlap.** Count events by host/hour, missing intervals, duplicate IDs/content and parser failures. Reconcile user/automation exports. Missing coverage is unknown visibility, not a history count of zero or proof of benign behavior.
4. **Check a fixed small roster of joins.** Include examples from each available host, partition and role-pair case. Verify that authentication events involve the relevant source/destination and occurred before the flow's declared decision time. Do not use target labels to manufacture a session join or infer successful movement.
5. **Inventory process/file signals without assuming them.** Count event types first. Only add archive execution, file access or parent-process features if the actual event schema, timing and observation coverage support them. Keep destination success unavailable when the destination is unmonitored.

The first deliverable should be a join receipt and a table of observable event types, clocks, coverage and unresolved joins. This qualification is independent of whether an eventual model score increases.

## 5. Bounded feature experiment after qualification

Keep the same flow anchors, fitting labels, split, model settings and stage metrics. Compare the current-flow model with:

- **Earlier authentication context:** counts of source-host successes and failures, time since the last qualified remote authentication, distinct observed peers and availability indicators over fixed lookback windows.
- **Earlier host plus flow history:** the same authentication context combined with the already specified flow-history features.
- **A causal wrong-host control:** equivalent history from a fixed different host, using only information available by the same decision time. This checks whether meaningful correspondence matters.

Use a baseline that receives the same host-log-availability indicators, so a gain cannot be attributed merely to which source host has Windows logs. Report within-source-host and within-role-pair results. Authentication history must include observed unlabeled traffic, not only retrospectively benign or attack-labeled events. All `Activity`, `Stage`, `DefenderResponse` and `Signature` fields are forbidden predictors and history counters.

If process/file evidence later qualifies, add it in a separately frozen extension. A process invocation or local archive operation is supporting context, not successful exfiltration. Report exact-stage exfiltration precision/recall/AP, movement-associated recall, normal false alerts and changes in the two confusion directions. The small movement denominator and single attack narrative remain material limits.

## Scope and conclusion

This inspection used filesystem metadata, format headers, bounded host-log samples and existing pilot flow files. It printed no credential values or executable commands, ran no source content, fitted no models and modified no existing scientific artifacts.

**Concrete next action:** qualify and join the 10.1.3.8 Linux authentication/audit and 10.1.3.17 Windows Security streams, then test whether strictly earlier authentication history adds information beyond the current flow. That is currently more supportable than promising archive/file-read or destination-success features. It can answer a narrower version of the original question while preserving the known telemetry and label limits.
