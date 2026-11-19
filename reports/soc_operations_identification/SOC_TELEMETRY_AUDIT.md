# SOC telemetry signal audit

## Bottom line

The original 30-second, command-free XGBoost result was promising within this
dataset, but a follow-up audit found that it depends heavily on network
traffic that may reflect the lab's infrastructure. After filtering traffic
involving two suspicious UDP ports, macro-F1 fell from 0.676 to 0.540 and AI
recall fell from 47.8% to 34.2%. This does not prove that the original model
identified infrastructure rather than operator behavior, but it makes that a
serious alternative explanation. Neither result establishes a deployable
AI detector.

These are exploratory analyses of the existing logs, not new experiments.
All use 30-second windows, five human and four AI attack sessions, and
leave-one-session-out evaluation. Existing login metadata supplies the attack
periods; terminal commands and command-line content are not model features.
The combined model uses Windows Security, Sysmon, selected additional Windows
event channels and IIS counts, plus VPC flow counts and timing features. It
does not use every available log type.

## 1. What are the important flow features?

For retained attack windows, rejected flow records averaged 21.0 per human
window and 37.9 per AI window. Non-TCP/UDP records averaged 7.9 and 9.9,
respectively. All four AI sessions had a higher *session-average* rejected
count than all five human sessions. With only nine sessions this is an
observed association, not evidence that AI operators cause rejected flows.
Counts below are **flow records**, not distinct connections or packets.

| Retained attack-window records | Human | AI |
|---|---:|---:|
| Rejected records | 19,521 | 11,165 |
| Rejected UDP, included above | 12,918 | 8,414 |
| Rejected ICMP, included above | 6,411 | 2,664 |
| Non-TCP/UDP records | 7,349 | 2,910 |
| ICMP, included in non-TCP/UDP | 7,341 | 2,909 |
| Rejected UDP with source port 41641 | 12,700 | 8,302 |
| Rejected UDP from port 41641 to port 3478 | 10,712 | 4,415 |

These categories overlap: rejected UDP and rejected ICMP are components of
rejected records, and many ICMP records are also rejected. They are not
independent indicators.

