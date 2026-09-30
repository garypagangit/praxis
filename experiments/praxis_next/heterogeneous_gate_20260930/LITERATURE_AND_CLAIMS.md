# Plan B claim check — September 30, 2026

**The proposed strong novelty statement is not established.** A useful controlled measurement may remain, but neither an OR operator nor correlated errors makes a new method by itself. This is a bounded primary-source check, not proof that every closely related paper has been found.

## Primary foundation and overlap

| Paper | Relevant established work | Consequence |
|---|---|---|
| Kittler, Hatef, Duin and Matas, *On Combining Classifiers*, IEEE TPAMI, 1998. [Institutional record](https://dspace.cvut.cz/entities/publication/829206e1-4e28-4091-b0a7-14f2455efaff), [DOI](https://doi.org/10.1109/34.667881). | Classical classifier-combination framework, including sum and max rules. The institutional search record was accessible; direct PDF/DOI retrieval failed in this check. | Cite as foundational fusion work. A classwise maximum-probability rule is not identical to our OR of hard non-benign labels; do not conflate them. |
| Kuncheva and Whitaker, *Measures of Diversity in Classifier Ensembles and Their Relationship with the Ensemble Accuracy*, Machine Learning 51, 181–207, 2003. [Paper](https://machine-learning.martinsewell.com/ensembles/KunchevaWhitaker2003.pdf), [DOI](https://doi.org/10.1023/A:1022859003006). | Studies pairwise and non-pairwise error diversity, including disagreement, double faults and coincident failures; examines their relationship to ensemble accuracy. | Error overlap is established research territory. The paper cautions against substituting a diversity statistic for measured ensemble performance. It does not establish that our particular ratio or dataset audit is an exact duplicate. |
| Brabec and Machlica, *Decision-forest voting scheme for classification of rare classes in network intrusion detection*, IEEE SMC 2018; arXiv release 2021. [Paper](https://arxiv.org/html/2107.11862), [DOI](https://doi.org/10.1109/SMC.2018.00563). | Identifies detection loss from standard aggregation under benign/malware imbalance and tests Bayesian tree aggregation using out-of-bag errors. Discusses detection/precision tradeoffs and threshold alternatives. | Direct overlap with the broad claim that aggregation can suppress rare security detections and should be repaired. Its method/task differ from our OR experiment, so it is prior work to compare, not an exact replication claim. |

## Corrections to the proposed argument

1. **“Nobody has shown why averaging loses warnings.”** Too broad. Aggregation under imbalance and error dependence already have a literature. Our contribution could be the particular paired warning-destination audit and controlled workload measurements, subject to closer novelty review.
2. **“One confident-benign member vetoes.”** This can happen, but it is not an absolute veto. At a mean decision, benign wins when its summed probability is at least that of every attack class (with the fixed tie convention). Warnings can also disappear when every member warns but they distribute support across different attack stages. The boundary tests cover both cases. OR avoids constituent-warning demotion by construction.
3. **“A lower overlap ratio proves independent views.”** False. For nonempty false-alert sets, duplicating an existing member leaves the union unchanged and increases the sum of member counts; the ratio decreases despite no new predictions. PX-093 includes this control. Different algorithms trained on shared rows are also not statistically independent observations or new campaign coverage.
4. **“False-alert cost is bounded.”** The union count is at most the sum of constituent counts. That mathematical bound can still be operationally unacceptable. A fixed baseline workload limit, marginal false alerts and absolute counts are needed; adding a noisy member must not enlarge the acceptance denominator.
5. **“Seven alternatives failed; only OR fixes it.”** Unsupported. Earlier recalibration recovered warnings at large cost. The earlier experiments differ in assumptions and scope; their outcomes are not a universal impossibility result for thresholding, calibration or other combiners. A common prospective workload budget and additional comparator families would be needed for a strong superiority claim.
6. **“Part C must pass.”** It already did not meet PX-092's strict per-execution improvement criterion. That result stays failed. A later heterogeneous extension cannot retroactively make the original hypothesis pass or make already examined AIT executions fresh validation.

## Defensible thesis direction

Candidate title: **Auditing Warning Loss and Alert Workload in APT Classifier Ensembles**.

Candidate claim: deterministic warning retention removes constituent-warning demotion, while its practical value depends on complementary attack coverage and the added false-alert workload. A reproducible audit can expose when attractive aggregate or overlap scores fail to demonstrate that value.

This is an evaluation and engineering-validation direction. Committee suitability and a sufficiently specific literature gap remain to be established; the experiment cannot guarantee acceptance. No claim that all SIEMs behave the same way, that OR makes a detector safe to deploy, or that added model diversity creates independent attack evidence is warranted.
