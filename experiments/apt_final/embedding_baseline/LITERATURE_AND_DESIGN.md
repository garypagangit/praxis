# Embedding anomaly baseline: literature and development design

Reviewed 2026-09-20. **Design recommendation, not a completed experiment or a claim of novelty.** No author checkpoints or cached scores were loaded, and no models were trained during this review. The completed native graph pilot and its registration remain unchanged.

**Operative choices:** The subsequently authored [PROTOCOL.md](PROTOCOL.md) and [config.json](config.json) take precedence over the suggestions below. The authorized scoring comparison uses a shared sampled bank of up to 8,192 training rows, k=10 on both datasets, clean and 50%-removal conditions, and a 0.001 scale floor. Its readiness gate requires every seed to attain clean recall at least 50% and FPR at most 2%; a positive scoring-improvement screen also requires mean clean F1 at least 0.05 above the best prior fixed arm. The full-reference and author-specific k suggestions in this memo remain alternatives, not additional runs or registered settings.

## Recommendation

First change **only the anomaly score**: extract embeddings from our frozen MLP and GIN checkpoints and measure their distance from benign training embeddings. Retain the old reconstruction scores as paired controls. This is the smallest experiment that distinguishes a scoring problem from a representation problem. It is an embedding-scoring ablation of our existing models, **not a MAGIC reproduction**.

Next, if needed, train a documented MAGIC-style encoder from scratch and apply the same independently calibrated nearest-neighbor score. That changes representation, architecture and training; report it as a separate comparison. A better checker remains downstream of establishing useful, complementary detectors.

The existing [pilot report](../native_graph/results/gpu_pilot_20260920/REPORT.md) and [post-hoc diagnostic](../native_graph/results/gpu_pilot_20260920/POSTHOC_DIAGNOSTIC.json) motivate this order. The original fixed neural decisions caught almost the same annotated malicious entities. Selecting between those decisions had virtually no unused recall to recover. Many annotated malicious entities also shared exact reconstruction scores. These observations do not isolate the cause or establish that all routing approaches fail.

## What MAGIC actually does

