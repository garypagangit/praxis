# Offline packet provenance runtime audit

Audit date: **2026-09-20**. The UTC rerun independently verifies the selected wire fields for **4,778 of 4,784 instrumentation alerts** from two real captures. One filename mismatch and five unsupported IPv6 alerts remain unverified. This is a packet-linkage result, **not threat-detection accuracy, attack ground truth, the complete P1 evidence contract, or a suppression certificate**.

The reviewer reread the original capture bytes and both instrumentation EVE outputs, checked raw PCAPNG metadata, and reran the unchanged linkage function. No captures, EVE timestamps, packet offsets or linkage tolerances were edited. No alert was relabeled as an attack or benign event.

## Runtime and preserved attempts

The runner used the official Windows Suricata **8.0.7** binary extracted from its installer. Its missing `wpcap.dll` dependency was supplied by MSYS2 libpcap 1.10.6-3 under that filename; additional runtime libraries are individually hashed in each generation freeze. This was an offline `-r` replay with one worker and checksum checking explicitly disabled through `-k none`. No live capture driver or service was installed. This portable runtime must not be described as an unchanged standard production installation.

| Preserved attempt | Rules and scope | Measured outcome |
|---|---|---|
| [Initial rules replay](../results/tier3_provenance_20260920/RESULTS.json) | Acquired ET rules archive; security-rule feasibility only. | Both processes exited zero; each loaded 52,302 rules and failed nine `file.magic` rules. Neither capture generated an alert. |
| [Instrumentation v1](../results/tier3_instrumentation_20260920/RESULTS.json) | Two explicit TCP/UDP diagnostic rules; local timezone rendering. | 4,784 diagnostic alerts; zero full field-linkage passes. All alert timestamps were exactly two hours ahead of their referenced capture times after interpreting the emitted timezone. |
| [Instrumentation v2, UTC](../results/tier3_instrumentation_20260920_v2_utc/RESULTS.json) | Same two diagnostic rules and captures; prospectively set `TZ=UTC0` for the Suricata subprocess only. | 4,778 field-linkage passes; one filename mismatch and five unsupported IPv6 records retained. All 4,784 timestamps exactly match their referenced packet times. |

The original ET run is an incomplete security-rule reproduction. Its preserved execution logs explicitly report the unsupported `file.magic` keyword; they also warn about an unavailable threshold configuration. Zero alerts from that run do not establish that either capture was benign or that the engine detected every threat. The subsequent diagnostic events are not substitutes for ET threat detections.

The two diagnostic rule IDs are `9900001` for TCP and `9900002` for UDP. Their messages explicitly say provenance only and make no attack judgment. Both diagnostic rules loaded without failures. Their emitted severity of 3 is a property of the test rules, not evidence that the traffic is safe to suppress.

## Timestamp failure and prospective correction

Both captures contain an Ethernet PCAPNG interface block with bytes `0100000000000400` and no timestamp-resolution or timestamp-offset options. Therefore the default timestamp scale is microseconds and the interface offset is zero. An independent direct block walk confirmed those bytes separately from the linkage reader.

For `s2`, the first enhanced packet block stores **1499450880020798 microseconds**, corresponding to `2017-07-07T18:08:00.020798Z`. Instrumentation v1 emitted `2017-07-07T14:08:00.020798-0600`, which denotes `20:08Z`. The wall time agrees with Eastern daylight time, but the emitted offset does not. A separate Python `datetime.fromisoformat` calculation, independent of the linkage timestamp helper, confirmed the same **+7,200 seconds for every one of the 4,784 alerts**.

