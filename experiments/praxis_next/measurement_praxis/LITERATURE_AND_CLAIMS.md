# Literature positioning and claim audit

**Review date:** September 23, 2026.
**Manuscript:** *When Better APT Scores Hide Missed Attack Warnings*.
**Scope:** Targeted primary-source review for a measurement praxis; no new model fitting, protocol changes, or edits to frozen experiments.

## 1. Recommended thesis and contribution

**Thesis:** APT-stage model evaluation should expose how training composition and historical evidence change both stage recognition and retention of attack warnings, and should verify that the benchmark can support the intended chronological comparison.

The completed work contributes three concrete measurements and their inspection tools:

1. A fixed-anchor comparison in which training-pool composition changes while the classifier family, evaluation records, and class fitting counts remain fixed.
2. A paired analysis of exact-stage classification, attack-to-benign errors, and benign false alerts from saved predictions under declared historical-evidence interventions.
3. A source-specific audit of the labels, chronology, class support, and dependence of proposed APT-flow releases.

These are defensible applied contributions without inventing a detector or a metric. The numerical training-composition effect and warning-loss comparisons can be stated directly for the evaluated records. Broad deployment superiority, independent-campaign replication, and priority over all earlier measurement studies are different claims and are not established.

A useful gap statement is: **Existing research establishes temporal evaluation concerns, hierarchical error destinations, and APT-stage modelling; this study supplies controlled flow-level evidence about their interaction and an executable check of whether named releases support the proposed comparison.** This describes the evidence added here. It does not assert that an exhaustive literature search found no equivalent experiment.

## 2. Closest-work matrix

