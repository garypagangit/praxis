# Literature review: reducing false alarms while preserving lateral-movement detection

**Review date:** September 21, 2026. **Purpose:** support a prospective praxis proposal, using completed experiments as preliminary evidence. This note introduces no experimental result, frozen success criterion, or claim of established novelty. It changes no earlier protocol.

## Recommendation

The research question is worth a focused applied study: **Can a validation-selected benign-training budget reduce false alarms without an unacceptable loss of lateral-movement detection when attack labels are scarce?**

The broad ideas are already established. Increasing benign support, resampling intrusion data, cost-sensitive classification, optimizing a threshold, and controlling class-specific errors are not new contributions. The most defensible potential contribution is a reproducible selection procedure and evaluation that separates benign-example diversity from changed training class balance, charges all labeling costs, and tests lateral-movement preservation on data that did not motivate the proposal. Its benefit and distinctness remain hypotheses.

Use two primary anchors: **Smiliotopoulos and Kambourakis (2026)** for the lateral-movement imbalance problem, and **Tian and Feng (2025)** for established error-constrained classification. Revell et al. (2026) is essential prior art for increasing benign support. The reference list supplies APA-style citations and direct sources.

## Preliminary evidence: motivation, not confirmation

The [completed decision report](../results/tabular_followup_decision_v1/REPORT.md) establishes the following development tradeoff for the training-CV-selected boosted tree, averaged over ten fits on the same test rows:

| Quantity | 32 benign + 160 attack fitting labels | 1,024 benign + the same 160 attack fitting labels |
|---|---:|---:|
| Six-class macro-F1 | 0.4421 | 0.6543 |
| Benign false-positive rate | 10.04% | 0.40% |
| Detection of any attack | 98.40% | 95.70% |
| Lateral movement detected as any attack | 94.24% | 83.06% |

Lateral detection here credits **any non-normal prediction on a true lateral-movement flow**. It differs from correctly assigning the lateral-stage label. The larger condition costs 992 additional benign labels. These observations motivate the question; they do not prove why the change occurred, how to repair it, or that it generalizes. Lateral movement became the focus after these results, so the existing SCVIC development test cannot serve as untouched confirmation for the new proposal.

The completed rescue policy also failed its registered improvement gate, and external Sandworm transfer was poor. Preserve both findings. Do not relabel the previous initial-compromise/exfiltration policy as a successful lateral-movement method.

## Closest verified literature

