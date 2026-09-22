# Dataset review: host context and earlier activity for movement versus exfiltration

**Reviewed September 22, 2026.** This is a primary-source and artifact-metadata review, not a model experiment or a human label audit. The question is whether information available about a host and its earlier activity improves recognition of author-labeled lateral movement and exfiltration. A large number of packets is not a large number of independent attacks.

## Recommendation

**Do not select a replacement from its title or advertised ATT&CK coverage alone.** This bounded review did not qualify three new, immediately usable datasets that simultaneously provide benign background, host/time information, observable labels for both requested stages, and multiple independent executions of both stages.

The three strongest additional qualification options are below. Of these, **Comprehensive APTs Dataset is the cheapest next artifact inspection**, while **corrected OpTC has the clearest directly verified movement-to-exfiltration narrative**. Neither is yet a qualified principal dataset for a repeated-execution statistical comparison. CICAPT-IIoT is a useful additional environment, but its small single-campaign stage support does not fix the independent-execution problem.

UNRAVELED remains a feasible local development source, subject to the substantial sensor and campaign limitations in [VALIDITY.md](VALIDITY.md). It is a different dataset from SCVIC, but it was already used in the original GML work and cannot be described as untouched external confirmation. The separate five-campaign `skrghosh/apt-dataset` acquisition is being investigated by the parent task; this note makes no qualification claim about its uninspected bytes.

## Three additional options, ranked by practical next action

