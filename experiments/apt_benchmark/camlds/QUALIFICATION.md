# CAM-LDS qualification completed

**Status:** raw audit acquisition and preparation are complete. T1105 passes the declared two-class support gate for the family-separated experiment. This note reports data qualification, not model performance. See the [frozen adapter design](README.md) and [corrected CAM protocol](../robustness_v2/camlds_masked_protocol.json).

## What the dataset can test

The task asks whether partial audit evidence identifies membership in an **author-designated tool-transfer manifestation window**. These windows are padded and sometimes manually adjusted; a positive does not certify that the particular event is malicious or that the attack step is still active. Windows apply across hosts, so unrelated or idle host activity can inherit the same label. There is no ordinary-user benign workload and no basis here for operational benign false-alert rates or before-impact detection claims.

The independent test split contains one scenario family with 18 variants. This is useful external dataset evidence, with substantially less independent replication than 18 unrelated attack campaigns.

## Source verification

- Peer-reviewed source: [Landauer et al. (2026), *International Journal of Information Security*, 25, 148](https://doi.org/10.1007/s10207-026-01318-x).
- Pinned data release: [Zenodo 18861762, version 2](https://zenodo.org/records/18861762); API license verified as **CC-BY 4.0**.
- Pinned author label/extraction repository: [`44028d8bd40a4a1d8bbbc6ee33261d47cb433827`](https://github.com/ait-aecid/attack-manifestations-interpretation/tree/44028d8bd40a4a1d8bbbc6ee33261d47cb433827).
- Acquired **148 selected members from all 34 scenario archives**: 114 complete defender audit files and 34 attacker chronology files used only for label verification. Compressed member sizes sum to **78,275,797 bytes**; extracted source bytes total **1,755,368,535**. These are member-size totals, not total network transfer including directories, retries, or abandoned partial downloads.
- Every selected member passed ZIP CRC32 validation and was SHA256 hashed. Publisher whole-archive checksums are recorded but **not verified**, because the complete ZIP archives were not downloaded by this acquisition route.
- Author manifestation-window timestamps span **September 17, 2025–January 21, 2026** across the full source. The 32 evaluated runs span **September 17–December 15, 2025**. The 2026 paper/release date does not make this evaluated slice a 2026 attack capture.

## Prepared corpus

| Check | Observed count |
|---|---:|
| Evaluated runs / families | 32 / 5 |
| Raw defender audit lines examined | 6,852,821 |
| Malformed audit lines | 0 |
| Lines outside the complete replay envelope | 4,009,039 |
| Exact duplicate fragments removed | 4 |
| Retained record fragments | 2,843,778 |
| Reconstructed audit events | 691,563 |
| First-event queries selected without labels | 9,461 |
| Queries inside known source windows, eligible for supervision | 6,524 |
| Published label anchors verified against raw chronology | 867 / 867 |

The source has 904 manifestation-window occurrences for 883 distinct step identifiers. The evaluated subset contains 888 occurrences and 867 distinct identifiers. Repeated identifiers are preserved as separate window occurrences. Every source interval's technique set matches its pinned author label entry. Anchor verification matches source command timestamp, command type, and command text; it is an automated provenance check, not independent human adjudication of maliciousness.

The retained channels include **686,784 SYSCALL**, **241,206 EXECVE**, **686,784 PROCTITLE**, and **1,110,887 PATH** fragments, supporting meaningful controlled record-type removal. Availability times are idealized from source timestamps; injected delay is synthetic.

One source-window pair overlaps: `6_macro_cron` steps 2 and 3 overlap by approximately **0.643 seconds**. It affects **zero eligible query events**. The adapter's disclosed overlap-union convention therefore changes no eligible label in this prepared corpus.

## T1105 support after the actual source join

| Role | Families | Runs | Eligible queries | T1105 positive | Other-window negative | Positive-bearing runs | T1105 source windows represented |
|---|---|---:|---:|---:|---:|---:|---:|
| Fit | 3, 6 | 11 | 2,060 | 214 | 1,846 | 9 | 32 / 35 |
| Development | 2 | 2 | 187 | 6 | 181 | 2 | 4 / 5 |
| Calibration | 4 | 1 | 68 | 8 | 60 | 1 | 1 / 1 |
| Test | 1 | 18 | 4,209 | 100 | 4,109 | 18 | 37 / 42 |

**The fixed query grid represents 74 of the 83 T1105 source windows.** Nine windows contain no eligible first-event query. All frozen queries remain in the evaluation denominator under subsequent missingness, but query recall must not be reported as recall over every attack step or source window.

Calibration has only 60 other-window negatives. A 1% empirical clean-calibration budget permits zero observed false flags on those 60 examples; this is a coarse operating point, not a population guarantee. The test family can have a different observed flag rate.

T1068 and T1548 are **unsupported for this family-separated design** because each has zero positive fit queries. T1068 has three test queries across two runs; T1548 has eight calibration and eight test queries, with no fit or development positives. They must not be fitted or silently included in a favorable external macro average.

## Reproducibility and resource bounds

Fourteen adapter/repair tests cover interval endpoints, overlapping windows, repeated source identifiers, source-anchor validation, attacker/config exclusion, label-blind query selection, duplicate handling, identity masking, earlier-feature invariance, preservation of generic command semantics, and rejection of unbound repair inputs. The root project separately runs the broader robustness test suite.

The corrected prepared JSONL is **1,998,701,073 bytes**. Its two largest per-run blocks are unchanged at 574,139,823 bytes / 224,059 events and 533,370,632 bytes / 211,957 events. Preparation completed successfully; feature extraction should process one run at a time.

### Source-quality correction before CAM fitting

An independent feature-text scan found eight fragments retaining the fixed cross-host name `LINUXSHARE`. The CAM-only static host mask was extended to include `linuxshare`, `corpdns`, and `reposerver`; generic `CLIENT` command variables and `rsh-client` package names remain intact. No CAM model score was inspected before making this correction.

The reproducible streaming repair changed **eight `text` fields across six calibration-family events**, and no `baseline_text` fields. All **691,563 events** passed complete nontext-structure equality checks; **691,557 events** were also preserved byte for byte. Labels, split membership, event order, timestamps, source references, query eligibility, and entity linkage remain identical. Every qualification count above is therefore unchanged. The old source corpus and cache remain preserved. The corrected input is `prepared_masked_v2`; it requires a fresh feature cache and an independent paired-input verification before model fitting.

| Evidence binding | SHA256 |
|---|---|
| Corrected EVENTS.jsonl | `17bbb1a7cf7b55ff5f8bf72a88fd8cc9c54f563d0f368441a1a626537356620a` |
| Corrected MANIFEST.json | `3596db41fd7aef1c999d589042f14985631a3dd20aad0d68455e9f6ba515313b` |
| Corrected adapter events.py | `c60f664cb364eedaeede8c43c50fb149d3fe82470521f8246a6bc0ba89b5ef2a` |
| Repair code remask.py | `2fdee26f0dc39aca34811f2a850ce450928014109a41f5cb2e21a5f37c0a4c7c` |
| REPAIR.json | `d142dfd07faad1c2020f1531ecdbabf5ba4286fc50f9a90cb4fa584f670ce57b` |

The correction receipt also binds the unchanged original corpus SHA256 `95ccab6ee76963940fbf2835680b121f5e1ca56dbd967f2b7739e855eaebf19c` and original manifest SHA256 `4298418aaca0031f7b44130c109142b80e8329b1d75424db61f4e493796b31e5`.

Private source and prepared files remain under `C:/w/apt_benchmark_data_20260920/camlds_v1`. Git contains this aggregate qualification note and the adapter, not raw logs or attacker chronology. Source preparation did not fit a model or establish a positive improvement.