| Source and status | Verified contribution | Consequence for this proposal |
|---|---|---|
| **Smiliotopoulos & Kambourakis (2026), peer-reviewed journal** | Studies 13 shallow/deep models, LMD-2023 Sysmon data, imbalance/resampling, and false-positive/false-negative tradeoffs for normal, remote-service exploitation, and hashing-related exploitation classes. Publisher metadata and abstract inspected; full experimental text was subscription-limited in this review. | A general study of balancing data for lateral-movement detection already exists. Do not claim that application or comparison as new. Exact split and selection details need full-text inspection before asserting a specific methodological omission. |
| **Revell et al. (2026), peer-reviewed journal** | Evaluates few-shot meta-learning on UQ-IoT-IDS-2021. Section 6.5 explicitly proposes substantially more benign support to address benign/attack ambiguity. | Asymmetric benign support is already proposed. The inspected study does not report the proposed fixed-attack, benign-budget sweep with a lateral-miss constraint. This is an opportunity to test an existing suggestion, not ownership of the idea. |
| **Tian & Feng (2025), peer-reviewed JASA article; online 2024** | Develops multiclass Neyman–Pearson algorithms through cost-sensitive learning, including feasibility and theoretical properties under stated assumptions. | Protecting selected class error rates while optimizing other errors has established mathematical foundations. Our applied selection procedure would adapt this objective, not invent it. Its theorem does not automatically certify our models or correlated cybersecurity flows. |
| **Debelie et al. (2026), peer-reviewed journal** | Controlled GAN-augmentation study on nine UWF-ZeekData22 tactic-versus-benign tasks, examining augmentation amount, training duration, and minority-detection behavior. University repository verifies authors, venue, and publication status. | Tactic-specific imbalance experiments and augmentation ablations are prior art. If augmentation is included, compare standard methods instead of presenting synthetic minority samples as the contribution. |
| **García et al. (2025), peer-reviewed journal** | Compares TabPFN/TabICL with classical models across three IDS datasets and reports rare-class behavior. Published author-institution copy and metadata verified. | A tabular foundation model applied to IDS or rare threats is not new. The earlier [novelty note](../tabular_followup/NOVELTY_POSITION.md) documents unequal sampling and further hybrid/conformal overlap. Equal-budget comparisons are necessary for a fair architecture claim. |
| **Wang et al. (2024), peer-reviewed JMLR article** | Develops non-splitting Neyman–Pearson classifiers using a parametric linear-discriminant setting to address the cost of reserving threshold-calibration data. | Calibration-label efficiency is established research. This result does not justify reusing fitting examples as independent calibration observations for arbitrary tree or foundation models. |
| **Fraiman & Fraiman (2026), arXiv preprint, v2 June 14; peer review unverified** | Maximizes minority sensitivity under a bound on the total positive-prediction rate and studies capacity-aware training versus post-hoc thresholding. | An analyst-capacity objective is not new. Total alert rate and benign FPR are different constraints; choose and name the primary one rather than treating them as interchangeable. |
| **Bilot et al. (2026), accepted-paper author version** | LARES models host behavior and outgoing lateral edges, evaluating LANL/OpTC with temporal splits and unseen-host scenarios. Its PDF explicitly states acceptance at ACSAC 2026. Official proceedings DOI/pages were not verified. | Host context, reduced lateral false positives, and generalization to new hosts are active prior art. A graph/context extension would need comparison with this approach; naming lateral movement alone supplies no distinction. |
| **Kalan et al. (2025), arXiv preprint; peer review unverified** | Studies Neyman–Pearson transfer when both class-conditional distributions shift, under a specified statistical framework. | A source-calibrated error target is not an arbitrary-network guarantee. Separate source-only transfer from target-assisted adaptation, and account for any new target labels. |

The selected literature spans the core 2024–2026 methods and current 2026 cybersecurity work. This is a bounded primary-source review, not a systematic review or proof that no closely matching study exists.

## Narrow contribution that could be defended if supported

**Proposed contribution statement:** “We evaluate a reproducible procedure for selecting benign training coverage and detector operating points under fixed attack-label budgets, using an explicit lateral-movement miss constraint, and determine when additional benign examples reduce false alarms without exceeding that constraint on independently held-out activity.”

The evidence would need to distinguish four issues:

1. **Coverage versus class balance.** Compare additional unique benign examples with controls that change their total training weight while retaining the same unique examples. Include a condition that expands unique benign coverage while holding total benign loss weight constant. This is most directly implementable with weighted tree models. It does not assume that duplicated examples, weights, and foundation-model context changes are equivalent.
2. **Model quality versus threshold choice.** Report ranking measures and entire validation tradeoff curves, but select one operating point without consulting final test outcomes. Compare against a conventional validation-selected threshold and ordinary class weighting. A more complicated rule must improve upon those controls.
3. **False alarms versus missed lateral movement.** Predeclare the lateral endpoint as benign misclassification of true lateral activity; report exact-stage classification separately. Choose the acceptable miss level/noninferiority margin before new evaluation. Minimize benign FPR among candidates meeting that constraint. If none qualify, report infeasibility rather than silently relaxing the requirement.
4. **Source performance versus independent confirmation.** Lock selection on development data, then evaluate held-out time periods, hosts, or incidents and a separately collected lateral-labeled source. Document the number of distinct incidents and the grouping rule. Ten fitting seeds on the same flows measure fitting variability, not ten independent replications.

This is an **applied contribution proposal**. A distinctive implementation could emerge, but neither a new acronym nor a combination of established operations would establish novelty. Any mechanism-level claim must survive the weight/coverage controls and the independent evaluation.

