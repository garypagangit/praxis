# Exfiltration recognition and stage-expert fusion: literature and feasible experiments

**Reviewed:** September 22, 2026. **Status:** literature note aligned with the implemented [design](DESIGN.md), [protocol](protocol.json), and [runner](run.py); no experimental result is asserted here. Experiments 1 and 2 below describe the fixed-configuration pilot. Feature-view loss and chronological DEDALE analysis are separate future extensions, not tests performed by this pilot. This is a bounded primary-source review, not a systematic review or a guarantee of novelty. All previously used SCVIC data remain exposed development data. A new source freeze cannot make those observations an untouched confirmation set.

## Decision in plain language

**Worth testing, with a narrower claim:** can the system correctly say *this is exfiltration*, rather than merely *something is malicious*? Measure whether an exfiltration specialist adds information beyond a fixed-configuration general model and simple feature engineering, and count the normal flows and other attack stages it mistakenly calls exfiltration. The implemented pilot uses complete feature views; changing feature availability is a follow-up question.

The ingredients already have direct precedent. Exfiltration-specific directional features, neural/tree combinations, temporal ensembles, and calibrated expert fusion are established. The credible pilot contribution would be a controlled account of **which re-encoded features and which specialists improve exact-stage ranking or recognition, and at what false-stage cost**. A later study could extend that account to declared feature-availability conditions. These are applied empirical contributions whose strength still depends on results and independent attack executions.

## Eight primary sources and their limits

### 1. Closest exfiltration paper: Cai et al. (2025)

