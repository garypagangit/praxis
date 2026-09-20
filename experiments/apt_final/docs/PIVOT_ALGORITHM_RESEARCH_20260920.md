# APT graph pivots: representation and efficiency

> Final access and decision update: the [consolidated shortlist](APT_PIVOT_SHORTLIST_20260920.md) supersedes provisional artifact status below. Full OCR acquisition failed; public OTRF APT29 day-one logs were acquired and qualified instead. Stable IDs and ordinary joins are mandatory baselines, not a new algorithm. The narrower evidence-selection idea remains conditional on a natural failure beyond those baselines. No new positive efficacy result is claimed.

Research cutoff: **September 20, 2026**. Status: **literature and feasibility assessment; no new model, data download, or cloud experiment performed for this memo**.

## Recommendation in plain language

The next graph experiment should ask whether a detector understands **what a program does**, instead of reacting mainly to familiar names or a familiar environment. However, adding names, timestamps, contrastive learning, or graph compression is already established work. Two narrow mechanisms below are testable; neither has an established novelty claim. The first needs richer event data. The second can use existing embeddings, but is an efficiency improvement and cannot repair our failed detection results.

The completed [normally calibrated MAGIC study](../magic_calibrated/results/gpu_calibrated_20260920/REPORT.md) did not pass its readiness gate in any of six cases. Exact duplicate removal and normal-only calibration are not new research contributions. That result closes the tested method; it does not establish that graph detection is impossible.

**Priority:** qualify a rich-data baseline and measure its specific failure before selecting a new architecture. If the goal is a stronger novel praxis immediately, the separately investigated ambiguity-aware evidence-binding direction deserves comparison with these graph options. An audit alone is a prerequisite, not the proposed contribution.

## What the closest work already covers

