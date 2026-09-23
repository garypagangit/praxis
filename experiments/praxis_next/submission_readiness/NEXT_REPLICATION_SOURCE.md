# Next independent replication source: bounded qualification decision

**Checked:** September 23, 2026.
**Scope:** Current author/repository metadata and the small Sandworm README. No new flow CSV, packet capture, log archive, model fit, external message, or authentication request was made.

## Decision

**Neither checked release is presently qualified for the complete movement/exfiltration-warning plus benign-workload replication.** This is a source-specific intake result, not a claim that no suitable dataset exists.

Sandworm is independently generated relative to UNRAVELED, but it is already exposed and evaluated in this project, has one execution, and has no native exfiltration flow class. CAM-LDS has multiple named executions and accessible network evidence, but its collection excludes simulated normal-user behavior. Treating its other attack techniques or idle system activity as representative benign traffic would change the research question.

**Best concrete next intake:** qualify the network evidence in the two CAM-LDS Scenario 2 runs against their exfiltration annotations, using the approximately 321 MB log/netflow archives before downloading their approximately 8.8 GB packet captures. This can establish an execution-linked attack-technique evaluation substrate. It is not yet a replication of the paper's benign-warning/FPR result. A GPU does not resolve the missing label/background contract.

## 1. Sandworm: obtainable, already examined, different target support

