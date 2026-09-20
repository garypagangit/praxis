# Timestamped attack datasets: publication, access and benchmark qualification

Checked 20 September 2026. This review separates publication verification, repository metadata and bytes actually inspected. No model fitting or model scores were used to choose datasets.

## Recommendation

**Use AIT-LDS source logs as the first runnable multistage pilot.** Its eight scenarios support a whole-run chronological split and include simulated normal activity. AIT-ADS is a useful alternative alert view of the same underlying runs, not an independent validation dataset. Select an independently generated second dataset only after the companion acquisition review confirms its labels and causal inputs.

**The frozen first pilot is strongly attack-enriched and dominated by Dirb scans:** 1,689,473 Dirb label occurrences among 1,768,861 acquired source lines. Its selected intranet view covers scans, webshell actions and privilege escalation, with no observed exfiltration, collection or lateral-movement labels. Its aggregate leaderboard cannot establish performance across a complete APT lifecycle or a realistic enterprise false-alert workload. A separately frozen expansion is needed to improve source coverage; it must preserve uncertainty in the author's rule-based negative labels.

**CAM-LDS is the strongest very recent supplement for interpreting attack stages**, but lacks simulated benign user behavior. Comprehensive APTs is small and reproducible, but its rule-produced labels and explicit emulation markers require a separate, clearly scoped evaluation. CICAPT-IIoT is relevant but its current official download route requires a form. Windows-APT has a published paper and public license, but actual version-4 bytes remain unverified here.

No dataset below establishes real-world actor attribution merely because an emulation uses an APT group's name. Stage recognition and warning before a later attack action are narrower, testable objectives.

## Eight candidates

