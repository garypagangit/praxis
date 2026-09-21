# Literature and validity review of the proposed tabular APT batch

Reviewed September 20, 2026 (America/New_York), using primary sources. This review does not contain experiment outcomes. It corrects the supplied E0-E7 proposal before any results from the proposed batch are interpreted.

## Decision

The batch contains testable ideas, but **none guarantees a positive research result**. E0 is necessary; a small E1 baseline study and a corrected E4 uncertainty audit are useful initial work. E3 is a bounded follow-up. E5 requires a different claim, and E6 requires an acquired, qualified sequence dataset. Reusing an existing method on an APT dataset may support a careful applied study; it does not by itself establish algorithmic novelty or a publishable doctoral contribution.

| Experiment | What is defensible | What must change |
|---|---|---|
| E0: dataset audit | Verify actual files, labels, grouping, provenance and access before modeling. | A paper's row count or stage list is not a verified dataset. Distinguish stage labels from attack categories and generator rules. |
| E1: few-shot foundation models | Compare sample-efficiency against equally tuned tree baselines on common splits. | Drop the unverified “first” claim and “wins at any budget” success rule. Freeze a primary budget/comparison; disclose all labeled development and calibration examples. |
| E2: fast screening cascade | Measure full-system recall, F1, latency and cost at a frozen gate threshold. | Published relative speed on another workload is not transferable. Include both stages, model loading/context preparation, feature processing and rejected attacks. |
| E3: label-noise treatment | Test whether an explicitly defined correction helps injected training-label errors. | The named paper does not establish that Gradients relabeling is universally best. Include early stopping and removal controls; measure damage to clean rare-stage examples. |
| E4: conformal sets | Measure empirical coverage and useful set size under clearly stated assumptions. | Ordinary coverage is marginal, not automatically per-stage, temporal-shift robust or useful. Direct conformalized foundation-model IDS prior art exists. |
| E5: known/unknown fusion | Compare held-out-stage recall at the same benign alert burden. | Calibration on known attacks does not certify a missed-attack bound for an unseen stage. Remove “guaranteed contribution.” |
| E6: next-stage prediction | Forecast a future stage from an observed prefix of an independently grouped campaign. | S-DAPT access/correction remains unresolved. Alert correlation is not automatically a next-stage baseline; add transition and persistence baselines. |
| E7: GRANDE | Optional model control after the core comparison works. | Parity on one searched cell is not evidence of a new contribution. “First security application” is unverified. |

## E3: the actual Gradients paper

Eisenbürger, Otten, Hudde and Hopfgartner's *Training Gradient Boosted Decision Trees on Tabular Data Containing Label Noise for Classification Tasks* is available as [arXiv 2409.08647v2](https://arxiv.org/html/2409.08647v2), revised January 6, 2025. The manuscript names Information Processing & Management; a final publisher DOI/publication record was not verified in this review, so cite the verified preprint rather than asserting publication.

Its Gradients method uses large absolute per-example gradients with a two-component Gaussian mixture to identify candidate errors. Settings include 15 boosting rounds before intervention and a five-round history. Relabeling uses recent averaged class probabilities and changes each example at most once; removal is another tested treatment. The source also studies AUM, likelihood-ratio correction and training-dynamics statistics. Its discussion warns that treatment can reduce classification performance, particularly on imbalanced data; good noise detection is not equivalent to a better classifier. These details matter for rare APT stages. A one-pass confidence filter is an adaptation, not a faithful Gradients reproduction. An authoritative implementation was not located during this review.

**Our inference:** a useful E3 question is whether noise treatment preserves clean rare-stage examples while recovering performance under a declared corruption process. It cannot demonstrate repair of real APT labels without independently established clean labels. GAN generation does not itself prove label corruption.

## E4: direct prior art and the actual guarantee

Two sources materially change the supplied novelty claim:

