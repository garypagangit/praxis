# Review of the proposed APT experiment batch

The batch contains testable research questions. Its promises of guaranteed positive results and several first-use claims do not survive the source and data checks. The [measured results](../results/tabular_batch_v1/REPORT.md) distinguish completed tests from work that remains untested.

| Idea | Assessment of the proposed contribution | Actual evaluation scope |
|---|---|---|
| E0: qualify four datasets | Essential preparation; passing a data check is not a predictive improvement. | All four source/data routes reviewed. SCVIC supports a 32-per-class development comparison. DSRL is a synthetic derivative of DAPT2020. S-DAPT remains unqualified. |
| E1: foundation models with few APT labels | APT stage-specific evidence may be useful, but broad foundation-model intrusion detection already exists. Exact APT-specific novelty is not established. | Thirty classical cells completed. The frozen full comparison requests ten seeds and two foundation models. A separate three-seed CPU prescreen evaluates all attack test rows and a fixed normal sample; its weighted scores are estimates. |
| E2: foundation screen followed by trees | The motivating paper already proposes this architecture. Implementation could establish practical value, but implementation alone does not establish method novelty. | A same-CPU necessary-speed test completed. It measures the screen alone against the full stage classifier. The complete cascade, accuracy frontier and GPU configuration were not evaluated. |
| E3: gradient-based label checking | The named approach already exists. A security-specific contribution would need a meaningful improvement or new failure analysis. | Two explicitly documented adaptations were tested with 0% and 20% symmetric noise, three seeds and fixed XGBoost settings. This is not the full 5–30% symmetric/asymmetric grid or an exact Gradients reproduction. |
| E4: conformal foundation predictions | The claim that foundation-model IDS lacks conformal work is contradicted by direct prior art. Coverage assumptions and useful set sizes require separate evaluation. | Classical prediction sets were measured at 90%/95%, both marginal and class-conditional. The registered foundation-model comparison remains incomplete. |
| E5: bound misses on an unseen stage | Calibration on known stages cannot by itself certify arbitrary unseen-stage misses. A useful empirical fusion is possible, but its guarantee needs a valid target population and assumptions. | Not fitted. The requested qualified S-DAPT artifact is unavailable; no unseen-stage certificate is claimed. |
| E6: predict the next S-DAPT stage | First external use is unverified. Alert correlation and next-stage forecasting are different tasks, so the proposed KNN comparator needs task qualification. | Not fitted. Corrected source, raw sequence structure, license and causal feature availability must be established first. |
| E7: GRANDE | The original paper includes phishing detection, defeating the proposed first-security-use claim. | Optional model arm not run. |

## Primary literature that changes the assessment

- **Foundation-model IDS:** [Electronics 2025 study](https://doi.org/10.3390/electronics14193792). An APT-specific setting would need a more precise contribution than applying the model family to security.
- **Hybrid screening:** [Al-Dahmani et al., 2026 preprint](https://arxiv.org/html/2604.11394v1) explicitly proposes the binary-screen/detailed-ensemble pipeline. Its reported 40-fold comparison is against Random Forest; it is not a guaranteed speed advantage over a tuned shallow GBDT in our setting.
- **Conformal IDS:** the [IEEE CSR 2026 program](https://www.ieee-csr.org/2026-conference-program/) lists *Reliable Intrusion Detection via Conformalized Tabular Foundation Models*. The full technical scope was not independently inspected; its existence already makes the broad novelty claim unsafe.
- **Uncertainty limitations:** [Costa et al., ESANN 2026](https://www.esann.org/sites/default/files/proceedings/2026/ES2026-261.pdf) study foundation-model uncertainty on 112 tabular datasets. Conditional coverage weakness is already a research topic.
- **Label treatment:** [Gradients primary manuscript](https://arxiv.org/html/2409.08647v2). Our method document identifies adaptation choices; its result cannot be attributed to a faithful reproduction of that paper.
- **Risk control:** [Conformal Risk Control](https://arxiv.org/html/2208.02814v4). Its assumptions do not disappear when an anomaly detector is added.
- **S-DAPT:** the [arXiv record](https://arxiv.org/abs/2601.06690) records withdrawal for analysis errors. A [later SSRN posting](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6603942) exists, but a posting alone does not qualify a corrected, downloadable, licensed dataset.
- **GRANDE:** the [ICLR 2024 paper](https://openreview.net/pdf?id=XEFWBxi075) includes a PhishingWebsites case study.

## Decisions fixed before foundation stage scores

The full protocol fixes TabICL as the primary candidate and reports TabPFN as secondary. This differs from the proposal's TabPFN-named success criterion; the choice was fixed before foundation stage-classification performance was observed. GBDT selection uses training-only cross-validation. Neither model family nor a winning seed is selected using test performance.

The separate CPU prescreen was registered after classical scores were known because AWS sign-in was unavailable. It keeps all 858 attack rows, samples 1,024 normal rows, and reports prevalence-adjusted estimates plus raw false-alarm counts. Three seeds reuse that same normal sample. No significance, full-query equivalence, independent-incident performance or E4 result follows from this prescreen. Earlier E2 binary predictions were used for timing; their classification quality was not evaluated.

## What would support a praxis decision

The next evidence gate is the complete frozen foundation comparison, followed by qualified independent author-holdout or incident data. A positive development score would justify that work; it would not establish novelty or operational reliability.

This batch concerns scarce labels, noisy labels and uncertainty. It does not test resilience when supporting logs are missing or delayed. That earlier research question requires a separately specified telemetry-loss experiment with a useful complete-evidence control.