## Design requirements suggested by the evidence

- **Bound the initial model scope.** Strong XGBoost/LightGBM controls can support a CPU-feasible primary experiment. Foundation-model comparisons are optional matched-budget controls, not prerequisites for novelty. If included, every family must receive the same unique attack examples and benign-label budgets; calibrating or adapting with extra labels must be disclosed.
- **Keep evaluation prevalence intact.** Vary fitting data only. Do not balance the final test set to make false alarms look inexpensive. Report false alerts per 10,000 benign flows, lateral miss counts, precision, and workload; macro-F1 and ROC-AUC remain secondary summaries.
- **Budget all labels.** Separate fitting, hyperparameter-validation, threshold-calibration, and final-audit labels. An experiment with 192 fitting labels and 29,929 benign calibration labels is not a 192-label system.
- **Choose constraints for operational meaning.** A lateral-recall floor or a noninferiority margin avoids repeating the prior ceiling-limited superiority endpoint. Numeric choices remain proposed until the protocol is frozen; they must not be selected to make the known SCVIC results pass. Report both the margin and the observed absolute recall.
- **Do not turn a validation constraint into an unsupported certificate.** Candidate selection can overfit a small validation set. Use a declared limited search, separate calibration/confirmation, and group-aware uncertainty when enough independent groups exist. Without that evidence, describe empirical constraint satisfaction. Formal NP guarantees require matching the theorem's assumptions and error definition.
- **Qualify the confirmation data first.** SCVIC is useful for development. LMD-2023 is a relevant Sysmon candidate referenced by a 2026 peer-reviewed paper; its modality and label taxonomy differ from flow data. LANL/OpTC support temporal/host-aware questions but also have label and incident-count limitations. Do not pool their class names or silently equate features. Sandworm's 37 attack flows do not independently confirm all SCVIC stages.

## Strongest objections a committee or reviewer could raise

| Objection | Required response or limit |
|---|---|
| “This repeats resampling and cost-sensitive detection.” | Acknowledge that foundation. Establish an applied gap through matched attack identities, explicit benign budgets, mechanism controls, and independent constraint-preservation evidence. If that distinction is not supported, present a replication or benchmark study, not a new algorithm. |
| “The lateral objective was picked after seeing a failure.” | Label the current finding exploratory. Freeze the new question before new outcomes and reserve independent confirmation. Existing results remain preliminary. |
| “Normal-data diversity is being confused with changing the prior.” | Include weight/coverage controls and retain the same attack examples; do not infer mechanism from the existing two-condition comparison. |
| “It only lowers false alarms by missing attacks.” | Make lateral misses a binding selection endpoint, disclose losses in every other attack stage, and report raw counts. An overall F1 gain cannot override a failed protection criterion. |
| “The confidence bound treats correlated events as independent.” | Use meaningful incident/time/host groups and state their counts. If there are too few groups, report descriptive results and that confirmation is underpowered. |
| “It requires abundant labeled benign data but is called few-shot.” | Give the full label ledger. Known-normal calibration has acquisition and verification costs even when no attack labels are added. |
| “A source threshold failed on a new network already.” | Preserve the negative transfer result. Evaluate source-only deployment separately from any target-calibrated variant, with target labels explicitly charged. |

## APA-style references and verification notes