The upstream Windows formatter explains this observation: Suricata 8.0.7 calculates the offset hour using `abs(_timezone)/3600 + _daylight`, while formatting the wall clock from local time. Eastern standard offset five plus the daylight flag produces six, although the July local offset is four. This is the observed two-hour discrepancy; it is not evidence that libpcap changed the capture timestamp. [Suricata 8.0.7 source, `WinStrftime` and its caller](https://github.com/OISF/suricata/blob/suricata-8.0.7/src/util-time.c#L182-L203).

The new runner creates a child-process environment containing `TZ=UTC0` before replay. Its [generation freeze](../results/tier3_instrumentation_20260920_v2_utc/GENERATION_FREEZE.json) records that choice. This avoids the problematic local daylight-offset rendering without changing the host timezone, the packet evidence or historical output. V1 remains preserved as a failed attempt. The linkage parser and **at-most-one-microsecond** comparison were unchanged; the observed UTC differences are exactly zero, not merely inside the tolerance.

## Independent verification of UTC output

The full check requires a valid one-based `pcap_cnt`, an expected filename or path, a supported actual packet, a matching timestamp and exact wire-oriented source/destination IP, protocol and source/destination ports. Reversed directions are not silently accepted. Unsupported or pseudo packets remain unverifiable.

| Capture | Captured packets | Supported IPv4 TCP/UDP packets | Diagnostic alerts | Verified fields | Filename mismatch | Unsupported IPv6 | Alert timestamp deltas equal to zero |
|---|---:|---:|---:|---:|---:|---:|---:|
| `s2` | 5,185 | 5,154 | 4,424 | 4,423 | 1 | 0 | 4,424 |
| `fs1` | 5,000 | 4,152 | 360 | 355 | 0 | 5 | 360 |
| **Total** | **10,185** | **9,306** | **4,784** | **4,778** | **1** | **5** | **4,784** |

`s2` emitted 4,338 TCP-rule and 86 UDP-rule alerts; `fs1` emitted 161 TCP-rule and 199 UDP-rule alerts. The EVE files also contain 2,226 and 197 flow records respectively, plus one statistics record each. Flow/statistics records are not counted as alerts or linkage successes.

The first `s2` alert still reports `pcap_filename="unknown"`. Its timestamp and wire tuple match packet 1, but the required filename check fails; the audit preserves `MISMATCH`. The five `fs1` exceptions are IPv6, outside the bounded Ethernet/VLAN/IPv4 TCP/UDP parser. Their timestamps can be compared, but their complete field linkage remains `UNVERIFIABLE`. Neither category is promoted to a pass.

### Pinned artifacts

| Artifact | SHA-256 |
|---|---|
| `s2` capture | `a540ea3c71406e881051706cde8433a9f7c38dfce58c591a64037b10934b86c1` |
| `fs1` capture | `ce7e03921cf52174d874251a279c96c20db7e6155e3636b04a11bf14cf295658` |
| UTC `s2/eve.json` | `6b7871c618b5eb4187dae71ce9993bb1064fee7742a8b79c309697f6d684c96c` |
| UTC `fs1/eve.json` | `d84379b185629c577c0ec22d7d4e5fbdc762042b3e7e3f3f74e185bf2a07b086` |
| Unchanged `tier3_linkage.py` | `bd4c516595873ab3d81b439665a01783cdc813e183a1d5adb93e17451fcf71d7` |
| Diagnostic rules | `531c4f52b40f6ceece88f700173620799115f3b8b91181db46006875c66b6c9d` |

Raw captures remain under `C:/w/cert_gate_data_20260920/tier3_compact/pcaps/`; UTC EVE files remain under `C:/w/cert_gate_data_20260920/tier3_instrumentation_v2_utc/`. The original ET and local-time instrumentation outputs are retained in their separate private directories. Public receipts record the corresponding hashes and commands.

## What remains unproved

This check establishes agreement between generated diagnostic alerts and selected packet fields. It does not authenticate a user identity or hostname, establish an independently trusted rule/host/user/time record for the original P1 contract, supply complete incident state at decision time, or establish benignness. Faithfully captured attacker-controlled content can still contain malicious instructions.

The two selected captures are not hundreds of independent attack incidents. Existing scenario-level labels must not be propagated to every packet or newly generated Suricata alert. There is no validated attack-alert calibration set here, no measured suppression benefit, and no population-risk or prompt-injection guarantee. A full security-rule reproduction and separately justified alert labels would be new work, with the original rule-loading limitations resolved and an appropriate sampling contract defined first.