MAGIC learns benign provenance representations and scores embeddings using nearest neighbors. Its Appendix F explains why the authors did not use reconstruction loss as the deployed anomaly score. Appendix D discusses choosing a threshold using benign false positives. The paper is therefore a relevant baseline, rather than evidence that our lightweight reconstruction detector reproduced its method. [Official USENIX paper](https://www.usenix.org/system/files/usenixsecurity24-jia-zian.pdf), sections 4.2–4.3 and appendices D/F.

The inspected author repository is [FDUDSDE/MAGIC](https://github.com/FDUDSDE/MAGIC), local commit **`aa0b647eea74b6faa0e52eb444370c4411a32cbe`**. The eight implementation files below were unmodified in that local checkout. The following is an audit of executable code, which has some differences from a clean reading of the intended method.

| Component | Inspected implementation |
|---|---|
| Inputs | One-hot node types and one-hot edge types. The released loader derives vocabulary widths using both training and evaluation graphs. [Loader](https://github.com/FDUDSDE/MAGIC/blob/aa0b647eea74b6faa0e52eb444370c4411a32cbe/utils/loaddata.py) |
| Encoder | Three edge-aware GAT layers, four attention heads, 16 channels per head: 64 channels per layer. Edge types enter attention weights; messages carry source-node projections. Residual paths and PReLU are used. Feature dropout is 0.1; attention dropout is zero. [GAT implementation](https://github.com/FDUDSDE/MAGIC/blob/aa0b647eea74b6faa0e52eb444370c4411a32cbe/model/gat.py) |
| Training objectives | Mask 50% of node feature rows with a learned token. Concatenate all three hidden layers into 192 dimensions for reconstruction. A linear projection and one-layer graph decoder reconstruct masked attributes. A second decoder predicts sampled edge existence. Its positive sample count is `min(10000, number_of_nodes)`, with a corresponding negative sample request; dense/small graphs need an explicit feasibility guard. [Autoencoder](https://github.com/FDUDSDE/MAGIC/blob/aa0b647eea74b6faa0e52eb444370c4411a32cbe/model/autoencoder.py) |
| Loss | Masked-feature loss is mean scaled cosine error with exponent 3; add binary cross-entropy for sampled edge reconstruction. [Loss implementation](https://github.com/FDUDSDE/MAGIC/blob/aa0b647eea74b6faa0e52eb444370c4411a32cbe/model/loss_func.py) |
| Optimization | Entity-level defaults: 50 epochs, Adam, learning rate 0.001, weight decay 0.0005, seed 0. Each graph receives an optimizer step; its loss is divided by the number of training graphs. [Training entry point](https://github.com/FDUDSDE/MAGIC/blob/aa0b647eea74b6faa0e52eb444370c4411a32cbe/train.py), [configuration](https://github.com/FDUDSDE/MAGIC/blob/aa0b647eea74b6faa0e52eb444370c4411a32cbe/utils/config.py) |
| Inference representation | `embed()` returns the **last layer's 64-dimensional embedding**, not the concatenated 192-dimensional training representation. Masking and dropout are disabled at inference. [Autoencoder](https://github.com/FDUDSDE/MAGIC/blob/aa0b647eea74b6faa0e52eb444370c4411a32cbe/model/autoencoder.py) |
| Anomaly score | Standardize embeddings using training means/stds. Fit a nearest-neighbor reference on training embeddings. Use mean Euclidean distance to 200 neighbors for CADETS or 10 for THEIA, divided by a training-distance constant. That constant uses at most 50,000 training queries, including each query's self-match. [Entity evaluator](https://github.com/FDUDSDE/MAGIC/blob/aa0b647eea74b6faa0e52eb444370c4411a32cbe/model/eval.py) |

### Reproduction hazards that must be explicit

1. **Test-selected thresholds:** the entity evaluator calls `precision_recall_curve(y_test, score)` and selects a threshold using dataset-specific target recalls. Reusing that operating point would violate our held-out benign calibration design. Cached distances are also accepted by filename alone. We will neither use those caches nor import the evaluator's threshold rule. [Evaluator](https://github.com/FDUDSDE/MAGIC/blob/aa0b647eea74b6faa0e52eb444370c4411a32cbe/model/eval.py).
2. **Normalization case mismatch:** `build_model` passes `norm='BatchNorm'`, while `create_norm` recognizes lowercase `batchnorm`; the inspected code therefore resolves this setting to no normalization. Enabling BatchNorm is a documented change, not exact execution of this snapshot. The seeding helper also misspells `cudnn.determinstic`; it does not establish deterministic CUDA execution. [Model builder](https://github.com/FDUDSDE/MAGIC/blob/aa0b647eea74b6faa0e52eb444370c4411a32cbe/model/autoencoder.py), [utilities](https://github.com/FDUDSDE/MAGIC/blob/aa0b647eea74b6faa0e52eb444370c4411a32cbe/utils/utils.py).
3. **Mask/target aliasing hazard:** masking clones the graph, then modifies its feature tensor in place. DGL 1.0's graph clone clones frames, whose tensor contents remain shared. This raises a source-level concern that masking also changes the intended clean reconstruction target. It was not reproduced in a runtime here. Before any port, a tiny synthetic test must check that clean targets remain immutable; clone feature tensors explicitly if necessary and record the departure. [DGL graph implementation](https://github.com/dmlc/dgl/blob/1.0.x/python/dgl/heterograph.py), [DGL frame implementation](https://github.com/dmlc/dgl/blob/1.0.x/python/dgl/frame.py).
4. **Numerical and sampling guards:** constant embedding dimensions can make the author's standardization undefined; a zero training-distance denominator can make scores undefined. Negative sampling may return fewer pairs than requested. These cases need declared, tested behavior, not silent clipping or result-dependent changes.
5. **Different split:** retaining `train3` for calibration leaves three representation-training graphs; the author entry point trains on every supplied training graph. This is a deliberate evaluation-design departure. Dataset IDs are not semantically aligned between CADETS and THEIA; fit separately.

These observations do not invalidate published results. They identify issues to resolve before calling our implementation a faithful reproduction.

## Stage A: isolate scoring with frozen representations

### Paired arms

| Arm | Representation and fitting | Score |
|---|---|---|
| Frozen MLP reconstruction | Existing model and preprocessing | Existing reconstruction error, unchanged |
| Frozen MLP embedding | Same weights and preprocessing | Benign-reference mean kNN distance |
| Frozen GIN reconstruction | Existing model and preprocessing | Existing reconstruction error, unchanged |
| Frozen GIN embedding | Same weights and preprocessing | Benign-reference mean kNN distance |
| Raw feature kNN control | Existing observed type/count features, no encoder training | Same kNN procedure |
| Isolation Forest reference | Existing fitted detector and decisions | Existing saved score |

Suggested first scope: clean graphs on both datasets, three existing seeds, then the original fixed edge-removal conditions if runtime permits. Declare the scope before evaluation and preserve all attempted results. Do not rename this as a new GNN algorithm.

### Extraction and scoring rules to freeze

- Bind the old data manifest, registration, fitted checkpoint hashes, preprocessing hashes, and saved baseline outputs. Load only our own verified portable weights. Do not load author checkpoints or cached scores.
- Extract the existing eight-dimensional bottleneck, immediately after `second_norm(second(h))`, under `eval()` with no masking. For the GIN, retain both directed aggregation steps and the same graph context. Verify that passing this embedding through the unchanged decoder reproduces the original reconstruction on synthetic data and a predetermined label-free sample.
- Build the reference and fit embedding normalization using `train0..2` only. Keep `train3` exclusively for calibration. Do not fit embedding statistics, reference selection, or an index using test nodes. Declare treatment of zero/near-zero training variance in advance.
- A concrete inherited neighbor choice is **k=200 for CADETS and k=10 for THEIA**, taken from author code, not selected against this pilot. If a bounded reference is required, choose its size and seed before querying evaluation labels, identify this departure, and use the same selection for paired representations.
- Preserve repeated benign reference vectors and their multiplicities. Unweighted deduplication changes the density estimate. Exact compression is acceptable only if a tested weighted-neighbor procedure gives the same k-neighbor distance as the full multiset.
- Use unnormalized mean Euclidean distance. With our empirical-tail calibration, dividing every calibration and evaluation score by the same **positive** constant produces identical rankings and alert decisions. Omitting that constant avoids a zero-denominator failure without changing this calibrated decision rule. This equivalence does not authorize changing per-node or per-scenario scaling.
- Keep the original clean-reference scaler/index fixed under missing edges; recompute observed features and query embeddings. Fitting a new reference to a damaged evaluation graph would answer a different question.
- Freeze the existing nominal 1% clean-benign calibration target and conservative empirical-tail ties. Preserve AP, precision, recall, FPR, counts, score-tie rates, and timing. Report AP separately from whether the calibrated alerts work.
- No routing is needed to answer the initial scoring question. If later analyzing complementarity, label a best-choice oracle as descriptive and bound it to the fixed decisions being compared.

Our previously examined `test0` graphs remain **development data**. Freezing new choices improves traceability but does not restore an untouched confirmation set.

## Stage B: a stronger MAGIC-style representation

If Stage A is weak, that only rejects useful scoring rescue for the existing bottleneck. It does not test MAGIC's richer encoder. The next comparison should train an edge-aware 3-layer, 64-dimensional, 4-head encoder on node/edge type inputs with the two masked-reconstruction objectives above, from fresh seeds. Use the same three benign training graphs, fourth-graph calibration, datasets, and scoring protocol.

Keep a departure ledger: input features, held-out calibration graph, normalization behavior, feature-target aliasing correction, deterministic negative sampling, sparse numerical implementation, and any bounded training/reference sampling. A reduced-epoch diagnostic should be called a budgeted MAGIC-style baseline, not reproduction of the author's 50-epoch model. No analyst-feedback adaptation is included in this static baseline.

The [paper](https://www.usenix.org/system/files/usenixsecurity24-jia-zian.pdf) is the methodological anchor; these proposed split and engineering choices are ours. A stronger baseline alone is not a novel praxis contribution. The possible later contribution concerns whether a defensible quality signal improves detector selection under missing provenance relationships, beyond strong fixed detectors and existing mixture methods.

## Computational plan and prospective gates

Nearest-neighbor scoring can dominate runtime even when GPU embedding extraction is quick. A tree is not guaranteed logarithmic query time for high-dimensional data. The paper's section 6.4 separates graph learning from CPU outlier detection; its timings are not predictions for this environment. [Paper](https://www.usenix.org/system/files/usenixsecurity24-jia-zian.pdf).

For Stage A, about one million 8-dimensional float32 reference embeddings occupy roughly 32 MB before index overhead; 64-dimensional embeddings take roughly 256 MB. Stream queries in bounded batches. Never allocate a full evaluation-by-reference distance matrix: approximately 350,000 by 1,000,000 float32 distances would require about 1.4 TB. Benchmark exact KD-tree queries for the 8-dimensional baseline. For higher-dimensional embeddings, assess an exact blocked CPU/GPU implementation; approximate search is a separate disclosed departure requiring neighbor-error checks.

Proposed gates below are **development defaults to finalize in the operative protocol**, not industry standards or registered claims:

1. **Integrity:** pass checkpoint/data binding, embedding-to-decoder parity, exact small-reference kNN comparison, zero-variance/duplicate/tie tests, and a real bounded memory/runtime preflight. Keep fit/calibration APIs free of test labels.
2. **Scoring diagnosis:** report every frozen arm on both datasets. Attribute any paired gain to the scoring change only. No test-driven choice of k, scaler, threshold, or winning seed.
3. **Detector readiness before routing:** a reasonable screening floor is at least 50% malicious-entity recall with at most 2% benchmark-negative FPR on each dataset, across the declared seeds, under the nominal 1% calibration policy. This is intentionally a development screen; the 2% allowance acknowledges calibration shift and must not be presented as a validated operational budget. Failure leads to representation work or an explicit stop, not threshold rescue.
4. **Routing headroom:** require useful error complementarity at the frozen operating points. For example, prospectively require at least one percentage point of extra union recall beyond the stronger fixed detector before training a selector. A union oracle alone does not establish achievable routing performance.
5. **Confirmation:** obtain an untouched, auditable evaluation design before campaign-generalization, deployment, or novelty claims. Continue calling separately fitted CADETS/THEIA results replication of a procedure, not frozen-model transfer.

## Source inventory

Local author code root: `external/MAGIC` in the main research workspace. Commit: `aa0b647eea74b6faa0e52eb444370c4411a32cbe`. These SHA-256 values identify the local bytes read, including local newline representation:

```json
{
  "train.py": "1babd5fe2e868105730b22f865255610c1492d39f6574d491c29a693c90d07a5",
  "model/autoencoder.py": "d719d60ebdbfe9b0893b68117182087bd84c5c196943acdc4b1da98644a789b8",
  "model/gat.py": "0cf4eddf4a623a307e1e162b1399e248fdee19f05c2d0718e3ce325848723776",
  "model/loss_func.py": "e696fa650ad8c86b6844bef1be6bc248a9bdc37a4b703549991c4192c635b870",
  "model/eval.py": "4761d6481bd29ddc2789eebf2d4dbb04a76176f23223e0690a1f0a0f5f2d75dc",
  "utils/utils.py": "bb6b8ba864b54221918016f71a635285c077e46d5713738512f3eac66763d877",
  "utils/loaddata.py": "a040e01265192993146322e4949a28eb86a34067952c9e279cb51fce47331c64",
  "utils/config.py": "88457e3dc8bcdc336dabb982310e535b9c76f4a05bcb6cad9120095356afbe94"
}
```

APA reference: Jia, Z., Xiong, Y., Nan, Y., Zhang, Y., Zhao, J., & Wen, M. (2024). MAGIC: Detecting advanced persistent threats via masked graph representation learning. In *33rd USENIX Security Symposium* (pp. 5197–5214). USENIX Association. [Official proceedings](https://www.usenix.org/conference/usenixsecurity24/presentation/jia-zian).
