# Literature gap for the completed findings

**Review date:** September 21, 2026. **Scope:** bounded current primary-source review for a findings-centered rewrite. This note changes no model, protocol, threshold, endpoint, recorded decision, or experimental artifact. The original development screen remains **INFEASIBLE**. Positive component findings and the unfavorable joint outcome must both remain visible.

## Recommended contribution statement

**This study supplies controlled development evidence about the benefits and stage-specific costs of increasing benign fitting data when attack fitting examples remain fixed: it measures how false alarms, lateral-flow detection, and other stages change across declared benign budgets, then compares weighting and threshold adjustments using the same permitted labels.**

The practical evidence gap is the **joint accounting of benign-data benefit, lateral-detection cost, and the contribution of the operating threshold under a fixed attack fitting budget**. The completed study partially addresses that question for supervised boosted trees on an exposed SCVIC development sample. It does not replicate Revell's meta-learners, establish the first such study, identify an optimal deployment policy, or demonstrate transfer of the proposed candidate. The importance is practical: an improvement in overall score or false alarms can conceal a loss at a dangerous stage.

This is a qualified synthesis of the sources below and our experimental design, not an assertion that every inspected author omitted these questions. A useful applied result need not invent a new algorithm. Whether the bounded contribution meets a particular institution's originality requirement remains a separate academic assessment.

## Closest sources: verified claims, overlap, and boundaries

### 1. Revell et al. (2026): the explicit future-work anchor