1. The [official IEEE CSR 2026 accepted-paper program](https://www.ieee-csr.org/2026-conference-program/) lists Thomas Zöller and Alexander Lawall's *Reliable Intrusion Detection via Conformalized Tabular Foundation Models*. Acceptance/title/authors are verified. The full paper was not obtained, so its exact datasets, calibration procedure and results remain unverified. Nevertheless, “foundation-model IDS plus conformal calibration is unexamined” is not a defensible starting claim.
2. De Melo Costa, Popineau, Rimmel and Doan compare foundation models and boosted trees using conformal uncertainty metrics on 112 tabular datasets in *High Performance, Low Reliability: Uncertainty Benchmarking for Tabular Foundation Models*. The [ESANN 2026 proceedings paper](https://www.esann.org/sites/default/files/proceedings/2026/ES2026-261.pdf) is a verified conference publication. General comparative conformal efficiency/reliability of these model families is already studied.

Standard split conformal prediction uses held-out calibration scores to form sets of possible labels. Its usual statement averages over calibration and future examples drawn exchangeably; it does not promise that each finite test set, rare class or chosen subgroup achieves exactly the nominal coverage. Class-conditional calibration is a separate construction requiring suitable within-class calibration data. Tiny classes can force full-label sets. A set containing every class has coverage but provides little discrimination. See [Angelopoulos and Bates, Sections 1, 3 and 4](https://arxiv.org/html/2107.07511v6).

Time-ordered splits, new campaign templates and held-out attack families are useful deployment stress tests. They do not automatically meet exchangeability. Methods for drift have their own assumptions or weaker targets; simply applying a rolling quantile does not restore a universal guarantee. See [Barber et al., Conformal prediction beyond exchangeability](https://arxiv.org/abs/2202.13415) and [Gibbs and Candès, Adaptive Conformal Inference Under Distribution Shift](https://arxiv.org/abs/2106.00170).

**Our inference:** the useful target is *informative, empirically reliable sets for rare stages under a declared shift*, compared with strong existing calibration methods. Wrapping a classifier is a control, not an original algorithm. Any proposed improvement needs its own validation and comparison with the CSR paper after full-text retrieval.

## E5: what a conformal risk bound cannot say

[Angelopoulos et al., Conformal Risk Control](https://arxiv.org/html/2208.02814v4) controls an expected bounded monotone loss under stated conditions. This is different from a high-probability guarantee for the realized miss rate in one deployment, every stage, or every future campaign. The paper's distribution-shift extension needs additional information such as appropriate density ratios and support conditions; it does not make arbitrary unseen attacks covered automatically.

For the proposed leave-one-stage-out experiment, withholding that stage from training **and calibration** removes the evidence needed to certify its miss rate. If its labels are supplied for calibration, it is no longer an entirely unseen-stage evaluation. A benign-only calibration can support a false-alarm statement under matching benign-distribution assumptions; it cannot establish unknown-attack recall. An “always alert” router has zero misses but may be operationally useless. Report recall and alert burden together.

If a later study needs a high-probability risk certificate after threshold/model selection, select an appropriate method and define the statistical unit, loss, candidate family and calibration population first. [Learn then Test](https://arxiv.org/abs/2110.01052) explicitly treats calibration as multiple hypothesis testing. It is an existing method to compare against, not proof that the proposed gate is novel.

**Correct E5 claim:** an empirical comparison of a known-stage classifier, an anomaly detector and their frozen fusion on held-out stages at calibration-selected operating points. Under shift, test false-positive and miss rates are measured results, not guaranteed ceilings.

## E6: dataset and task assumptions

The [S-DAPT arXiv record](https://arxiv.org/abs/2601.06690) still marks the January 10 manuscript withdrawn on April 1, 2026. A [later SSRN abstract](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6603942) was posted April 18 and describes a k-nearest-neighbor alert-correlation framework and stage-aware synthetic data. The later abstract does not establish a verified next-stage forecasting baseline or resolve the raw-data acquisition, correction history, reuse terms and peer-review checks. See the existing [dataset intake](../sdapt2026/README.md).

Do not present “8,100 sequences,” supplied mappings or independence of scenarios as inspected facts until actual files are audited. A deterministic current-alert-type-to-stage mapping can make stage classification trivial without supporting future prediction. For forecasting, campaign identifiers are grouping metadata, not features; current and past observations must be separated from future labels and full-campaign summaries.

## Statistical safeguards for the whole batch

- Fix a primary dataset, budget, model comparison and outcome before fitting. A gain at any budget, dataset, noise level or metric is a multiple-search result. Label the wider grid exploratory or use an explicitly specified simultaneous procedure.
- Ten training seeds share the same test campaigns. They describe fitting/subsampling variability; they are not ten independent replications of the deployment population.
- Bootstrap complete independent units (campaign, execution, generator realization or defensible groups), not correlated rows. If there are too few independent groups, publish descriptive differences and their denominators instead of manufacturing precise confidence intervals.
- Select hyperparameters and operating points on development data. Reserve calibration for its specified purpose and lock test data before selection. Fit encoders, feature selection and imputation on training data only.
- Few-shot budgets include every labeled example used for model selection, calibration or relabeling decisions, with fitting/context counts reported separately. No balancing, oversampling or noise injection may cross the split boundary.
- Missing timestamps or campaign IDs may prevent temporal/generalization claims even when row-level modeling runs successfully. A valid software execution and a useful scientific test are separate gates.

## Suggested priority

E0 -> small E1 -> corrected E4; run E3 only with a verified clean-label test reference and an explicit algorithm implementation. E2 is worthwhile only if measured component timings support a possible speed benefit. E5 is exploratory open-set evaluation until its claim is rewritten. E6 remains conditional on data. E7 is optional. The [suggested finite pilot protocol](PILOT_PROTOCOL_REVIEW.md) defines a bounded path without treating publication or positive results as guaranteed.