Primary publication: Iturbe, E., Dalamagkas, C., Radoglou-Grammatikis, P., Rios, E., & Toledo, N. (2026). A pattern-aware LSTM-based approach for APT detection leveraging a realistic dataset for critical infrastructure security. *Future Generation Computer Systems, 178*, Article 108308. [Publication](https://doi.org/10.1016/j.future.2025.108308); [author dataset page](https://pradoglougrammatikis.com/portfolio-items/apt-sandworm-dataset/).

The current [author Zenodo release](https://zenodo.org/records/16911636) is v1, dated August 20, 2025; its API still reports last modification August 21, 2025. It lists only these three artifacts:

| Actual author file | Exact bytes | Published MD5 |
|---|---:|---|
| SandwormAPT_flow_labelled.csv | 1,342,640 | fce7ee12fbf7b347f56275cbd8a08f7c |
| APT_Dataset_Readme.pdf | 525,281 | ecfe84f85a3773ea89d28366f1099b24 |
| SandwormAPT.pcap | 1,814,217,841 | bd5d20ab543180e2311c472586d425b1 |

Metadata and the README were anonymously accessible. The newly read README matches the published MD5. The [API](https://zenodo.org/api/records/16911636) says CC BY 4.0; the landing-page copyright field says CC BY-NC-ND 4.0. That previously documented discrepancy remains unresolved. Availability should not be described as permission to redistribute adapted data.

### Native labels, timing, and prior exposure

The [existing hash-bound project qualification](../../apt_benchmark/tabular_followup/HOLDOUT_QUALIFICATION.md) records the following author CSV counts. These counts are carried forward from that audit; the CSV was not downloaded or recounted in this metadata-only pass.

| Native procedure | Raw rows |
|---|---:|
| Normal | 2,096 |
| PHP_insecure_intrusion | 16 |
| smb_intrusion | 8 |
| rdp_intrusion | 7 |
| ssh_intrusion | 5 |
| remote_system_discovery | 1 |
| **Total** | **2,133** |

The earlier preparation retained 2,091 unique predictor rows, including 37 attack rows. It then completed binary transfer experiments; see the [prior audited result](../../apt_benchmark/results/tabular_followup_v1/TRANSFER_SUMMARY.json). Reusing those rows is disclosed development or secondary analysis, not a fresh holdout.

The README supplies these important semantics:

- **PDF page 6, printed page 5:** procedure labels come from correlating Caldera activity with visible network flows. SMB can describe shared-resource access or lateral movement; RDP/SSH labels describe unauthorized access attempts. They are not interchangeable with confirmed successful lateral compromise.
- **PDF page 10, printed page 9:** Timestamp denotes the first packet; Flow duration is in microseconds. An adapter can therefore propose an end-time calculation, subject to validating the actual field and clock interpretation.
- **PDF page 8, printed page 7:** the timeline lists T1041, keystroke-file upload, from **2025-02-18 11:16:51Z through 11:17:06Z**. The native flow-label list has no corresponding exfiltration category.
- One PCAP and one campaign timeline identify one execution. Packet/flow timestamps or host names do not create independent execution groups.

A timeline entry is useful for an annotation investigation. It does not establish which packet/flow carries the file, that the transfer succeeded, or that every contemporaneous flow is exfiltration. Re-labeling flows by time overlap alone would manufacture certainty.

**Eligibility:** useful as the already completed independent-source binary transfer check, or for a separately registered annotation-coverage study. Ineligible as an unchanged fresh exfiltration-warning replication. Missing evidence comprises source-linked exfiltration flow identity/outcome and additional independently recorded executions; a more powerful model cannot supply either.

## 2. CAM-LDS: concrete next intake, with a different current scope

Publication: Landauer, M., Hotwagner, W., Boenke, T., Skopik, F., & Wurzenberger, M. (2026). CAM-LDS: Cyber attack manifestations for automatic interpretation of system logs and security alerts. *International Journal of Information Security, 25*(5), Article 148. [Publisher](https://doi.org/10.1007/s10207-026-01318-x).

The current [log/netflow release](https://zenodo.org/records/18861762) and [PCAP release](https://zenodo.org/records/18701095) are public, with CC BY 4.0 in both APIs. Files represent named execution variants. Scenario 2 covers archive exfiltration; Scenario 3 covers movement. The authors explicitly state that normal-user behavior was not simulated. A complete file inventory, byte sizes, checksums and direct URLs are retained in [metadata](NEXT_REPLICATION_SOURCE_METADATA.json).

### Smallest relevant execution pair

| Author artifact | Exact bytes | Role |
|---|---:|---|
| scenario_2_cron.zip | 160,486,494 | Logs/netflow and attack execution record |
| scenario_2_rootkit.zip | 160,978,125 | Second variant's logs/netflow and execution record |
| scenario_2_cron_pcaps.zip | 3,781,246,514 | Optional packet-level linkage verification |
| scenario_2_rootkit_pcaps.zip | 5,035,956,936 | Optional packet-level linkage verification |

The two log archives total **321,464,619 bytes**; their paired PCAPs total **8,817,203,450 bytes**. Listed bytes establish download scope, not decompressed storage or memory needs. Archives were not downloaded in this task.

The [author repository](https://github.com/ait-aecid/attack-manifestations-interpretation) provides [attack_times.csv](https://raw.githubusercontent.com/ait-aecid/attack-manifestations-interpretation/main/attack_times.csv), [labels.json](https://github.com/ait-aecid/attack-manifestations-interpretation/blob/main/labels.json), extraction scripts, and scenario definitions. Timing metadata includes scenario, event identity, technique set, start and end. The author warns that technique/sequence exports can duplicate logs; per-step records and original run archives are preferable for counting. Repository code is GPL-3.0; dataset metadata separately says CC BY 4.0.

### Qualification contract before fitting

1. Bind each original archive and its native run/variant identity to its published checksum. Preserve prior project exposure: CAM-LDS logs and T1105 targets were already examined in [PX-083](../px083_policy_transfer/README.md). A new packet representation is not automatically an unseen campaign.
2. Inspect `attacker/logs/attackmate.json`, command output, and the original network records. Confirm recorded-time alignment and whether the exfiltration action completed. Retain absent, failed, ambiguous, and overlapping actions explicitly.
3. Join labels to network evidence using available endpoint/connection identities and time, not interval membership alone. Publish unmatched/ambiguous rates and native technique sets. Do not flatten overlapping techniques into one convenient stage without a declared rule.
4. Enumerate class support within actual executions. Keep complete runs together and disclose shared scenario recipes. Two variants are two recordings, not two independent organizations or an adequate population sample.
5. If successful, freeze a **technique-recognition/annotation-coverage** study. Its negatives remain other techniques or identified idle traffic. Do not report a normal-user false-positive rate from that target.
6. To replicate the complete paper claim, add **new independently recorded runs with deliberate legitimate background activity and verified movement/exfiltration outcomes**, all captured in the same environment. Merely mixing an unrelated benign corpus into CAM-LDS risks making source identity the classifier's shortcut.

The author [AttackBed environment](https://github.com/ait-testbed/attackbed) supplies a potential basis for such separately designed collection. This review did not deploy it or establish that its present workload configuration already satisfies the missing requirements. New collection would be a separate study, with frozen instrumentation, execution IDs and background workload, rather than an acquired ready-made benchmark result.

## 3. What is complete and what remains

**Complete:** current primary file inventories; exact byte/checksum metadata; fresh Sandworm README inspection; source publication links; identification of prior project exposure; an explicit next intake pair and its qualification rules.

**Not complete:** new archive acquisition, network-to-step ground-truth validation, benign workload collection, new execution generation, adapter qualification, or independent replication fitting. No such outcome is claimed.

This bounded review examined the prioritized Sandworm release and CAM-LDS alternative. It did not conduct an exhaustive search or revisit the four D1 source decisions. Its recommendation is to finish the evidence contract before compute allocation, while keeping the completed measurement manuscript's claims intact.
