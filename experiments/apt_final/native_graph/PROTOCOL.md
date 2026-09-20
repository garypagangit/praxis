# Native graph missing-relationship pilot

## Prospective scope

This is a separately registered **development-only** alternative to the Unraveled experiment. It does not revise the original E0 HOLD, release that dataset, or overwrite the original configuration. The user authorized starting this alternative after reviewing the available CADETS and THEIA data.

Question: can an observable quality rule preserve malicious-entity detection when recorded graph relationships disappear, while limiting extra false positives?

The pilot tests malicious-versus-unlabeled/background entities under the supplied benchmark annotations. It does not identify five attack stages, infer APT actors, measure delayed arrival or real-time detection, or establish independent-campaign generalization. All already inspected datasets are development benchmarks. THEIA repeats a frozen procedure with a separately fitted model; it is not frozen-weight transfer or untouched confirmation.

## Inputs and source limitations

Use the locally downloaded MAGIC author graph archives for DARPA TC E3 CADETS and THEIA. Bind archive, parser, metadata, normalized-array, and executable hashes. Audit graph sizes, integer attribute ranges, endpoint ranges, directed pairs, annotation indices, split file names, and missing fields before model execution.

The source parser removes known malicious endpoints from training except specified object types. Training benign status is this upstream preprocessing assumption, not independent verification that no attack information remains. Nodes without supplied malicious annotations are benchmark negatives, not exhaustively proven benign. Source UUIDs, time, and semantic type-name maps are absent from the prepared arrays. Different numeric IDs need not represent the same type across datasets. The upstream vocabulary dimensions include train and test types, a label-free transductive schema assumption. Exact entity/campaign independence across graphs cannot be established from these arrays. Report those limitations; do not invent identifiers or regard individual nodes as independent campaigns.

The parser collapses repeated directed source-target pairs and retains typed relationships. Thus the intervention removes **retained relationships**, not raw logging events. TRACE is excluded because its source train/test file lists overlap. No upstream saved scores, checkpoints, or test-label-selected MAGIC thresholds are reused.

## Training and calibration

For each dataset separately, train from author train0, train1, train2 and calibrate using the entire author train3 graph. Evaluate only test0. This follows file partitions, without asserting chronological or campaign independence.

Fixed models:

- A denoising MLP autoencoder without message passing.
- A small denoising GIN autoencoder using graph neighbors.
- Isolation Forest on local structural features as a stronger inexpensive control.
- A node-type rarity control if supported by the implementation, explicitly limited to the few type categories.

Shared autoencoder inputs consist of node-type encoding and log-transformed incoming/outgoing typed relationship counts. Fit scaling using training data only. Count features are recomputed from each observed damaged graph for every model; neither model receives hidden intact degrees. The MLP therefore uses local graph-derived summaries, and must not be described as independent of graph information. Matching widths/epochs does not equalize FLOPs.

Use the committed config: three model seeds, ten fixed epochs, hidden width 32, bottleneck 8, 15% feature masking, and at most 8192 sampled loss roots per training graph/update while retaining graph context. Isolation Forest fits at most 100,000 sampled benign training nodes, with 100 trees and 2,048 samples per tree. No early stopping or parameter selection using test labels. Save portable checkpoints and actual package/device versions.

Convert anomaly scores to conservative empirical calibration-tail probabilities: p=(1 + number of calibration scores at least as large)/(n+1). Predict malicious when p<=0.01. Keep score ties together; report achieved calibration FPR. Calibration is not recomputed after corruption or from attack labels.

## Fixed selectors and interventions

Quality rule: use GIN when observed total degree>=2, otherwise MLP. Confidence control: choose the arm with larger absolute calibrated margin log(0.01/p), selecting GIN on ties. Neither selector uses the true deletion fraction or test labels. Selection can increase false positives even when both arms were calibrated; measure achieved selector FPR rather than assuming a 1% guarantee.

Drop retained edges independently at fractions 0, .25, .5, .75, 1 using two fixed mask seeds. Every arm sees the same observed graph for a condition. The clean condition need not be rerun twice; identical duplicates do not create replication. Relation-outage and delay experiments are outside this initial run.

Report per-dataset/per-model/per-mask outcomes. A label-informed choice may be reported only as a descriptive accuracy upper bound, never as a runnable gate or an F1 ceiling.

## Outcomes and advancement

Report TP,FP,TN,FN, precision, recall, F1, average precision where defined, FPR and false positives per 10,000 benchmark negatives. Report corrected and newly introduced errors against every fixed comparator; do not present comparison only to the weakest baseline. Model-seed and corruption-seed variability is descriptive. No node-bootstrap campaign CIs, alerts/day, production cost savings, or new state-of-the-art claim.

This first run is a feasibility screen. Record whether graph context adds value over the MLP and Isolation Forest, whether missing relationships create complementary errors, and whether the fixed quality rule preserves recall while controlling false alarms. A later learned checker requires a separately declared attack-bearing development partition; do not train it on test0 and reuse test0 as confirmation. A failed fixed rule is a result, not permission to tune against the same labels and call the next attempt confirmation.

## GPU execution and operational bounds

Use the existing authorized AWS g5.xlarge only after source/config/data registration. Use a separate run directory/prefix, a one-hour host ceiling, a verified independent automatic stop schedule, and final STOPPED verification. Reserve at most $10 for this bounded attempt; record a fresh AWS compute-rate estimate, distinct from actual billing. Publish aggregates and hashes, keeping raw arrays, credentials and cloud identifiers outside public Git.

The worker must check CUDA and record device/runtime details, use explicit device placement and synchronized timings, and fail rather than silently skip an unsupported deterministic operation. Verify repeatable synthetic CPU/GPU predictions within declared tolerances before real execution. A hardware test or synthetic success is not research evidence. Use a fresh output directory and persist partial status if the bounded job cannot finish. Do not claim a measured GPU speedup without a paired timing benchmark.

Runtime revision: the first cloud attempt ended during environment selection before any model fitting. Preserve that failed attempt and its stop receipt. The replacement runtime creates an isolated per-run environment inheriting existing CUDA PyTorch, with NumPy1.26.4, SciPy1.14.1, scikit-learn1.5.2, joblib1.4.2 and threadpoolctl3.5.0 installed as binary wheels under a240-second install limit. It does not change the host's existing packages. Use a new registration and attempt directory; no detector settings or data splits changed in this repair. Publish both attempts and aggregate observed compute estimates.

## Literature context

- MAGIC establishes benign-trained provenance representation learning: [USENIX Security 2024](https://www.usenix.org/conference/usenixsecurity24/presentation/jia-zian), [author code/data](https://github.com/FDUDSDE/MAGIC).
- Mowst already mixes feature-only and graph experts with confidence routing: [ICLR 2024 paper](https://arxiv.org/abs/2311.05185).
- SAGMM already studies topology-aware expert gating: [AAAI 2026 proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/39615).
- PIDSMaker documents inconsistent label/split choices and provides stronger follow-up benchmark infrastructure: [dataset documentation](https://ubc-provenance.github.io/PIDSMaker/datasets/).

Novelty remains unestablished. The question is incremental benefit under missing provenance relationships and benign-only calibration; simply combining a GNN and MLP is existing work.
