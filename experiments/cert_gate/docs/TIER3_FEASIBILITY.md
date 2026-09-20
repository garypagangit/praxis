# Tier 3 network-evidence feasibility

Checked: 20 September 2026. Scope: data access, provenance design and scientific feasibility. This memo does not release G1–G5, amend `REGISTRATION.json`, establish human-review completion, or report alert-suppression performance.

## Decision

**A small network-provenance experiment is now practical.** Two SIABench CIC-IDS2017 capture files have been acquired and independently checked against ZIP metadata. They can test whether a generated alert points back to a particular packet. **They do not satisfy the existing enterprise user/incident predicates or supply a population-risk certificate.** A network-only experiment needs an explicit prospective scope amendment; it must not fill absent users or incident context with invented values.

The immediate deliverable is a reproducible packet-to-alert evidence trail, followed by an assessment of whether usable, independently labeled alerts exist. A positive result at this stage means the evidence pipeline works, not that suppression is safe, useful, novel, or validated on APT incidents.

## What is actually available

| Artifact | Verified access on this date | What is local |
|---|---|---|
| Original CIC-IDS2017 full days | Publisher describes Wednesday as 13G and Friday as 8.3G; these are approximate published sizes, not measured file lengths. The current official download link displays a registration form. | Neither full-day capture nor original flow-label archive acquired. |
| Corrected CICIDS2017 archive | HTTP HEAD and an exact HTTP 206 range verify **343,549,013 bytes**. ZIP directory contains five daily CSVs. | Only a 1,048,576-byte directory tail was fetched for metadata inspection; no complete CSV acquired. |
| Corrected Wednesday CSV member | ZIP metadata: 89,163,460 bytes compressed, 291,290,505 uncompressed. | Metadata only. |
| Corrected Friday CSV member | ZIP metadata: 77,431,866 bytes compressed, 285,188,226 uncompressed. | Metadata only. |
| SIABench `pcaps.zip` | Exact archive length **510,929,677 bytes** from verified range responses. | ZIP directory and two members; not the complete archive. |
| SIABench CIC scenario labels | Previously acquired, pinned JSONL contains 35 scenarios: 5 positive and 30 negative. | Scenario-level author labels, not independently validated labels for each packet, flow, or newly generated alert. |

