# G0 dataset access and schema review

Research date: 2026-09-20. Scope: primary-source verification, modest public downloads, schemas, labels, and sample counts. **No scorer training, model inference, efficacy evaluation, AWS compute, or messages to authors.** Full alert content remains in the private acquisition directory.

Machine-readable evidence: [G0_DATASET_RECEIPT.json](../data_manifest/G0_DATASET_RECEIPT.json). Private acquisition root: `C:/w/cert_gate_data_20260920/access_review/`.

## Decision

**The proposal's full primary experiment has not passed G0.** We acquired a substantial processed SecAlertBench dataset and small SIABench scenarios, but neither currently supports every proposed predicate and independent calibration requirement. CORTEX's claimed release could not be located. The harness can be built and tested on fixtures while these limitations remain explicit.

| Dataset | Actual accessible artifact | Main limitation | G0 status |
|---|---|---|---|
| SecAlertBench | 8,322 processed alerts; nine illustrative raw alerts | No license found; no released full raw logs, severity, timestamps, enterprise IDs, or campaign IDs in processed records | Hold for research-use terms, evidence/label audit, and independent-unit design |
| CORTEX | Primary paper, not its dataset | No dataset download URL, data bytes, or dataset license located | Artifact hold |
| SIABench CIC | 35 labeled scenario JSON records: five positive / 30 negative | Too few positives; linked 487 MB PCAP archive not downloaded in this modest acquisition | Diagnostic only |
| SIABench TII | 150 distinct JSON scenarios: 100 positive / 50 negative | Fewer positives than needed for a simple 1% / 95% zero-miss bound; linked “PCAP” archive contains JSON only | Diagnostic only |
| CIC-IDS2017 regenerated alerts | Primary dataset and reuse terms verified; no new alerts generated | Full capture/flow-label acquisition, alert generation, labeling joins, and independent-unit design remain | Not yet built |

## SecAlertBench: real bytes, restricted context

