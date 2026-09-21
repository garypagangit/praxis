# Evidence and data plan: fewer false alarms without hiding lateral movement

Evidence checked: 21 September 2026. This is a proposal-supporting audit and acquisition plan, not a new experiment or a declaration of novelty.

## 1. What the completed experiments establish

**The problem is supported by a measurable tradeoff; a successful solution remains unproven.** Giving a strong tree model more benign examples greatly reduced false alarms, while more lateral-movement flows were classified as normal. Foundation models improved the original scarce-label classification score, but the tested checker did not improve on its strongest control and transfer to another dataset remained poor.

All SCVIC numbers below are means over the same ten fitting seeds and the same 30,787 test flows. Seeds reuse the test set and are not ten independent attacks. The test includes 29,929 normal flows and 144 flows labeled LateralMovement. Macro-F1 averages all six classes, including NormalTraffic.

### SCVIC: independently recomputed from saved confusion matrices

| Model and fitting budget | Six-class macro-F1 | Normal flows incorrectly flagged | Lateral flows flagged as any attack | Lateral flows given the correct stage |
|---|---:|---:|---:|---:|
| Stronger CV-selected tree; 32 examples per class, 192 total | 44.20649% | 10.03642% | 94.23611% | 69.79167% |
| Same stronger-tree selection procedure; 1,024 normal + 32 per attack class, 1,184 total | 65.42991% | 0.39961% | 83.05556% | 63.33333% |
| TabICL v2; 32 per class, 192 total | 54.44208% | 7.26152% | 94.44444% | 74.93056% |
| TabPFN 2.5 synthetic; 32 per class, 192 total | 54.08388% | 8.31134% | 93.40278% | 72.08333% |

The tree comparison holds the 160 attack examples fixed and adds 992 normal examples. Average false alerts fall from **3,003.8 to 119.6** per 29,929 normal flows. However, lateral flows flagged as attacks fall from **135.7 to 119.6** out of 144: an **11.18056 percentage-point loss**. Correct lateral-stage labels decline from 100.5 to 91.2. These are different outcomes and must remain separate.

Tree selection uses training-only cross-validation between XGBoost and LightGBM. The stronger search evaluated 12 configurations for each, plus six random-forest configurations; it was bounded, not exhaustive. At equal fitting budgets TabICL exceeds the selected stronger tree by **10.23559 percentage points** of macro-F1 and passes the frozen descriptive gate. **Foundation models with 1,024 benign examples have not been tested.** Therefore the unequal-budget result does not establish that trees outperform foundation models given the same abundant-benign information. Sources: [full foundation analysis](../results/tabular_followup_v1/E1_ANALYSIS.json), [stronger controls](../results/tabular_followup_v1/COMPARISONS.json).

### The tested checker is negative, and it did not specifically protect lateral movement

The frozen checker combined general attack scoring with a rescue score for **InitialCompromise and DataExfiltration**. Its minimum recall across those two stages changed by **−0.09434 percentage points versus TabICL alone**, although it improved by **15.13208 points versus the selected tree**. It failed its requirement to improve over both controls: `DEVELOPMENT_NEGATIVE`.

At the separately calibrated review operating points, checker versus single TabICL had:

| Outcome | Checker | Single TabICL |
|---|---:|---:|
| Normal flows sent to review | 0.79889% | 0.96428% |
| Lateral flows sent to review | 76.94444% | 81.38889% |
| All attack flows sent to review | 91.93473% | 93.42657% |

Routing a flow for review is not correctly labeling its stage or proving that an analyst resolved it. This checker used 29,929 labeled normal calibration flows in addition to fitting labels. The separate conformal evaluation used 30,782 labeled calibration flows overall. Those label costs cannot be hidden behind “192 training labels.” Sources: [checker aggregate](../results/tabular_followup_v1/GATE_AGGREGATE.json), [independent checker audit](../results/tabular_followup_v1/GATE_AUDIT.json).

### Sandworm: independent dataset, negative practical transfer result

