# Cadets Concept Drift Gate

Generated: 2026-05-10

## Decision

Gate result: `PIPELINE READY - DRIFT DATA INSUFFICIENT`

The Cadets parser and chronological windowing work, but this local sample spans only a short interval and should not be treated as a real concept-drift benchmark.

## Corpus

| Metric | Value |
|---|---:|
| Edge rows | 98862 |
| Source files | 1 |
| Timestamp span seconds | 245.329 |
| Event types | 29 |
| Exec values | 33 |

## Drift Metrics

| Metric | Value |
|---|---:|
| Adjacent event JS max | 0.5037 |
| Adjacent exec JS max | 0.7591 |
| First-last event JS | 0.2209 |
| First-last exec JS | 0.6138 |

## Chronological Windows

| Window | Rows | Span seconds | Top events | Top execs |
|---:|---:|---:|---|---|
| 0 | 19773 | 61.760 | EVENT_READ:5654, EVENT_WRITE:5067, EVENT_CLOSE:1908, EVENT_OPEN:1693, EVENT_MMAP:1276 | dlogd:5867, sshd:4905, sysctl:3141, bash:1640, syslogd:677 |
| 1 | 19772 | 76.500 | EVENT_READ:7047, EVENT_WRITE:6280, EVENT_MMAP:1087, EVENT_CLOSE:1015, EVENT_OPEN:864 | dlogd:7250, sysctl:4431, sudo:1852, sshd:1786, scp:898 |
| 2 | 19772 | 84.790 | EVENT_READ:8632, EVENT_WRITE:2942, EVENT_CLOSE:1549, EVENT_OPEN:1421, EVENT_MMAP:1093 | dlogd:8034, sshd:3453, ssh:2014, scp:1303, bash:1244 |
| 3 | 19772 | 10.860 | EVENT_MODIFY_PROCESS:6043, EVENT_CLOSE:6037, EVENT_OPEN:6035, EVENT_READ:934, EVENT_WRITE:272 | du:18138, dlogd:1259, UNKNOWN:268, syslogd:62, tmux:31 |
| 4 | 19773 | 11.419 | EVENT_CLOSE:4449, EVENT_OPEN:4397, EVENT_MODIFY_PROCESS:4169, EVENT_WRITE:3092, EVENT_READ:2486 | du:12449, dlogd:3232, dmesg:2502, sshd:829, UNKNOWN:276 |

## Next Logical Step

Use this only as a parser/windowing smoke test. A publishable provenance concept-drift experiment needs longer chronological host streams, attack labels or anomaly windows, and at least one detector family. This sample is too short to support a drift claim by itself.
