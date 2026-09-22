# UNRAVELED host-role and earlier-activity data inventory

## Decision

A **bounded, single-sensor, chronological development test is feasible now**. It can compare flow statistics alone with static host-zone roles and strictly earlier observable traffic. It cannot establish independent reliability, unseen-host generalization, verified adversary progression, or early warning. All 173 source files were already exposed in the original GML work; the source describes one emulated APT campaign alongside other attacks.

Use the 11 complete `net1013x` capture files listed in [PILOT_INPUTS.json](PILOT_INPUTS.json). This IT-subnet sensor avoids mixing gateway and subnet views. The fixed capture assignment gives the following counts **before target-class filtering, benign subsampling, or fitting**:

| Split | All flows | Benign | Lateral movement | Exfiltration | Foothold | Cover-up |
|---|---:|---:|---:|---:|---:|---:|
| fit | 161,216 | 147,087 | 27 | 1,740 | 12,362 | 0 |
| calibration | 12,919 | 8,929 | 0 | 1,331 | 2,659 | 0 |
| test | 208,094 | 192,193 | 35 | 3,442 | 12,066 | 358 |

Calibration contains **zero movement examples**. It can inform a benign false-alarm operating point, but cannot tune or certify movement recall. Movement performance must be reported with its small test denominator of 35 flows. Multiple training seeds are repeated fits of this same campaign, not independent incidents.

## Source, provenance, and parsing correction