1. Smiliotopoulos, C., & Kambourakis, G. (2026). Machine learning for lateral movement detection using Sysmon logs: An empirical comparison of imbalanced and resampled data. *International Journal of Information Security, 25*, Article 38. [https://doi.org/10.1007/s10207-025-01182-1](https://doi.org/10.1007/s10207-025-01182-1). Published January 22, 2026; the DOI's “2025” is not the publication year. Publisher abstract/metadata verified; full methods access limited.

2. Revell, L., Kang, H., Seo, J. T., & Kim, D. D. (2026). Systematic evaluation of few-shot learning for unseen IoT network attack detection. *Computer Modeling in Engineering & Sciences, 147*(1), Article 45. [https://doi.org/10.32604/cmes.2026.078467](https://doi.org/10.32604/cmes.2026.078467). [Publisher full text](https://www.techscience.com/CMES/v147n1/67129/html), especially Section 6.5; published April 27, 2026.

3. Tian, Y., & Feng, Y. (2025). Neyman–Pearson multi-class classification via cost-sensitive learning. *Journal of the American Statistical Association, 120*(550), 1164–1177. [https://doi.org/10.1080/01621459.2024.2402567](https://doi.org/10.1080/01621459.2024.2402567). [Author preprint record](https://arxiv.org/abs/2111.04597). Journal issue year is 2025; first online publication was November 19, 2024.

4. Debelie, A., Bagui, S. S., Bagui, S. C., & Mink, D. (2026). A systematic ablation study of GAN-based minority augmentation for intrusion detection on UWF-ZeekData22. *Electronics, 15*(6), Article 1291. [https://doi.org/10.3390/electronics15061291](https://doi.org/10.3390/electronics15061291). [Author-institution publication record](https://ircommons.uwf.edu/esploro/outputs/journalArticle/A-Systematic-Ablation-Study-of-GAN-Based/99381734458706600) identifies a peer-reviewed article published March 19, 2026.

5. García, P., de Curtò, J., de Zarzà, I., Cano, J. C., & Calafate, C. T. (2025). Foundation models for cybersecurity: A comprehensive multi-modal evaluation of TabPFN and TabICL for tabular intrusion detection. *Electronics, 14*(19), Article 3792. [https://doi.org/10.3390/electronics14193792](https://doi.org/10.3390/electronics14193792). [University repository and published PDF](https://zaguan.unizar.es/record/163027); published September 24, 2025.

6. Wang, J., Xia, L., Bao, Z., & Tong, X. (2024). Non-splitting Neyman–Pearson classifiers. *Journal of Machine Learning Research, 25*(292), 1–61. [Official article and PDF](https://jmlr.org/papers/v25/22-0795.html).

7. Fraiman, D., & Fraiman, R. (2026). *Imbalanced classification under capacity constraints* (Version 2) [Preprint]. arXiv. [https://doi.org/10.48550/arXiv.2605.03289](https://doi.org/10.48550/arXiv.2605.03289). [Versioned record](https://arxiv.org/abs/2605.03289v2); first submitted May 5 and revised June 14, 2026. No peer-reviewed venue verified.

8. Bilot, T., Zouaoui, A., Al Agha, K., El Madhoun, N., & Pasquier, T. (2026). *LARES: Host-centered lateral movement detection via inductive graph reasoning* [Accepted conference paper, author preprint]. 42nd IEEE Annual Computer Security Applications Conference. [Author PDF](https://tfjmp.org/publications/2026-acsac.pdf) and [author publication page](https://tfjmp.org/publication/2026-acsac/). Acceptance is explicitly stated on the manuscript's first page; final proceedings metadata was not verified.

9. Kalan, M. M., Deng, Y., Neugut, E. J., & Kpotufe, S. (2025). *Neyman–Pearson classification under both null and alternative distributions shift* [Preprint]. arXiv. [https://doi.org/10.48550/arXiv.2511.06641](https://doi.org/10.48550/arXiv.2511.06641). [Author record](https://arxiv.org/abs/2511.06641); submitted November 10, 2025. No peer-reviewed venue verified.

## Search boundaries

The review used publisher pages, official journal records, author manuscripts, and author-institution repositories. Search themes combined 2024–2026 lateral movement, false alarms, imbalance/resampling, asymmetric benign support, class-specific error control, Neyman–Pearson classification, and alert capacity. Bibliographic dates were checked against primary records rather than search-engine age labels. The [earlier benign-label note](../tabular_followup/BENIGN_LABEL_NOVELTY_NOTE.md) and [earlier novelty review](../tabular_followup/NOVELTY_POSITION.md) were read before drafting; their cautions remain in force.

This note is complete as a literature-supported proposal input. **The proposed protection method has not been run or shown to work.**
