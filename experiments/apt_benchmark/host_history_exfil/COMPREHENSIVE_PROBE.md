# Comprehensive APTs Dataset: actual archive qualification

**Review date: September 22, 2026. Status: artifacts acquired; principal study not qualified.**

The files are accessible, but this release does **not currently provide a defensible principal benchmark** for determining whether host roles and earlier activity distinguish successful lateral movement from exfiltration amid verified benign activity. This is a dataset qualification result, not a failed model experiment. No model was fitted.

The actual-byte findings below supersede the metadata-only reservation in [DATASET_LITERATURE.md](DATASET_LITERATURE.md). The full per-file hashes, observed label counts, column names, host counts and timestamp ranges are in [COMPREHENSIVE_PROBE.json](COMPREHENSIVE_PROBE.json).

## What was downloaded and checked

- Source: [author repository](https://github.com/AbSamad99/APTsDataset), pinned commit `cb74048ea76b286f9c63efcbd8e795c3de7f7543`.
- **24 log archives: 7,910,924 bytes.** With campaign profiles, sequence JSONs, READMEs and the label-mapping configuration: **98 files, 8,598,540 bytes**.
- Every downloaded file matched its pinned Git blob SHA-1 and expected size. SHA-256 hashes were also recorded.
- All 24 archives contained one CSV. Member names were checked, and CSVs were read to standard output without extracting archive paths onto the filesystem. Downloaded scripts, commands and profiles were never executed.
- The CSV members total **519,063,587 uncompressed bytes**, including one duplicate copy. The source license is CC-BY 4.0, as declared by the authors.

## The decisive findings

### 1. Only one qualified-width file contains both target tags

The parser encountered **201,658 CSV records**. Of these, **137,463 match their file's sole header width**; **64,195 do not**. Assigning columns to the latter would require guessing a missing or changed schema. They were quarantined from all label, host and time statistics.

Among the header-compatible records, the observed counts are:

| Observation | Count | Interpretation |
|---|---:|---|
| Lateral-movement tactic tags | 23 | Correlated rule-tagged records, not 23 independently verified movements |
| Exfiltration tactic tags | 81 | Includes one duplicated campaign copy and failed/preparatory activity |
| Distinct exfiltration records after the documented host/time/original-event/tactic key | 58 | Descriptive duplicate removal, not a count of successful transfers |
| Missing tactic tags | 125,153 | Unknown/unmatched; **not certified benign** |
| Explicit benign/normal tactic values | 0 | No benign target established by this field |
| Campaign directories with both target tags in compatible records | 1 | APT28/Campaign 1: three lateral and three exfiltration records |

**These are partial, header-compatible counts, not complete ground-truth totals for the malformed files.** A zero in the table below does not prove that the discarded records contain no attack.

### 2. Two nominal campaigns contain identical CSV data

`APT10/Campaign 2` and `APT32/Campaign 2` have **byte-identical, 33,210,183-byte CSV members**:

`c01f3ee7ecf46975378477e6e378143041dedcd4efe26eadb525bd035b783a9f`

Their archive container hashes differ, but the CSV contents do not. The 1,000 compatible records also share event IDs and original-event content; 692 records in each file have a header-width mismatch. The copies must never appear in separate training and evaluation partitions. The APT10-named copy includes the APT32 scenario path in its tagged upload command, reinforcing the need to treat source filenames as provenance rather than ground truth.

### 3. APT28/Campaign 1 shows a remote action and an upload attempt, not six independent attacks

The **44-record** file contains two observed source host identifiers. Its three lateral-tagged records include the SSH process, its launcher and a corresponding remote marker-file creation on the second source host. This is stronger evidence of a remote action than the profile alone.

The three exfiltration-tagged records comprise **local encryption, local file creation and a curl upload invocation**. An invocation is not proof of successful receipt by an external destination. The target records do not supply an independent transfer-success outcome. Moreover, the source topology uses the same attack/collection environment; these two host identifiers do not establish a varied enterprise role inventory.

The [author sequence JSON](https://github.com/AbSamad99/APTsDataset/blob/cb74048ea76b286f9c63efcbd8e795c3de7f7543/APT28/Campaign%201/APT28-Campaign-1-Sequence.json) describes intended tactic order with generic `Node: Server` entries. It has no event times or success flags. It cannot turn the six observed tags into independent execution ground truth.

### 4. Some lateral tags describe local key-file activity

`APT41/Campaign 1` contains **eight lateral-tagged records, all from one observed host**, associated with downloading, preparing and running a key-search script and accessing its output. Those records do not demonstrate cross-host movement. `APT29/Campaign 1` has **three lateral tags** on local key-script file operations, again with one observed host.

The [Logstash rules](https://github.com/AbSamad99/APTsDataset/blob/cb74048ea76b286f9c63efcbd8e795c3de7f7543/ELK/logstash.conf) assign tactics from literal command/path matches. Such tags should be described as source-rule supervision. Private-key search is ordinarily a Credential Access activity under [MITRE T1552.004](https://attack.mitre.org/techniques/T1552/004/); a later remote login would require separate evidence. This probe preserves the original labels and does not silently relabel them.

### 5. Exfiltration tags include failures and preparation

- `APT32/Campaign 2`, and its duplicated APT10 copy, include exfiltration-tagged messages reporting **HTTP 501: the server does not support the attempted POST**.
- `APT3/Campaign 2` includes tagged upload processing with a **missing archive path and a terminating error**.
- `APT28/Campaign 2` has one exfiltration-tagged script block that splits an archive into parts. The record alone does not establish data transfer.

These observations do not prove that every attempted transfer failed or that no other telemetry could establish success. They do establish that **the released tactic tag is not a transfer-success label**. A model learning these tags would answer a narrower question about emulation-associated log activity.

## Per-directory counts

`Records` counts all parsed CSV records. `Compatible` matches the sole header width. Tactic, host and missing-tag counts apply **only to Compatible records**. Host counts are distinct nonmissing `host.name` strings and may represent collection/container identifiers; they are not validated independent endpoints or roles.

| Directory | Records | Compatible | Lateral tags | Exfil tags | Host strings | Missing tactic |
|---|---:|---:|---:|---:|---:|---:|
| APT10 / Campaign 1 | 28 | 28 | 3 | 0 | 2 | 0 |
| APT10 / Campaign 2 | 1,692 | 1,000 | 0 | 23 | 1 | 702 |
| APT28 / Campaign 1 | 44 | 44 | 3 | 3 | 2 | 0 |
| APT28 / Campaign 2 | 578 | 578 | 0 | 1 | 1 | 285 |
| APT29 / Campaign 1 | 39,227 | 39,227 | 3 | 0 | 1 | 39,159 |
| APT3 / Campaign 1 | 64,901 | 64,901 | 0 | 0 | 1 | 59,045 |
| APT3 / Campaign 2 | 368 | 368 | 0 | 31 | 1 | 320 |
| APT32 / Campaign 1 | 37 | 37 | 0 | 0 | 1 | 0 |
| APT32 / Campaign 2 | 1,692 | 1,000 | 0 | 23 | 1 | 702 |
| APT35 / Campaign 1 | 33,020 | 1,500 | 0 | 0 | 1 | 1,500 |
| APT35 / Campaign 2 | 1,200 | 1,200 | 0 | 0 | 1 | 879 |
| APT39 / Campaign 1 | 58 | 58 | 3 | 0 | 2 | 0 |
| APT39 / Campaign 2 | 888 | 888 | 0 | 0 | 1 | 382 |
| APT41 / Campaign 1 | 46 | 46 | 8 | 0 | 1 | 0 |
| APT41 / Campaign 2 | 40 | 40 | 0 | 0 | 1 | 0 |
| APT41 / Campaign 3 | 28 | 28 | 0 | 0 | 1 | 0 |
| APT5 / Campaign 1 | 38 | 38 | 3 | 0 | 2 | 0 |
| APT5 / Campaign 2 | 507 | 507 | 0 | 0 | 1 | 243 |
| Aquatic Panda / Campaign 1 | 5,355 | 4,000 | 0 | 0 | 1 | 3,176 |
| Aquatic Panda / Campaign 2 | 2,770 | 2,500 | 0 | 0 | 1 | 41 |
| Dragonfly / Campaign 1 | 16,620 | 16,620 | 0 | 0 | 1 | 16,556 |
| Dragonfly / Campaign 2 | 1,664 | 1,664 | 0 | 0 | 1 | 1,397 |
| Windshift / Campaign 1 | 30,166 | 500 | 0 | 0 | 1 | 485 |
| Windshift / Campaign 2 | 691 | 691 | 0 | 0 | 1 | 281 |

Compatible `@timestamp` values span June 18–October 4, 2024 across the files; exact per-directory ranges and parse checks are in the JSON. The exported timestamps have no explicit timezone. Linux records also contain embedded audit epochs. For example, the receiving-side marker in APT28 appears earlier by exported timestamp than its SSH launcher, while embedded audit times place the marker after the launcher. **Do not construct causal history from the exported clock without normalizing event-time and collection-time semantics.** The files' row order must also be checked rather than assumed chronological.

## What can reasonably be done next

**Do not spend model compute on the intended principal study using this release as currently qualified.** More training cannot create missing benign truth, independent successful transfers, or reliable schemas.

Retain these pinned artifacts as a small reproducible **label-quality and data-integrity case study**. To reconsider them for host-history modeling, first obtain or reconstruct from authoritative source evidence:

1. The missing per-segment column schemas, without guessing column alignment.
2. Correct campaign-to-CSV associations and an explicit duplicate policy.
3. Timestamped operation/run manifests with attempt and success distinguished, including destination receipt evidence for exfiltration.
4. Actual source/destination host inventory and clock semantics.
5. A documented benign background interval or independently established benign labels.

Any narrower experiment would need a new title and target: for example, classifying the author's rule-associated emulation steps. It could not claim demonstrated differentiation of successful movement and data theft, nor operational false-alarm control. No author contact was sent as part of this probe.

## Reference and reproducibility

Syed, A., Nour, B., Pourzandi, M., Assi, C., & Debbabi, M. (2025). Comprehensive advanced persistent threats dataset. *IEEE Networking Letters, 7*, 150–154. [https://doi.org/10.1109/LNET.2025.3551989](https://doi.org/10.1109/LNET.2025.3551989)

The accompanying JSON records all 98 source-file hashes, each CSV hash/size, per-directory counts, header fields, naive timestamp ranges and the byte-identical pair. Private acquisition, inspection and focused-row receipts preserve the evidence needed to reproduce the aggregate findings. The parsing and duplicate checks are software checks; they are not an external human review or a new independent relabeling of the source dataset.
