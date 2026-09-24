# Dataset Provenance, Features, and Evaluation Support

## Why source qualification is part of the experiment

An APT dataset name does not establish an independent attack execution, a valid clock, or a label for successful movement or theft. This study therefore separates datasets used for completed predictions from artifacts inspected for possible extension. The qualification decisions below describe the inspected releases and the registered comparison, not the usefulness of each dataset for every research question. Source-status statements are inherited from the verified September 23, 2026 audit; this publication assembly performs no new source search or download.

| Dataset | Role in this paper | Inspected support | Interpretation boundary |
|---|---|---|---|
| UNRAVELED | Primary completed experiments | 382,229 prepared flows; eleven IT-sensor captures | One previously examined campaign; author stages |
| SCVIC-APT-2021 | Extension qualification | 259,120 rows; six native classes | Recorded timestamps do not establish physical chronology |
| DAPT2020 | Extension qualification | 86,691 rows; five native classes | No all-native-class single chronological cutoff under the stated rule |
| DSRL-APT-2023 | Extension qualification | 65,000 rows; five native classes | Synthetic attacks and reused benign rows derived from DAPT |
| S-DAPT-2026 | Source-access qualification | No qualified source bytes | No measured dataset count or model result |
| CasinoLimit | Secondary T1105 policy development | Evaluation: 920 targets, 17 T1105 positives | Annotation-onset proxies; negatives are other techniques |
| CAM-LDS | Secondary T1105 policy transfer | Evaluation: 4,209 targets, 100 T1105 positives | Labeled interval proxies; distinct decision unit |

## Primary corpus: UNRAVELED