**Peer-reviewed journal; publisher full text inspected.** Sections 5.4 and 6.2 discuss benign/attack ambiguity; Section 6.5 proposes asymmetric support, including “allocating a substantially larger support set to the benign class.” Its evaluated models are meta-learners, with a common per-class shot count in Section 4.3. Our supervised-tree budget experiment tests a related published suggestion in a different setting; it is not a replication of those architectures. [Publisher full text, especially §§4.3, 5.4, 6.2, 6.5](https://www.techscience.com/CMES/v147n1/67129/html).

**Boundary:** Larger benign support is prior art. Our contribution can be its measured stage-cost tradeoff and controls, not origination of the idea.

### 2. Smiliotopoulos and Kambourakis (2026): direct lateral-movement overlap

**Peer-reviewed journal; publisher abstract and metadata inspected.** The paper studies 13 models on LMD-2023 Sysmon data and explicitly examines resampling and false-positive/false-negative tradeoffs in lateral detection. Its abstract questions extrapolating general IDS balancing findings to this application. The page exposes a subscription preview; no full-method or future-work omission is inferred. [Publisher abstract and record](https://link.springer.com/article/10.1007/s10207-025-01182-1).

**Boundary:** Neither lateral-specific imbalance evaluation nor attention to both error types is new. Our exact support, label, policy, and stage accounting defines a narrower empirical scope.

### 3. Singhal and Kumar (2026): direct constrained-threshold overlap

**Peer-reviewed journal; publisher full text inspected.** Sections 3.6.2–3.6.4 combine class penalties and validation-selected thresholds with an explicit miss constraint. Section 5 identifies binary ARP scope and offline evaluation as limitations, and multiclass extension as future work. The article also reports a supplementary dataset evaluation, so it must not be characterized as having no cross-dataset experiment. [Primary full text](https://www.frontiersin.org/journals/big-data/articles/10.3389/fdata.2026.1878242/full).

**Boundary:** Weights plus constrained thresholds are established. Our known-stage comparisons and fixed fitting supports extend the empirical question; they do not establish a new general method or a population guarantee.

### 4. Bae et al. (2026), DUPIN: verified conference publication

**Peer-reviewed conference proceedings verified through USENIX.** DUPIN uses extensive benign audit-log pretraining and few-shot attack learning with provenance graphs. The official proceedings list the four authors, venue, and pages 2287–2306. This upgrades the publication status left unverified in the earlier [benign-label note](../../tabular_followup/BENIGN_LABEL_NOVELTY_NOTE.md). [Official proceedings](https://www.usenix.org/conference/usenixsecurity26/presentation/bae); [author full text](https://arxiv.org/html/2609.00259v1).

**Boundary:** Abundant benign information plus scarce attack supervision is already implemented prior art. A small supervised-tree support sweep is a different information budget and representation; no superiority to DUPIN was tested.

### 5. Li et al. (2026), APMP: additional current few-shot APT prior art

**Peer-reviewed open-access journal; primary text inspected.** APMP predicts relations to supplement attack provenance graphs. Its Discussion acknowledges dependence on labeled training data, seed quality, and changing attack behavior. The publisher verifies all five authors, May 26 publication, volume 9, and article 172. [Publisher full text and author metadata](https://link.springer.com/article/10.1186/s42400-026-00592-5).

**Boundary:** Few-shot APT recognition and context completion are established topics. Its seed-supply, entity-level task is not equivalent to our fixed stage-labeled fitting rows. Its performance numbers should not be ranked against our flow metrics.

### 6. Kushwaha et al. (2022): older direct tree-weighting precedent

**Author preprint; peer-reviewed publication not verified here.** Sections 4.2–4.3 use class-weighted XGBoost and neural models for lateral detection; Section 4.5 specifies recall/FPR objectives. The user-grouped data and engineered authentication representation differ from our numerical-flow setup. [Author PDF, pp. 9–11](https://arxiv.org/pdf/2208.13524).

**Boundary:** Even a lateral-focused class-weighted XGBoost model is prior art. Its inclusion prevents an overly narrow review of only 2026 papers from suggesting otherwise.

## How to connect the actual findings to that gap

| Experimental evidence | Positive knowledge it can contribute | Required companion statement |
|---|---|---|
| Matched attack supports with declared benign-budget changes | Quantifies whether additional normal examples improve false alarms and classification in the tested setting. | Report all stage recalls and the additional benign labels. More rows change coverage, proportions, regularization, and possibly selected hyperparameters; this is not a pure causal test of diversity. |
| Natural versus balanced/lateral weighting on identical rows | Measures how training emphasis changes the operating tradeoff without acquiring different fitting examples. | Report both false alarms and lateral detection for every declared weighting cell. Do not select a favorable cell after evaluation and present it as a prospectively validated winner. |
| Locked reference, candidate, and threshold-only ablation | Separates a policy's observed benefit from benefit available by moving the same detector's threshold. | Selection-side false-alarm ordering follows from optimization. Only verification measures whether the improvement persists, and source exposure still limits generalization. |
| Feasible-subset candidate/reference comparison | Six selected seeds showed a descriptive 33.3% false-alarm reduction. | Lateral recall also fell from 88.2% to 84.5%, a 3.70-point loss; four other seeds were infeasible. This is not the ten-seed primary success result. |
| DEDALE source-only controls | Shows actual operating-point behavior under a qualified external shift. | The fixed source candidate was unavailable. These controls do not validate the proposed candidate; four lateral flows represent one execution. |

The numerical conditional finding above is from the project's [audited evidence](../../results/lateral_protection_v1/EVIDENCE.json), not an external publication. Any additional favorable weighting or budget contrast belongs in the rewrite only after its values, matched seed roster, class denominators, and comparison status are checked against those artifacts.

## Recommended wording for a findings-centered praxis

**Thesis:** Under a fixed attack fitting budget, benign-data allocation and training emphasis can produce useful false-alarm improvements, but their value must be judged alongside the detection cost at individual attack stages and the effect of threshold selection.

**Gap:** The reviewed literature motivates richer benign support and already studies imbalance and constrained decisions. The present study adds a bounded, reproducible evaluation of their joint implications for supervised trees: identical attack supports, explicit benign budgets, identical-row weighting comparisons, a threshold-only ablation, stage-specific outcomes, and a full label ledger. This addresses an operational evidence question rather than claiming new mathematical machinery.

**Outcome:** The completed evidence can support particular favorable component comparisons while also showing that the tested procedure did not satisfy its stricter joint engineering screen. The screen's 90% recall, 1% FPR, greater-than-20% reduction, less-than-three-point loss, and all-ten-feasible requirements were investigator-chosen development requirements, not external industry standards. Their self-imposed origin does not license changing their recorded result after seeing outcomes.

**Limit:** These exposed-source findings identify tradeoffs and useful candidate practices; they do not establish guaranteed lateral preservation, an optimal policy, independent incident-level benefit, measured analyst-time savings, or a proven novel algorithm. A new question motivated by favorable contrasts requires new confirmation data and a prospective analysis.

## APA-style references

Bae, C., Ding, H., Ma, S., & Zhang, X. (2026). DUPIN: Attack learning is still needed! Demonstrating few-shot after unsupervised pretraining is a nimble forensics learner. In *35th USENIX Security Symposium (USENIX Security 26)* (pp. 2287–2306). USENIX Association. [Official proceedings](https://www.usenix.org/conference/usenixsecurity26/presentation/bae).

Kushwaha, D., Nandakumar, D., Kakkar, A., Gupta, S., Choi, K., Redino, C., Rahman, A., Chandramohan, S. S., Bowen, E., Weeks, M., Shaha, A., & Nehila, J. (2022). *Lateral movement detection using user behavioral analysis* [Preprint]. arXiv. [https://doi.org/10.48550/arXiv.2208.13524](https://doi.org/10.48550/arXiv.2208.13524).

Li, J., Li, T., Zhang, R., Wan, Z., & Yang, Z. (2026). Apmp: APT attack detection in few-shot scenarios based on entity potential relations. *Cybersecurity, 9*, Article 172. [https://doi.org/10.1186/s42400-026-00592-5](https://doi.org/10.1186/s42400-026-00592-5).

Revell, L., Kang, H., Seo, J. T., & Kim, D. D. (2026). Systematic evaluation of few-shot learning for unseen IoT network attack detection. *Computer Modeling in Engineering & Sciences, 147*(1), Article 45. [https://doi.org/10.32604/cmes.2026.078467](https://doi.org/10.32604/cmes.2026.078467).

Singhal, S., & Kumar, K. A. (2026). A cost-sensitive random forest framework for ARP spoofing detection in Internet of Medical Things networks. *Frontiers in Big Data, 9*, Article 1878242. [https://doi.org/10.3389/fdata.2026.1878242](https://doi.org/10.3389/fdata.2026.1878242).

Smiliotopoulos, C., & Kambourakis, G. (2026). Machine learning for lateral movement detection using Sysmon logs: An empirical comparison of imbalanced and resampled data. *International Journal of Information Security, 25*, Article 38. [https://doi.org/10.1007/s10207-025-01182-1](https://doi.org/10.1007/s10207-025-01182-1).

## Review record and limits

The review reopened the three anchor publisher pages, inspected the stated future-work passages, checked the newer graph-based APT sources, and searched combinations of asymmetric benign support, few-shot lateral movement, class weighting, and false-positive control. It also read the existing [benign-label novelty note](../../tabular_followup/BENIGN_LABEL_NOVELTY_NOTE.md) and [earlier novelty position](../../tabular_followup/NOVELTY_POSITION.md). Search absence is not evidence of first use. The six sources serve different roles; they are not six head-to-head experimental baselines.

No new models were run for this review. Publication status is stated as verified on the review date. The old notes remain historical records; this file supplies the current DUPIN publication correction without silently rewriting their prior verification status.