**Peer-reviewed journal article.** [Publisher DOI](https://doi.org/10.1109/ACCESS.2025.3567772); [university-hosted version of record](https://kyutech.repo.nii.ac.jp/record/2001922/files/10463076.pdf); [author code](https://github.com/cxjuan/EDXGB-for-APT). Full PDF inspected, especially Sections III–VI and pp. 81808–81810, 81818–81819.

EDXGB feeds DNN/CNN representations to XGBoost and evaluates multiclass predictions, including exfiltration precision/recall/F1, on SCVIC-APT-2021 and Unraveled-2023. Packet/byte transfer metrics distinguish directional transfer conditions. Reconstructed, oversampled evaluation sets differ from our unchanged original-class query rows. Reported SCVIC exfiltration recall varies substantially: for the size-limited condition, DNN/CNN variants average 12.13%/7.22%. Section VI identifies precision, computation, and alternative-protocol limitations.

The inspected methods do not establish campaign-disjoint or feature-fingerprint-disjoint partitions. I did not identify a calibrated false-exfiltration budget or a missing/delayed-view experiment in the inspected sections; this bounded observation is not a claim about all associated code. **Exact-stage exfiltration, directional features, and neural/tree fusion are already prior art.**

**APA:** Cai, X., Zhang, H., Ahmed, C. M., & Koide, H. (2025). Detecting advanced persistent threat exfiltration with ensemble deep learning tree models and novel detection metrics. *IEEE Access, 13*, 81803–81822. https://doi.org/10.1109/ACCESS.2025.3567772

### 2. Why simple ensembles may not help: Revell et al. (2026)

**Peer-reviewed journal article.** [Full text](https://www.techscience.com/CMES/v147n1/67129/html). Sections 3.7, 5.4, and 6.2–6.5 inspected.

The authors compare probability averaging and majority voting across three few-shot meta-learners on UQ-IoT-IDS. Section 6.4 says these combinations do not consistently surpass the strongest member; shared class-specific errors limit gains. Section 6.5 proposes richer flow/session context for subtle attacks. This supports measuring complementary errors before constructing a fusion model. Their stage-wise scenario concerns variants of IoT attacks, not our six SCVIC stages or an exfiltration experiment. Our proposed supervised-tree evaluation is not a replication of their meta-learning study.

**APA:** Revell, L., Kang, H., Seo, J. T., & Kim, D. D. (2026). Systematic evaluation of few-shot learning for unseen IoT network attack detection. *Computer Modeling in Engineering & Sciences, 147*(1), Article 45. https://doi.org/10.32604/cmes.2026.078467

### 3. Closest calibrated feature-expert fusion: Nweke (2026)

**Peer-reviewed journal article, published July 11, 2026.** [Full text](https://link.springer.com/article/10.1007/s10791-026-10343-2). Sections 3.2, 4.5, 5, and 11 inspected.

This study combines timing/volume and semantic autoencoders with a CUSUM timing detector. Baseline-only calibration maps expert scores to tail probabilities; Fisher-style fusion is thresholded on separate benign windows. It reports fixed-FPR detection and feature/expert ablations on SGSim IEC 61850 traces. Missing protocol-specific values receive indicators and imputation. Its deployed decision is binary anomaly detection; DoS/FDI labels support stratified analysis, not supervised stage prediction. The authors explicitly limit generalization to real substations and broader attacks. Thus neither feature-specialized experts, missing indicators, nor benign-calibrated fusion is new. “Availability expert” here concerns disruption attacks, not availability of an input feature view.

**APA:** Nweke, L. O. (2026). Tail-calibrated mixture of experts for ultra-low false-alarm intrusion detection in IEC 61850 communications. *Discover Computing, 29*, Article 434. https://doi.org/10.1007/s10791-026-10343-2

### 4. Temporal and multimodel integration: Cheng et al. (2025)

**Peer-reviewed journal article, published July 22, 2025.** [Full text](https://www.mdpi.com/2079-9292/14/15/2924/html); [publisher PDF](https://mdpi-res.com/d_attachment/electronics/electronics-14-02924/article_deploy/electronics-14-02924.pdf). Methods and Section 5.1 inspected.

TSE-APT combines RF, MLP, and BiLSTM using attention-based model weights, temporal statistics, and static context. Its evaluation uses CIC-IDS2018. The authors explicitly acknowledge that this dataset does not establish the long-duration, multi-stage APT behavior claimed as the motivating problem and propose further APT-focused validation. It is direct precedent for adaptive multimodel traffic fusion and temporal features, but not independent evidence that such a model reconstructs a complete APT campaign. We should not repeat its broad APT claims from an ordinary traffic-classification result.

**APA:** Cheng, M., Xiang, G., Yang, Q., Ma, Z., & Zhang, H. (2025). TSE-APT: An APT attack-detection method based on time-series and ensemble-learning models. *Electronics, 14*(15), Article 2924. https://doi.org/10.3390/electronics14152924

### 5. Explicit temporal flow information: Luay et al. (2026)

**Peer-reviewed journal article, published April 28, 2026.** [IEEE record and abstract](https://ieeexplore.ieee.org/document/11498288/); [author-university metadata](https://about.uq.edu.au/experts-publication/24474/4748). Scope verified from the publisher abstract; full experimental details were not independently audited in this review.

NF3 adds timestamps and inter-arrival statistics to NetFlow benchmarks and compares Transformers, LSTMs, and one-dimensional CNNs. The publisher abstract reports larger multiclass than binary gains from temporal information. This supports testing temporal context, not assuming it will improve our exfiltration class. Its reported improvements are not transferable performance estimates for SCVIC or DEDALE. Completed per-flow summaries cannot substitute for a validated past-only sequence of observations.

**APA:** Luay, M., Layeghy, S., Noorbin, N., Sarhan, M., Kulatilleke, G., Moustafa, N., & Portmann, M. (2026). Time matters: Temporal NetFlow features for ML-based network intrusion detection. *IEEE Access, 14*, 66899–66913. https://doi.org/10.1109/ACCESS.2026.3688204

### 6. Host/provenance context and scarce attack labels: DUPIN

**Peer-reviewed USENIX Security 2026 proceedings.** [Official paper record](https://www.usenix.org/conference/usenixsecurity26/presentation/bae). Official abstract and proceedings metadata rechecked; the earlier project review inspected the author manuscript.

DUPIN pretrains on extensive audit-event provenance and then uses limited attack supervision. Its reported evaluation spans 25 APT campaigns across four sources. This is direct precedent for combining abundant context with few attack labels. Our numerical flow table does not contain its process/file causal information; renaming a flow ensemble “provenance reasoning” would not recreate that capability. It is contextual prior art, not an equal-data baseline we can claim to reproduce cheaply.

**APA:** Bae, C., Ding, H., Ma, S., & Zhang, X. (2026). DUPIN: Attack learning is still needed! Demonstrating few-shot after unsupervised pretraining is a nimble forensics learner. In *35th USENIX Security Symposium (USENIX Security 26)* (pp. 2287–2306). USENIX Association. https://www.usenix.org/conference/usenixsecurity26/presentation/bae

### 7. Inferring relations in sparse APT evidence: APMP

**Peer-reviewed journal article, published May 26, 2026.** [Full text](https://link.springer.com/article/10.1186/s42400-026-00592-5). Publisher methods/discussion were inspected in the preceding literature review; metadata and scope rechecked today.

APMP uses predicted entity relations to enrich provenance evidence under limited attack labels. Its discussion retains dependencies on label/seed quality and generalization to unfamiliar behavior. Context enrichment and relational completion are therefore already APT research topics. Masking flow features neither replicates this graph problem nor demonstrates that actual missing audit events can be recovered. Our claim must name the information truly observed.

**APA:** Li, J., Li, T., Zhang, R., Wan, Z., & Yang, Z. (2026). Apmp: APT attack detection in few-shot scenarios based on entity potential relations. *Cybersecurity, 9*, Article 172. https://doi.org/10.1186/s42400-026-00592-5

### 8. Data for a chronological case study: DEDALE

**Peer-reviewed workshop proceedings, first online May 1, 2026.** [Publisher chapter](https://link.springer.com/chapter/10.1007/978-3-032-16092-8_1); [official dataset](https://doi.org/10.57745/Y5JLDG); [author labeling code](https://gitlab.inria.fr/mlanvin/dedale_labeling). Chapter abstract/metadata inspected; implementation facts below use our separately qualified local artifacts.

DEDALE includes network and system logs across benign periods and a multi-day APT scenario, with an open testbed for replication. It supports temporal correlation research. The existence of timestamps and multiple labels does not create multiple independent campaigns.

**APA:** Lanvin, M., & Majorczyk, F. (2026). Get out of DEDALE with RESCOUSSE: A new dataset and testbed for evaluating the detection of APT attacks among network and system logs. In R. Laborde, J. Garcia-Alfaro, G. Blanc, P.-F. Gimenez, H. Kalutarage, N. Yanai, A. Shukla, S. Pirbhulal, J. Posegga, & K.-Y. Lam (Eds.), *Computer security. ESORICS 2025 international workshops* (Lecture Notes in Computer Science, Vol. 16232, pp. 3–23). Springer. https://doi.org/10.1007/978-3-032-16092-8_1

## The defensible gap

> In an exposed six-stage development benchmark with matched attack fitting identities, evaluate whether directional-feature engineering and stage-specialist fusion improve exact exfiltration ranking or recognition beyond equally informed fixed-configuration general classifiers, while quantifying false exfiltration labels on normal and other-stage traffic.

The implemented pilot addresses this question with complete feature views. Measuring how any advantage changes under simulated feature-view unavailability remains a future extension.

This is a proposed **controlled application question**, not a claim that the field has never used the components. The closest papers establish substantial overlap. What our actual experiment can add is a reproducible comparison with a fixed endpoint, equal information, independent selection/measurement roles within development, and explicit costs. A positive result would justify fresh campaign-level confirmation, not establish broad reliability or a novel algorithm.

## Available data and measurement boundaries

The current SCVIC `DATA.npz` contains 73 numerical features and six labels. Checked feature names include forward/backward byte and packet totals, packet sizes, flow/IAT summaries, bulk/subflow statistics, and TCP flags. The prepared table **has no host identities or chronological timestamps**. Existing `Flow Bytes/s`, `Flow Packets/s`, and `Down/Up Ratio` mean some proposed “new” rate features would be redundant.

Forward/backward is the flow extractor's direction. Without verified host-role orientation it is not automatically victim-outbound versus external-inbound. Within-flow IAT variability is not a measured sequence of cross-flow bursts. Final flow totals are available at flow completion, so their accuracy alone cannot demonstrate early warning.

The [local DEDALE qualification](../lateral_protection_experiment/dedale/QUALIFICATION.md) covers 16 acquired days: 71 author-labeled attack flows, including **two exfiltration flows**, plus 21 attack-related rows kept distinct from malicious and normal. All belong to one documented campaign. Raw flow identities/times can support a chronological case study after timestamp and direction checks. The earlier lateral-only prepared stress table excludes exfiltration and must not be reused as an exfiltration test. No new data acquisition or modeling was performed for this note.

## Implemented Experiment 1: Feature engineering and an exfiltration specialist

**Question:** Can we improve exact `DataExfiltration` recognition rather than an already strong any-attack decision?

The frozen pilot uses the existing partitions and three fitting seeds, 20260922–20260924. Each seed provides the same 1,184 fitting rows to every arm: 1,024 normal and 32 from each of five attack classes. Calibration labels are additional information, not part of this fitting count. Eighteen deterministic additions, specified exactly in `engineered()` in [run.py](run.py), include:

- Log-ratios or bounded asymmetry of forward/backward bytes and packets.
- Bytes per packet and directional size asymmetry.
- IAT/active-time variation and duration-normalized summaries, with explicit zero/missing handling.

Call these directional summaries until victim-relative orientation is verified. Predictors exclude source IPs, file names, absolute capture time, author stage fields, and future traffic. Median imputation is fitted inside each training fold. Test rows retain their original class labels and are not oversampled. XGBoost and LightGBM use the fixed configurations in the protocol, with no hyperparameter search or class weighting. These are bounded pilot controls, not tuned state-of-the-art baselines.

| Arm | Features/model | What it isolates |
|---|---|---|
| A | Fixed-configuration six-class tree, original 73, separately for XGBoost and LightGBM | General-classifier baselines |
| B | Same tree and fitting budget, engineered additions | Representation change alone |
| C | Exfiltration-versus-rest specialist, same original inputs | Specialization alone |
| D | Specialist with engineered additions, separately for each family | Feature benefit within the specialist task |
| E | Fixed averages and learned general-plus-specialist fusion | Whether combining the available scores adds value |
| F | General-only averaging and learned general-only fusion | Whether specialist information adds value beyond combining/reweighting general scores |

All six-class outputs remain available; a binary specialist alone is not a completed six-stage classifier. Learned fusion uses regularized logistic regression with fixed C=1 on clipped-logit base scores from three-fold cross-fitting. Each fitting row is scored by base models and imputers that did not fit that row. Calibration/test rows do not fit base or fusion models. Binary experts treat every competing stage, as well as normal traffic, as negative. Comparisons disclose calibration labels as an additional information cost.

**Primary descriptive endpoint:** exfiltration-versus-all **average precision (AP)**. Secondary exact-exfiltration precision, recall, F1, and confusion counts use a threshold maximizing F1 on the original calibration partition, with higher thresholds breaking ties. Report ROC-AUC and separate false exfiltration labels from normal traffic and every other stage. Additional thresholds use nominal 0.1%, 0.5%, 1%, and 2% calibration false-positive budgets, separately against normal rows and all non-exfiltration rows. These are comparison points, not acceptance standards or guarantees. Report observed test rates and all improvement/loss directions; there is no global pass/fail improvement magnitude. Binary any-attack recall on true exfiltration is a separate diagnostic and cannot substitute for the correct stage label.

The frozen roster remains visible regardless of results. Complementary-error analysis can explain whether specialists add information, but it must not select a new preferred arm or retune the pilot after observing test outcomes.

## Implemented Experiment 2: Stage-specialist fusion with complete feature views

**Question:** Do separate models for each stage produce a more accurate stage assessment than general models with the same fitting rows and features?

The pilot trains an XGBoost and a LightGBM one-versus-rest expert for every label, including normal traffic, using engineered inputs. It compares individual and averaged general models, general-only learned fusion, averaged specialist scores, specialist-only learned fusion, and fixed/learned general-plus-specialist fusion. Specialist-family score vectors are normalized before fixed averaging; this normalization does not establish probability calibration.

A separate fixed selection arm chooses one family per stage using fit-only out-of-fold AP, with ties favoring XGBoost, then normalizes the six selected scores. This selector is not an input to learned fusion. Learned fusion uses the same strict cross-fitting and fixed logistic settings as Experiment 1; calibration/test rows do not train it.

**Primary descriptive endpoint:** six-class macro-F1. Report precision, recall, F1, AP, ROC-AUC, and confusion for every stage, plus separate any-attack detection. Show stage gains and losses together; an exfiltration gain cannot hide a lateral-movement cost. Three seeds share the same evaluation rows and are not three independent attacks. This experiment evaluates per-flow stage assessment, not temporal progression, missing logs, or loss of a feature view.

## Future extension, not implemented: Fusion under feature-view unavailability

**Question:** Does a fusion rule that receives an explicit availability mask preserve exact-stage recognition better than a general classifier when a defined feature family is unavailable?

Partition the features into predeclared views, such as directional volume/size, timing/activity, and protocol/flags. Train a small set of stage/view specialists using the same fitting labels. Use a general model given **all the same features and missingness indicators**, simple averaging over available experts, and mask-augmented general-model training as controls. Compare any learned availability-aware fusion against these controls, not just an unprepared clean-data model.

Freeze complete-view and whole-view-loss conditions independently of labels. Recompute or remove every dependent feature: for example, masking byte totals while retaining a byte-rate or subflow-byte alias can secretly preserve the supposedly missing information. Apply the same missingness pattern to every method. Training augmentation, imputation, fusion weights, and calibration must use training/selection data only. Report intact performance as well as degradation; a robust but consistently inferior model is not automatically an improvement.

For each condition, report exact-stage confusion, exfiltration recall/F1, normal-to-exfiltration false labels, other-stage-to-exfiltration confusion, total any-attack FPR, abstentions, and runtime. An unavailable expert should not silently produce a confident zero-risk score. A disagreement/unknown output is permissible if its coverage and review burden are counted.

**Correct scope:** this measures simulated *feature-view unavailability*. It does not test real lost or delayed logs, causal evidence recovery, or known sensor failure rates. Actual delay requires event-availability timestamps and a specified arrival process. Mask-dependent calibration must be declared; a clean-data threshold provides no guarantee after masking.

### Future DEDALE extension: a separate chronological demonstration, not run by this pilot

Apply source-locked models to the qualified raw DEDALE flow sequence. Join predicted evidence by observed host-pair/time fields, retain stage disagreements, and show a timeline with source rows and availability times. Author labels are used afterward to score the output, not to supply the stage history to the predictor. Do not force every campaign into a single monotone stage order; stages can repeat or overlap, and context absence is not proof of benignness.

If adding past-only host aggregates, introduce them as a separately frozen feature experiment: verify flow completion/availability times and use only earlier observable events. An early benign-only baseline would be target adaptation and must be labeled as such, with an unadapted source control. The existing two exfiltration flows support detected/missed counts and a worked example, not fitting a temporal deep network or claiming reliable transfer. A campaign picture is a linked evidence display, not attribution of an adversary identity.

## Recommendation and strongest objections

1. **Interpret the implemented CPU pilot through its controls.** Experiment 1 separates feature, specialization, and fusion effects; Experiment 2 measures complete-view stage fusion. Report continuous gains, losses, and stage costs without a blanket pass/fail gate. No GPU is required for these modest fitting sets.
2. **Keep feature-view robustness as a future study.** It is not implemented Experiment 2 and has not been measured by this pilot. Its potential contribution is stage-specific error accounting under known feature availability; expert fusion itself has extensive overlap.
3. **Use DEDALE for a transparent case study, then collect independent executions.** It cannot confirm exfiltration reliability with two correlated flows.

The strongest objections are exposed data, few independent attack executions, extractor/domain shift, small exfiltration support, shared errors across models, implicit label costs, and the possibility that engineered additions merely re-express existing features. None is solved by ensembling alone. Preserve negative results and keep new development findings separate from the completed lateral-protection study.

## Search record

Searches covered exfiltration directional/burst features, APT stage classification, temporal ensembles, mixture-of-experts IDS, and missing-feature fusion. Only publisher, author, conference, and author-university sources support the claims above. An aggregator result for NetBurst-X was not used as verified evidence because the publisher record could not be inspected in this bounded pass. Existing [novelty notes](../tabular_followup/NOVELTY_POSITION.md) remain relevant; no previous experiment, protocol, result, or manuscript was changed.