[Tailscale's firewall documentation](https://tailscale.com/docs/reference/faq/firewall-ports)
identifies UDP 41641 as its default WireGuard port and UDP 3478 as a STUN
port. The pattern is **consistent with**, but does not prove, Tailscale-related
infrastructure traffic: ports alone do not identify a process. A local
correlation using exact UDP endpoints and flow-time ranges found no selected
Sysmon Event ID 3 records or matches on the four included hosts. This is
inconclusive: collection gaps, NAT, other hosts, timing or logging settings
could prevent a match.

Similar port-pattern traffic also occurred in available windows outside the
included login periods. Average rejected flow records per 30-second window:

| Period | Human windows / sessions | Human average | AI windows / sessions | AI average |
|---|---:|---:|---:|---:|
| Up to five minutes before first included login | 36 / 4 | 10.14 | 35 / 4 | 5.89 |
| Included attack windows | 930 / 5 | 20.99 | 295 / 4 | 37.85 |
| Up to five minutes after last included login | 35 / 5 | 12.97 | 23 / 4 | 18.87 |

These pooled averages weight sessions by available windows. Coverage and
sample sizes vary, and outside-login windows are not known to be benign or
free from other activity. Flow records are assigned by their end time, not
necessarily when the underlying traffic happened.

## 2. Remove important feature columns

Fixed XGBoost was retrained separately for each variant on the same 1,225
windows. The paired interval is a 95% session bootstrap of the *difference*
in macro-F1 using fixed held-out predictions.

| Features | Macro-F1 | Change vs baseline | Paired interval | AI recall | Human attack-window FPR | Session accuracy |
|---|---:|---:|---:|---:|---:|---:|
| Combined baseline | 0.676 | — | — | 47.8% | 13.7% | 8/9 |
| Remove rejected count | 0.620 | -0.056 | -0.218 to +0.087 | 42.0% | 18.1% | 7/9 |
| Remove non-TCP/UDP count | 0.631 | -0.045 | -0.091 to -0.006 | 42.0% | 16.3% | 7/9 |
| Remove both | 0.607 | -0.069 | -0.226 to +0.075 | 40.0% | 18.7% | 7/9 |

The model's score fell, but these intervals do not account for refitting or
model selection, and most span zero. Removing these columns does not remove
all related information: non-TCP/UDP count can be reconstructed from total,
TCP and UDP counts.

## 3. Filter the suspicious port traffic

As a stronger sensitivity check, all UDP flow records with **either** source
or destination port 41641 or 3478 were removed before recomputing every flow
count, packet/byte total and five-second flow bin. Before filtering, all
recomputed flow features and bins matched the previous extraction in all
1,225 windows. The filter removed 12,701 of 344,862 human and 8,302 of 93,927
AI flow records; respectively 12,700 and 8,302 of those were rejected.

| Fixed XGBoost | Macro-F1 | AI recall | Human attack-window FPR | Session accuracy |
|---|---:|---:|---:|---:|
| Combined baseline | 0.676 | 47.8% | 13.7% | 8/9 |
| UDP port-filtered | 0.540 | 34.2% | 25.6% | 6/9 |

The paired fixed-prediction session-bootstrap interval for the macro-F1
change was -0.341 to +0.054. The filter was selected after inspecting the
data, can remove unrelated traffic, and leaves other infrastructure signals
in flow and host features. It does not isolate a particular application or
prove that the remaining signal is operator behavior.

## 4. Coverage and host-only telemetry

Of 1,900 candidate attack windows, 1,225 had the original common coverage.
Network `SKIPDATA` affected 673 candidates: 476 of 1,408 human windows
(33.8%) and 197 of 492 AI windows (40.0%). Three candidates fell outside
required host timestamp extents; these exclusion reasons can overlap.
First-to-last event timestamps are only a coarse coverage proxy, not proof of
continuous logging. Differences in log availability, host configuration,
network topology and session duration may be associated with class labels.

Heuristic, session-specific Sysmon address mapping could assign the source of
12,844 human rejected records to one included host, but 11,149 of 11,165 AI
rejected sources remained unmapped. This is evidence of unequal *mapping
coverage*, not a reliable comparison of actual host origins: NAT, missing
events and reused addresses can all affect it.

We also retrained without *any* flow features and without requiring flow
coverage. Host features contain Security, Sysmon, selected additional Windows
events, IIS counts and host-channel timing; no command content is used.

| Fixed XGBoost | Windows, human / AI | Macro-F1 | AI recall | Human attack-window FPR | Session accuracy |
|---|---:|---:|---:|---:|---:|
| Combined baseline, matched | 930 / 295 | 0.676 | 47.8% | 13.7% | 8/9 |
| Host-only, matched | 930 / 295 | 0.514 | 28.5% | 25.5% | 6/9 |
| Host-only, all host-covered | 1,405 / 492 | 0.527 | 32.7% | 27.1% | 5/9 |

For the matched comparison, the host-only minus combined macro-F1 interval was
-0.396 to +0.059, using the same fixed-prediction session bootstrap. The
larger host-only dataset is **not** a matched comparison with the combined
model. Additional event channels may have incomplete coverage even inside
their first-to-last timestamps.

## Interpretation and limitations

The most defensible conclusion is that this dataset contains a measurable
label-associated signal, but much of the original score appears sensitive to
network-flow information that may be tied to the environment. The host-only
and port-filtered scores are substantially weaker. The audit cannot determine
whether any remaining signal generalizes to a different network, identifies
autonomous behavior, or is safe to use for SOC alerting.

Each model was refit for all 126 possible four-AI/five-human session-label
assignments. The port-filtered model's raw, unadjusted association p-value
was 0.1270; the two host-only models' Holm-adjusted values were 0.2222 within
that two-model family. The four column-ablation association p-values were
Holm-adjusted within that family only. These tests are not tests of score
improvement and do not correct for all prior exploration. They assume
exchangeable sessions, which lab or operator differences may violate. Fixed
prediction bootstrap intervals also omit model-refitting and selection
uncertainty.

Human false-positive rates here refer to **human attack windows**, not normal
business traffic. The analysis does not measure benign-traffic alert rates,
unknown attack-period discovery, real-time latency, calibration, or
independent-environment performance. For reproduction and privacy guidance,
see the [audit runbook](../../scripts/DEFENDER_SOC_AUDIT.md).
