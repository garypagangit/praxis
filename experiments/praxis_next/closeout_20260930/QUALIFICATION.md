# Replication and literature closeout

Checked September 30, 2026. Qualification is complete for this bounded review. **PX-091 exact replication remains blocked; novelty is unconfirmed.** This does not assert that no suitable dataset exists anywhere.

## Independent data

Exact replication requires native benign/movement/exfiltration targets, an explicit other-attack category, independent execution identity, qualified timing and both evidence groups. Changing the task must be declared before evaluation.

| Source | What is available | Remaining requirement or exclusion |
|---|---|---|
| SCVIC-APT-2021 | Local training CSV, 259,120 rows; six native classes | Mixed 1970/2015 timestamps; missing author-supported execution/clock mapping and native holdout. Author GitHub API still returns 404. DOI metadata has no direct content URL. |
| DAPT | Ten acquired CSVs, 86,691 rows | Fifteen exfiltration rows; class/day support prevents an all-native-class single chronological cutoff. No new independent execution established. |
| DSRL | Synthetic DAPT-derived attacks with reused benign rows | Does not provide independent recorded attacks. |
| S-DAPT | Public manuscript record | Withdrawn April 1, 2026 for analysis errors affecting conclusions; no qualified acquired release. |
| AIT | Existing execution-separated validation | Adapted three-class, one-evidence task already completed; does not meet unchanged four-class/two-evidence replication. |
| CAM-LDS / CasinoLimit | Existing PX-083 transfer evaluation | T1105 task and annotated-technique negatives do not supply the required movement/exfiltration/verified-benign task. |
| ProvICS | Previously acquired pinned physical-data subset | No qualifying exfiltration annotations or full provenance evidence group; scripts and failed actions cannot substitute for observed labeled events. |
| Windows-APT2025 | Official v4 description now accessible; 36 emulated scenarios advertised | File metadata requests return HTTP 403. No row-level schema, native labels, benign coverage, clocks or evidence pairing verified. A promising source remains unqualified. |

Fresh request statuses are in [SOURCE_CHECKS.json](SOURCE_CHECKS.json). The accessible [Windows-APT v4 landing page](https://data.mendeley.com/datasets/b8fmtzvpy8/4) describes a July 3, 2026 release. Public API access failed; this is an access limitation, not evidence that the data lack the required fields. No access challenge was bypassed. The [S-DAPT arXiv record](https://arxiv.org/abs/2601.06690v2) explicitly records withdrawal.

Local findings retain their original evidence trails: [D1 qualification](../d1_benchmark_audit/DATASET_QUALIFICATION.md), [execution validation](../campaign_validation_20260928/README.md), [data qualification](../data_qualification/README.md), and [PX-083](../px083_policy_transfer/README.md). Existing adapted evaluations are not relabeled as new exact replications.

To unblock PX-091, acquire a source-supported release and verify class mapping, execution IDs, physical time and evidence pairing on actual bytes; then freeze an execution-separated protocol. More compute alone does not resolve these requirements. No additional model fitting or AWS allocation is justified for PX-091 until those checks pass.

## Published foundation and overlap

| Primary source | Established overlap | Consequence for this praxis |
|---|---|---|
| [Conformal Risk Control, v4](https://arxiv.org/html/2208.02814v4) | Calibration of bounded monotone risks, including false-negative risks | Stage-conditioned rank calibration is an application of established machinery; do not claim a new theorem or a realized deployment bound. |
| [Selective Conformal Risk Control, v1](https://arxiv.org/html/2512.12844v1) | Selective acceptance plus calibrated risk, with specific selector corrections | PX-088 uses independently split selection and risk calibration. It is an adaptation, not an exact SCRC-I/T reproduction or a new selective-risk method. |
| [LightGBM monotone constraints](https://lightgbm.readthedocs.io/en/stable/Parameters.html#monotone_constraints) | Increasing/decreasing feature constraints in tree models | PX-090 tests expert-score semantics. Monotonicity itself is established and does not imply warning retention. |
| [CALIBURN record, now retitled, v3](https://arxiv.org/abs/2605.24696v3) | Current work audits streaming evaluation assembly and scoring artifacts | Version history must be respected; earlier performance claims cannot serve as validated evidence for our proposed detector. |

**Material correction:** the September 14 CALIBURN revision changed its title to *Stream Assembly Is an Uncontrolled Treatment in Streaming Intrusion-Detection Benchmarks*. Its author reports that earlier versions described a scoring rule not implemented in code and contained tables without archived origins. The current work concerns evaluation assembly. Preserve the earlier proposal as historical overlap, but remove reliance on its earlier performance account. This correction does not establish novelty for our work.

The defensible contribution under development is the controlled measurement of warning destinations and workload under fixed evidence and time splits. Probability averaging, warning union, recalibration, selective review and monotone trees are established approaches. These experiments provide results and counterexamples, not proof that the research gap is unique. An independent replication and a precise comparison with the closest evaluation audits remain necessary before claiming a novel general result.
