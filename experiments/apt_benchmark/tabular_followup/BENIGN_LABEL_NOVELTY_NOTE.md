# Benign-label budgets: useful finding, limited novelty claim

Bounded primary-source review, September 21, 2026. This is a separate interpretation note written after the stronger-tree outcomes. It changes no frozen method, success gate, worker, or protocol, and authorizes no additional experiment.

## Conclusion

**More benign examples helping a detector is not a new idea.** A 2026 peer-reviewed IDS study explicitly proposes asymmetric support allocation for this purpose. Controlled studies also show that tabular foundation-model performance depends on context size and class composition. The precise combination of fixed attack-label supports, independently varied benign-label budgets, matched foundation/tree controls, and stage-specific detection at a common false-alarm target was not established as already completed by the sources inspected here. That is a bounded search result, not a first-method or first-benchmark claim.

Our existing result shows a **tree-model trade-off**, not a foundation-versus-tree ranking reversal: foundation models have not been tested in the abundant-benign condition.

## What our completed control actually establishes

The audited ten-seed tree summary compares 32 versus 1,024 benign fitting examples, retaining the same 160 attack examples: 192 versus 1,184 total fitting labels, a cost of 992 additional labels. For the training-CV-selected tree, mean six-class macro-F1 rises from approximately .442 to .654, and the normal false-positive rate falls from 10.04% to .40%. However, binary detection of lateral-movement flows falls from 94.24% to 83.06%. This last metric credits **any** predicted attack class; it is not exact lateral-stage identification.

These are development results on the same test flows across seeds. They do not establish generalization to new incidents, an optimal label allocation, a causal explanation of the improvement, or superiority over equally resourced foundation models. More normal examples change both coverage of benign behavior and the training class balance; tuning/model selection can also differ between conditions. Those mechanisms are not isolated by the observed aggregate score.

## Closest verified evidence

| Primary source | What is actually studied | Relation to the precise question |
|---|---|---|
| Revell, Kang, Seo, & Kim (2026), [*Systematic Evaluation of Few-Shot Learning for Unseen IoT Network Attack Detection*](https://www.techscience.com/CMES/v147n1/67129/html), doi:10.32604/cmes.2026.078467; peer-reviewed full text, published April 27 | ProtoNet, Relation Networks, MetaOptNet and ensembles on UQ-IoT-IDS-2021; five support sizes, four attack compositions. Benign/attack ambiguity is a documented failure mode. Section 6.5 explicitly proposes allocating substantially more support examples to the benign class. | The asymmetry idea is already proposed. It is future work in this paper, not a measured benign-only budget sweep against TabPFN/TabICL and tuned trees. Their model rankings vary with the task setting, so context-dependent ranking is not new in general. |
| García et al. (2025), [*Foundation Models for Cybersecurity*](https://www.mdpi.com/2079-9292/14/19/3792); peer-reviewed full text | TabPFN/TabICL use balanced per-class caps, while classical baselines use the full data on three IDS datasets. Rare-class performance is explicit. The methods inconsistently give 2,000 versus 3,000 per-class TabPFN caps. | Direct TFM/classical IDS comparison already exists, including unequal data access. It does not isolate an increase in benign labels while fixing identical scarce attack supports across model families. |
| Tanna et al. (2026), [*Data Presentation Over Architecture*](https://arxiv.org/html/2605.18635v1); author preprint, peer-review status unverified | Five TFMs and four classical baselines on Home Credit/Lending Club; seven context-construction strategies and sizes from 1K to 50K. The study reports context-dependent performance and crossovers against full-data classical baselines. | It directly studies sample composition, scale, and relative performance. This is financial classification, with varying minority exposure and unequal baseline data budgets, not fixed attack labels or APT-stage safety. The general thesis that sampling can matter more than model choice is already articulated. |
| Bae, Ding, Ma, & Zhang (2026), [*DUPIN: Attack Learning Is Still Needed!*](https://arxiv.org/html/2609.00259v1); author preprint | Large-scale benign provenance pretraining followed by few-shot attack adaptation; attack forensics on multiple APT datasets, with explicit concerns about false positives and attack/benign similarity. | Abundant benign data plus scarce attack supervision is established motivation and an implemented pipeline. It is a graph-pretraining approach, not a controlled TabPFN/TabICL-versus-tree budget comparison. |

## Additional overlap with the frozen review policy

A public [WCCI 2026 submission PDF, *CALIBER: Benign-Calibrated Dual-Score Rejection for Label-Scarce Open-World Sequence Classification*](https://linklings.s3.amazonaws.com/organizations/WCCI/wcci2026/submissions/stype113/KViKg-ijcnn_pap2418s1.pdf) contains further direct overlap. The eight-page manuscript is anonymous; authorship, acceptance, DOI, and released code were not verified. It must **not** be cited as an established peer-reviewed publication.

Its CAN-sequence encoder combines energy and Mahalanobis scores, calibrates thresholds on benign data, and rejects if either threshold is exceeded. It evaluates two in-vehicle datasets with held-out attack types and label-fraction sweeps. Algorithm 1 uses a separate `1-alpha` quantile for each score; it does not specify our `.005 + .005` allocation. Its scores, unknown-rejection task and representation differ from our known-stage review rule. Nevertheless, benign-only, dual-score, budgeted rejection is already publicly described; splitting an error budget is standard practice, not a new algorithm by itself.

Private retained PDF: SHA-256 `982b1318ffb08e70650feb1ab84697631a8e01c66fc4271cb8a64580239ce26d`, 2,489,887 bytes, eight pages. No manuscript bytes are republished here.

## A precise question worth resolving, without claiming it is novel

**When attack labels are fixed and scarce, which model and benign-example allocation best protect the worst-detected attack stage at a specified false-alert budget, and does that choice survive a new incident or network?**

A defensible answer would require:

1. The same attack examples and benign-label budgets for every model family, with tuning and inference costs stated. An abundant-benign tree versus a balanced-context TFM is an unequal-resource comparison, not a clean ranking test.
2. Separate accounting for fitting, calibration, tuning, and any pretraining labels. Our 29,929 benign calibration labels must not disappear behind a 192-row fitting headline.
3. Both fixed operating-point and ranking metrics, raw false-alert counts, and all attack stages. Any new emphasis on lateral movement is post-result hypothesis generation and needs independent confirmation.
4. Evidence separating broader benign coverage from class-prior/weighting effects, plus independent grouped or temporal incidents. Reused seed splits cannot supply that independence.
5. Comparison with the named prior work's actual constraints, followed by a narrower, result-supported contribution statement. The source-normal budget may not remain a target-normal budget after network shift.

**Praxis assessment:** this can motivate a useful applied evaluation of labeling and review costs. At present it is not a validated model-ranking result or a novel algorithm, and the completed Sandworm transfer failure cautions against claiming deployment benefit. Finish the frozen work before selecting a final thesis. No further fits were performed for this note.