| Candidate | Peer-reviewed publication and dates | Official artifact / access / size | Labels, time and appropriate use |
|---|---|---|---|
| **AIT-LDS v2 / v2.1** | Landauer et al., *Maintainable Log Datasets for Evaluation of Intrusion Detection Systems*, IEEE TDSC 20(4), 3466–3482 (2023); [DOI](https://doi.org/10.1109/TDSC.2022.3201582). Online publication predates the 2023 issue. Collection January–February 2022; v2.1 packaging published 9 April 2026. | [Pinned v2.1](https://zenodo.org/records/19483937), **CC BY-NC-SA 4.0**. Eight no-PCAP ZIPs are 522,084,364–1,319,137,852 bytes each. Public range requests work. Paired source/label members acquired separately; see acquisition section. | Timestamped heterogeneous enterprise logs, eight emulated runs with normal activity. Labels reference original source line numbers and attack-step names. Useful detection/stage/causal-warning pilot; eight variants of shared scenarios are not eight independent real APT campaigns. |
| **AIT-ADS** | Landauer, Skopik, and Wurzenberger, *Introducing a New Alert Data Set for Multi-Step Attack Analysis*, CSET 2024, 41–53; [DOI](https://doi.org/10.1145/3675741.3675748), [author paper](https://www.skopik.at/ait/2024_cset.pdf). Artifact first released 18 August 2023; conference 13 August 2024. | [Zenodo 8263181](https://zenodo.org/records/8263181), **CC BY 4.0**. ZIP 96,202,946 bytes; labels.csv 3,703 bytes. ZIP acquired and publisher MD5 verified. | Wazuh, AMiner and Suricata alerts derived from AIT-LDS. Exact event labels require source-log/label joins; interval labels alone do not prove individual alerts malicious. Suitable alert-analysis view; downstream of existing detectors. |
| **CAM-LDS** | Landauer et al., *CAM-LDS: cyber attack manifestations for automatic interpretation of system logs and security alerts*, IJIS 25, 148, **26 August 2026**; [publisher](https://doi.org/10.1007/s10207-026-01318-x). Artifact v2 released 4 March 2026; author examples contain September 2025 events. | [Pinned record 18861762](https://zenodo.org/records/18861762), **CC BY 4.0**; 7.4 GB listed total. Individual scenario ZIPs 160–447 MB; filtered manifestations 213,771,977 bytes. Metadata only inspected. [Author code](https://github.com/ait-aecid/attack-manifestations-interpretation). | Seven scenario families, 34 variant runs, 81 techniques, 13 tactics, 18 sources; attack-execution timestamps provide step intervals. No simulated benign user activity. Use for conditional stage/technique interpretation, not operational false-positive validation. |
| **Comprehensive Advanced Persistent Threats Dataset** | Syed et al., IEEE Networking Letters 7(2), 150–154, **June 2025**; [DOI](https://doi.org/10.1109/LNET.2025.3551989), [IEEE issue listing](https://www.comsoc.org/system/files/2025-08/publications_contents_digest_2025_jun.pdf), [author paper](https://ncc.encs.concordia.ca/papers/IEEE_L_NET_25__APTs_Dataset.pdf). One inspected run contains June 2024 events. | [Author repository](https://github.com/AbSamad99/APTsDataset/tree/cb74048ea76b286f9c63efcbd8e795c3de7f7543), **CC BY 4.0**. At this commit: 24 campaign archives, 7,910,924 bytes combined. One tiny archive actually inspected. | Linux/Windows logs with timestamps, rule-enriched tactic/technique fields, planned sequence JSON. Good small stage-mapping qualification set; independent benign truth not established. Rule-derived labels and artificial command markers limit generalization claims. |
| **CICAPT-IIoT2024** | Ghiasvand et al., *Resilience Against APTs: A Provenance-Based IIoT Dataset for Cybersecurity Research*, MobiQuitous **2024**, proceedings first online **2 January 2026**, pp.121–144; [publisher](https://doi.org/10.1007/978-3-032-10554-7_7). The 2024 arXiv version is not the sole publication. | [Official page](https://www.unb.ca/cic/datasets/iiot-dataset-2024.html), [current download route](https://cicresearch.ca/IOTDataset/CICAPT-IIoT-Dataset/). Form requires name, email, organization and other fields; no form submitted. Paper reports about 10 GB; actual release inventory/license not verified. | Provenance CSV nodes/edges and packets, attack information with time/PID/category. Four days normal, three attack days; APT29-inspired plan with over20 techniques/eight tactics. Relevant graph-vs-sequence benchmark once acquired, but small campaign diversity. |
| **Windows-APT 2025** | Mozaffari, Yazdinejad, and Dehghantanha, Data in Brief 65,112569, online **11 February 2026**, April2026 issue; [publisher](https://doi.org/10.1016/j.dib.2026.112569). Capture **28 October–22 December 2024**. | [Author lab](https://cybersciencelab.com/datasets/windows-apt-2025/); [Mendeley v4](https://data.mendeley.com/datasets/b8fmtzvpy8/4), published3July2026, **CC BY4.0**. Article lists combined CSV242,124KB plus period files/metadata. Version4 actual bytes not acquired; direct metadata requests returned403. | 36 APT-inspired Caldera scenarios,102,011 records, Wazuh/Sysmon timestamps, manifests and tactic/technique mappings. Paper distinguishes intended scenario coverage from nine tactics actually observed. Verify row-to-scenario linkage and benign labels before choosing; emulated identities are not attribution evidence. |
| **CICIoT2023** | Neto et al., Sensors23(13),5941, **26June2023**; [publisher](https://doi.org/10.3390/s23135941). Dataset name/publication year do not independently establish every capture date. | [Official artifact page](https://www.unb.ca/cic/datasets/iotdataset-2023.html). PCAP, feature CSV, example notebook and extraction code described. [Current download route](https://cicresearch.ca/IOTDataset/CIC_IOT_Dataset2023/) requires form; actual size and dataset license not verified here. | 33 attacks/seven categories across105 IoT devices. Supports malicious-traffic classification; no linked APT-chain labels established. Absolute timing is not evident in listed feature columns; PCAP reconstruction would be needed for causal prefix evaluation. |
| **CICIoMT2024** | Dadkhah et al., *CICIoMT2024: A benchmark dataset for multi-protocol security assessment in IoMT*, Internet of Things28,101351, **December2024**; [publisher](https://doi.org/10.1016/j.iot.2024.101351). | [Official artifact page](https://www.unb.ca/cic/datasets/iomt-dataset-2024.html), [current download route](https://cicresearch.ca/IOTDataset/CICIoMT2024/). Form required; exact inventory, release size and dataset license not verified. Article license must not be assumed to license dataset bytes. | 18 attacks,40 devices, Wi-Fi/MQTT/Bluetooth, plus device-state profiling. Appropriate medical-device domain shift for traffic detection. Device lifecycle states and attack categories are not an ordered APT lifecycle. |

## Concrete artifact qualifications

### AIT source labels and usable chronology

The label format is JSONL with `line` (one-based original source line), `labels` (attack-step strings), and `rules` (label-rule provenance). Preserve source bytes and line numbering before parsing. Only selected log files with corresponding annotation files qualify for this pilot; an unmatched alert or a log from an unannotated source remains unknown. Absence from a positive annotation file is an author-label convention, not independent proof of benignness. The dataset release includes labeling rules and simulation intervals for auditing this convention. [Official v2.1 documentation](https://zenodo.org/records/19483937).

AIT-ADS's published analyzer defaults `do_event_labeling=False`. Exact host-alert labels require underlying source lines; some network alerts require AIT-NDS flow labels and a documented DNS-label correction. The provided filtering script removes alerts outside attack intervals. Therefore, reusing its filtered output would invalidate a binary detection/FPR benchmark. [Pinned author analyzer](https://github.com/ait-aecid/alert-data-set/blob/ce927ddaeaa674f6909e1de676fa7dc293e393bd/analyze.py), [author workflow](https://github.com/ait-aecid/alert-data-set/blob/ce927ddaeaa674f6909e1de676fa7dc293e393bd/README.md).

### Comprehensive APTs: small does not mean independently labeled

The inspected APT10 campaign1 archive is3,642 bytes, SHA256 `5c8fea9ccabcd81c9d066c87e9245a93967cd3b5bd4da3245862063f62dcb1c2`. Its CSV is45,674 bytes and28 parsed rows, with11 distinct technique values. Every row in this small sample has a tactic; that does not establish the entire release's negative class. The CSV carries `@timestamp`, raw audit `epoch`, command/message, tactic/technique, and duplicated `.keyword` columns. One raw message contains an explicit stage-name marker. The planned sequence JSON lacks timestamps. Strip target fields and duplicated enrichment, compare a rule baseline, and separately audit artificial markers. [Pinned campaign](https://github.com/AbSamad99/APTsDataset/tree/cb74048ea76b286f9c63efcbd8e795c3de7f7543/APT10/Campaign%201).

The paper describes83 manually authored TTP mapping rules. Predicting these labels may measure reconstruction of that mapping. It is not automatically evidence of discovering a previously unknown intrusion. [Author paper](https://ncc.encs.concordia.ca/papers/IEEE_L_NET_25__APTs_Dataset.pdf).

### CAM-LDS: correct target and independent units

The release explicitly distinguishes idle-system events from realistic benign user activity. Filtered manifestations also use known attack intervals and remove recurring normal-system events. Do not compare that view against unfiltered operational streams as though they were the same task. Use raw chronological steps for stage interpretation; hold whole scenario families out. The `steps`, `sequences` and `techniques` directories repeat some of the same events, so they must never cross folds independently. [Release documentation](https://zenodo.org/records/18861762).

## Common benchmark requirements

1. **Same information at the same time:** every model receives the same timestamp-bounded observations. Completed flow duration, total bytes, future graph edges and end-of-attack summaries are unavailable before their completion.
2. **Separate three outcomes:** malicious-event detection, stage identification after evidence arrives, and warning before a named later action. Do not rename postattack classification as early warning.
3. **Freeze groups before fitting:** no random row split across one attack run, repeated templates, overlapping windows or copied logs. Report campaign/scenario counts beside event counts.
4. **Keep the negative target explicit:** distinguish author-labeled nonattack, interval nonattack, unannotated and unresolved records. Never convert all missing labels to benign across unrelated sources.
5. **Remove answer channels:** tactic/technique fields, labels, scenario/actor directory names, attack scripts and investigator summaries remain outside model features. Preserve genuine raw command evidence, but measure dependence on artificial emulation markers.
6. **Primary warnings:** recall by stage at a fixed false-alert rate, delay from first observable attack evidence, and warning lead time before the selected later action. A model cannot detect a step leaving no observable trace; report that coverage separately.
7. **Scope:** these are controlled emulations. No result establishes attribution, production safety, or a mathematically certified attack-miss guarantee under new environments.

## Recent exclusions

- [6TiSCHSet-2026](https://zenodo.org/records/22113022) is public, but its own citation says the IEEE Access article is under review. It does not yet meet the peer-reviewed requirement.
- [Multi-Source Cybersecurity Logs](https://arxiv.org/abs/2606.18190) is a relevant2026 preprint; no peer-reviewed publication was verified in this bounded review.
- A newer release date can describe repackaging, not new collection. AIT-LDS v2.1 is a2026 package of2022 simulations; Windows-APT2025 has2024 capture and2026 publication.

## Acquisition record

Private artifact directory: `C:/w/apt_benchmark_data_20260920/ait`.

- `ait_ads.zip`: full archive acquired, publisher MD5 `43db6b1f0996e0024befd617706c50e9` matched; SHA256 `9f0595c4ebe56ac9223763881f55369dd4f249a8108064e4ae108eb3309aeeb9`. Inventory in `ADS_INVENTORY.json`; raw16JSONL members remain in the ZIP.
- `LDS_PARTIAL_JOIN_PROBE.json`: initial Russellmitchell source/label feasibility probe. Its text-only alert join is not a benchmark label assignment.
- `partial_lds/<scenario>/`: final reusable acquisition output from `acquire_ait.py`, containing exact paired intranet audit/auth/Apache members, `dataset.yaml` and `gather/attacker_0/logs/attacks.log`. Per-scenario and top-level `ACQUISITION.json` record the pinned release, ranges, archive publisher checksum, member CRC32 and SHA256. The entire LDS archive was **not** downloaded or checksum-verified. `lds_core` is an earlier partial acquisition and is not the final benchmark source root.

The acquisition helper was checked with a synthetic ZIP for directory parsing, paired selection, byte preservation, path-traversal rejection and corrupted-CRC rejection. It does not execute source scripts or assign model scores. **Acquisition completed for all eight runs:** 80 members, 653,687,563 decompressed bytes and 1,768,861 source lines. The final successful/resumed invocation requested 29,631,219 range bytes; earlier attempts also transferred ranges before Zenodo rate limits. This figure is not cumulative network usage across those attempts. Publisher ZIP checksums are recorded, while individual member CRC32 and SHA256 are verified.

All eight ZIP central directories were inspected. Each has exactly four intranet annotation files, all nonempty; the helper nevertheless includes empty annotation files if present. Shaw uses `auth.log.1`; the other runs use `auth.log`. Apache log rotation suffixes vary. Additional source logs without corresponding annotation files are deliberately outside this pilot's label scope.

The proposed assignment, fixed before fitting, is fit: Santos, Fox, Wardbeck, Russellmitchell; development: Shaw; calibration: Wheeler; test: Wilson, Harrison. Fit simulation starts range 14–21 January 2022 and end by 25 January. Development and calibration simulations overlap in late January and end by 31 January. Test simulations start 3–4 February. This separates the final test period from fitting/tuning/calibration; it does not make the runs independent campaigns or establish nonoverlapping chronology between every role. Source YAML omits timezone; attacker chronology includes explicit UTC. Parse source offsets where present and exclude unresolved timestamps from early-warning metrics. Do not use the first attacker-log line blindly as onset: it can be a service-stop action preceding the main chain.

| Run | Raw source lines | Lines with author attack annotations | Simulation interval (2022; source YAML omits timezone) |
|---|---:|---:|---|
| Santos | 12,039 | 7,867 | 14–18 January |
| Fox | 417,719 | 412,208 | 15–20 January |
| Wardbeck | 14,338 | 5,363 | 19–24 January |
| Russellmitchell | 11,154 | 7,748 | 21–25 January |
| Shaw | 10,861 | 5,290 | 25–31 January |
| Wheeler | 437,491 | 432,920 | 26–31 January |
| Wilson | 439,830 | 429,487 | 3–9 February |
| Harrison | 425,429 | 416,762 | 4–9 February |

These are acquisition counts, before timestamp filtering, parsing or model preparation. The selected files contain 1,717,645 author-annotated attack lines and 51,216 other source lines. This is an **attack-enriched source subset**, not the original enterprise traffic prevalence. Observed labels cover service scans, Dirb/WPScan, webshell actions and privilege escalation. There are no exfiltration, collection or lateral-movement labels in this selected intranet view. Evaluate only supported stages; whole-lifecycle detection claims would exceed the data. Dirb contributes 1,689,473 label occurrences, so per-stage and per-run metrics are necessary alongside aggregate scores.

## Post-freeze source-coverage qualification

This qualification does not change frozen pilot v1. Its question is whether missing annotation files always mean that the corresponding source file was outside the author's labeling pipeline.

The author's label exporter enumerates source files only among documents containing a label-rule match, then writes their matching lines. A file with zero rule hits therefore has no annotation file by construction. This is verified behavior in the pinned author code; the exact historical code revision used to produce the 2022 runs was not established. [Positive-only file enumeration and export](https://github.com/ait-aecid/kyoushi-dataset/blob/8cd65dce86d39e67c3038a853e281210a96a9332/src/cr_kyoushi/dataset/labels.py#L1451).

Separately acquired, CRC32- and SHA256-verified processing artifacts from all eight scenario ZIPs explicitly configure `audit/audit.log*`, `auth.log*`, `apache2/*access*.log*` and `apache2/*error*.log*`. Their archived `file-completed.log` files confirm ingestion of **96 additional nonempty intranet source files** without corresponding annotation files. The additional members total **1,721,587 compressed bytes**. Directory and ingestion checks support calling them covered sources with no exported rule matches; they do not prove parser success for every line or independently establish semantic benignness. Private file-level evidence is recorded in `ait/coverage_probe/COVERAGE_QUALIFICATION.json`.

| Run | Additional source files without annotation files | All listed in archived ingestion-completion log | Compressed bytes |
|---|---:|---|---:|
| Santos | 9 | Yes | 95,390 |
| Fox | 11 | Yes | 162,991 |
| Wardbeck | 12 | Yes | 437,968 |
| Russellmitchell | 10 | Yes | 49,879 |
| Shaw | 15 | Yes | 115,788 |
| Wheeler | 12 | Yes | 69,568 |
| Wilson | 15 | Yes | 465,214 |
| Harrison | 12 | Yes | 324,789 |

The label-method paper explains that hand-authored rules can miss unexpected attack manifestations. Accordingly, any expanded negative target must be named **`AUTHOR_RULE_NONMATCH_FROM_COVERED_FILE`**, with unknown/failed parses kept separate. It is not independently confirmed benign activity. [Author's peer-reviewed labeling-method paper](https://doi.org/10.1145/3510547.3517924), [author PDF](https://www.skopik.at/ait/2022_satcps.pdf).

### Observation-time correction to freeze separately

All eight archived `processing/logstash/conf.d/0000_pre_process.conf` files encode numeric observation epochs **one hour earlier than interpreting the timezone-free dataset YAML as UTC**. Those numeric epochs provide a stronger explicit time basis than guessing a timezone for YAML. A local CET interpretation is consistent with the difference, but that explanation is an inference. Do not silently alter an already scored protocol.

| Run | Archived observation start, UTC | Archived observation end, UTC |
|---|---|---|
| Santos | 2022-01-13 23:00 | 2022-01-17 23:00 |
| Fox | 2022-01-14 23:00 | 2022-01-19 23:00 |
| Wardbeck | 2022-01-18 23:00 | 2022-01-23 23:00 |
| Russellmitchell | 2022-01-20 23:00 | 2022-01-24 23:00 |
| Shaw | 2022-01-24 23:00 | 2022-01-30 23:00 |
| Wheeler | 2022-01-25 23:00 | 2022-01-30 23:00 |
| Wilson | 2022-02-02 23:00 | 2022-02-08 23:00 |
| Harrison | 2022-02-03 23:00 | 2022-02-08 23:00 |

**Next gate:** acquire the additional covered source members into a separate directory, retain byte/line provenance, and freeze an expanded-source v2 before fitting. Use the archived epoch boundaries, audit explicit-offset timestamps and unresolved timestamps separately, and distinguish author-positive, author-rule-nonmatch and unknown records. Preserve the chosen whole-run split and avoid tuning against revealed v1 test outcomes. Broader source coverage still leaves a shared synthetic scenario and rule-label limitations; a later independent dataset remains necessary.

### Completed separate background acquisition

All **96 additional source files** were acquired into private `ait/coverage_expansion/<run>/`, preserving original bytes and one-based source lines. Every member passed local-header/name, decompression-length, CRC32 and SHA256 checks. The source acquisition requested **1,733,071 range bytes**, including member headers; previously acquired processing proofs were reused after verification. Whole archive checksums remain recorded but unverified.

| Run | Additional files | Source lines | Lines with explicit-offset timestamps inside archived interval |
|---|---:|---:|---:|
| Santos | 9 | 10,528 | 6,322 |
| Fox | 11 | 14,165 | 10,084 |
| Wardbeck | 12 | 35,400 | 30,839 |
| Russellmitchell | 10 | 6,876 | 2,654 |
| Shaw | 15 | 13,105 | 9,120 |
| Wheeler | 12 | 8,389 | 7,726 |
| Wilson | 15 | 33,675 | 29,275 |
| Harrison | 12 | 23,773 | 19,563 |
| **Total** | **96** | **145,911** | **115,583** |

The explicit timestamps are in Apache access records. Authentication timestamps omit year/timezone; Apache error records either omit timezone or lack a recognized timestamp. These other **30,328 lines** are not automatically eligible for causal time-bounded evaluation. Across the original two test runs, **48,838 explicit-clock lines** qualify and **8,610 other lines** remain excluded. These are acquisition/clock counts, not model predictions or independently verified benign counts.

`acquire_background.py` reproduces the fixed member selection from the original pinned archive directory plus archived configured globs and completed-ingestion paths. It copies verified processing proofs, records numeric observation epochs, and never executes log contents. Each run's `ACQUISITION.json` contains `observation_epoch`, `coverage_proof_members`, and per-member `label_basis`, `ingestion_completed_proof`, ranges, CRC32, SHA256 and timestamp-format counts. A local reuse validation reproduced all eight inventories and counts with zero additional download bytes. The final helper refuses to overwrite a completed acquisition directory.

For a first supplement, keep all v1 models and calibration thresholds fixed and score only the eligible additional sources in the same two test runs. Report the **author-rule-nonmatch flag rate**, not a verified operational false-positive rate, and do not calculate attack recall or F1 from this single-class supplement. A later refitted expansion needs its own frozen protocol. This adds source coverage but does not create an independent external test environment.

Receipt binding note: local reuse verification refreshed acquisition metadata after the supplemental scorer had already recorded the original test-run receipt hashes. Exact original receipt bytes were reconstructed and independently matched to those recorded hashes, then preserved under `coverage_expansion/ORIGINAL_SCORE_RECEIPTS/<run>/ACQUISITION.json`. Source member bytes, hashes and clock eligibility counts did not change. The original scored receipt hashes are Wilson `9e7eaad052abbe07934504b40ae8d15454b7428c52ad5589d2021c5aed42af9f` and Harrison `213807f4c443376ae97b262bb5d380f5b585addb76fafb9eaf9bf36543cdc843`. Receipts are now frozen; this note does not imply a second scoring run.
