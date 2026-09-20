# APT final: literature and design audit

Reviewed September 19, 2026. Status: **prospective research design; no new detection result or novelty validation**. This bounded screen uses primary papers, author repositories, and official documentation. A source not located here is not proof that it does not exist.

## What the two supplied documents define

The first attachment proposes three separate tracks: local LLM deployment, detector instability, and structural/semantic representation comparison. The second defines an E0–E4 **telemetry-quality routing program**, which is a distinct proposed contribution. E0–E4 does not by itself test all three tracks. The registry retains all three candidates while the main experimental sequence implements the routing program's prerequisites and gates.

The historical GML document was reviewed as an April 1, 2026 draft; its publication status was not established. Its same-procedure DAPT corrective comparison found MLP macro-F1 0.6386 and GIN 0.5895, with only three exfiltration test records. Accordingly, GIN is the primary historical graph reference. GATv2 and R-GCN are optional comparisons, not the winners of that corrected experiment. A single stratified experiment cannot establish general failure of all graph models. See the historical `reports/gwu_committee_response/DAPT_SOH_GML_APPLES_TO_APPLES_RESULT_20260519.md`.

## Literature findings that change the candidate claims

| Claim in the supplied ideas | Primary evidence checked | Required correction |
|---|---|---|
| No published local open-weight APT pipeline has been tested. | [SHIELD](https://arxiv.org/html/2502.02342v1) deploys Qwen2.5-32B locally. [CAPTAIN](https://arxiv.org/html/2607.20832v1) uses a small Qwen3 backbone. | Drop the first-local-LLM claim. An isolated-deployment study needs a narrower operational contribution. |
| OCR-APT makes local-vs-cloud comparison an untouched gap. | The [OCR-APT author repository](https://github.com/CoDS-GCS/OCR-APT) documents local Llama3 8B and local embedding experiments and supplies a results spreadsheet. Its README reports comparable report quality. | This directly overlaps the proposed swap experiment. Report quality is not proof of detection noninferiority or full disconnected operation. Reproduce and inspect that comparison before defining an extension. |
| OCR-APT is only an unverified preprint. | The same repository identifies ACM CCS 2025 and supplies DOI [10.1145/3719027.3765219](https://doi.org/10.1145/3719027.3765219). The publisher page could not be opened in this session. | Correct the earlier local review's preprint-only characterization: conference status is supported by the author artifact. Its arXiv version is a preprint of that work. |
| Instability has never been a first-class metric. | [PIDSMaker's instability documentation](https://ubc-provenance.github.io/PIDSMaker/features/instability/) already provides repeated-seed uncertainty experiments with mean, standard deviation, and relative variation; its configuration names a deep-ensemble repetition mode. | Measuring seed variance alone is replication. That documentation does not establish that every proposed voting/abstention wrapper was previously evaluated; each wrapper still requires a separate overlap check. |
| Standardized datasets make labels and splits automatically valid. | [PIDSMaker dataset documentation](https://ubc-provenance.github.io/PIDSMaker/datasets/) explicitly exposes alternative ground-truth versions whose choice affects metrics. It evaluates malicious node UUIDs. | Pin labels and audit missing identifiers, benign coverage, time windows, and campaign grouping. Node labels do not automatically become lifecycle-stage or fully correct window labels. |
| Semantic graph enrichment is a new representation family combination. | [Auto-Prov](https://arxiv.org/html/2603.17100v1) already enriches provenance graphs using LLM-derived functionality and evaluates graph detectors. | A controlled minority-stage study may still be useful, but neither semantic graph enrichment nor Qwen-plus-graph is novel by itself. |
| Switching between MLP and GNN is new. | [Mowst, ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/6a8449c080c3d27e5e16995e82beaade-Abstract-Conference.html) conditionally uses a GNN through a confidence mechanism. | Test whether observable telemetry quality adds useful information beyond confidence-based routing at measured cost. Cite and compare the prior mechanism. |

The [USENIX Security 2025 analysis](https://www.usenix.org/conference/usenixsecurity25/presentation/bilot) and [2026 PIDSMaker framework paper](https://arxiv.org/abs/2601.22983) are distinct citations. The former compares eight systems and discusses deployment shortcomings; the latter describes the reusable framework. Neither eliminates our responsibility to validate the selected protocol.

## Revised candidate assessments

### Candidate 1: disconnected local LLM pipeline

**Problem:** A security team needs useful detection and investigation while the analysis machine cannot send telemetry outside its network.

**Defensible question:** At a fixed measured hardware and latency budget, can a completely local pipeline preserve independently scored campaign detection and evidence-grounded reconstruction on held-out environments?

**Potential contribution:** A reproducible boundary on quality, cost, and full offline dependency closure. The proposed contribution is applied evaluation; a Qwen model substitution is insufficient algorithmic novelty.

**First gates:** Inspect OCR-APT's local spreadsheet and executable pipeline; verify all runtime dependencies, model weights, retrieval, embeddings, and logging work with network access disabled; reproduce a reference arm. Score detection separately from reconstruction. A rubric needs exact event support, omissions, false attack claims, and independent review, not an LLM's general impression.

**Design repair:** Changing the language model and embedding model simultaneously confounds their effects. Use a factorial or staged ablation. A five-percentage-point F1 noninferiority margin in the attachment is an example, not a registered operational justification. Define the margin, one-sided confidence criterion, metric, campaign unit, and compute limits before the test. Negative outcomes are informative when the reproduction and uncertainty are credible; publishability is not guaranteed.

**Judgment:** High operational relevance; medium-to-high execution cost; **high overlap risk as written**. No GPU or API execution is justified by calling the local gap already established.

### Candidate 2: dependable alerts across retraining

**Problem:** Rebuilding a detector can change which attacks and benign activities it flags, making operations unreliable.

**Defensible question:** Can a specific, frozen decision rule reduce attack-level prediction disagreement and worst-case alert burden under retraining without simply suppressing detections?

**Potential contribution:** A narrowly defined reliability intervention with equal-cost controls and a held-out environment. Seed ensembling and score-band abstention are baseline mechanisms, not presumed new algorithms.

**First gates:** Reproduce two systems before expanding to four. Separate initialization, data-order, threshold-fitting, and environment effects. Record paired per-event decisions across runs, detection delay, campaign recall, false alerts per host-day, and analyst escalation volume. Abstention is neither a correct prediction nor a free human fix.

**Design repair:** An exactly repeated deterministic wrapper can still depend on unstable trained models. Ensemble inference and training cost must be charged. Compare equal total compute and an ordinary ensemble/threshold baseline. Lower variance at uniformly bad detection is failure. Ten seeds estimate training variability; they do not create ten independent attack campaigns.

**Judgment:** High engineering relevance and useful replication foundation; moderate effort; **novelty conditional on the particular intervention and operational evaluation**.

### Candidate 3: representations for rare attack stages

**Problem:** Rare stages such as exfiltration can be missed even when an overall traffic score looks good.

**Defensible question:** Under the same observable inputs and independent campaign splits, which representation improves prespecified rare-stage detection beyond strong tabular models, and does the gain survive resampling controls?

**Potential contribution:** A reproducible failure-boundary study separating representation, training balance, and graph information. No exhaustive literature clearance of this exact comparison was completed.

**First gates:** Obtain and audit stage-labeled data and campaign identifiers. Fix the minority-stage set using training data or a domain definition. Compare MLP and tree models before expensive fine-tuning; include real/shuffled/self-only graph ablations. The semantic and structural arms must see equivalent information: additional host text only in one arm changes the question from representation to information availability.

**Design repair:** No random row split when campaigns or duplicates cross partitions. Train-only resampling; SMOTE on arbitrary text or graph topology is not automatically meaningful. Use a defined within-family balancing strategy and a factorial interaction comparison. Bound any stage-taxonomy mapping before cross-dataset testing. Serialization may expose identifiers or template labels rather than demonstrate semantic reasoning.

**Judgment:** Strong continuity with the GML draft; moderate-to-high engineering effort; **dataset access, independent campaigns, and representation leakage are unresolved gates**.

## Dataset feasibility: what is and is not verified

| Dataset | Verified in this audit | Remaining prerequisite |
|---|---|---|
| Unraveled | Prior local experiments establish use of flow features. | The new E0 audit must establish real host/flow keys, clock alignment, campaign independence, and ground-truth provenance. This review does not assume joins passed. |
| DARPA TC / OpTC through PIDSMaker | Official framework lists releases, schema, labels, and per-host/engagement coverage. | Download or inventory an exact bounded release; pin source versions and audit endpoint labels. A fallback from stage classification to node/campaign detection requires an explicit scope amendment. |
| SCVIC-APT-2021 | An [author research paper](https://arxiv.org/abs/2208.05089) uses the dataset. The listed [dataset DOI](https://doi.org/10.21227/g2z5-ep97) and [IEEE DataPort landing page](https://ieee-dataport.org/documents/scvic-apt-2021) could not be opened here. | **Existence supported; free direct access, downloadable bytes, license, code, and campaign metadata not verified.** Do not say all data are already free and ready. |
| S-DAPT-2026 | [The January 2026 paper](https://arxiv.org/html/2601.06690v1) exists and describes synthetic alert generation with stage mappings. | No working author data/code release verified by this bounded title/GitHub/Zenodo search. Alert data differ from raw flow features. Generated alert types can directly encode stages; audit for trivial mappings before using this as a generalization test. |

The supplied SCVIC scores of 95.20% and 96.67% are not reproduction targets until the exact paper, split, preprocessing, and metric are pinned. Counts in unrelated published comparisons also cannot substitute for counts in our actual acquired files.

## Required E0–E4 protocol repairs

These recommendations define the scientific interpretation. The executable protocol/configuration must implement them before any confirmation run.

### E0: data verification

- Define the join denominator and unique, ambiguous, unmatched, and impossible matches. A high timestamp-window hit rate alone can arise by coincidence; use negative-control time offsets and manually auditable examples.
- Preserve raw event time and ingestion time separately. Publish clock skew and missingness by source, stage, and campaign. Do not infer absence of an attack from an unlabeled record.
- Retain immutable campaign/host/time grouping and duplicate checks. A folder name or flow-file source is not automatically an independent campaign identifier.
- Treat 30 positive rows as a **provisional exclusion screen**, not a power analysis. Count independent campaigns as well as rows. Perform a precision/power assessment for the endpoint and planned effect after metadata inspection. Low-support stages remain descriptively reported; apply the same prespecified macro-F1 class set to every arm.
- Specify pass thresholds and metadata requirements before model-result inspection. If the target changes on fallback data, version the scope and endpoint; do not silently substitute binary malicious-node detection for lifecycle-stage classification.

### E1: graph-information diagnostic

- Primary historical graph reference: GIN. Arm A feature-only MLP; B real edges; C degree-preserving rewired edges; D self-only graph. Optional GATv2 is a sensitivity arm.
- Preserve direction, relation type, time feasibility, and train/evaluation boundaries where required. Record actual rewiring success and topology change; a failed or nearly unchanged rewire is not an informative control.
- Match train-only preprocessing, observed feature availability, tuning budget, and maximum resources. Equal epochs do not guarantee equal compute. Use the same seed inventory across arms and record actual cost.
- Report paired uncertainty across independent campaigns or justified time blocks, with training-seed variation separately or through a hierarchical analysis. Resampling ten seeds alone supports a conditional claim about training randomness, not unseen-environment generalization. With too few independent groups, report descriptive uncertainty and limit inference.
- H1a not supported means **no demonstrated edge advantage in this test**, not evidence of equivalence. A no-useful-benefit claim needs a defined equivalence margin and sufficiently precise interval. H1a supported but H1b not supported means edges help this GNN relative to its rewired control while the simpler baseline remains competitive; it does not prove the architecture cannot exploit signal.
- Continue to gate development only if development predictions show useful complementary errors or a meaningful cost opportunity. Routing two uniformly equivalent/bad experts has no automatic value.

### E2: degradation and policy development

- Use a declared **development partition** because its results select E3 indicators and thresholds. Calling these data test data does not make the ensuing tuned policy a confirmed result.
- Apply missingness and delay to raw available telemetry before features and edges are constructed. Simulating delay by changing event timestamps conflates clock errors with late arrival; model ingestion availability explicitly. Do not drop only GNN evidence while leaving equivalent derived evidence intact for the MLP unless this is a separately named intervention.
- Set alert thresholds on development data at a declared false-alert budget. Freeze them for evaluation; report actual test budget violations rather than recalibrating on test labels to guarantee compliance.
- A curve crossover is a candidate observation subject to uncertainty and multiple conditions. A weak point estimate is not sufficient reason to promote the gate.

### E3: frozen policy test

- The attachment actually lists **six arms**: MLP, GNN, label-oracle, random routing, static quality gate, learned quality gate. Add an ordinary confidence-routing baseline to test incremental value over Mowst-like selection; use an exact Mowst reproduction or label any simplified adaptation honestly.
- A label-oracle is an unimplementable diagnostic. Macro-F1 is not additive over windows: a window-wise better classifier is not automatically the global macro-F1 upper bound. Define the diagnostic objective precisely; a correctness oracle gives an accuracy ceiling but not an unconstrained operational detector.
- Fit the random routing probability from development-set gate usage, then freeze it. Matching it to a test-label oracle's routing rate leaks outcome information into the comparator. Cost-matched controls must also satisfy measured budget feasibility.
- Gate features must be available before the work being skipped. Charge ingestion, quality summaries, join work, graph construction/update, both models if executed, routing, memory, and p50/p95 latency. A simulated lookup using two precomputed prediction arrays measures policy choices, not realized compute savings.
- Freeze the comparison target on development data, or account for selecting the better arm on the evaluation set. Report both baseline contrasts and prespecified multiple-comparison handling. Compare accuracy/recall, false alerts, and compute jointly; do not collapse them into an unexplained score.
- Define the oracle-gap ratio only when the same-metric oracle advantage is strictly positive. Otherwise output null with reason `NO_POSITIVE_ORACLE_GAP`. An oracle computed with a different objective is not an eligible denominator.
- Define the static/learned benefit ratio only when the learned benefit over the same baseline is positive. Otherwise output null with reason `NO_POSITIVE_LEARNED_BENEFIT`. Absolute deltas and their uncertainty remain primary. The illustrative 50% and 80% ratios are proposed targets requiring a frozen operational rationale, not already established facts.

### E4: external confirmation

- Reserve campaign groups before E1/E2 inspection. E4 requires a policy, feature definitions, label mapping, thresholds, and resource budget frozen before accessing evaluation outcomes.
- Lead with the frozen transfer result. Any recalibrated result is a separate adaptation analysis using a distinct calibration portion. A second dataset alone does not create independence if it copies attacks, labels, or templates from the development corpus.
- State a numeric permitted degradation and precision requirement in the committed confirmation protocol. Missing required metadata or failed E0 gates yields blocked/not run, not a performance failure or a passed experiment.

## Parallel collision check: the earlier safety-gated TTA work

The local prior method adapts BatchNorm in a flow-feature MLP and uses a validation-chosen policy that protects confident exfiltration predictions while allowing limited reconnaissance overrides. Its original source-file result is bounded evidence; the later UNSW replication did not meet its registered criteria. Do not inherit an older `defense ready` label as evidence of cross-environment success.

[METANOIA](https://arxiv.org/abs/2501.00438) explicitly handles benign concept drift, forgetting, and avoiding ingestion of malicious behavior into learning. This overlaps broad claims of safe adaptation for APT detection. Its provenance-based incremental mechanism is not identical to the local BatchNorm/decision policy; novelty requires a mechanism-level comparison and matched prospective evaluation.

[CAPTAIN](https://arxiv.org/html/2607.20832v1) supplies a small language-model detector with recent context and score smoothing. Its printed centered filter can require future entries; an online comparison must declare lookahead or delay. This is an engineering comparison issue, not proof that CAPTAIN's offline results are invalid. Neither switching to Qwen nor labeling a gate deterministic resolves these overlaps.

**Disposition:** Retain three candidates as proposed tracks. Start with audited data and graph-information diagnostics. Promote a track only when the exact added contribution, labels, independent evaluation, and real resource budget survive these gates.
