# Novelty position: rare-stage review under scarce attack labels

Literature check: September 21, 2026. This note changes no frozen experiment, score, threshold, or success criterion.

**The broad method is already covered by prior work.** Combining tabular foundation models, tree models, conformal uncertainty, few-shot learning, and a rescue path is not a defensible first-method claim. Our narrower applied question remains testable: can complementary models recover dangerous, sparsely labeled known stages at a prespecified benign-review budget? A positive development result would justify further validation; it would not establish algorithmic novelty or operational readiness.

## Closest 2026 work: what is actually verified

Zöller and Lawall's *Reliable Intrusion Detection via Conformalized Tabular Foundation Models* appears in the [official IEEE CSR program](https://www.ieee-csr.org/2026-conference-program/) and [program handbook](https://www.ieee-csr.org/wp-content/uploads/2026/08/csr2026_program-handbook_final.pdf). The full article was not obtained in this bounded search. Its exact label budgets, calibration provenance, split construction, checkpoint versions, and detailed guarantees remain unverified.

An accessible primary source provides substantially more evidence than its title: Lawall's [35-slide keynote](https://www.dtrsociety.org/wp-content/uploads/library/porto2026/keynotes/CYBERSEC2026_02_002.pdf), dated **June 8, 2026**, linked from the [conference contribution record](https://www.dtrsociety.org/library/contribution/cybersec2026_02_002/).

| Evidence | Verified scope | Boundary |
|---|---|---|
| Slides 21–27, Part II; slide 21 explicitly cites the CSR paper | TabPFN; APS and Mondrian prediction sets; IDS2017, IDS2018, and IDS2017→IDS2018 transfer; alpha=.1 and class-dependent set expansion. | Exact fitting counts and source-versus-target calibration details are unavailable. The presentation does not establish valid coverage after arbitrary distribution shift. |
| Slides 28–34, separate Part III | LightGBM with Mondrian uncertainty; singleton fast path, nonsingleton TabPFN rescue, empty-set rejection; Lycos-Unicas-IDS2018 with DoS Hulk withheld; adaptation with k≤50 examples. | This related hybrid work must not automatically be attributed to the CSR article. Four attack categories are excluded, including a 50-row category. |

Thus, foundation-model transfer with limited context and conformal uncertainty has direct precedent, as does tree-to-foundation rescue with few-shot adaptation. The slides do not identify our exact stage-pair score and benign-only budget split. **That is a limited difference in the inspected presentation, not proof that the full article or wider literature omits it.**

## Other nearest primary sources