| Dataset and literature status | Access and size | What is directly established | What remains unresolved |
|---|---|---|---|
| **1. Comprehensive Advanced Persistent Threats Dataset (2025)**. Peer-reviewed *IEEE Networking Letters* paper, [DOI](https://doi.org/10.1109/LNET.2025.3551989). | [Author repository](https://github.com/AbSamad99/APTsDataset), CC-BY 4.0. Pinned tree `cb74048ea76b286f9c63efcbd8e795c3de7f7543`: **24 log archives, 7,910,924 bytes**; excludes the separate 41,841-byte ability archive. | Authors describe 24 Windows/Linux emulations inspired by 12 profiles. Direct inspection of all 24 campaign READMEs finds both tactic declarations in APT28/Campaign 1 and APT41/Campaign 1. | These are ability declarations, not observed successful event counts. Benign truth, identifiable execution boundaries, timestamps/host joins, actual stage support, and inconsistent tactic mappings need checking. No principal-model recommendation yet. |
| **2. Corrected DARPA OpTC (2026 artifact; 2025 correction paper; 2019 activity)**. [Correction paper](https://doi.org/10.1109/ACSACW69556.2025.00064). | [Corrected artifact](https://doi.org/10.57745/UXCWOC), CC-BY 4.0 in artifact terms; [correction code](https://gitlab.inria.fr/fmajorcz/a_new_hope_for_darpa_optc). Existing author-API receipt: **939,321,857,639 bytes**, ten daily TARs plus README. Relevant September 24 TAR: **111,941,212,160 bytes**. | [Original author release](https://github.com/FiveDirections/OpTC-data) contains continuous benign activity, timestamped host/network events and red-team ground truth. Report pp. 4–6 explicitly documents lateral movement, RDP hops and two subsequent exports on September 24. | Three red-team days are not three verified exfiltration campaigns. The two exports are linked activities in one exercise. Event-level stage joins and correction/label versions need qualification. Storage and parsing costs are substantial. |
| **3. CICAPT-IIoT2024 (peer-reviewed proceedings published 2026)**. [MobiQuitous 2024 chapter, online January 2, 2026](https://doi.org/10.1007/978-3-032-10554-7_7). | [UNB dataset page](https://www.unb.ca/cic/datasets/iiot-dataset-2024.html); official download redirects to a [registration form](https://cicresearch.ca/IOTDataset/CICAPT-IIoT-Dataset/). Approximately **10 GB**, as reported by authors; exact downloadable bytes/license not verified here. | Host roles, event times, network/provenance data and Caldera attack information. [Author preprint Table 4](https://arxiv.org/html/2407.11278v1) reports **22 exfiltration and 10 lateral provenance nodes**, plus **42 and 14 network packets**, respectively. | Four benign days followed by one three-day APT29-inspired campaign. These nodes/packets are not independent attacks. Current download route shows a form/server-error message; no access or successful byte download is asserted. |

### Why option 1 needs more than a file download

The author [Logstash configuration](https://github.com/AbSamad99/APTsDataset/blob/main/ELK/logstash.conf) creates tactic labels from command/path matches. A detector using those same strings can reproduce the annotation rule. Remove annotation fields, and distinguish independent execution evidence from rule-proxy labels.

The [APT41 Campaign 1 definition](https://github.com/AbSamad99/APTsDataset/blob/main/APT41/Campaign%201/Readme.md) calls a key-search-script ability T1021.004/lateral movement. Its displayed command does not itself establish a remote login. [MITRE T1552.004](https://attack.mitre.org/techniques/T1552/004/) categorizes private-key search under Credential Access. Conversely, [APT28 Campaign 1](https://github.com/AbSamad99/APTsDataset/blob/main/APT28/Campaign%201/Readme.md) includes a remote SSH command. Success, telemetry and labels must still be joined. **Do not count 24 campaigns as 24 executions of both target stages.**

### Why option 2 is an external case, not a large sample of incidents

The [original red-team report](https://github.com/FiveDirections/OpTC-data/blob/master/OpTCRedTeamGroundTruth.pdf) identifies a September 24 export at 13:44:34, an intervening RDP chain, and a second export at 15:04:14. This is unusually concrete evidence for the requested context question. These related events can support an external case study; they do not support a broad independent-campaign success rate. The smallest corrected archive is September 16, **13,437,603,840 bytes**; its small size does not make it the appropriate attack-day sample.

## Important exclusions and reservations

### Windows-APT2025: exfiltration was simulated but is absent from released telemetry

The peer-reviewed [paper](https://doi.org/10.1016/j.dib.2026.112569), checked through [primary full-text XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12950481/fullTextXML), is explicit: Credential Access and Exfiltration did not produce observable mapped events under the pinned collection configuration. Table 7 contains **4,884 lateral-movement events** and no exfiltration category. The introductory list of intended tactics does not override that limitation.

The paper reports three Windows agents, October 28–December 22, 2024 collection, 36 scenarios, ten validation repetitions per scenario, and 19 CSV files; the combined log is approximately 242 MB. These statements do not establish 360 separately identifiable released executions. The [Mendeley v3 artifact](https://data.mendeley.com/datasets/b8fmtzvpy8/3) is CC-BY 4.0; the API request returned 403 during this review. **Exclude it from direct movement-versus-exfiltration supervised evaluation.** It remains relevant to a visibility-failure study.

### UWF releases: inspect the actual variant, not the family name

The [UWF-ZeekData24 paper](https://doi.org/10.3390/data10050059) is peer reviewed and the [official dataset site](https://datasets.uwf.edu/) provides public data. Direct directory inspection establishes the following narrower facts:

| Official CSV directory | Relevant released class-folder observation | Decision for this question |
|---|---|---|
| [UWF-ZeekData24](https://datasets.uwf.edu/data/UWF-ZeekData24/csv/) | Exfiltration and Benign exist; **no Lateral_Movement folder** among eight class folders. | Do not call it a two-target-stage benchmark without additional released labels. |
| [UWF-ZeekDataFall22](https://datasets.uwf.edu/data/UWF-ZeekDataFall22/csv/) | Lateral_Movement and Benign exist; **no Exfiltration folder**. | Same exclusion. |
| [UWF-ZeekDataFall24-2](https://datasets.uwf.edu/data/UWF-ZeekDataFall24-2/csv/) | Lateral_Movement and Benign exist; no Exfiltration folder. | Same exclusion. |
| [UWF-ZeekDataSum25-1](https://datasets.uwf.edu/data/UWF-ZeekDataSum25-1/csv/) | Lateral_Movement and Benign exist; no Exfiltration folder. | Same exclusion. |
| [UWF-ZeekDataSum25-2](https://datasets.uwf.edu/data/UWF-ZeekDataSum25-2/csv/) | Benign, Discovery and Reconnaissance folders only. | Exclude. |

Folder absence is an artifact-layout observation, not proof that no underlying packet ever involved that behavior. Combining differently labeled releases could make the collection environment predict the class. It would require its own domain-confounding controls and would not create within-execution progression evidence. The newly listed UWF-HostData25 was discovered, but this review did not qualify its stage counts or corresponding peer-reviewed description.

### AIT-LDS/AIT-ADS: good repeated testbeds, insufficient verified movement target here

[AIT-LDS v2.1](https://zenodo.org/records/19483937) was released April 9, 2026, using eight 2022 testbeds. It has benign background, host inventory, timestamps and explicit attack-step labels; public per-testbed archives include smaller no-PCAP options. Exfiltration is documented, but this review did not establish an author-labeled cross-host lateral-movement class suitable for the requested contrast. Moreover, the [author environment README](https://github.com/ait-aecid/kyoushi-environment) says the DNS exfiltration process is already running at simulation start. It must not be presented as the final consequence of the separately staged attack chain. AIT-ADS is a derived alert view, not an independent dataset. Reserve for different step/context questions until exact movement joins qualify.

### New 2026 multi-source log preprint: promising coverage, unqualified availability and timing

[Niloy et al. (2026)](https://arxiv.org/abs/2606.18190) report 70 attack and 800 benign 20-minute sessions, approximately 2.3 million events, 21% lateral-movement session coverage and 100% exfiltration coverage. The [full text](https://arxiv.org/html/2606.18190v1) describes Windows host/network/browser data with per-event ATT&CK labels. This is a **preprint**, not a verified peer-reviewed publication.

No usable author dataset-download link or byte size was established in this review. Its scripted movement at minute 10 and exfiltration at minute 15 make session-relative time a serious shortcut; internal-IP masking may also affect host-role joins. Do not infer the exact count of lateral sessions from a rounded percentage. Keep it as a future qualification candidate rather than claim it is runnable now.

### LMD2023, LANL, DARPA TC and eCAR

[LMD2023](https://github.com/ChristosSmiliotopoulos/Lateral-Movement-Dataset--LMD_Collections) and [LANL's public collections](https://csr.lanl.gov/data/) are relevant to lateral behavior, but this review did not verify matched exfiltration stage ground truth for the proposed task. LANL authentication red-team labels must not be reinterpreted as exfiltration. eCAR is OpTC's event representation, not a new independent dataset. DARPA TC contains multiple engagements, but engagement-specific telemetry and ground truth still need an explicit two-stage qualification; no blanket inclusion is justified here.

## What UNRAVELED can actually contribute

The [author README](https://gitlab.com/asu22/unraveled/-/blob/master/README.md) describes one sustained APT alongside two less-skilled attack scenarios, six weeks of traffic, host logs, inventory and network-flow stage labels. Its APT narrative includes a technical-support-to-database-administrator progression and later data extraction. This makes the scientific question meaningful, but **31 capture directories are not 31 independent APT executions**.

The local [qualification receipt](../tabular_followup/UNRAVELED_QUALIFICATION.json) records 173 CSVs, **3,723,532,930 bytes**, 6,877,157 raw rows, **27,445 lateral** and **7,522 exfiltration** rows. Those are observations before duplicate/conflict qualification. All files appeared in earlier GML work. The new [validity review](VALIDITY.md) finds sensor-stage association and mirrored observations; literal sensor, host or subnet identity could improve scores without learning transferable behavior. Use it only for a disclosed development study with chronological blocks, causal history, role-only controls and sensor/conflict sensitivity. Its GNU/GPL license and existing local source provenance are recorded in the prior qualification.

## Minimum evidence needed before a new principal experiment

These are proposed qualification checks, not post-result success rules:

1. **Observable target truth.** Count successful, timestamped lateral and exfiltration events by execution. Distinguish a scenario intending exfiltration, a command attempting it, a detector tag and an observed transfer. Preserve unknown/failed outcomes.
2. **Independent units.** Identify acquisition/execution IDs, repeated templates, shared hosts and reset boundaries. Hold out executions or environments, not random rows. Report both row counts and execution counts for each stage.
3. **Benign comparison.** Verify what the source calls benign, whether normal activity overlaps attacks, and whether background contains realistic administrative connections and large legitimate transfers. Untagged rule output alone is not independently certified benign behavior.
4. **Permitted context.** Build coarse roles from deployment inventory, not labels or known victim identities. Compute history only from completed, earlier observable events; use one explicit state policy for continuation or reset. Never include true previous stages, attack schedules, full-session totals or future-derived host roles.
5. **Shortcut controls.** Keep sensor/filename/absolute time/host identity out of the primary estimator. Include current-event-only, role-only, history-only, combined and causal wrong-host-context controls. Compare within source/destination role pairs and sensor views where supported.
6. **Stage costs.** Measure exfiltration AP and exact-stage precision/recall/F1, movement-to-exfil and exfil-to-movement errors, and false stage alerts on normal and other attacks. Report binary any-attack detection separately. Keep the full evaluation prevalence or disclose inclusion weights.

**Narrow defensible result, if it works:** prior, legitimately available host context improves held-out-execution stage recognition under a specified telemetry and label definition. The experiment would not establish attacker identity, a new graph-learning algorithm, universally earlier warning, or independence from environment shortcuts merely by increasing pooled F1.

## References

Elam, M., Mink, D., Bagui, S. S., Plenkers, R., & Bagui, S. C. (2025). Introducing UWF-ZeekData24: An enterprise MITRE ATT&CK labeled network attack traffic dataset for machine learning/AI. *Data, 10*(5), 59. https://doi.org/10.3390/data10050059

Ghiasvand, E., Ray, S., Iqbal, S., Dadkhah, S., & Ghorbani, A. A. (2026). Resilience against APTs: A provenance-based IIoT dataset for cybersecurity research. In A. Soylu, F. Liu, K. Mitra, Y. Zhang, & T.-M. Grønli (Eds.), *Mobile and ubiquitous systems: Computing, networking and services* (LNICST Vol. 634, pp. 121–144). Springer. https://doi.org/10.1007/978-3-032-10554-7_7

Ghiasvand, E., Ray, S., Iqbal, S., Dadkhah, S., & Ghorbani, A. A. (2024). *CICAPT-IIoT: A provenance-based APT attack dataset for IIoT environment* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2407.11278

Landauer, M., Skopik, F., & Wurzenberger, M. (2024). Introducing a new alert data set for multi-step attack analysis. *Proceedings of the 17th Cyber Security Experimentation and Test Workshop* (pp. 41–53). https://doi.org/10.1145/3675741.3675748

Majorczyk, F., Pilastre, B., & Dijoud, F. (2025). A new hope for DARPA OpTC. *2025 Annual Computer Security Applications Conference Workshops (ACSAC Workshops)* (pp. 551–561). https://doi.org/10.1109/ACSACW69556.2025.00064

Mozaffari, M., Yazdinejad, A., & Dehghantanha, A. (2026). Windows-APT 2025: A dataset for APT-inspired attack scenarios on Windows systems. *Data in Brief, 65*, 112569. https://doi.org/10.1016/j.dib.2026.112569

Myneni, S., Jha, K., Sabur, A., Agrawal, G., Deng, Y., Chowdhary, A., & Huang, D. (2023). Unraveled—A semi-synthetic dataset for Advanced Persistent Threats. *Computer Networks, 227*, 109688. https://doi.org/10.1016/j.comnet.2023.109688

Niloy, A. A., Ryan, A., Rafi, I. H., Erfan, M., & Rahman, M. R. (2026). *Multi-source cybersecurity logs: An ATT&CK-labeled dataset and SLM evaluation* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2606.18190

Syed, A., Nour, B., Pourzandi, M., Assi, C., & Debbabi, M. (2025). Comprehensive advanced persistent threats dataset. *IEEE Networking Letters, 7*, 150–154. https://doi.org/10.1109/LNET.2025.3551989

## Review provenance and limits

Primary pages, author README files, the OpTC red-team PDF and Windows-APT full-text XML were read on the review date. Existing local qualification receipts supplied explicitly identified local row/file/byte counts and corrected-OpTC archive sizes. The pinned Comprehensive APT tree was recounted; all 24 campaign READMEs were fetched directly for tactic-declaration checks. A 4,845-byte author archive was fetched into memory, but in-memory 7z extraction failed; no CSV row count or successful archive-content inspection is claimed. No new models were fitted, no authors were contacted, and no large dataset was downloaded by this subtask.

This review does not certify label correctness or exhaust all possible public datasets. Its strongest conclusion is operational: **qualify actual two-stage observations, context availability and independent executions before spending compute on a replacement benchmark.**