[The author repository](https://github.com/Dxsssu/SecAlertBench/tree/42a84889fda912ca432c994924a1ccd4b9df6274) identifies itself as the artifact for *SecAlertBench: Evaluating Large Language Models for Tier-1 Alert Triage in Security Operations Centers*. Its abstract states three enterprise SOCs, 241 alert types, and 16 evaluated LLMs. It reports average TPR 79.71%, F1 70.92%, and FPR 44.13%. A separate paper PDF, DOI, or publication page was not located; retain those figures as **author-reported artifact claims**, not independently reproduced results.

The README explicitly says the complete raw enterprise logs cannot be released, timestamps were removed, and source/destination IPs were randomized. The pinned repository tree and README contain no license declaration; GitHub's license metadata is null. Public availability alone does not satisfy the proposal's explicit license acceptance requirement.

### Verified acquisition

- Commit: `42a84889fda912ca432c994924a1ccd4b9df6274` (2026-05-03).
- File: `0x02. Processed SecAlertBench Dataset/secalertbench.json`.
- Actual size: **21,719,558 bytes**.
- SHA-256: `33f95305d1c42f8e615e4f94066119570859dee7eb086dff7c2273536c932ea3`.
- Parsed list: **8,322 records = 2,496 Attack + 5,826 Non-Attack**.
- Distinct `rule_name`: **241**; distinct `attack_type`: **23**; distinct `proto`: **2**.
- Each record has the same 19 keys: `attack_type`, `dip`, `host`, `method`, `rule_name`, `rsp_body`, `kill_chain_all`, `proto`, `xff`, `dport`, `rsp_status`, `parameter`, `sip`, `rsp_header`, `uri`, `req_header`, `req_body`, `sport`, `Label`.

There is no released train/calibration/test partition in the acquired dataset. The positive and negative files are label-specific subsets, not independent evaluation splits. Every processed record is unique when all fields are included. A descriptive duplicate screen excluding label, randomized IPs, and ports leaves **7,946 content groups**, including **376 extra rows and one mixed-label group**. This is an exact-content diagnostic, not a full near-duplicate audit or proof that the remaining groups are independent incidents.

Each of the three raw-example files contains three examples. Some examples have severity, times, and richer fields, but these nine records have no demonstrated join to all 8,322 processed rows. They cannot supply missing predicates for the full corpus.

### Predicate support

| Proposed evidence condition | What can actually be checked |
|---|---|
| Fields verified against independent raw telemetry | Not supported for the processed corpus. Request/response fields are embedded in the same alert; comparing them internally is not independent verification. |
| Critical severity never suppressed | Processed severity is absent. Do not fabricate it from attack labels. A separately justified, frozen rule-class exclusion would be a different predicate. |
| Rule class in registered eligibility list | `rule_name` is present and can support a frozen allowlist. Class membership does not establish benignness. |
| Correlated alerts or campaign context | Original source identities, incident groups, and times are absent. Random IPs are not reliable host identities. |
| Temporal calibration and drift | No valid event-time field. Occasional HTTP `Date` header text is not a substitute for release timestamps or a validated event clock. |

A blinded human review can assess whether the provided alert text appears consistent with its label. It cannot independently recover omitted enterprise telemetry or prove that the original investigation label was correct. “Unable to verify from released evidence” must be available as an audit outcome.

## CORTEX: paper verified; dataset not acquired

[Wei et al.'s primary paper](https://arxiv.org/abs/2510.00311), v1 dated 2025-09-30, describes several thousand production investigation traces and reports actionable F1 changing from **0.66 to 0.78**, with its reported FPR changing from **24.9% to 14.2%**. These are the paper's results, not a reproduction. Its FPR wording is unusual and the denominator should be verified from code before comparing it with suppression risk.

The paper claims a release and describes useful metadata, including tenant and time. However, the inspected [full text](https://arxiv.org/html/2510.00311v1) contains no dataset repository/download link; targeted searches did not locate an author artifact. No dataset bytes or dataset license were acquired. The paper's CC-BY license is not evidence of a separate dataset license. Status is **unlocated**, not proven “available on request” or definitively private. Do not count CORTEX as an available second evaluation tier.

The downloaded paper HTML is pinned by SHA-256 in the machine receipt. No authors were contacted.

## SIABench: usable small diagnostics, with a material artifact discrepancy

Primary paper: [Jajodia et al., *Before You Hand Over the Wheel*, March 2026](https://arxiv.org/abs/2603.06422). It describes 25 investigation scenarios and 135 triage scenarios. The [author GitHub repository](https://github.com/llmslayer/SIABench/tree/99327f02d4c0eb9902b4df00881e527255d14ca6), pinned to `99327f02d4c0eb9902b4df00881e527255d14ca6`, has no detected license file and says the TII set will be uploaded. The [author Hugging Face dataset](https://huggingface.co/datasets/SIABench/SIA_Dataset/tree/ec48d6049811c48273a23c77e3000124e238cb64), however, is ungated and declares Apache-2.0 in its card.

### Actual downloaded Hugging Face records

Commit: `ec48d6049811c48273a23c77e3000124e238cb64`.

| Exact file | Bytes | Parsed records | SHA-256 |
|---|---:|---:|---|
| `data/alert_triaging_cic_test.jsonl` | 41,201 | 35: five positive, 30 negative | `269d08d214edc0e0cfc529205b2d5689980576740c99daf8d658aa119d66f3fd` |
| `data/alert_triaging_tii_tp.jsonl` | 102,748 | 100 positive | `7a2281cae880dcd7cbd75fd6acff9449d16ec2543de7b357db039ec71140e983` |
| `data/alert_triaging_tii_fp.jsonl` | 51,414 | 50 negative | `184cf2737e798ae9c8009a77822ee211924b322ccfb42bac02bf5a3a8b1c51c5` |

All scenario IDs and alert strings are distinct within each downloaded file. **The actual TII release has 100 positive records, not the 50 described in the README.** This is a version/count discrepancy; no assumption of correspondence to the paper's evaluated cases should be made. Of the 100 positives, 75 are two Telnet login alert types. Fifty negative scenarios include 36 “Ethertype unknown” alerts. Distinct rows and IDs do not establish independent attacks or broad SOC coverage.

The flattened JSONL schema includes `scenario_name`, `alert_name`, `alert_type`, `scenario`, `alert`, tools, a `capture.pcap` filename, instructions, a placeholder directory, and question/answer pairs. **Exclude `alert_type`, question answers, and label-revealing IDs such as `false_alert_1` from model input.** Some alert text has timestamps and source/destination tuples; TII examples include epoch-era timestamps, which need validation against actual captures before temporal claims. Priority appears in some CIC alert strings; no uniform independently validated severity schema was established.

### Raw artifact probes

- The author-linked CIC PCAP URL reaches a Google Drive download page for **`pcaps.zip` (487 MB)**. Only the landing page was read; the complete archive and its checksum remain unverified.
- The author-linked TII “PCAP” URL returned a complete **124,517-byte ZIP**, SHA-256 `b704207165a9a7b4a8cd0a3f0e9b07dce79590fdd837c1483a57a8cf8210743b`.
- Inspection of that ZIP's central directory found **150 JSON files, zero PCAP files** (153 entries including directories; 227,512 uncompressed bytes). It supplies scenarios rather than the promised packet evidence. Nothing from the archive was executed.

The HF card's license declaration covers the released dataset representation; original third-party capture terms still need to be retained when obtaining those captures. SIABench's ethics statement describes source-platform access conditions for its separate CTF tasks. Those tasks should not be confused with a large production alert corpus.

## CIC-IDS2017 regenerated alerts

[The primary UNB dataset page](https://www.unb.ca/cic/datasets/ids-2017.html) provides the capture schedule and attack/flow-label description. [UNB's dataset FAQ](https://www.unb.ca/cic/datasets/) expressly permits reuse, redistribution, and mirroring with citation. Full PCAPs and flow-label files were not downloaded in this bounded review; no Suricata pipeline or new labels were produced.

This remains the most concrete route to independent packet evidence, but generated alert volume is not unlimited independent calibration evidence. Many rules can fire on the same packet, flow, or attack episode. The recording spans five days; split and uncertainty calculations must respect correlated episodes. A label join needs five-tuples, direction/NAT handling, time-zone validation, and an explicit unresolved category. “Inside an attack time window” alone is not a sufficient alert label.

## Calibration support and next actions

For orientation, **299 independent positive calibration units with zero observed misses** are needed for a one-sided exact-binomial 95% upper bound below 1% for one fixed rule. This illustration is not the final calibration algorithm: threshold selection, multiplicity, dependence, and the chosen estimand can change the requirements. At 100 positives, that zero-miss upper bound is approximately 2.95%; at five it is approximately 45.07%. Repeating seeds or splitting the same incident into more alerts does not create new independent positive units.

SecAlertBench has enough *positive rows* numerically, but its independent positive-unit count is unknown. SIABench's current small files do not satisfy the original primary calibration/evaluation targets. No dataset presently passes all of the proposal's unchanged two-tier G0 requirements.

Recommended immediate work is concrete: build the gate with explicit missing-evidence behavior; retain SecAlertBench as an access/schema candidate pending its terms and audit; acquire and qualify actual capture-to-alert evidence for a controlled tier; and keep CORTEX on hold until an artifact exists. None of these access findings supports a guaranteed positive workload-reduction result.
