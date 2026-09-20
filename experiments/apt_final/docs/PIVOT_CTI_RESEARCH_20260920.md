# CTI opportunities for an executable APT praxis

Research date: 2026-09-20. Status: literature and artifact screening; **no new positive experiment has been run**.

## Recommendation

A pivot from anomalous-node detection to **extracting reliable attack behaviors from intelligence reports** is executable with public, labeled data. It is a change of task: better ATT&CK mapping can assist APT investigation, but does not demonstrate detection of an intrusion or identification of its perpetrator.

My strongest CTI candidate is **behavior mapping that resists misleading actor identity cues**. It has a clear operational problem, small public data, and an inexpensive falsification experiment. Its novelty is conditional, because counterfactual evidence filtering, contrastive learning, and ordinary entity masking already exist. A second candidate is **dependence-aware APT shortlisting**, but its attribution ground truth and sample size make it a weaker first investment.

Do not describe either as a proven positive praxis. The next result must be a held-out improvement over strong controls, not a good score on a changed split or an invariance property that follows directly from the implementation.

## What the recent literature rules out

| Primary source | What already exists | Consequence for us |
|---|---|---|
| [Büchel et al., USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/buechel) | Unified comparison of TTP extraction methods; traditional NLP can outperform generative systems in realistic settings; ontology ambiguity remains a limitation. | Start with small supervised models and realistic document splits. A larger LLM alone is weak novelty. |
| [Lange et al., LREC-COLING 2024](https://aclanthology.org/2024.lrec-main.103/) | Expert annotations and linking of explicitly and implicitly expressed ATT&CK concepts in reports. | Use the existing gold labels; do not replace them with an LLM's opinion. |
| [Cheng et al., EuroS&P 2025, CTINexus](https://arxiv.org/abs/2410.21060) | Retrieved demonstrations, hierarchical entity alignment, and long-distance relation prediction. | Generic entity canonicalization or a graph of extracted CTI is already covered. |
| [Alam et al., AthenaBench, 2025](https://arxiv.org/abs/2511.01144) | Anonymized threat actor attribution and evaluations of Qwen-family and other models; the paper reports only 39% attribution accuracy for its best tested model. | Substituting Qwen for a classifier is not a novel contribution. The reported number is the authors' historical benchmark result, not our experiment or a current universal model ranking. |
| [DTGBI-TM, Electronics, December 2025](https://www.mdpi.com/2079-9292/14/24/4958) | Dual-tower TTP matching with hierarchical hard negatives and soft/hard supervision. | Hierarchy plus contrastive matching is already disclosed. |
| [CTIArena OpenReview manuscript, 2025](https://openreview.net/pdf/2d1cfedb304f8c4be2d7471333b42d79173b2295.pdf) | Appendix describes counterfactual removal of incidental entities and temporal evidence prioritization. | Generic counterfactual CTI filtering cannot be claimed new. This is a dated preprint disclosure; the [2026 CTIConnect version](https://arxiv.org/html/2510.11974v2) differs, and this audit does not assert the same implementation is in the final version. |
| [MLDSJ, Journal on Information Security, 2025](https://link.springer.com/article/10.1186/s13635-025-00222-6) | Text, TTP, and graph features fused with Dempster–Shafer evidence; explicit discussion of imbalance and overlapping behaviors. | Fusion, confidence, and uncertainty in APT attribution are established. Dependence between views needs an explicit comparison, not a claim that fusion is new. |
| [TTP-MAS, official CSCWD 2026 program](https://fyust.edu.cn/gjhyqk/cscwd2026/program.pdf) | A paper titled “TTP-MAS: A Collaborative Multi-Agent System for Uncertainty-Aware TTP Extraction” is listed. | “Uncertainty-aware TTP extraction” is not an unoccupied title or broad gap. Only the program was verified, not its full method or results. |

The [2026 CSEM-CTI article](https://pmc.ncbi.nlm.nih.gov/articles/PMC13320542/) also describes contrastive evidence extraction and explanation-faithfulness evaluation. Thus, “extract evidence and remove irrelevant words” is insufficient novelty by itself.

## Candidate 1: Learn the behavior, not the actor name

**Plain language problem:** A report can mention a famous hacking group, and a model may fill in the things that group usually does instead of identifying what this report actually says happened.

**Thesis to test:** An ATT&CK mapper trained to preserve behavior predictions when incidental actor identities change will make fewer unsupported technique assignments on reports from unfamiliar sources, without losing useful detection of the techniques that are actually described.

### Specific proposed mechanism

Use one fixed small text encoder and multi-label classifier. Train on original evidence sentences plus carefully constrained paired versions in which an actor identity span is replaced by a neutral typed identifier such as `ACTOR_1`. Retain the sentence's actions, objects, operating-system terms, and commands. Penalize disagreement between predictions on the two versions in addition to the ordinary supervised label loss.

Mask **actor/group identity only** in the first experiment. Do not indiscriminately mask tools: “PowerShell” can be direct evidence for T1059.001. Likewise, do not mask a behavior span just because it contains an entity name. This restriction distinguishes a meaningful nuisance intervention from destroying the evidence.

At inference, use a frozen actor-span detector or a fixed public alias list that was prepared before the test. Using gold test annotations to identify spans is permitted only as an explicitly labeled oracle diagnostic, never as the deployed arm. The method does not predict the attacker; actor identity is deliberately treated as a potential shortcut for the **behavior-mapping** task.

### Feasible data and code

Use [AnnoCTR's author repository](https://github.com/boschresearch/anno-ctr-lrec-coling-2024) at commit `d510b6949e1938d47c93a43eedd562dc538439dc` and the [SoK author's implementation](https://github.com/MarvinBuechel/SoK_CTI_TTP) at `52c5e36dda9b4442b2043a4c91da88a0bd5a4664` as the starting reference.

**Important size correction:** AnnoCTR has 400 reports overall, but only 120 have the cybersecurity annotation layer. The repository's relevant text split was verified directly as **70 train / 16 development / 34 test documents**. Do not promise 400 fully TTP-labeled reports.

The AnnoCTR corpus is CC-BY-SA 4.0. Its repository is archived but downloadable. Actual label bytes were fetched and parsed successfully, not merely discovered in a search result:

- File: `AnnoCTR/linking/dev.jsonl`.
- Size: 3,510,715 bytes; 1,542 linking records across entity categories, **not 1,542 independent reports or all technique labels**.
- SHA-256: `e75daf565b8b631126ce4c2d832c209cd6d1f21c2f5af4b2bc13d36f52d92b10`.
- Fields include mention, left/right context, document identity, entity type, linked title, and linked ATT&CK URL. An observed record maps a “Mustang Panda” group mention to G0129; technique records are a separate subset.

No dataset-owner response is required for this academic experiment. Use only ungated encoders; reproducing every SoK arm would be unnecessary and would introduce DarkBERT access requirements and much greater hardware needs. The first lexical/frozen-embedding screen fits on CPU; training a small encoder can use the existing A10G if needed. Runtime must be measured in a smoke test before committing a full budget.

### Smallest fair pilot

1. Freeze the corpus commit, exact relevant labels, aliases, preprocessing, and existing document split. Group near-duplicate reports before any additional split; never split sentences from one report across train and test.
2. Work only with train/development data to confirm enough actor-containing technique examples exist. If fewer than 50 such independent evidence spans, or fewer than five independent reports, the proposed mechanism is insufficiently exposed for even a diagnostic pilot: record a feasibility hold.
3. Compare four arms using the same encoder, labels, training steps, and seeds: ordinary supervised training; masking alone; paired augmentation without consistency loss; paired augmentation with consistency loss. Include a sparse lexical baseline to detect whether the neural contribution is necessary.
4. Choose the one intervention weight and all thresholds using development documents, then freeze. Evaluate the 34 untouched test documents and report **all** runs.
5. Primary measurements: report-level macro F1 and false technique assignments at matched recall on unmodified real reports. Secondary: actor-name sensitivity on paired perturbations, and supported-label precision. Report exact micro F1 for comparison with prior literature, but do not let it hide rare-label failures.
6. A proposed advancement gate is at least a 10% relative reduction in false technique assignments at matched recall, a positive paired document-bootstrap confidence interval, and no more than a one-percentage-point absolute macro-F1 loss. This is a research gate to register before running, not a deployment safety guarantee.
7. Repeat on a source-held-out split or TRAM2 transfer before calling the effect robust. Audit identity and campaign overlap rather than assuming vendor separation means different campaigns.

Perturbed text is a **synthetic diagnostic**, not a separate real attack dataset. An improvement solely on that diagnostic does not satisfy the primary positive-result gate. No new human labels are needed to test existing gold labels, but checking whether a newly alleged false assignment is actually an annotation omission can require an expert review; preserve such cases as unresolved rather than automatically counting the model wrong or relabeling them to help the score.

### Novelty assessment

**Executable: high. Scientific novelty: low-to-medium and conditional.** Entity masking, consistency regularization, and counterfactual CTI filtering are established. A defensible applied contribution would need to establish the specific actor-identity shortcut under document/source shift and demonstrate that a constrained behavior-preserving treatment improves real report mapping beyond masking and augmentation controls. “An LLM checker with entity removal” would not meet that standard. If the baseline has little identity sensitivity, stop this candidate immediately.

## Candidate 2: Avoid counting the same attribution evidence three times

**Plain language problem:** A text model, a technique model, and a graph model may all agree because they read the same claim. Their agreement can create confidence without adding independent evidence.

**Thesis to test:** Discounting dependence among evidence channels improves the accuracy of shortlists at a fixed analyst review budget when some channels repeat the same information or disagree.

### Specific proposed mechanism

Construct actor compatibility scores separately from report behavior, tools/infrastructure, and independently dated actor profiles. On development reports, estimate dependence between the channels' errors. Fit a constrained fusion model that penalizes redundant evidence and emits a candidate set or “insufficient evidence” according to a development-selected rule. Contrast this with a simple average, a stacked logistic model, the best single channel, and a reproducible Dempster–Shafer baseline.

The important comparison is **against an ordinary learned stacking model**, not only against naively multiplying probabilities. Covariance-aware weighting and cautious evidence fusion are not new mathematical ideas. The proposed contribution would be an APT-specific evaluation with explicit independent-source accounting and real report labels.

### Data readiness and limits

[AthenaBench's public TAA file](https://github.com/Athena-Software-Group/athenabench/blob/39d3a74eaf84b93e21dde0a4b60ddd4f08620eaf/benchmark/athena-cti-taa.jsonl) was downloaded and parsed: **100 cases**, 504,834 bytes, SHA-256 `19ddbdab54e97037fa90e1ca50cab6d042455dd8ff8794d6be6b406915326393`. Fields contain report URL, timestamp, description, prompt, answer, and prompt hash. Source code and prior model outputs are public at this commit. Both license files permit academic/educational noncommercial use, with attribution and other conditions; this is not a general-purpose commercial-data license.

Use pinned [MITRE ATT&CK STIX](https://attack.mitre.org/resources/working-with-attack/) for actor profiles, but exclude any profile citation or copied text derived from the held-out report. Ideally use the last ATT&CK release preceding each report; if historical profile coverage is insufficient, report a retrospective benchmark rather than a forward-looking capability.

The [AttackAttributionDataset](https://github.com/eyalmazuz/AttackAttributionDataset) referenced by MLDSJ is also reachable at `69fb489375ca0775487a0a1e1feb5d26c5c3420a`; MLDSJ describes 238 reports / 12 groups. This screening found no repository license, so it is **not** the clean no-owner-response redistribution route. Filenames themselves include the actor label; they must never become model input. Old reports, alias leakage, and related campaign reports require a substantive audit before using reported high attribution scores as a foundation.

### Pilot and stop conditions

First run a feasibility audit of all 100 Athena cases: actor aliases, related-group ambiguity, profile availability before report date, source families, and independent evidence channels. Keep answer labels outside preprocessing. If too few cases have both independent channels and defensible references, stop rather than manufacture independence.

If viable, freeze a deterministic document-grouped development/test split and compare candidate-set recall, mean set size, wrong singleton attributions, and abstention rate. Report performance at fixed candidate budget or fixed coverage, not accuracy after rejecting most hard cases. A suggested pilot objective is fewer wrong singleton attributions with unchanged candidate-set recall and a mean shortlist of at most three. With only 100 reports, uncertainty will be substantial; the pilot can reject a poor idea but cannot establish broad operational attribution reliability.

Duplicate-source injection can check that the implementation does not multiply evidence merely because a report is copied. That is a software stress test, **not measured progress on real APT identification**. Missing MITRE profiles are not ground-truth unknown actors, and dropping an actor from a candidate list creates an artificial open-set task rather than discovering genuinely new threat actors.

### Novelty assessment

**Executable: medium. Scientific novelty: low-to-medium and conditional.** MLDSJ already combines these information types and uncertainty. The gap worth testing is explicitly modeled dependence and source provenance under actor-name-redacted, document-disjoint evaluation. The small corpus and ambiguous actor taxonomy make this a second choice, not the fastest route to a persuasive praxis.

## Opportunities screened out for an immediate pilot

- **Plain Qwen attribution, generic RAG, or graph-based CTI extraction:** substantial direct prior work already exists.
- **Attack-sequence completion:** [AttackSeqBench v3, March 2026](https://arxiv.org/html/2503.03170v3) is relevant and admits limitations of its multiple-choice/yes-no tasks, but the currently linked GitHub repository `hulkima/AttackSeqBench` returned HTTP 404 through the GitHub API on this research date. Its generated questions are not independent human-labeled attack observations. Do not promise an immediately runnable artifact until its actual bytes are acquired.
- **A better confidence threshold alone:** duplicates both the prior local path and a large selective-prediction literature. It does not solve missing discrimination.
- **Generic rare-class weighting:** MLDSJ already proposes distribution-aware margins and richer weighting as future work; a new weight formula needs strong matched baselines and a real contribution beyond its name.

## What would justify calling a CTI idea positive

A positive result means an improvement on untouched real reports, with equivalent label space and data access, against controls capable of explaining the gain, replicated across seeds and preferably a second source/domain. It does not mean finding one good score, showing an oracle threshold, using synthetic examples as independent attacks, or citing someone else's positive results as ours.

At this point: **one reasonably executable behavior-extraction hypothesis and one weaker attribution hypothesis; zero new validated positive experiments.**
