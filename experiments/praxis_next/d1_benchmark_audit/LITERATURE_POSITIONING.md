# D1 literature positioning and claim boundaries

Primary-source review completed September 23, 2026. This is a targeted closest-work review, not a systematic review or proof that a literature intersection is empty. No experiments, thresholds, or manuscript claims were changed for this review.

## 1. The unnamed 2025 study is identified

Uddin, M. A., Aryal, S., Bouadjenek, M. R., Al-Hawawreh, M., & Talukder, M. A. (2025). Hierarchical classification for intrusion detection system: Effective design and empirical analysis. *Ad Hoc Networks, 178*, Article 103982. [Publisher/DOI](https://doi.org/10.1016/j.adhoc.2025.103982).

The publisher abstract reports ten classifiers across ten datasets: comparable aggregate performance, but flat classification more often calls attacks normal while hierarchical classification more often confuses attack types. The [author manuscript](https://arxiv.org/html/2403.13013v1) appeared March 17, 2024. Detailed checks use that manuscript; the final publisher full text was inaccessible.

The manuscript already contains:

- Per-attack exact classification recall in Section 4.3.3, Figures 6–8.
- Per-attack counts classified as normal in Section 4.3.4, Figures 9–10.
- Full multiclass confusion matrices in Figures 11–14.
- The accompanying false-positive tradeoff in Section 4.3.5.
- Stratified ten-fold evaluation in Sections 3 and 3.2.

**Novelty consequence:** the error distinction and equivalent per-class accounting already exist. A paired table is useful presentation, not a new metric. The inspected design does not establish the proposed controlled chronological/evidence-perturbation result. Do not claim that no previous work considered stages: its taxonomy includes kill-chain groupings and datasets containing lateral/exfiltration categories.

## 2. What the paired measurements mean

Use the same frozen predictions, evaluation rows, denominator, and operating point. Let `C[s,j]` count rows whose true author label is attack stage `s` and whose predicted class is `j`; let `b` mean benign and `N_s = sum_j C[s,j]`.

| Measurement | Calculation | Plain-language meaning |
|---|---|---|
| Exact-stage recall for stage s | `C[s,s] / N_s` | Of the records labeled this stage, how many received that same stage label? |
| Any-attack recall within stage s | `1 - C[s,b] / N_s` | Of those same records, how many received some attack label? |
| Attack-to-benign fraction within stage s | `C[s,b] / N_s` | How many records of this stage were dismissed as normal? |
| Wrong-stage but still attack fraction | `sum(C[s,j] for j not in {s,b}) / N_s` | How many retained an attack label but received the wrong stage? |

The second measurement is ordinary binary attack recall conditioned on the true stage. The last fraction equals any-attack recall minus exact-stage recall. This is confusion-matrix decomposition, not a novel mathematical construct. Exact-stage recall cannot exceed any-attack recall under these definitions; observing that inequality is not an empirical discovery.

Example: among 100 exfiltration-labeled records, 60 predicted exfiltration, 20 another attack, and 20 benign yield 60% exact-stage recall and 80% any-attack recall. The scientifically interesting question is whether a model/protocol change alters the *distribution of these outcomes*, including cases where an improved aggregate score accompanies more attack-to-benign errors.

Always include benign-to-attack counts/rates and alert workload. An all-attack predictor trivially obtains 100% any-attack recall. For thresholded comparisons, choose thresholds on development data, state the target workload, and report the workload actually obtained on evaluation data. A shared numerical threshold does not itself establish equal workload or comparable score calibration.

If a policy can abstain, expose a separate abstention count and define whether it generates a review alert before evaluation. Do not silently count abstentions as either benign or detected attacks. Report `N_s=0` metrics as unavailable. An author-stage label is not an independently verified successful attack outcome.

## 3. Closest evaluation and APT-flow precedents

| Primary work | Already established or studied | Consequence for D1 |
|---|---|---|
| [Pendlebury et al., TESSERACT, USENIX Security 2019](https://www.usenix.org/conference/usenixsecurity19/presentation/pendlebury) | Spatial and temporal evaluation constraints; inflated Android malware scores under unsuitable splits; an evaluation framework. | Temporal hygiene is foundational prior art. Applying chronological evaluation to APT data is not by itself a new research principle. |
| [Bilot et al., USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/bilot) | Eight provenance detectors in a shared framework, nine evaluation/practical shortcomings, simple-model controls, and attack-coverage-oriented evaluation. The SC2 discussion in the [paper](https://www.usenix.org/system/files/usenixsecurity25-bilot.pdf) examines limitations of ordinary entity-level metrics and introduces ADP. | Neither evaluating APT systems critically nor separating attack discovery from entity-level recovery is new. ADP is not our per-stage binary recall and should not be relabeled as such. |
| [Guerra et al., 2026 version 3 manuscript](https://arxiv.org/html/2608.01454v3) | Temporally separated provenance evaluation, validation-based choices, dataset-semantic audits, simple allowlist controls, and divergence between alerting and process recovery. | This directly occupies broad claims about APT benchmark/protocol sensitivity. Available September 9, 2026 revision; authors report NDSS 2027 acceptance. Cite the available 2026 preprint, not an already-published 2027 proceeding. |
| [Ha Thanh, TAN-IDS, PLOS One 2026](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0346801) | A shared NetFlow feature interface and in-domain, cross-domain, fine-tuned and mixed-domain comparisons. Section 4.2 specifies stratified splits. Section 5.6.1 explicitly limits the study to binary detection and leaves multiclass/family discrimination and systematic feature ablation outside scope. | A direct flow-level evaluation anchor with an explicit scope boundary. D1 can investigate stage-specific outcomes under temporal/evidence controls; it cannot claim the first deployment-oriented flow benchmark. |
| [Iturbe et al., Future Generation Computer Systems 2026](https://scienceportal.tecnalia.com/en/publications/a-pattern-aware-lstm-based-approach-for-apt-detection-leveraging-/) | Sandworm emulation and multiclass LSTM/BiLSTM analysis of atomic and multi-step patterns in network flows. | Sequence-aware APT-flow classification and dataset contributions already exist. The [author's dataset description](https://pradoglougrammatikis.com/portfolio-items/apt-sandworm-dataset/) explicitly limits flow labels to network-visible procedures; endpoint-only stages cannot be inferred to be absent from the attack. |
| [Ibrahim et al., Journal of Big Data 2025](https://link.springer.com/article/10.1186/s40537-025-01272-w) | An LSTM/KNN/logistic-regression ensemble evaluated using UNRAVELED; the ensemble section describes binary normal/APT outputs. | Neither an ensemble on UNRAVELED nor improved aggregate APT detection is an unoccupied idea. Our existing results are not a reproduction of this published model. |
| [SANGL, Scientific Reports 2026](https://www.nature.com/articles/s41598-026-42756-w) | Network-pattern/graph modeling of APT stages, evaluation including CICAPT-IIoT, DAPT20 and UNRAVELED, and reported stage-transition measures. | Flow-based stage and temporal-pattern evaluation also has recent direct precedents. A bounded review does not verify every implementation or justify accusing a paper of leakage. |

The first four works establish the evaluation lineage. The last three prevent a misleading claim that recent flow-level APT work is absent. Their scopes and protocols differ; published headline scores are not comparable baselines without reproducing their data, units, labels and evaluation choices.

## 4. Defensible proposed measurement contribution

**Research question:** On qualified flow datasets with author stage labels, how do training time/composition and incomplete or incorrectly linked historical evidence change the relationship between exact-stage recognition, attacks dismissed as benign, and benign alert workload?

**Candidate contribution statement:** We provide a reproducible, controlled measurement of these tradeoffs on explicitly qualified APT-flow artifacts, using established metrics, fixed evaluation rows for the training-pool comparison, bounded evidence interventions, and transparent stage support and annotation limits.

This is narrower than proposing a new detector or discovering that false negatives matter. The contribution would be the new measurements, controlled comparisons and reusable evidence package. Its strength depends on completed data qualification, informative results and replication. This review does not establish that the full combination is unprecedented, important enough for a particular venue, or certain to be accepted.

Keep the two interventions separate:

1. **Training-pool comparison:** hold later evaluation rows and class-specific fitting budgets fixed; compare earlier-only fitting with time-mixed fitting; exclude exact evaluation-feature matches consistently. Attribute the measured contrast to the changed training pool. It does not isolate time from changes in the variety of training data.
2. **Evidence comparison:** hold fitted models and evaluation rows fixed; vary declared visibility, age or correspondence conditions. Precomputed-history perturbations are simulated evidence conditions, not measured sensor outages or verified real workflow changes.

Different datasets may answer different portions of this question. Do not force unlike technique/stage labels into a common target merely to increase the dataset count. A dataset that fails a gate should remain a documented qualification outcome.

## 5. Preregistration and manuscript corrections

- Replace **new metric**, **first to distinguish missed attacks from wrong stages**, and **no prior APT evaluation work** with the established definitions and citations above.
- Separate historical results from new hypotheses: the PX-081 any-attack analysis was added after first-seed inspection and remains supplementary; registering D1 cannot make that earlier discovery prospective.
- State before new outcomes which metric contrasts, stage labels, baseline pairs, conditions and operational thresholds are primary. Preserve favorable, unfavorable and inconclusive outcomes; no requirement that a detector win.
- For any matched-workload claim, define the development-only threshold procedure and evaluation workload reporting. Report ordinary fixed-rule comparisons separately if they are the actual design.
- Predefine the evaluation unit and uncertainty unit. Flow rows, duplicate patterns, perturbation views and fitting seeds are not independent campaigns. Report per-run/capture support; do not turn a handful of captures into population-level confidence by row resampling.
- Make unsupported targets explicit: PX-080/081 movement labels have only 35 evaluation rows and concern author-annotated Remote System Discovery on one host pair. PX-082 has 18 such anchor rows. These do not validate successful lateral movement or forecast theft.
- PX-083 examines T1105 versus other technique labels and lacks verified benign negatives. Its other-label flags are not production false alarms, and its binary target is not any-attack-versus-benign detection. Keep it a separate supporting policy-transfer result.
- Claim data/code/arithmetic reproducibility only to the extent audited. A computational audit cannot independently certify author ground truth, eliminate all leakage channels, or guarantee deployment performance.
- A completed manuscript is an artifact milestone. Call publication potential provisional until the evidence, scope and literature contribution are assessed; neither a positive score nor a negative method result determines acceptance by itself.

## 6. Reference metadata for newly identified anchors

Ha Thanh, D. (2026). A transfer-aware, deployment-oriented evaluation framework for NetFlow-based intrusion detection systems (TAN-IDS). *PLOS One, 21*(4), e0346801. [doi:10.1371/journal.pone.0346801](https://doi.org/10.1371/journal.pone.0346801). Published April 8, 2026; author name follows the publisher's citation record.

Iturbe, E., Dalamagkas, C., Radoglou-Grammatikis, P., Rios, E., & Toledo, N. (2026). A pattern-aware LSTM-based approach for APT detection leveraging a realistic dataset for critical infrastructure security. *Future Generation Computer Systems, 178*, Article 108308. [doi:10.1016/j.future.2025.108308](https://doi.org/10.1016/j.future.2025.108308). Author institution records the issue as May 2026; a 2025 DOI/copyright does not change the cited issue year.

Uddin's verified journal citation appears in Section 1. Existing full references for TESSERACT, Bilot and Guerra remain in [the manuscript reference audit](../paper/REFERENCES.md). The evidence table links directly to the other publisher records; no unverified author initials or publication status are inferred.

## Review limits

The query set targeted the named ten-dataset study, hierarchical versus flat error destinations, recent temporal/protocol evaluation in APT/provenance, and flow-level APT benchmarks. Primary publisher, conference and author sources support the conclusions above. The 2025 Uddin abstract and its 2024 full author manuscript were distinguished explicitly; the final full text was inaccessible. No failure to find a matching study is used as proof of novelty.