Author source: [UNRAVELED repository](https://gitlab.com/asu22/unraveled), pinned commit `d2ea90055d82fa448ab20588a13e3ec8bfd74816`. The author metadata links the GNU GPL v3 license. Citation: Myneni, S., Jha, K., Sabur, A., Agrawal, G., Deng, Y., Chowdhary, A., & Huang, D. (2023). *Unraveled?A semi-synthetic dataset for Advanced Persistent Threats*. *Computer Networks, 227*, 109688. [Paper DOI](https://doi.org/10.1016/j.comnet.2023.109688).

Private original path: `C:/Users/garyp/OneDrive/Documents/codex/imports/unraveled/data/network-flows`. This audit checked **173 CSV files, 31 capture directories, 6,877,157 rows, and 3,723,532,930 bytes**. All current file SHA-256 values, row counts, and the initial positional-label counts match the earlier pinned-author-source audit. The [JSON inventory](DATA_INVENTORY.json) records each hash, timestamp extent, and corrected stage count. The older 203 MB `benchmark_cache.csv` benign-subsampled the raw stream; it should not supply the history or false-alarm denominator for this experiment.

**A consequential CSV-format defect was found before fitting.** The 89-column files contain unquoted commas in descriptive DPI fields: 6,863,988 rows have 89 fields; 11,676 have 90; 1,481 have 104; 4 have 102; 6 have 99; and 2 have 107. Fixed-position `pandas` label extraction therefore reported spurious stages such as `Normal`, `6`, and `26`. They are not extra attack classes.

Reading the four rightmost fields as the author's `Activity`, `Stage`, `DefenderResponse`, and `Signature` resolves the stage of every raw row without inventing labels. It yields **6,779,914 benign, 34,796 reconnaissance, 27,118 foothold, 27,445 lateral-movement, 7,522 exfiltration, and 362 cover-up flows**. The 13,169 overflow rows account for 13,167 additional benign rows and two reconnaissance rows. Seven foothold rows have the literal missing signature `nan`; they do not affect this IT pilot.

For all 11 pilot files, the numeric and identity prefix at header positions 0?76 is intact, with zero invalid or nonfinite numeric values; the final four annotations are valid. Discard the ambiguous DPI region, positions 77?84, rather than trying to reconstruct its text fields. There are zero unresolved pilot labels and zero within-file exact duplicates of the observable prefix after excluding source record ID and expiration reason. This narrow duplicate check does not rule out repeated behavior or near-duplicate feature vectors. Numeric-prefix validation outside the selected pilot was not required and was not performed.

The inventory retains the previous positional counts as explicitly marked parsing diagnostics. Scientific preparation must use `right_anchored_stage_counts`, not those diagnostics. The raw source and all earlier frozen studies remain unchanged.

## Capture and sensor boundaries

?Complete capture? means all locally present, author-released CSV files for the stated directory; it does **not** mean complete visibility of all network or host activity. Some directories contain fewer than six sensor views, and some span multiple days. Directory names do not reliably denote their actual date range.

Across all 31 directories, first-packet to last-packet intervals have no overlapping connected components. All 6,877,157 rows have positive finite first/last timestamps, last time at least first time, and bidirectional duration equal to last minus first. CSV order is not chronological: 1,658,816 successive-row first-time decreases were found. Sort by timestamps; never treat file order as causality.

The author explicitly states that Internet-bound traffic can appear in both a subnet sensor and the gateway, and that intra-subnet traffic is unobserved at these gateway interfaces. The strong stage-by-sensor association makes an indiscriminate pooled experiment misleading:

| Sensor | Corrected benign | Lateral movement | Exfiltration |
|---|---:|---:|---:|
| net1011x | 1,792,756 | 0 | 0 |
| net1012x | 734,331 | 0 | 0 |
| net1013x | 1,038,246 | 164 | 6,513 |
| net1014x | 207,423 | 0 | 0 |
| net1015x | 174,506 | 153 | 1,003 |
| netgw | 2,832,652 | 27,128 | 6 |

Keep sensor and capture IDs out of predictors. A single IT sensor also avoids unresolved cross-sensor duplicate linkage; it does not remove repeated host identities or campaign-specific traffic patterns.

## What the roles and labels mean

The author's static topology supports **zone roles**, not a verified role for every individual user or machine: HR/executive (`10.1.1.0/24`), marketing (`10.1.2.0/24`), IT (`10.1.3.0/24`), public services (`10.1.4.0/24`), and private services (`10.1.5.0/24`). Treat unmatched addresses as `OTHER_ADDRESS`, not automatically as the public Internet. The topology names classes of private services but does not establish a complete per-address asset inventory. Do not derive ?privileged user,? ?compromised host,? or attacker roles from the attack narrative.

On the IT sensor, all **164 movement flows come from one directed host pair**, and all have author Activity `Remote System Discovery`. There are 6,513 exfiltration flows across three directed host pairs: 5,412 IT?OTHER_ADDRESS and 1,101 IT?PRIVATE_SERVICES. Thus the shared IT?PRIVATE_SERVICES stratum contains both labels, along with benign traffic, but is small and temporally uneven. **Its exfiltration examples occur only in the July test captures**, never in this pilot's fitting or calibration files. Report it as a held-out destination-role context. It is not a balanced role-matched training subset.

The selected shared-role stratum has these exact corrected counts:

| IT→PRIVATE_SERVICES subset | Benign | Movement | Exfiltration |
|---|---:|---:|---:|
| Fitting captures | 1,172 | 27 | 0 |
| Calibration capture | 136 | 0 | 0 |
| Test captures | 1,576 | 35 | 1,101 |

The source's stage names are author annotations. Exfiltration includes `Data Transfer Size Limits` (6,988 flows), `Exfiltration over C2 channel` (446), and `Unsecured Credentials` (88). Movement includes `Maintain Access` (27,128 gateway flows) and `Remote System Discovery` (317 subnet flows). These semantic differences must be disclosed: predicting the author label does not independently prove actual host movement or data theft. No newly verified flow-level attack-ground-truth reconstruction was found in the inspected source tools.

All four annotation columns are prohibited as model inputs or history features. In particular, `DefenderResponse=Benign` is not a benign traffic label: all exfiltration and movement rows have that response. `Signature=APT` is also prohibited as a predictor. Absolute addresses, MACs, serial record IDs, capture names, and absolute dates should serve only as bookkeeping/history keys where necessary, not direct class predictors.

## Exact bounded pilot files and time support

Intervals below are UTC conversions of packet timestamps, rounded to seconds for display; JSON retains millisecond bounds. Their calendar boundaries differ from the directory names. The final test file reaches **July 6**, not July 4.

| Split | Capture | First packet UTC | Last packet UTC | Benign | Movement | Exfiltration |
|---|---|---|---|---:|---:|---:|
| fit | Week5_Day1_06212021 | 2021-06-21 07:08:58 | 2021-06-22 07:29:02 | 45,655 | 9 | 441 |
| fit | Week5_Day2_06222021 | 2021-06-22 07:32:11 | 2021-06-23 07:33:46 | 36,356 | 4 | 0 |
| fit | Week5_Day3_06232021 | 2021-06-23 07:35:22 | 2021-06-24 07:00:46 | 18,266 | 5 | 0 |
| fit | Week5_Day4_06242021 | 2021-06-24 07:05:02 | 2021-06-25 07:21:30 | 6,948 | 0 | 0 |
| fit | Week5_Day5-6_06252021-06262021 | 2021-06-25 07:23:40 | 2021-06-26 21:31:57 | 39,862 | 9 | 1,299 |
| calibration | Week5_Day6_06272021 | 2021-06-27 08:53:23 | 2021-06-28 07:03:17 | 8,929 | 0 | 1,331 |
| test | Week6_Day2_06292021 | 2021-06-28 07:06:17 | 2021-06-30 07:18:42 | 62,400 | 18 | 2,253 |
| test | Week6_Day3_06302021 | 2021-06-30 07:20:05 | 2021-07-01 13:33:38 | 48,951 | 0 | 9 |
| test | Week6_Day4_07012021 | 2021-07-01 13:56:16 | 2021-07-02 07:52:06 | 35,261 | 11 | 228 |
| test | Week6_Day5_07022021_part2 | 2021-07-02 19:51:53 | 2021-07-03 12:37:12 | 25,120 | 6 | 258 |
| test | Week6_Day6-7_07032021-07042021 | 2021-07-03 20:51:47 | 2021-07-06 06:42:02 | 20,461 | 0 | 694 |

For transparency, the same selected files grouped by the UTC calendar date of the first packet give:

| UTC date | Benign | Movement | Exfiltration |
|---|---:|---:|---:|
| 2021-06-21 | 40,366 | 9 | 24 |
| 2021-06-22 | 37,568 | 4 | 417 |
| 2021-06-23 | 20,529 | 5 | 0 |
| 2021-06-24 | 6,663 | 0 | 0 |
| 2021-06-25 | 34,542 | 9 | 6 |
| 2021-06-26 | 7,419 | 0 | 1,293 |
| 2021-06-27 | 5,970 | 0 | 907 |
| 2021-06-28 | 8,637 | 0 | 1,439 |
| 2021-06-29 | 47,111 | 17 | 1,238 |
| 2021-06-30 | 47,251 | 1 | 3 |
| 2021-07-01 | 41,768 | 11 | 21 |
| 2021-07-02 | 18,951 | 5 | 316 |
| 2021-07-03 | 12,499 | 1 | 193 |
| 2021-07-04 | 8,651 | 0 | 288 |
| 2021-07-05 | 8,067 | 0 | 288 |
| 2021-07-06 | 2,217 | 0 | 80 |

This daily table is descriptive. Assignment remains by the 11 whole capture files, so no rows from one capture are randomly divided between fitting and evaluation.

## Requirements before the mechanism comparison

1. Freeze the parser, exact file hashes, complete-capture assignment, target-class policy, and feature definitions before model outcomes. Other stages may be excluded from a declared three-class target, but their unlabeled observable traffic should remain in the causal history stream if the protocol says the sensor observes it.
2. Build history from the full retained sensor stream **before** benign sampling. Use static topology roles and observable packet/flow quantities, never prior ground-truth stages or test labels. Fit any learned normalization only on fitting data.
3. Define availability explicitly. Whole-flow statistics are post-completion observations. A conservative earlier-history rule uses only flows whose last packet precedes the current flow's first packet; current-flow values enter history after scoring. Process equal-time ties together. History reset/continuation at split and capture boundaries must be declared. Last packet is not a verified log ingestion/export time, so this is not a measured early-warning or delayed-log experiment.
4. Compare matched flow-only, role-only, and history-augmented variants under the same split and fitting budget. Report the shared IT?PRIVATE_SERVICES stratum separately. This distinguishes a broad role shortcut from added temporal context as far as this small campaign permits.
5. Publish per-class confusion counts, movement and exfiltration recall/precision, and benign false alarms with denominators. Disclose the zero-movement calibration set, 35 movement test rows, shared-host repetition, new destination-role context, and prior exposure. Avoid confidence claims based on treating thousands of repeated flows or three seeds as independent attacks.

**Go:** implement this bounded mechanism-development test. **No-go:** call it independent APT confirmation, generalization to unseen attackers, an actor-attribution system, verified stage progression, or operational early warning. A subsequent confirmation dataset needs independently generated campaigns, documented roles, causal telemetry, and adequate movement/exfiltration support in each prespecified split.

## Full source capture inventory

Corrected author stage labels, before filtering or deduplication; counts include multiple sensor views and are not independent attack counts.

| Author capture directory | Files | Benign | Reconnaissance | Foothold | Movement | Exfiltration | Cover-up |
|---|---:|---:|---:|---:|---:|---:|---:|
| Week1_Day1-2_05262021-05272021 | 5 | 238,174 | 0 | 0 | 28 | 0 | 0 |
| Week1_Day3_05282021 | 5 | 138,302 | 0 | 0 | 0 | 0 | 0 |
| Week1_Day4_05292021 | 5 | 55,324 | 0 | 0 | 0 | 0 | 0 |
| Week1_Day5_05302021 | 5 | 48,807 | 0 | 0 | 0 | 0 | 0 |
| Week2_Day1_05312021 | 5 | 146,791 | 0 | 0 | 0 | 0 | 0 |
| Week2_Day2_06012021 | 6 | 4,160 | 0 | 0 | 0 | 0 | 0 |
| Week2_Day3_06022021 | 6 | 569,848 | 0 | 0 | 0 | 0 | 0 |
| Week2_Day4_06032021 | 6 | 382,178 | 131 | 0 | 0 | 0 | 0 |
| Week2_Day5-7_06042021-06062021 | 6 | 303,926 | 291 | 0 | 0 | 0 | 0 |
| Week3_Day1_06072021 | 6 | 338,980 | 162 | 0 | 0 | 0 | 0 |
| Week3_Day2_06082021 | 6 | 101,838 | 31 | 0 | 14 | 0 | 0 |
| Week3_Day3_06092021 | 6 | 216,959 | 32 | 0 | 30 | 0 | 0 |
| Week3_Day4_06102021 | 1 | 102,552 | 38 | 0 | 0 | 0 | 0 |
| Week3_Day5-7_06112021-06132021 | 6 | 388,244 | 0 | 0 | 32 | 0 | 0 |
| Week4_Day1_06152021 | 6 | 215,729 | 0 | 0 | 18 | 0 | 0 |
| Week4_Day2_06152021 | 11 | 186,910 | 0 | 0 | 20 | 0 | 0 |
| Week4_Day03_06162021 | 6 | 277,510 | 0 | 0 | 20 | 0 | 0 |
| Week4_Day4_06172021 | 6 | 230,322 | 0 | 0 | 18 | 0 | 0 |
| Week4_Day3_7_06162021_06202021 | 6 | 404,431 | 0 | 0 | 24 | 0 | 0 |
| Week5_Day1_06212021 | 6 | 287,493 | 0 | 32 | 491 | 446 | 0 |
| Week5_Day2_06222021 | 5 | 164,599 | 0 | 2,039 | 1,522 | 0 | 0 |
| Week5_Day3_06232021 | 6 | 153,880 | 0 | 2,812 | 2,678 | 0 | 0 |
| Week5_Day4_06242021 | 4 | 49,040 | 0 | 2,921 | 2,914 | 0 | 0 |
| Week5_Day5-6_06252021-06262021 | 6 | 321,429 | 0 | 4,583 | 5,782 | 1,300 | 0 |
| Week5_Day6_06272021 | 6 | 52,668 | 4,466 | 2,660 | 2,157 | 1,331 | 0 |
| Week6_Day2_06292021 | 6 | 440,901 | 23,793 | 5,784 | 8,047 | 2,253 | 0 |
| Week6_Day3_06302021 | 6 | 352,541 | 5,852 | 3,628 | 2,680 | 9 | 0 |
| Week6_Day4_07012021 | 6 | 153,285 | 0 | 2,133 | 879 | 354 | 0 |
| Week6_Day5_07022021_part1 | 1 | 99,863 | 0 | 0 | 0 | 0 | 0 |
| Week6_Day5_07022021_part2 | 6 | 166,151 | 0 | 526 | 91 | 441 | 362 |
| Week6_Day6-7_07032021-07042021 | 6 | 187,079 | 0 | 0 | 0 | 1,388 | 0 |

## Audit scope

This qualification read source data and metadata, checked file hashes and timestamps, corrected CSV parsing, and counted annotations and role strata. It performed **zero model fits, zero inference, zero downloads, and no changes to raw data or earlier frozen results**. The model protocol is a separate artifact; [PILOT_INPUTS.json](PILOT_INPUTS.json) binds the inputs only.
