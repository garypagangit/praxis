# Can the stronger graph model choose a useful alert threshold from normal data?

## Thesis and development hypothesis

The published MAGIC representation may retain useful attack detection when the alert threshold is selected exclusively from a separate normal graph. This tests a practical prerequisite for a future checker intervention, not algorithmic novelty. The completed all-four-training-graph reproduction produced strong descriptive scores using attack-label-selected thresholds; those scores alone do not establish this claim.

On each of THEIA and CADETS, independently train seeds **0, 101 and 211**. Every one of the six fixed cases must achieve **attack recall at least 50% and benchmark-negative false-positive rate at most 2%**, using a threshold fixed with normal calibration data only. Report all cases. Averaging seeds cannot rescue a failed case. These are declared development gates, not a statistical claim about real-world deployment or independent campaigns.

## Model and partition

Reuse the qualified original MAGIC model/objective source and exact multiplicity-preserving scorer, without changing their frozen files. Use original dimensions, 64-dimensional embeddings, three edge-aware attention layers, 50% masking, Adam and 50 epochs. Train only on prepared normal **train0, train1 and train2**. Reserve **train3 exclusively for calibration** and **test0 for final evaluation**. Fresh graph construction and original objective/optimizer behavior remain, including measured target aliasing and absent normalization. Each epoch has three graph updates (150 total), compared with 200 in the all-four-graph reproduction; outcome differences cannot be attributed solely to threshold selection. Each case trains from scratch; no earlier checkpoint is reused.

Fit the mean and standard deviation on the full training embeddings only. Apply them unchanged to calibration and test embeddings. Abort on nonfinite or zero training scale. Use k=10 THEIA and k=200 CADETS, retaining every fit-reference row mathematically through exact vector multiplicities. Store complete original row-aligned banks. Never include calibration or test rows in the reference bank.

The preserved author seed helper does not explicitly seed DGL negative sampling. These are three seeded training runs with residual stochasticity; they are not an isolated initialization-only comparison or a deterministic replay guarantee.

## Frozen threshold rule

Use raw mean Euclidean k-neighbor distance for both calibration and test. Omit the author's positive distance-normalization constant: multiplying both score vectors by the same positive constant cannot change their quantile-threshold decisions. This simplification is explicit; no numerical floor, smoothing or test-informed rescaling is inserted.

Set the calibration-tail target alpha to **0.01**. For n calibration scores, choose ascending order-statistic rank `ceil((n+1)*(1-alpha))`. If rank is within n, threshold is that score and an alert requires **score strictly greater than threshold**. This tie policy is conservative. If rank exceeds n, use an explicit never-alert sentinel and report it, without emitting nonfinite JSON. Record the rank, calibration support, ties and empirical alert fraction.

The 1% value is a calibration-tail target. Dependent graph rows, upstream normal-label assumptions and distribution shift prevent a distribution-free false-alert or conformal-coverage guarantee. The same calibration graph chooses the threshold, so its measured alert rate is not independent normal validation.

## Training/test boundary and evidence

Complete all six normal fits and calibrations before loading any attack test array in this run. For each, save first/final checkpoints, all 50 epoch records, full fit/calibration embeddings, calibration scores and threshold. Hash them in a per-case FIT_CALIBRATION_FREEZE receipt. Then write GLOBAL_CALIBRATION_FREEZE with the exact six-case inventory. If any normal case is incomplete or invalid, withhold every attack evaluation; do not quietly drop a seed or dataset.

Only after the global freeze, use each fixed model/scaler/reference/threshold on its complete test graph. Save embeddings, scores, labels and fixed alerts. Report confusion counts, precision, recall, F1, false-positive rate, AUROC and average precision. Rank metrics use labels for descriptive evaluation only. No oracle threshold search, test-driven threshold update, best-seed selection or gate relaxation. Reusing these previously exposed benchmarks is explicitly development evidence.

An independent auditor recomputes the rank/tie policy from saved calibration scores, scaler values from fit banks, full-reference sampled distances, labels, fixed predictions, metrics, gates, all six freeze identities and checkpoint/source hashes. The audit does not retrain neural models or create campaign independence. Publish positive and negative outcomes together, including partial/runtime attempts.

## Qualification and resource budget

Reuse the pinned qualified Python 3.10/Torch 2.5.1+cu121/DGL 1.1.3+cu121 environment, GPU source forward/backward probe, and direct NumPy numerical oracle for the exact compact scorer. Qualify partition isolation, threshold ties, never-alert behavior, global freeze before any test access, malformed data/receipt refusal, and incomplete-case handling before freeze.

Each normal case begins with one measured full epoch and training-only scoring samples for a conservative runtime estimate. Include remaining training, bank construction, full calibration and eventual test scoring, serialization, a 1.25 multiplier and 180-second margin. Preserve a reserve for pending test evaluations of earlier completed normal cases. Resource holds are incomplete evidence, not negative efficacy results. Keep the fixed six cases and absolute worker deadline.

Use one additional primary attempt (attempt 4 in the ongoing MAGIC work), the existing g5.xlarge, 2,400 seconds of science, one-hour host cap, independent stop watchdog and verified shutdown. Across the two original qualifications, one compact reproduction and this calibrated experiment, the existing maximum four-hour compute envelope is about $4.024 plus the $5 incidental reserve, within $10. No new infrastructure or model API. Any genuine runtime interruption is preserved and cannot be called scientific completion.

## Literature and interpretation

Jia et al. (2024), [MAGIC, USENIX Security](https://www.usenix.org/conference/usenixsecurity24/presentation/jia-zian), supplies the representation. [PIDSMaker](https://ubc-provenance.github.io/PIDSMaker/features/instability/) already studies retraining instability, and normal-only threshold selection is established practice. Exact duplicate compression is also established engineering ([Faiss](https://github.com/facebookresearch/faiss/blob/v1.7.4/faiss/IndexIVFFlat.cpp#L336)). No novelty claim follows from combining these prerequisites.

Only one supplied test graph per dataset, three training seeds, incomplete-negative annotations, previously exposed data, vocabulary derived upstream from training/test types, and absent campaign/UUID/time mappings remain. Seeds are not independent campaigns. A positive six-case result would make this a plausible stronger baseline for a specifically justified new checker; it would not by itself complete a novel praxis contribution or establish APT actor attribution.