UNRAVELED is the semi-synthetic APT corpus of Myneni et al. (2023), published in *Computer Networks*. The pinned author release is the [UNRAVELED repository](https://gitlab.com/asu22/unraveled), commit `d2ea90055d82fa448ab20588a13e3ec8bfd74816`. The upstream inventory records 173 network-flow files, 31 capture directories, and 6,877,157 rows. The completed experiments use a fixed subset of eleven complete locally available `net1013x` IT-sensor capture files, not all source traffic and not eleven independent attacks. Using a single sensor avoids indiscriminately pooling overlapping gateway/subnet observations. It does not establish complete visibility of the network.

The 382,229-row prepared artifact is bound by SHA-256 `b2a491474e722f4dabcd4c419c83a4a6b49f08dfc3bc059aa42ef2aaa4c3de14`. It was already examined in prior development. Captures 0–4 provide earlier fitting data, capture 5 is the original calibration partition, and captures 6–10 provide later evaluation. All history entries finish before the corresponding current flow begins. Current features describe completed flows, so the model decision is not an early forecast.

| Partition | Benign | Other attack stage | Movement label | Exfiltration label |
|---|---:|---:|---:|---:|
| Earlier fitting pool | 147,087 | 12,362 | 27 | 1,740 |
| Original calibration | 8,929 | 2,659 | 0 | 1,331 |
| Later evaluation | 192,193 | 12,424 | 35 | 3,442 |
| Fixed temporal anchor, a subset of later evaluation | 96,098 | 6,213 | 18 | 1,722 |

The original calibration partition contains no movement examples and cannot calibrate movement recall. The fixed temporal anchor totals 104,051 rows. The temporal study's conventional random comparison has a different 210,226-row population, including 191,515 benign, 15,095 other-stage, 34 movement, and 3,582 exfiltration labels. These denominators must not be substituted for the fixed-anchor denominators.

### Source parsing and target mapping

The upstream preparation found unquoted commas in descriptive DPI fields of the source CSVs. It recovered the four annotation fields from the right end of each row, preserving the stable numeric prefix and excluding the ambiguous text region. This correction preceded the studied fits. A fixed-position parser would have interpreted some descriptive values as spurious stages. The raw source files and prior frozen artifacts were not rewritten.

The models use a declared four-class target: Benign, OtherAttackStage, LateralMovement, and DataExfiltration. The mapping combines source Reconnaissance, Establish Foothold, and Cover up labels into OtherAttackStage; it does not claim that the source has only four native stages. In the selected eleven captures, the other-stage rows consist of foothold and cover-up annotations. The mapping and full native-source inventory remain in the upstream qualification artifacts.

For this sensor, the movement activity is **Remote System Discovery on one directed host pair**. Those labels do not establish successful remote login, compromise, or movement to a new host. The exfiltration class is also the author's stage annotation, not independently verified stolen-file receipt. Annotation fields, including Stage, Activity, DefenderResponse, and Signature, are prohibited as predictors. In particular, a DefenderResponse value of Benign is not the traffic's true benign label.

### Prepared feature groups

| Feature group | Actual representation | Availability and excluded information |
|---|---|---|
| Current completed flow | Numeric duration, packet/byte counts, packet-size and inter-arrival summaries, TCP flag counts; three destination-service indicators | Full-flow measurements; no literal host identities, absolute dates, capture names, or annotation columns |
| Coarse endpoint roles | Eight one-hot values: four source categories and four destination categories | Department, public services, private services, other address; derived from documented static topology |
| Earlier activity | Thirty-six summaries: nine state values × source/destination × five/thirty-minute windows | Only previously completed flows, ending strictly before current-flow start |
| Selector availability signals | Relative history age and declared availability indicators where included in the protocol | Observable signals; no true stage provided to the deployed selector |

The nine history values are logged completed-flow count, transmitted bytes, received bytes, distinct peers, initiated flows, remote-administration flows, internal-peer flows, whether the current peer appeared in the window, and whether the host had appeared previously. Numerical counts use the source's `log1p` transformation. Other address does not automatically mean public Internet, and coarse role is not a verified per-user or per-machine business function. These definitions come from the existing [feature preparation](../../../apt_benchmark/host_history_exfil/run.py) and [history implementation](../../../apt_benchmark/host_history_exfil/context.py).

The acquisition experiment treats precomputed role and history summaries as hypothetical information requests. A role lookup costs one simulated unit; history costs two. Delivery and failure schedules are shared across compared policies. This is a test of acquisition decisions under declared assumptions, not measurement of actual sensor costs or latency. Missing, stale, and wrong-host histories are explicit synthetic interventions.

### A real published aggregate example

No previously published individual feature-value row was found in the inspected public evidence. An individual flow is therefore not fabricated or presented as though it were observed. The documented schema above shows the actual prepared fields; the following example is an **actual aggregate evidence record**, with endpoint identities absent.

| Field in saved clean evaluation, seed 20260924 | Recorded value |
|---|---|
| Model arm | Current flow plus roles |
| Evaluation capture group | 6 |
| Total flow records | 70,451 |
| True-class counts: benign / other / movement / exfiltration | 62,400 / 5,780 / 18 / 2,253 |
| Movement label predictions: benign / other / movement / exfiltration | 3 / 0 / 15 / 0 |

This example is copied from the source aggregate in `PX080` and can be independently checked in [the bound source snapshot](source_snapshots/PX080_METRICS.json). It illustrates both the denominator and the distinction between exact-stage recognition and a missed warning. It contains no invented feature values or assertion that the eighteen labels represent eighteen independent intrusions.

## Extension artifacts and native stage support

![Native class support and source dependence](figures/fig07_native_support_and_lineage.png)

**Figure. Native class support in inspected extension releases.** Bars show measured rows in each source's native taxonomy, on a logarithmic scale. Counts describe the inspected files. S-DAPT has no bar because its dataset bytes were not qualified; unavailable is not equivalent to zero. DSRL's row count does not establish an independent replication of DAPT.

### SCVIC-APT-2021

Liu et al. (2022) published the benchmark in *IEEE Networking Letters*, with a separate [IEEE DataPort dataset record](https://doi.org/10.21227/g2z5-ep97). The inspected training CSV contains 254,836 NormalTraffic, 73 InitialCompromise, 833 Reconnaissance, 729 LateralMovement, 2,122 Pivoting, and 527 DataExfiltration rows. All six classes remain distinct in qualification.

A recorded-time ordering can be computed, and the necessary all-class start-time support interval is nonempty. Physical chronology remains unresolved: 220 benign rows parse to January 17, 1970; the other rows parse to October 21, 2015; timestamps mix minute and second resolution; and no qualified row-to-execution mapping or author-supported clock correction was found. A cached source page lists a separate test artifact, but its contents and independence were not qualified in the inspected workspace. These findings permit a carefully scoped random/grouped development question, not an unchanged deployment-valid temporal claim.

### DAPT2020

Myneni et al. (2020) describe DAPT2020 as a benchmark for advanced persistent threats. The inspected ten CSVs cover five capture dates and contain 63,712 benign, 11,909 reconnaissance, 8,604 foothold, 2,451 movement, and fifteen exfiltration labels. Ten files are collection units within an attack progression, not ten campaigns.

The necessary single-cutoff support test requires at least two earlier fitting rows and one later evaluation row for every native class. The cutoff must exceed each class's second-earliest start and be no later than every class's latest start. The resulting lower bound is July 19, 2019 at 16:38:37, imposed by exfiltration; the upper bound is July 17 at 19:24:55, imposed by reconnaissance. The interval is empty. Thus no single cutoff satisfies that stated all-class rule on these bytes. Completed-flow availability and duplicate controls can only make the rule more restrictive.

This is a precise support result, not a failed detector or a judgment that DAPT is unusable. Different questions, such as unknown-stage recognition or stage-duration/survival analysis, require different protocols. The benchmark can remain useful for those tasks without meeting this paper's closed-set chronological requirement.

### DSRL-APT-2023

Shadabfar et al. (2025) describe DSRL as a synthetic dataset. The inspected file has 10,000 benign, 14,366 reconnaissance, 22,968 foothold, 12,664 movement, and 5,002 exfiltration rows. The publisher paper's Section 5 states that the attack generation was trained on DAPT2020 and that the benign rows were sampled from DAPT. A generated timestamp is not evidence of an observed campaign clock, and the release has no qualified execution or generator-realization grouping. DSRL can support a declared synthetic-development question; it cannot serve as independent confirmation of its parent simply by being a different file.

### S-DAPT-2026

The inspected arXiv version of Tijjani et al. (2026) was withdrawn on April 1, 2026. The source audit did not acquire a corrected, qualified dataset or generator release. A later posting was noted, but corrected data access, source lineage, clock semantics, and dataset rights remained unverified. Consequently there is no measured row count, fitted result, or ROC-AUC for S-DAPT in this work. The finding is bounded to inspected sources; it is not proof that no usable artifact exists anywhere.

## Secondary technique datasets

CasinoLimit was published by Kilian et al. (2025) at RAID; CAM-LDS has a 2026 journal version by Landauer et al. Both supply additional log-based context for the secondary T1105 experiment, but neither changes the primary UNRAVELED estimand by being listed alongside it.

CasinoLimit selector development uses 1,494 clean-calibration targets, including 87 T1105 positives, across eighteen runs. Evaluation uses 920 targets with seventeen positives across eighteen runs. CAM-LDS evaluation uses 4,209 targets with 100 positives across eighteen runs from one held-out family. The small CAM-LDS calibration set of 68 targets/eight positives is not used to fit or tune the transferred selectors. The underlying source-specific classifiers remain unchanged.

CasinoLimit targets are annotation-onset proxies; CAM-LDS targets are labeled interval-state proxies. Negative targets are other author techniques, not verified benign activity. The project had already examined both datasets. Thus this supplement provides previously exposed score-policy transfer evidence, not an untouched independent replication of exfiltration detection, a common-unit pooled accuracy, or a legitimate-background false-positive rate.

## Source references and reproduction materials

Dataset citations and verified publication status are supplied in [REFERENCES.json](REFERENCES.json). Complete native counts appear in [native_class_counts.csv](tables/native_class_counts.csv); source qualification and exact cutoff bounds are preserved in the source snapshots. The [source manifest](SOURCE_MANIFEST.json) binds the publication inputs. Raw network/host traces and private row-linked predictions are not redistributed by this publication assembly.

The completed scope is therefore explicit: one primary flow-stage measurement campaign, two secondary technique datasets with a different target, and four documented extension-qualification decisions. More files, fitting seeds, or synthetic rows do not independently broaden the number of real attack executions represented by a result.