Original source and research-use/citation statement: [UNB CIC-IDS2017](https://www.unb.ca/cic/datasets/ids-2017.html). Current access endpoint: [official download](https://cicresearch.ca/CICDataset/CIC-IDS-2017/). Corrected artifact: [author directory](https://intrusion-detection.distrinet-research.be/CNS2022/Datasets/). SIABench capture link and scenario-name convention are in the [pinned author documentation](https://github.com/llmslayer/SIABench/blob/99327f02d4c0eb9902b4df00881e527255d14ca6/Alert_Triaging_Dataset/Alert_Triaging_Dataset.md). No registration form was submitted and no author was contacted.

### Captures acquired for this bounded pilot

| Scenario | Pinned author scenario label | Compressed member bytes | Actual local bytes | Private path |
|---|---|---:|---:|---|
| `s2` | True positive; row 26, zero-based | 179,948 | 604,560 | `C:/w/cert_gate_data_20260920/tier3_compact/pcaps/s2/capture.pcap` |
| `fs1` | False positive; row 30, zero-based | 261,468 | 1,287,768 | `C:/w/cert_gate_data_20260920/tier3_compact/pcaps/fs1/capture.pcap` |

Both files are **PCAPNG**, identified by magic `0a0d0d0a`, despite the `.pcap` extension. Acquisition checked exact Content-Range/length, local ZIP header and filename, raw-deflate completion, uncompressed size, CRC32 and SHA256. File hashes are:

- `s2`: `a540ea3c71406e881051706cde8433a9f7c38dfce58c591a64037b10934b86c1`
- `fs1`: `ce7e03921cf52174d874251a279c96c20db7e6155e3636b04a11bf14cf295658`

Capture acquisition used **1,490,095 downloaded bytes**, including its directory tail and local-header probes. The separate corrected-label metadata probe used another 1,048,576 bytes. Neither full archive was downloaded or assigned a whole-archive checksum. Detailed receipts and member inventory are in [TIER3_ACCESS_PROBE.json](../data_manifest/TIER3_ACCESS_PROBE.json).

`s2` was the smallest positive capture. `fs1` was the smallest negative capture with an exact archive-folder/scenario-name match. A smaller `mon_pri_3_1` folder was not silently equated with the differently named `monday_pri_3_1` scenario. This is a convenience sample for pipeline development, not a representative evaluation sample.

The label crosswalk uses Hugging Face revision `ec48d6049811c48273a23c77e3000124e238cb64` and JSONL SHA256 `269d08d214edc0e0cfc529205b2d5689980576740c99daf8d658aa119d66f3fd`. Both selected author alerts have the same Snort-style `(port_scan)` signature family but opposite author conclusions. Current Suricata rules are a different detector; its outputs do not inherit those conclusions. The author documentation explicitly describes Snort alerts. [Pinned schema and artifact link](https://github.com/llmslayer/SIABench/blob/99327f02d4c0eb9902b4df00881e527255d14ca6/Alert_Triaging_Dataset/Alert_Triaging_Dataset.md)

## Known label and flow defects matter here

Liu et al. (2022) document problems in attack execution, feature extraction, documentation and labeling, and release corrected data and labeling logic. Their corrected flow extractor changes TCP termination and segmentation and writes UTC timestamps with microsecond precision. Therefore an original CSV row is not automatically an exact connection label, and mixing original and corrected time conventions can break a join. [Paper and author release](https://intrusion-detection.distrinet-research.be/CNS2022/), [tool changes](https://intrusion-detection.distrinet-research.be/CNS2022/Tools_Documentation.html)

The detailed revision excludes some manually generated browsing from an attack window and distinguishes attempted attacks from effective attack flows. An unsuccessful malicious attempt can still be actionable for a SOC: the suppression experiment must define its target rather than automatically treating every `Attempted` category as benign. Pin executable labeling logic and audit its interpretation; do not copy only the human-readable attack schedule. [Per-attack corrections](https://intrusion-detection.distrinet-research.be/CNS2022/CICIDS2017.html), [author code](https://github.com/GintsEngelen/CNS2022_Code)

For original-to-corrected comparisons, report discordant and unmapped labels separately. A timestamp within an advertised attack period is insufficient ground truth for every packet from a host. The original network includes NAT; the published external attacker address can differ from the observed wire address. [Original network description](https://www.unb.ca/cic/datasets/ids-2017.html)

## Proposed network-only contract

These are **new proposed predicates**, not evidence that the registered P1–P4 already pass.

| Proposed predicate | Evidence it can check | Important limit |
|---|---|---|
| N1: verifiable packet provenance | Capture hash plus real packet ordinal; independent decoding agrees on packet time, protocol and address/port tuple. Rule identity is separately checked against the frozen rule manifest. | A signature ID and authenticated enterprise user are not packet-header fields. Matching raw text establishes integrity, not benign meaning. |
| N2: trusted rule eligibility | Pinned rule ID/revision and explicit severity mapping; fixed eligible classes; unknown/critical rules deferred. | Low priority is not a benign label. Regenerated priority need not match the original detector. |
| N3: observed network-context coverage | Explicit required time window/flow evidence, gap and truncation checks; insufficient capture history causes deferral. | This supports a bounded network-context claim, not “no related enterprise incident.” Cropped captures may fail it. |
| N4: valid, unambiguous evidence | Typed fields, supported packet format/protocol, known timestamp units and unique accepted joins. | Missing packet anchors, competing mappings or mixed labels remain unresolved. |

Packet captures and EVE output do not establish a complete, authenticated user directory or complete enterprise incident membership. The original webpage mentions additional host collection, but no released per-alert host/user/incident evidence supporting the current predicates was acquired in this probe. Network flows or HTTP user-agent strings cannot substitute for those facts.

An independent packet parser is an independent implementation, not an independent observation of attacker behavior. Source-consistent malicious instructions in packet payloads can still pass an exact provenance check. Prompt-injection resistance must be measured separately.

## Exact joining and bounded execution plan

Suricata 8.0.7 documents `pcap_cnt` as a capture packet number and `pcap_filename` as the input file. They are absent on internal pseudo packets, including timeout events. `flow_id` links EVE records; it is not itself a cross-tool ground-truth identifier. `alert.action=allowed` is not a benign label. [EVE format](https://docs.suricata.io/en/suricata-8.0.7/output/eve/eve-json-format.html)

1. Freeze the engine binary, full configuration, rule files, rule revisions and capture hashes. Treat this as a newly generated alert corpus. Run each capture in a separate offline process: directory replay retains flow state between files. Check configuration with `-T`; use the intended rule-loading mode explicitly. [CLI](https://docs.suricata.io/en/suricata-8.0.7/command-line-options.html)
2. Enable `pcap-file: true`. Preserve the observed tuple; keep X-Forwarded-For overwrite disabled. A community ID may help correlate tools, but tuple reuse still requires a time/connection boundary. [EVE configuration](https://docs.suricata.io/en/suricata-8.0.7/output/eve/eve-json-output.html)
3. Independently inventory PCAPNG packet ordinals, interfaces, timestamp resolution, capture lengths and wire tuples. Resolve an EVE anchor using **capture SHA256 plus packet ordinal**, then verify decoded fields. Use integer timestamp units with a documented conversion. Missing anchors defer; do not replace them with ordinal zero or an arbitrary nearest packet.
4. Keep gold labels in a separate table. For a later flow-label join, pin the label release, normalize UTC/units and observation point, and match protocol, bidirectional tuple, interval and connection instance. Deduplicate only equivalent records with an audit trail. Zero candidates are unmapped; conflicting multiple candidates are ambiguous. A connection crossing label boundaries remains mixed/unresolved. Never label every flow from the scenario's single author answer.
5. Report packets, generated alerts, uniquely anchored alerts, eligible alerts, connection instances, scenarios and independently justified attack episodes separately. Retain unresolved counts in the denominator of provenance coverage. Show both captures separately.
6. Stop at a pipeline feasibility result if no useful alerts are emitted, anchors cannot be checked, or all evidence remains incomplete. Do not tune rules using the two scenario answers and then report classification improvement. A diagnostic rule can test plumbing if explicitly labeled as such; it is not a detection baseline.

**Immediate completion gate:** byte checks pass; every alert admitted as anchored has exact, independently checked source agreement; unresolved evidence is rejected; usable coverage is reported. A checker that rejects everything has zero coverage, not a useful positive experiment. Engine/rule outputs and any subsequent evaluation belong in separate run receipts; the acquisition receipt does not claim them.

## Why attack rows do not automatically supply 1% / 95% certification

For one fixed rule and IID Bernoulli attack calibration units, observing zero misses gives the familiar one-sided bound `1 - 0.05**(1/n)`. It falls below 1% at **n = 299**. This arithmetic does not establish that 299 flows from one scan are 299 independent attack opportunities. Likewise, duplicating alerts, changing seeds or splitting overlapping capture slices cannot create independent calibration units.

The current two files contain one author-positive scenario and one author-negative scenario; no count of independent attack episodes has been established. Even the full 35-scenario CIC subset has only five author-positive scenarios. A Wednesday/Friday row split may separate days while leaving few environments and a substantial attack-family shift. That does not validate the existing IID population guarantee under the new distribution.

A defensible near-term result is descriptive, finite-corpus provenance and eventually labeled alert-suppression performance with dependence-aware splits and uncertainty. A prospective population certificate additionally requires a defensible sampling unit, enough independently sampled attack units for calibration, untouched evaluation support, and a frozen procedure. More packet volume alone does not meet those requirements.

## Recommended next action

Use the two validated captures to finish the offline alert-to-packet prototype now. If its provenance coverage is useful, freeze a network-only contract and obtain validated flow/alert labels plus additional independent scenarios before fitting scorers. Downloading both multi-gigabyte original days is not needed to answer the first feasibility question.

### Primary references

- Sharafaldin, I., Lashkari, A. H., & Ghorbani, A. A. (2018). *Toward generating a new intrusion detection dataset and intrusion traffic characterization*. ICISSP. [Publisher dataset page](https://www.unb.ca/cic/datasets/ids-2017.html)
- Engelen, G., Rimmer, V., & Joosen, W. (2021). *Troubleshooting an intrusion detection dataset: The CICIDS2017 case study*. IEEE Security and Privacy Workshops. [Author PDF](https://intrusion-detection.distrinet-research.be/WTMC2021/Resources/wtmc2021_Engelen_Troubleshooting.pdf)
- Liu, L., Engelen, G., Lynar, T., Essam, D., & Joosen, W. (2022). *Error prevalence in NIDS datasets: A case study on CIC-IDS-2017 and CSE-CIC-IDS-2018*. IEEE CNS, 254–262. [Author release](https://intrusion-detection.distrinet-research.be/CNS2022/)
- SIABench authors. Pinned alert-triage artifact documentation and scenario dataset; revisions listed above. [Repository](https://github.com/llmslayer/SIABench/tree/99327f02d4c0eb9902b4df00881e527255d14ca6), [dataset](https://huggingface.co/datasets/SIABench/SIA_Dataset/tree/ec48d6049811c48273a23c77e3000124e238cb64)
- Open Information Security Foundation. *Suricata 8.0.7 documentation*. [EVE format](https://docs.suricata.io/en/suricata-8.0.7/output/eve/eve-json-format.html), [EVE configuration](https://docs.suricata.io/en/suricata-8.0.7/output/eve/eve-json-output.html), [CLI](https://docs.suricata.io/en/suricata-8.0.7/command-line-options.html)