The author-released target contains **2,091 unique flows: 2,054 normal and 37 attack**. It is one capture with five procedure labels, not an independent six-stage benchmark. The released CSV contains no exfiltration examples. No target fitting, calibration or threshold tuning occurred.

| Rule / model | Attack recall | Normal false-positive rate | Attack precision | Attack F1 | Mean TP / FP |
|---|---:|---:|---:|---:|---:|
| Original argmax / TabICL | 44.32432% | 28.20837% | 2.64756% | 4.90697% | 16.4 / 579.4 |
| Original argmax / selected tree | 76.21622% | 40.96884% | 3.46974% | 6.60845% | 28.2 / 841.5 |
| Source-normal 1% tail / TabICL | 3.78378% | 2.19572% | 1.13508% | 1.67448% | 1.4 / 45.1 |
| Source-normal 1% tail / selected tree | 14.32432% | 4.41091% | 5.43996% | 7.66016% | 5.3 / 90.6 |

Mean precision is the mean of per-seed precision, not the ratio of mean TP to mean predicted positives. Source calibration lowers target false alarms but discards most attacks. A 1% source operating target is **not a 1% guarantee on another environment**. Always predicting normal already achieves 98.23051% accuracy here, with zero attack recall. This is evidence against deployment readiness; it does not validate lateral-stage protection. Source: [complete transfer audit](../results/tabular_followup_v1/TRANSFER_SUMMARY.json), [author artifact](https://zenodo.org/records/16911636), [publication DOI](https://doi.org/10.1016/j.future.2025.108308).

## 2. Claims the proposed study can actually test

- **Flow-level lateral detection:** a flow labeled lateral movement is flagged as suspicious, regardless of the predicted attack stage. This is the appropriate primary protection measure for this proposal.
- **Exact stage classification:** the predicted stage equals the dataset's lateral label. Report this separately; detecting a lateral flow as reconnaissance still counts only for the first measure.
- **Actor attribution:** identifying the responsible APT group. These experiments do not establish this.
- **Early warning:** detection before a specified later action, using only information already available. Completed-flow features and random flow partitions do not establish this.
- **Resistance to missing or delayed logs:** also untested in this batch. Adding such a claim would require separately frozen degradation experiments.

Current SCVIC preparation removes identifiers, IPs, ports, timestamps and all Idle statistics, then deduplicates the final feature view and uses stratified feature-group partitions. This prevents exact predictor duplicates crossing partitions; **it does not establish campaign, host, chronological or collection independence**. The now-exposed SCVIC results are development evidence for selecting the new question.

## 3. Recommended dataset roles

| Dataset | Realistic role | Evidence and remaining qualification |
|---|---|---|
| **SCVIC-APT-2021, currently prepared author training data** | Development, ablations and matched label-budget comparisons | Already exposed. The author test artifact remains unqualified locally. Even an acquired author test needs collection/group checks before an independence claim. See [E0 qualification](../tabular_batch/E0_DATASET_GATE.md). |
| **Unraveled (2023), local author-matching data** | Practical replication on another dataset, with exposure disclosed | The existing byte audit found 173 CSVs in 31 capture directories, 6,877,157 rows, including 27,445 lateral rows. All 173 files appeared in prior GML work. This is **not an untouched confirmation set**. Label parsing and grouping still need qualification. |
| **DEDALE, published online May 2026** | Best candidate for a fresh, stage-aware flow confirmation, conditional on qualification | Author documentation provides Zeek/CICFlowMeter archives, flow-level labels and tactics. Exact accessible archive sizes, label joins, lateral support and feature compatibility are not yet verified. No data were acquired for this note. |
| **Sandworm artifact (2025; paper 2026)** | Preserve the completed negative binary-transfer stress test | Already evaluated; one capture, 37 attack flows, procedure labels, no exfiltration. It cannot become a new independent lateral confirmation by renaming its labels. |
| **LMD-2023** | Reserve for a separately scoped host-log replication | Sysmon modality differs from flow tables. Its paper describes EDR-rule-derived labels with manual verification; independent event truth and label-feature circularity require scrutiny. Not a drop-in independent flow benchmark. |

### Unraveled: available, but do not erase prior exposure

The peer-reviewed dataset paper describes a cloud testbed, host/network logs and six weeks of emulated employee activity. [Myneni et al. (2023)](https://doi.org/10.1016/j.comnet.2023.109688); [author repository](https://gitlab.com/asu22/unraveled).

Our [existing qualification receipt](../tabular_followup/UNRAVELED_QUALIFICATION.json) binds local files to author commit `d2ea90055d82fa448ab20588a13e3ec8bfd74816` and records the author's GPL-3.0 data notice. Its counts are **raw**, before deduplication and partition qualification. There are 1,493 rows with unresolved numeric stage strings. Quarantine these until their source meaning is established; do not invent mappings. Use full normal traffic, not the earlier cache's benign subsample. NFStream predictors need their own adapter; keep Activity, Stage, DefenderResponse and Signature out of features. Overlapping captures/interfaces must remain in the same evaluation block. Predefine a grouped partition and record that the dataset was previously used.

### DEDALE: the best fresh candidate has concrete gates

Lanvin and Majorczyk's paper describes one month: two benign weeks, an eight-day APT campaign, then six benign days. It was published online **1 May 2026** in the ESORICS 2025 workshop proceedings. This is one campaign, not many independent APT incidents. [Paper](https://doi.org/10.1007/978-3-032-16092-8_1).

The [author download documentation](https://dedale.inria.fr/download.html) offers precomputed Zeek and CICFlowMeter archives. It explicitly attaches labels and ATT&CK tactics/techniques to Zeek `conn.log`: 0 benign, 1 attack, 2 attack-related but not inherently malicious. Labels use execution times, addresses and sometimes ports; scripts are public. It recommends the first two weeks for training/calibration and the last two for testing. **A correct labeled-CICFlowMeter join is not yet verified.** The page permits reuse with citation; archive access, version and exact terms must be recorded at acquisition. [Artifact DOI](https://doi.org/10.57745/Y5JLDG); [author labeling code](https://gitlab.inria.fr/mlanvin/dedale_labeling).

Proposed acquisition and qualification sequence, before any target outcomes:

1. **Inventory only first.** Resolve the versioned artifact, rights, file IDs, byte sizes and checksums. Choose the required flow and labeling archives; do not download the multi-terabyte PCAP corpus. A public page is not proof that the needed archive is accessible.
2. **Trace labels to executed actions.** Count lateral tactics/techniques, normal periods and uncertain/attack-related records by day, host pair, execution and capture interface. Verify actual lateral support; a tactic column alone is insufficient. Keep class 2 separate from confirmed normal.
3. **Resolve flow correspondence.** Check Zeek-to-CICFlowMeter joins for direction, time zones, exporter timeouts, repeated keys and ambiguous matches. Require a documented rule and measured join/conflict rates. If no reliable join exists, use a Zeek feature protocol across both source and target or reject this transfer design.
4. **Check feature meaning, units and availability.** Matching names are insufficient. If a shared source/target feature view changes, refit every compared model on source data under a new frozen protocol before seeing target scores. Do not silently coerce the existing 73-feature model. Retain identity and execution metadata only for grouping/audit, not predictors.
5. **Lock independent blocks and denominators.** Group the same communications across interfaces; keep repeated execution blocks together. Preserve natural benign prevalence and report flow counts plus independent execution counts. Never treat thousands of dependent flows as thousands of attacks for uncertainty estimates.
6. **Specify the adaptation regime.** Source-only transfer and calibration using the target's first two benign weeks answer different questions. Those weeks cannot supply supervised lateral training examples: use a qualified external attack source, or separately justify a grouped attack split that changes the author's temporal benchmark. A benign-only adaptation arm is feasible in principle, but must disclose its target label cost and apply identically to controls. Never calibrate with the final two weeks or their attack labels in the temporal confirmation design.
7. **Freeze the comparison before outcomes.** Fix label budgets, comparator selection, alarm budget, lateral protection margin, feature handling and final evaluation blocks. Determine whether independent execution counts can support the intended uncertainty or noninferiority claim. If not, report a descriptive external check with counts; do not manufacture statistical power from fitting seeds.

**Go:** lawful usable flow artifacts, auditable lateral-event linkage, enough benign evaluation exposure, a valid feature adapter, and a locked evaluation split. **No-go for independent confirmation:** missing/ambiguous lateral truth, unresolved leakage, no benign background, inaccessible artifacts or inadequate independent executions for the claimed inference. In that case retain SCVIC development and disclosed Unraveled replication, and state that confirmation is pending. DSRL's synthetic derivative data and an unqualified S-DAPT release do not fix this gap.

LMD remains a reserve because its [primary paper, section 3.4](https://doi.org/10.1007/s10207-023-00725-8) assigns Normal/EoRS/EoHT using an EDR policy, followed by manual verification. This may test reproduction of those rules rather than independently established malicious events. Resolve that issue before using it as confirmatory truth.

## 4. Read-only audit receipt

This check recomputed macro-F1 from **all 110 saved SCVIC confusion matrices**, verified training-CV tree selections, derived the lateral binary/stage distinctions above, and recomputed the checker's minimum-stage deltas from its ten rows. It independently recomputed binary metrics from counts and verified aggregate means for **20 primary and 20 source-threshold Sandworm records**. No models, predictions or thresholds were changed. Existing independent audits report PASS; their scientific conclusions include the negative results above.

All six public artifact hashes matched [PUBLICATION.json](../results/tabular_followup_v1/PUBLICATION.json). The following full SHA-256 values identify the evidence used:

| Aggregate | SHA-256 |
|---|---|
| E1_ANALYSIS.json | `d4e81bcb0e53f9b072e1b608f787bd64db80e575d53b26b85433653391fc7cca` |
| COMPARISONS.json | `53215361720d45c50decc2f6f7d1523239c9ecdcb9fda0703c7445b1851f4076` |
| GATE_AGGREGATE.json | `89da5dbf5a2bd6d17e85cc0d3fef073f15e8304a2ab73d212c6d33ba35176524` |
| GATE_AUDIT.json | `d12dc22dc16470ba401eda5e68acedfd1db4c674948f72de93fa629f5f1b8bea` |
| TRANSFER_SUMMARY.json | `2fc03977d7cda5025cc6967e35bcec59ff3b0e401b4e4ff0e72ffd3945047e99` |

Actual private prepared-data bytes were also rehashed against the public evidence bindings:

| Bound input | SHA-256 |
|---|---|
| SCVIC prepared DATA.npz | `8e8a7474d4db03b78977a3c6a48be083d60d7648dd7548788037db721e80e565` |
| SCVIC prepared MANIFEST.json | `772edbce9548a1dc87a0e9dd835f9002dfd5a2bb7b3cc37de212d7b3c43791e3` |
| Sandworm prepared DATA.npz | `3b3779f4d0b9c77841dddaf51598447b75f09569da19d6bc5ddd5f23d5a1e00a` |
| Sandworm prepared MANIFEST.json | `debacd905ea707cd198854c4192e27492ddf0e89279f240f23ff98736ad144f2` |
| Original E1 protocol | `9d4c69f9ab8af48dae44aae6c237a25cedc56a1f50eff819513fa2e9beb7c687` |
| Stronger-control protocol | `8781a4a002aa0e1764a4413dd68f74e34fdbbf4b3c06acfe5144db7509a5c792` |
| Checker protocol | `03199d57cbb68c339a38926b8d338076695e0aace3045b90c4c578fbd6fd18cd` |
| Sandworm protocol | `ef42dd21680a2d0f9843ba439c3889a8e8804a183346c4d0adc2bacf01b5cfd8` |

The four protocol files and original runner/backend/requirements files matched their bound hashes on disk. Prediction hashes, model checkpoints and per-cell completion receipts remain in the linked audited aggregates. This supplemental check verifies the saved evidence chain; it is not a fresh independent collection or a re-execution of the experiments. Only this document was created; no datasets were downloaded or models run.