| Primary work | What it already covers | Relation to this manuscript |
|---|---|---|
| [Uddin et al., 2025](https://doi.org/10.1016/j.adhoc.2025.103982), with [2024 author manuscript](https://arxiv.org/html/2403.13013v1) | Ten classifiers and ten datasets; similar aggregate scores can accompany different attack-to-normal versus attack-type errors. Manuscript §§4.3.3–4.3.5 and Figures 6–14 expose corresponding counts and false-positive tradeoffs. | The error distinction and equivalent confusion-matrix accounting are prior art. Our contribution is the controlled temporal/evidence comparison and its measured outcomes, not discovery of these categories. The two versions are one study. |
| [Pendlebury et al., TESSERACT, 2019](https://www.usenix.org/conference/usenixsecurity19/presentation/pendlebury) | Spatial and temporal evaluation constraints in malware classification. | Chronological hygiene is established methodology. Included as foundational work outside the recent-literature window. |
| [Bilot et al., 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/bilot) | Shared evaluation of eight provenance detectors, simple-model controls, evaluation shortcomings, and attack-discovery-oriented measurement. SC2, printed pp. 7197–7198, discusses metric limitations and ADP. | Broad claims to originate critical APT benchmarking or attack-coverage measurement would overlap. ADP is not our stage-conditioned binary recall. |
| [Guerra et al., 2026, v3](https://arxiv.org/html/2608.01454v3) | Benchmark semantics, temporal leakage/calibration, and alerting versus process recovery; especially §§III-A/B, IV-A/B/H, and VII-C/D/E. | Closest broad evaluation precedent. Our narrower unit is the APT-flow record, with fixed-anchor composition and native-class cutoff support. Cite the available 2026 preprint; authors report NDSS 2027 acceptance. |
| [Ha Thanh, TAN-IDS, 2026](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0346801) | Shared NetFlow features and transfer comparisons; §4.2 specifies stratified splits. §5.6.1 excludes fine-grained multiclass/family discrimination and systematic feature ablation. | A concrete flow-level scope boundary that motivates stage-specific measurement. It is not evidence that deployment-oriented flow evaluation is absent. |
| [Othman et al., 2026](https://www.mdpi.com/2073-8994/18/9/1439) | DAPT2020 residual time-to-compromise and stage-duration/survival modelling; §§3.1, 4.5, and 7.3 describe campaign/session scope and limits. | Its temporal task differs from closed-set classification requiring all native classes on both sides of one cutoff. Our empty support interval does not invalidate its task; its task does not supply the missing support for ours. |
| [Iturbe et al., 2026](https://doi.org/10.1016/j.future.2025.108308) | Pattern-aware LSTM/BiLSTM analysis of emulated Sandworm traffic. The author release limits flow labels to network-visible procedures. | Sequence-based APT-flow recognition already exists. Network labels must not be interpreted as comprehensive host-action ground truth. |
| [Phan and Bauschert, StageFinder, 2026](https://arxiv.org/abs/2603.07560v2) | Temporal and graph-based provenance learning for APT-stage estimation. | Stage reasoning and temporal/structural fusion are existing approaches. The inspected version is a preprint with author-reported GLOBECOM 2026 acceptance. |
| [SANGL, 2026](https://www.nature.com/articles/s41598-026-42756-w) | Sequential/graph APT-stage modelling, including DAPT20 and UNRAVELED, with stage-transition measures. | Recent stage-oriented flow/graph comparisons must be acknowledged. This review neither reproduces nor independently validates its algorithm and split. |
| [Luengo Viñuela et al., 2026](https://doi.org/10.1111/exsy.70181) | Multi-dataset APT model comparisons, including SCVIC and DAPT; §4 and Tables 3–4. | Comparing models across these named datasets is already prior art. Published headline scores cannot substitute for matched comparisons on our rows and targets. |
| [Ibrahim et al., 2025](https://link.springer.com/article/10.1186/s40537-025-01272-w) | An LSTM/KNN/logistic-regression ensemble evaluated on UNRAVELED. | An ensemble on this corpus is not sufficient novelty. Its reported binary results are not a baseline reproduced by our four-class chronological experiments. |

The matrix establishes overlap and concrete distinctions. It does not establish that every listed method used the same records, labels, clock, or operating point. No comparison of published headline accuracy is treated as evidence that our models outperform those methods.

## 3. Dataset provenance and claim boundaries

| Source | Verified publication/release basis | What the present audit can claim |
|---|---|---|
| UNRAVELED | [Myneni et al., 2023](https://doi.org/10.1016/j.comnet.2023.109688); [author README](https://gitlab.com/asu22/unraveled/-/raw/master/README.md). Peer-reviewed semi-synthetic dataset. | The 382,229 prepared rows and eleven chosen captures describe this project's artifact. They are not whole-release counts. Native annotations support the declared classification targets, not independent proof of successful compromise or stolen-file receipt. |
| SCVIC-APT-2021 | [Liu et al., 2022 paper](https://doi.org/10.1109/LNET.2022.3185553); [dataset DOI](https://doi.org/10.21227/g2z5-ep97). Dataset registration year is 2022 despite its name. | Local file counts and timestamp anomalies can be reported. Article identity and a nonempty recorded-start support interval do not authenticate local bytes, resolve physical clocks, or establish execution IDs. |
| DAPT2020 | [Myneni et al., 2020 chapter](https://doi.org/10.1007/978-3-030-59621-7_8); [author CSV schema](https://gitlab.com/asu22/dapt2020/-/raw/main/csv/README.md). Timestamp is documented as flow start. | Our inspected release lacks the necessary all-native-class start-time support for the unchanged single-cut closed-set comparison. This is a task-specific finding, not a declaration that DAPT is unusable for survival, anomaly, unknown-stage, or other questions. |
| DSRL-APT-2023 | [Shadabfar et al., 2025](https://doi.org/10.22042/isecure.2025.214212), §5, printed p. 112. Attacks use DAPT-trained CTGAN/CopulaGAN; benign records are sampled from DAPT. | DSRL and DAPT do not constitute independent observed-campaign replications. Generated timestamps do not establish a physical event sequence. Synthetic studies remain possible when described as such. |
| S-DAPT-2026 | [Tijjani et al., withdrawn arXiv v2](https://arxiv.org/abs/2601.06690v2), withdrawn April 1, 2026. A later [SSRN listing](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6603942) exists. | No qualified source artifact was acquired. The accessible withdrawal remains material; the inaccessible later listing is not proof of a corrected dataset or of its absence. Neither listing supplies an experiment result. |

The [qualification audit](../d1_benchmark_audit/DATASET_QUALIFICATION.md) and [support-cutoff audit](../d1_benchmark_audit/SUPPORT_CUTOFF_AUDIT.md) are the sources for locally measured counts and eligibility decisions. Literature citations establish provenance and author descriptions; they do not replace these inspections. Four source-qualification outcomes are not four completed detector replications.

For DAPT, the strongest statement is an explicit necessary-condition result: if the maximum second-earliest native-class start exceeds the minimum latest native-class start, no one cutoff can provide two earlier fitting rows and one later evaluation row for every class under the stated inequalities. This rules out that design on those records even before stricter completion-time and duplicate controls. It does not establish a minimum statistically adequate sample size, nor invalidate other temporal designs.

## 4. Paired metrics: ordinary quantities with an operational use

For a true attack stage `s`, use the same evaluation rows, operating point, and denominator `N_s`. Let `C[s,j]` be its confusion-matrix counts and `b` the benign class:

- Exact-stage recall: `C[s,s] / N_s`.
- Warning recall: `1 - C[s,b] / N_s`.
- Missed-warning fraction: `C[s,b] / N_s`.
- Wrong-stage warning fraction: warning recall minus exact-stage recall.
- Benign false-positive rate: `sum(C[b,j] for j != b) / N_b`.

“Warning” means a non-benign model output. It does not mean an analyst saw an alert, investigated a case, or prevented harm. Warning recall is binary attack recall conditioned on the true stage. Its relationship to exact-stage recall follows algebraically; that relationship is not a new empirical discovery. The empirical result is that a specified intervention can improve macro-F1 while increasing attack-to-benign errors on the same records.

Always retain benign workload. Predicting attack everywhere obtains perfect warning recall at unacceptable false-positive cost. Equal maximum acquisition budgets are not equal realized expenditure; a shared numeric threshold is not equal workload. Zero-support stage metrics are unavailable, and abstention requires its own declared treatment.

## 5. Claim audit for the manuscript

### Claims the completed evidence supports

- A declared training-composition change increased the reported score on the fixed anchor, with architecture and class budgets controlled.
- Particular historical-evidence and acquisition comparisons produced measurable tradeoffs between stage recognition, warning retention, and benign false alerts.
- The source audit established concrete obstacles to the unchanged proposed comparison, including an empty necessary native-class cutoff interval for the inspected DAPT release.
- The accompanying protocols, predictions, aggregate tables, input hashes, and calculation checks make those results traceable subject to documented input access.

These statements need exact tables and denominators, not global hedges. They remain meaningful findings even though no new detector superiority is established.

### Corrections or limits that must remain explicit

1. **Prior art:** Uddin already distinguishes wrong-type predictions from attacks dismissed as normal. TESSERACT, Bilot, and Guerra already establish evaluation concerns. Do not call the paired accounting a new metric or the first such security observation.
2. **Temporal treatment:** Mixed training changes the available record distribution and temporal access. Historical features of later fitting records may include earlier anchor observations. Call it a controlled training-composition effect, not a pure causal estimate of future-label leakage.
3. **Analysis chronology:** Warning-loss reanalysis is retrospective. Freezing its computation prevents later changes but does not convert the already observed pattern into prospective confirmation.
4. **Experimental unit:** Fitting seeds repeat the same events; capture blocks come from a shared workflow. Do not multiply the number of attacks by the number of seeds or equate captures with independent campaigns.
5. **Construct:** In the inspected UNRAVELED sensor, the movement target denotes discovery-related author annotations. Correct labels do not independently demonstrate successful lateral compromise. Completed-flow features do not establish early warning before a flow completes or prediction of future exfiltration.
6. **Intervention realism:** Missing, delayed, and wrong-host history are declared simulated conditions. They do not estimate real sensor-failure prevalence, live collection costs, or AWS savings.
7. **Computational versus human audit:** Hashes and independent arithmetic checks establish specified consistency, not correctness of all source annotations. “Qualified” must name the requirement satisfied.
8. **Benchmark support:** An empty single-cut class-support interval is a definite result for that design. It must not become a general claim that temporal APT work is impossible; Othman provides a relevant different temporal task.
9. **Proposal versus requirement:** The paired report is an evidence-backed proposed evaluation practice. It is not a literature-mandated 90% criterion, established industry standard, or legal obligation.
10. **Completion versus acceptance:** A complete manuscript and evidence package can be delivered now. Publication acceptance, universal novelty, external campaign validation, or a solved deployment problem are not completed outcomes.

The earlier manuscript, [When Historical Context Helps and Hurts](../paper/manuscript.md), largely preserves the necessary experimental limits. Its method-selection framing should not impose a new-algorithm win as a prerequisite for a measurement paper. Its “applied evaluation requirement” wording should remain explicitly a proposal. Its literature coverage needs the hierarchical-error and flow-evaluation precedents above. The new template already addresses these distinctions in its methods and validity sections.

## 6. Review method, verification record, and access limits

This was a **bounded targeted review**, not a systematic review or a registered search protocol. The search date was September 23, 2026. Starting points were the existing D1 positioning file, prior manuscript references, source repositories, and the manuscript's concrete claims. Recent closest-work searches focused on 2024–2026; older original dataset publications and foundational evaluation work were retained for provenance.

Representative query families were:

- `hierarchical classification intrusion detection ten datasets flat attacks normal 2025 Uddin`
- `provenance intrusion detection benchmarks evaluation protocols Guerra 2026`
- `TAN-IDS transfer-aware deployment-oriented NetFlow evaluation 2026`
- `DAPT2020 temporal MITRE residual time compromise 2026`
- `SCVIC-APT-2021 benchmark Liu Shen Simsek`
- `DSRL-APT-2023 CTGAN CopulaGAN DAPT`
- `S-DAPT-2026 Tijjani Ghita Clarke Craven withdrawn`
- Exact-title checks for UNRAVELED, StageFinder, SANGL, and the UNRAVELED ensemble study.

Sources were official proceedings, publisher pages/PDFs, author repositories or institutions, author preprints, and publisher/repository DOI metadata. Crossref and DataCite entries were used for deposited bibliographic metadata, not independent validation of scientific claims. Full author order and initials were retained rather than invented. The unusual SANGL family-name fields follow the publisher deposit and are documented in the machine-readable record.

Material access distinctions:

- Uddin's journal abstract/metadata were accessible; detailed section verification used its 2024 author manuscript.
- DAPT's book metadata and author schema were verified; the original chapter full text was inaccessible.
- SCVIC metadata and author bibliography were verified; DataPort and full article protocol were not fully accessible.
- DSRL's primary PDF was read directly, including the dependency statement on printed p. 112.
- Othman's publisher-indexed full text was readable, while direct retrieval intermittently returned maintenance/rate-limit responses.
- The S-DAPT arXiv withdrawal was accessible. The later SSRN full text and a qualified replacement release were not verified.
- Iturbe's institution abstract and author dataset description were accessible; the full paper was blocked.
- Guerra and StageFinder are cited as the inspected 2026 preprints, with author-reported acceptances recorded separately.

The evidence is sufficient to avoid the identified broad novelty errors. It does not prove that no additional closely matching publication exists. No detector, source clock, source ground truth, or external paper implementation was independently validated merely by reading its publication.

## 7. Reference assembly

[references.json](references.json) contains 18 APA-style entries with stable IDs, URLs, publication status, support scope, locators, and access limits. Uddin's preprint and journal entry identify two versions of the same study; SCVIC's paper and dataset identify two related artifacts. Counts of references must not be presented as counts of independent empirical replications.
