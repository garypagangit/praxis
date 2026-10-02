# PX-099: what can currently be scored

The independent PX-098 input audit traced all 208,094 existing UNRAVELED test rows back to their raw source files. File hashes, source/destination identity, flow completion time and native-to-coarse stage mapping passed.

| Native author label | Test flows |
|---|---:|
| Benign | 192,193 |
| Establish Foothold | 12,066 |
| Data Exfiltration | 3,442 |
| Cover up | 358 |
| Lateral Movement | 35 |
| Reconnaissance | 0 |

These are source annotations, not independently verified attacker intentions. A successful reconstruction here could support the five observed labels, but could not establish complete kill-chain reconstruction. Movement has very little support. Accuracy alone would be misleading because benign traffic dominates.

The first two smoke-test pages each display the eight hosts with the most flows and the first 144 five-minute bins. They are 12-hour capture slices, not whole campaigns. The first capture has 873 hosts and 579 bins; the second has 720 hosts and 363 bins. Full coverage requires more pages and a frozen pagination rule before efficacy evaluation.

Next scientific gate: reconstruct per-host native stage sets from verified source rows, preserve simultaneous labels, then freeze interval and transition scoring plus matched-text and persistence baselines. Until that is done, valid model JSON establishes only that the inference pipeline works.

Evidence: [input audit](../vlm_gate_20261002/INPUT_AUDIT.json), [protocol](PROTOCOL.md).