| Primary source | Relevant overlap and implication |
|---|---|
| [FLASH, IEEE S&P 2024, author paper](https://mati607.github.io/assets/Flash.pdf) | Uses semantic/temporal representation and embedding reuse. Its persistent-node-identifier abstraction removes user/execution-specific information. Merely canonicalizing paths, ignoring usernames, or caching embeddings is insufficient novelty. |
| [KAIROS, IEEE S&P 2024](https://arxiv.org/abs/2308.05034), [ORTHRUS, USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/jiang-baoxiang) | Temporal provenance learning and attack reconstruction already exist. “Add timestamps” or “capture causal relationships” is too broad a contribution. Here causal means observed dependencies, not identification of real-world causal effects. |
| [MirGuard, August 2025 preprint](https://arxiv.org/html/2508.10639v1) | Combines logic-aware node/edge/feature augmentations, contrastive representation learning, and centroid anomaly scoring. Its displayed feature encoding uses node/edge types; feature replacement is within type. A claim limited to “semantic-preserving contrastive robustness” would substantially overlap. Type-compatible edits also do not by themselves prove unchanged program behavior. |
| [TFLAG, January 2025 preprint](https://arxiv.org/html/2501.06997v1), [EA-THGN, Information Sciences, September 5, 2026](https://doi.org/10.1016/j.ins.2026.123518) | Temporal attention, normality adaptation, adaptive temporal aggregation, and hard-negative training are already explored. A different temporal layer or a hard-negative objective alone is not a defensible novelty statement. |
| [Hybrid Time–Position Embedding, February 2026](https://doi.org/10.3390/electronics15051004), [LADE, author 2026 manuscript](https://www3.cs.stonybrook.edu/~stoller/papers/LADE-2026.pdf) | Security-context/time-position representation and richer command-oriented APT processing are additional nearby work. Richer text plus an existing graph model is not automatically a new method. |
| [The Case for Learned Provenance-based System Behavior Baseline, ICML 2025](https://proceedings.mlr.press/v267/zhu25k.html) | Addresses unseen entities, normality shifts, compact behavioral encoding, and integration with tag propagation. “Handle unfamiliar benign behavior efficiently” is an existing research objective. |
| [TAPAS, USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/zhang-bo-tapas) | Reduces spatial and temporal redundancy using a process backbone, learned summaries, and task-guided segmentation. Generic task-aware graph reduction is crowded. |
| [CSCProv, September 17, 2026](https://link.springer.com/article/10.1186/s42400-026-00648-6) | Directly targets causal-semantic graph compression, attack-path preservation, and downstream detection efficiency. Its mapping-based path completeness endpoint also prevents claiming that merely adding a path-preservation metric is new. |
| [GridPRISM, July 2026](https://doi.org/10.1016/j.ijcip.2026.100849) | Prior-guided subgraph routing and budgeted semantic masking are direct overlap for a generic budget-aware graph checker. Full artifact availability was not established in this audit. |
| [Attack structure matters, Computers & Security 2025](https://doi.org/10.1016/j.cose.2025.104578) | Provides causality-preserving structural evaluation beyond individual-node scores. Preserving node recall alone cannot demonstrate preservation of an investigative explanation. |
| [Sometimes Simpler is Better, USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/bilot), [PIDSMaker, 2026](https://arxiv.org/abs/2601.22983) | Establish strong simple baselines and a common implementation framework. A new graph layer must beat the simple control under the same inputs and evaluation procedure. |

This is a bounded primary-source review, not a systematic review or evidence that no closer paper exists. Paper claims have not been independently reproduced here.

## Public artifacts and what is runnable

The following repository heads were verified through the public GitHub API on September 20. Availability of source is distinct from a successfully reproduced experiment.

| Artifact | Verified commit / readiness |
|---|---|
| [PIDSMaker](https://github.com/ubc-provenance/PIDSMaker/tree/ae1e9fd42604c769c01b2eaed6fb7f65e27f3cac) | `ae1e9fd42604c769c01b2eaed6fb7f65e27f3cac`; Apache-2.0; includes VELOX, FLASH, ORTHRUS, KAIROS and MAGIC configurations. Best common starting point. |
| [ORTHRUS author implementation](https://github.com/ubc-provenance/orthrus/tree/e7f25dfee1ddd182a955b88f8a90a8cbd4a8e543) | `e7f25dfee1ddd182a955b88f8a90a8cbd4a8e543`; Apache-2.0; documented installation/data path. |
| [FLASH author implementation](https://github.com/DART-Laboratory/Flash-IDS/tree/ccbafee7eb796c76aceaabdc259ebd1f12b867cc) | `ccbafee7eb796c76aceaabdc259ebd1f12b867cc`; dataset notebooks and dependency file. API returned no recognized repository license; establish reuse terms before redistributing source. |
| [KAIROS author implementation](https://github.com/ubc-provenance/kairos/tree/0e0b633beb46a1117c0a6d63be5d2481b59ac0dc) | `0e0b633beb46a1117c0a6d63be5d2481b59ac0dc`; public code. API returned no recognized repository license. |
| [TAPAS source archive](https://doi.org/10.5281/zenodo.15610687) | Author paper's Open Science section links this archive. Full download and execution not verified here. |

PIDSMaker documents downloadable prepared databases, including DARPA/OpTC and ATLASV2_EDR, listed at 1 GB. Its attack counts are repository descriptions, not verified independent-campaign counts. The framework warns about sensitivity to training perturbations; our experiment must retain every prespecified seed rather than select a favorable run. Dataset acquisition and schema qualification remain separate gates.

Our **already prepared MAGIC arrays** contain node types, typed directed edges and entity annotations. They lack source UUIDs, timestamps and raw names/attributes. UUID renumbering on these arrays would largely test graph implementation invariance, not semantic robustness. They cannot support an honest temporal or name-change experiment.

The [OCR-APT release](https://zenodo.org/records/17254415) documents richer events and attributes. The earlier [artifact memo](LOCAL_LLM_ARTIFACT_GATE_20260920.md) verified a 64-byte range request against its 2,940,005,988-byte archive, not full acquisition or checksum validation. A separate current acquisition audit may supersede that status. No dataset-owner response is required to attempt the public artifact path. Benign periods, raw fields, annotation joins, timestamp resolution and entity continuity still require inspection; preprocessed data must not silently replace a missing field with an invented value.

No runnable author release was established for MirGuard, TFLAG, CSCProv or EA-THGN in this bounded check. The ICML behavior-baseline paper links `AddoZhu/behavior_baseline`; its repository API returned 404 during this audit. These are limitations of our access check, not assertions that code does not exist. An independent implementation must be labeled as such.

## Candidate 1: learn which changes should matter

**Problem:** renaming an ordinary temporary directory should not create an intrusion alert, while changing the order or role of security-relevant actions should remain visible.

**Precise proposed mechanism:** extend one fixed temporal encoder with a paired representation loss. For a training event neighborhood `G`, create:

1. `Tname(G)`: a consistent substitution only in a frozen list of nuisance attribute fields. Preserve entity equality, node types, action types, timestamp order and security-relevant path roles.
2. `Torder(G)`: a separately specified change to an action/dependency sequence that makes the behavior non-equivalent while preserving its event multiset where feasible.

Penalize distance between `z(G)` and `z(Tname(G))`; require a fixed margin separating that distance from `z(G)` versus `z(Torder(G))`. Retain the original normal-event prediction loss to discourage collapsed representations. An example is:

`L = Lnormal + lambda * d(z, z_name) + mu * max(0, margin + d(z, z_name) - d(z, z_order))`.

All coefficients and transformation rules are prospective choices. Synthetic order changes are **representation probes, not labeled attacks**. Impossible traces must be identified separately; success on detecting an impossible ordering is not evidence of detecting realistic APTs. Paths, usernames and IP addresses can carry security meaning, so wholesale removal or unrestricted renaming is not justified. Unsupported transformations are excluded.

**Possible gap, not established novelty:** explicitly controlling the tradeoff between nuisance invariance and retained action/order information under a reviewed transformation contract. FLASH already abstracts identifiers; MirGuard already aligns augmented views; temporal hard negatives also have prior art. The mechanism is worth pursuing only if the paired evaluation exposes a reproducible failure those controls do not fix. Combining familiar losses is not enough by itself.

### Small, fair pilot

- Start with one public host/day or other bounded recording whose raw fields and benign/annotated periods have been verified; cap the first diagnostic by a prospective time interval, not by selecting easy entities. Reserve a second host/recording for replication where available.
- Fit on earlier benign periods, calibrate once on a disjoint benign period, then freeze. Keep source UUID groups together across splits where feasible; report unavoidable repeated entities. Do not infer independent campaigns from graph files or random seeds.
- Compare the same base encoder unchanged, the base with FLASH-style canonicalization only, nuisance-augmentation loss only, and the proposed paired loss. Include a VELOX/simple edge-prediction control and a strong temporal ORTHRUS baseline. Equalize data, optimizer updates, inference information and the declared resource budget; report extra view-generation cost.
- Use three prespecified training seeds and separately fixed perturbation seeds. Evaluate clean data, unseen nuisance substitutions, and action/order probes separately. Identity-only relabeling is a software sanity control. A score-constant model is a collapse control. No test-label threshold optimization.
- **Proposed development gates:** first require at least a measurable baseline problem, such as more than 1% alert flips under the declared nuisance transformations. Then require at least 50% reduction in flips against the strongest canonicalization/augmentation control, with clean recall loss no greater than 2 percentage points, clean and perturbed benchmark-negative FPR at most 2%, and recall at least 50% in every prespecified dataset/seed. Report AP and all errors as well. These are proposed gates for a new experiment, not changes to any completed study.
- Separately require the proposed representation to retain action/order discrimination at least as well as the unchanged temporal baseline on held-out probes. This prevents declaring a model useful simply because it ignores all input changes. Probe success never substitutes for measured intrusion detection.

**Finite ending:** if canonicalization already solves the paired problem, the data do not support the stated gap; if the learned objective loses behavior sensitivity or fails detection gates, close this candidate. Passing supports a development result, followed by independent-data validation and a closer novelty review. It does not establish deployment readiness.

## Candidate 2: certify an alert without computing every distance

**Problem:** an exact normal-reference nearest-neighbor detector can spend substantial time comparing a query with reference points whose distances cannot change the alert decision.

**Precise proposed mechanism:** group normal embeddings, retaining every member and its multiplicity for exact fallback. For group center `c` and radius `r`, triangle inequality bounds each query distance by `max(0, ||q-c||-r)` and `||q-c||+r`. The mean of the `k` smallest multiplicity-weighted lower bounds and of the `k` smallest upper bounds bounds the exact mean-`k` score. With frozen strict rule `score > threshold`:

- Alert when the lower bound is strictly above the threshold.
- Clear when the upper bound is at most the threshold.
- Otherwise refine uncertain groups or compute the full exact score.

Use conservative floating-point bounds and exact fallback around ties. Index construction uses fit embeddings only. Calibration remains exact and unchanged. This preserves the detector's decisions rather than deleting graph actions or accepting an approximate recall loss; it makes no claim to preserve arbitrary graph queries.

**Novelty assessment: weak as a standalone praxis.** Triangle-inequality pruning, clustering indexes, quantization and exact nearest-neighbor methods are established. The [Faiss library paper, 2024](https://arxiv.org/abs/2401.08281) is a mandatory efficiency baseline; our existing multiplicity-preserving duplicate compression is another. A rigorous systems study under retraining, tight ties and reference shift could be practically useful, but neither the bound nor pairing it with a calibrated threshold is a new mathematical result. This mechanism cannot improve the six completed MAGIC detection decisions if it preserves them exactly.

### Small pilot possible with existing artifacts

Use the six frozen fit banks, calibration thresholds and saved test embeddings without retraining or retuning. Compare exhaustive chunked float64 scoring, existing exact duplicate compression, a qualified exact Faiss index where applicable, and the proposed bound/refinement implementation. Keep distance definition, multiplicity, tie handling, thread count, device and output decisions identical. No oracle threshold selection is needed.

**Proposed gates:** zero alert disagreement on every evaluated query, exhaustive qualification on small banks including duplicate/tie/adversarial boundary cases, and at least 2x median end-to-end scoring speedup over the fastest qualified exact comparator in every dataset, across repeated timed runs. Include index build, storage, refinement frequency and amortization separately. Stop if the bound almost always falls back, preprocessing erases the gain, or any decision mismatch remains. A passing result earns an engineering efficiency claim; it does not revive the negative detection candidate or establish research novelty.

## Why not graph sparsification as the lead pivot?

CSCProv, TAPAS, ORTHRUS pruning, and earlier dependence-preserving compaction already address retaining useful evidence while reducing graph cost. A proposed reducer would need a precisely specified preserved query class, falsifiable checks for both missing and spurious paths, and total runtime including compression. Node preservation alone is insufficient. Our current arrays also cannot verify temporal path preservation. This family should remain on hold unless a specific unhandled contract or failure is demonstrated; “keep important actions” is too close to existing work.

## Decision

**GO:** public-data/schema qualification and one paired semantic/order baseline audit, with a finite no-headroom stopping rule. **CONDITIONAL:** Candidate 1 only after that failure is measured and the transformation assumptions survive review. **ENGINEERING ONLY:** Candidate 2 if exact scoring remains a material bottleneck. **HOLD:** claims of a novel graph algorithm, generic causal/semantic compression, or success from a model swap. A stronger investigation contribution may emerge from preserving competing entity bindings and resolving them with a bounded discriminating query, but that separate proposal must beat exact UUID joins, abstention and standard budget-matched query-selection controls.