| Source and evidence level | Models, data, budget or error control | Implication for this project |
|---|---|---|
| García et al. (2025), [*Foundation Models for Cybersecurity*](https://www.mdpi.com/2079-9292/14/19/3792), [publisher full text](https://mdpi-res.com/d_attachment/electronics/electronics-14-03792/article_deploy/electronics-14-03792.pdf); read methods and discussion | TabPFN/TabICL versus tree and other baselines on CIC-IDS2017, N-BaIoT, CIC-UNSW; rare-class recall is central. Methods contain inconsistent caps: §3.3.1 says 2,000/class for both TFMs, while other sections say TabPFN 3,000/class. Classical models use different sampling. | Neither TFM intrusion detection nor rare-threat recovery is new. §5.2–5.3 also **proposes** traditional-model screening → TabICL → LLM explanation; its operational example is not a measured cascade experiment. Our matched 32/class comparison is a narrower evaluation. Evaluating several datasets is not automatically zero-target-fit transfer. |
| Ruiz-Villafranca et al. (2024), [*A TabPFN-based intrusion detection system for the industrial internet of things*](https://link.springer.com/article/10.1007/s11227-024-06166-x); publisher full text | Edge-IIoTset; TabPFN versus RF/XGBoost/LightGBM; 250, 500, 750, and 1,000 training examples; binary and multiclass tasks. | Small-label TFM intrusion detection predates this batch. A new checkpoint or smaller budget alone is weak novelty. |
| Ding, Fermanian, and Salmon (2025), [*Conformal Prediction for Long-Tailed Classification*](https://arxiv.org/html/2507.06867v1); author preprint full text | Prevalence-adjusted scores and label-weighted interpolation between marginal and classwise calibration; large, imbalanced species-image datasets. | Rare-class calibration and reweighting are established research topics. Different application labels do not make those mechanisms new. |
| Tong, Feng, and Li (2018), [*Neyman-Pearson classification algorithms and NP receiver operating characteristics*](https://jsb-lab.org/wp-content/uploads/2018/02/ScienceAdvances_eaao1659.full_.pdf); author manuscript | Classification with prioritized error control and threshold selection. | A benign-tail threshold is not new mathematics; our empirical budget must not be advertised as their high-probability NP certificate. |
| Youssef (2026), [*CALIBURN*](https://arxiv.org/html/2605.24696v1); author preprint full text, peer-review status unverified | Streaming change detection, isotonic calibration, cost thresholds and alert-budget controls on LITNET2020, CIC-IDS2017 and UNSW-NB15. | Operational alert burden and calibrated thresholding are already explicit objectives. Its streaming regime differs from our fixed scarce-label, known-stage review study. |

## The narrower constraint we can test

The [frozen design](RARE_STAGE_DESIGN.md) and [protocol](protocol_rare_stage_gate.json) specify:

- **Identical scarce fitting labels:** 32 per class across six classes, including NormalTraffic; 192 unique labels shared by TabICL and the training-CV-selected tree model.
- **Two fixed scores:** general attack probability plus the maximum rare-versus-normal probability ratio over InitialCompromise/DataExfiltration and the two model families.
- **A fixed workload target:** two benign-only upper-tail thresholds, each allocated .5% nominal error, with OR routing. Calibration uses **29,929 additional benign labels**. This is not a system needing only 192 total labels.
- **A demanding comparison:** improve the worse of the two rare-stage recalls by at least five percentage points against each single-model control, protect other stages, and stay below 1.5% observed benign routing in every seed. A TabICL-only rescue ablation tests whether the second model contributes.

This differs in its stated constraint from classwise uncertainty sets or adapting to an unseen attack. It remains an empirical combination of established operations. A routed case is an analyst-review request, not a correctly identified stage or a solved incident. The source split does not establish the exchangeability needed for a future false-alarm guarantee.

## Claims and praxis decision

| We can report if supported by the frozen results | We cannot currently claim |
|---|---|
| Matched-label development performance and the measured rare-stage recall/workload trade-off, including failure. | First TFM intrusion detector, first TFM/tree rescue system, first conformal IDS, or first few-shot transfer method. |
| A zero-target-fit **binary** model-transfer check on independent Sandworm data. | Independent validation of the rare-stage improvement: Sandworm has 37 attack flows and different procedure labels, not the source six-stage taxonomy. |
| Whether the second model adds useful rescue beyond score engineering and both single-model controls. | New mathematical error control, reliable unseen-campaign detection, or deployment-ready alert burden. |

**Recommendation:** finish the frozen tests, then decide. A passing gate could support an applied praxis about protecting scarce, dangerous known stages under a measured review budget, provided stronger baselines and independent stage-labeled incidents confirm it. InitialCompromise has only 15 development-test rows; ten reused seed runs are not ten independent incidents. If the gate fails, preserve the negative result rather than declaring a novel improvement. Neither dataset recency nor changing TabPFN to TabICL resolves the novelty issue.

## Search and evidence record

Exact-title, official IEEE program, author/project, arXiv, and Crossref searches did not yield accessible CSR article full text. This is an access limitation, not evidence of absence. The keynote is a primary author presentation; it is not a substitute for the peer-reviewed article's complete methods. No account creation, author contact, or access-control bypass was used. The broader comparison is bounded, not a systematic review or novelty guarantee.

Private retained source hashes (PDFs and derived page images are not republished):

- Lawall keynote: SHA-256 `3efc19de776bd4f8ebe0eba23609e34bc660eaaa2bea3382371bf5ad51d03b9e`; 3,217,029 bytes; 35 pages.
- García publisher article: SHA-256 `f9c46d7a359b93892648a2487686431c1b3ba68f1f009230ea731959d7a89419`; 1,006,914 bytes; 29 pages.
