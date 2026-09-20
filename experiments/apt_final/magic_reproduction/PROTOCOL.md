# Establish the published graph baseline before changing the detector

## Question and bounded scope

Does the original MAGIC architecture and training objective recover useful attack separation on the available CADETS and THEIA prepared graphs, where our much smaller models failed? This is a development reproduction and resource qualification, not a new algorithm or confirmatory experiment. The prior stability comparison remains closed with its negative result.

Primary source: Jia et al. (2024), [MAGIC, USENIX Security](https://www.usenix.org/conference/usenixsecurity24/presentation/jia-zian). Upstream source is pinned at `aa0b647eea74b6faa0e52eb444370c4411a32cbe` in [FDUDSDE/MAGIC](https://github.com/FDUDSDE/MAGIC/tree/aa0b647eea74b6faa0e52eb444370c4411a32cbe). Every used upstream source file is copied byte-for-byte from its Git blob into a private, hash-bound source tree. Author checkpoints and cached distances are excluded.

## Frozen comparisons

Two datasets, in order THEIA then CADETS; one original seed (zero) each. All four provided normal training graphs, original graph order, 50 epochs, 64-dimensional embeddings, three four-head attention layers, 50% feature masking, attribute plus structural reconstruction. Adam, learning rate .001, weight decay .0005, original loss scaling by four graphs and optimizer step per graph. Config records all parameters. A run may select either dataset without changing these settings; no score-based selection or early stopping.

The implementation imports the original model and optimizer. It rebuilds DGL graphs from the previously passively decoded, audited NPZ arrays, preserving node rows, edge order/direction, node/edge one-hot attributes and dimensions. It does not execute data pickle reducers. Source masking mutates the original graph feature targets under the qualified runtime; that behavior is preserved and measured. The source's `BatchNorm` spelling resolves to no normalization, also preserved. The source's misspelled determinism flag is not silently repaired and deterministic repeatability is not claimed. Each training graph is freshly constructed for every step, matching the author's reload behavior.

## Runtime adaptation and qualification

AWS A10G with existing Torch 2.5.1+cu121, Python 3.10, pinned DGL 1.1.3+cu121. These differ from the paper repository's Torch 1.12.1/cu116 and DGL 1.0.0 requirements. This is an author-source reproduction under a qualified newer runtime, not exact historical-runtime reproduction. Wheel identity, environment, source, config, data and runtime receipts are retained.

Before science, check CUDA availability, small-graph forward/backward, target aliasing and normalization behavior, graph/feature reconstruction, and exact full-reference kNN against independent NumPy direct-difference distances on synthetic and sampled real training queries. Also report scikit-learn comparisons, but its norm-identity distance kernel can return nonzero distances for identical rows; the direct-difference calculation is the numerical gate. Include at least k identical rows to expose that case. Exhaustive chunked GPU distance computation is an implementation adaptation; no approximate neighbors or reference subsampling. Distance arithmetic is float64 and tolerances are recorded. The author's scikit-learn/float32 arithmetic is not reproduced bit-for-bit. Abort rather than replace a failed method silently. No test arrays or labels are read in the training-only resource qualification.

For each dataset: run one full epoch, extract all training embeddings, and time fixed training-only queries against the entire reference bank. Estimate the remaining 49 epochs, final embeddings, up to 50,000 normalizer queries and all known test rows, with a 1.25 multiplier and 180 seconds of safety. Finish only if that fits the remaining science/absolute deadline. If not, save the first-epoch checkpoint and return `NOT_RUN_RESOURCE_HOLD`. Interrupted or resource-held cases are incomplete evidence, never negative scientific results. Checkpoint reuse is not implemented by this registration.

## Evaluation

Train-standardize all 64 dimensions with the author's mean and standard deviation. Abort on zero/nonfinite scale; do not insert a tuned floor. Use every training row as reference, k=10 THEIA and k=200 CADETS. Reset the author's seed before evaluation and use the author's shuffled first up-to-50,000 training queries for the distance normalization mean, including self-neighbors as the author does. Abort on zero/nonfinite mean distance.

Only after 50 epochs and final training embeddings are saved may the worker load the dataset's test graph and annotation vector. Save row-aligned scores and report AUROC, average precision, and confusion matrices at (1) the original label-selected recall rule (.99996 THEIA, .9976 CADETS), and (2) supplemental maximum-F1 threshold. Both thresholds use the test labels and are **oracle/descriptive only**. A favorable score does not establish a usable operational false-alert rate. Report FPR and recall together; do not label this detector production-ready. An independently normal-calibrated comparison needs a separately frozen train/calibration design.

The author threshold loop is reproduced exactly where valid; an undefined endpoint fails explicitly. Metrics are independently recomputed from saved scores/labels after the run. Check full-reference distances on saved sampled queries. Confirm 50 completed epochs before counting any evaluated case. Preserve partial results and all failed attempts.

## Data and interpretation limits

Use the exact existing manifest `de06215e30e36c6063eeeb6a1ed18a738735fd909dbeeda7fa7789728fb2feab` and its ten NPZ hashes. Prior work has already exposed these test sets. Prepared node rows are not verified unique entities; normal labels are the upstream filtered-benign assumption and test negatives are unannotated rows, not independently verified innocence. One test graph per dataset provides no independent campaign replication. Timestamps, UUID mapping and original repeated events are absent. Vocabulary dimensions were determined using training and test types upstream. No APT actor attribution, stage classification, real outage robustness or external generalization claim follows.

## Operations and completion

Use the existing stopped g5.xlarge only; no new infrastructure. Each attempt has the existing one-hour host cap, 52-minute worker deadline, independent 56-minute stop watchdog and $10 reserve including incidental allowance. Allow up to two primary attempts, one per dataset if needed; operational repairs require separate preserved receipts and explicit runtime amendment. Data, temporary files and dependencies stay on the already qualified dedicated EBS mount. Inputs/outputs are bounded at 4GB/2,000 members. Stop and verify the host before removing only its own watchdog.

Completion means both cases have a documented terminal outcome, raw evidence collected and hashed, independent metrics/source/inventory audit complete, costs estimated with limitations and AWS shutdown verified. A resource or runtime hold completes its feasibility assessment, not the planned 50-epoch scientific evaluation. A successful reproduction is a prerequisite for the strongest next intervention; it is not itself claimed as novel praxis.
