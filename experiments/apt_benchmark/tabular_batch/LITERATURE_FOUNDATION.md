# Foundation-model batch: literature and implementation audit

Reviewed 2026-09-21 UTC. Scope: attachment experiments E1, E2 and E7. This is a bounded primary-source review and feasibility assessment, not a systematic review or a model evaluation. No fitting or model-weight download was performed for this audit.

## Decision

**E1 is a feasible development benchmark, E2 is a replication/engineering extension, and E7 is an optional model comparison. None currently supports a verified first-use claim.** Start E1 with matched-budget tree baselines and TabICLv2 on a dataset that passes E0. A GPU is useful for the foundation-model arm; it does not fix insufficient independent scenarios, unreliable labels, or unavailable data.

The attachment's claim that every experiment can produce a positive result is not a valid acceptance rule. A useful negative benchmark is possible, but improvement, novelty and publication cannot be guaranteed. Success at any one of several budgets, targets and models also requires a prespecified primary comparison or multiplicity adjustment.

## E1: few-label APT-stage classification

The broad premise has substantial prior work. García et al. already compared TabPFN and TabICL with conventional models on CIC-IDS2017, N-BaIoT and CIC-UNSW, including rare attack classes and limited training samples. This is a peer-reviewed journal article, published September 24, 2025. Those are intrusion-classification benchmarks; their results do not establish APT-stage performance on the proposed datasets. [Electronics article](https://doi.org/10.3390/electronics14193792)

Leroy, Dass and Ullah report 2–6% low-data metric improvements for TabPFN in memory-based malware classification, with a computational tradeoff. The January 12, 2026 arXiv record has no verified journal/conference publication attached. This supports testing the hypothesis, not assuming it will transfer to APT stages. [Malware preprint](https://arxiv.org/abs/2601.07305)

The targeted search did not establish a previous exact evaluation of TabPFN/TabICL on the attachment's four APT datasets. **That does not establish absence of prior art.** Drop “first” from the working title. A defensible contribution would need rigorously separated scenarios, genuine scarce-label budgets, stage-specific failure analysis, and reproducible comparisons that change a practical decision.

Protocol requirements (our assessment):

- Count labeled examples used for model selection, calibration and threshold selection as well as the fitting context. Otherwise a 32-per-stage setting can conceal a large labeled development set.
- Split independent executions/scenarios before subsampling; deduplicate related records across partitions. Use temporal evaluation only when reliable timestamps support it.
- Fit all feature transforms on permitted training data. Exclude stage IDs, scenario IDs, attacker identity and other outcome proxies from predictors.
- Report an explicitly named primary budget and comparator. Choose the best tree baseline using development data, never test scores.
- Resample independent scenarios for uncertainty when rows are correlated. Ten seeds do not create ten independent datasets.
- In-context learning still uses labeled support data and inference computation; “no gradient training” does not mean “no fitting cost.”

## E2: foundation-model screen followed by trees

The exact architecture is already proposed in Al-Dahmani et al.'s April 13, 2026 TON_IoT preprint: TabPFNv2.5 screens records, then Random Forest and Gradient Boosting classify flagged traffic. Table 3 reports 0.02 seconds per 10,000 predictions for TabPFN, 0.82 for Random Forest and 0.94 for Gradient Boosting. The headline 40-fold claim refers to Random Forest; this is not a tuned XGBoost comparison. The paper describes Colab/Xeon/12 GB RAM and does not provide a GPU specification in its experimental configuration. It reports individual model timings rather than a threshold-swept end-to-end cascade frontier. No peer-reviewed publication was verified. [Paper, sections 3.2–3.4 and Table 3](https://arxiv.org/html/2604.11394v1)

**Assessment:** worthwhile to reproduce the throughput claim, weak novelty as proposed. Do not assume a transformer is faster than a deployed tree ensemble. Measure preprocessing, context preparation, device transfer and synchronized inference; distinguish warm and cold execution and retain batch-size/hardware details. Run the full tree baseline on the same hardware budget. Any first-stage false negative must count as a final missed attack. A binary screen also needs genuinely labeled non-attack examples; other attack stages alone cannot supply that class.

For a cascade with screen cost `c_screen`, detailed-model cost `c_detail`, and flagged fraction `p`, idealized per-row cost is `c_screen + p*c_detail`. A fivefold speedup over the full detailed model is impossible unless this sum is at most `0.2*c_detail`, even before routing overhead. This is an analytical feasibility check, not a measured result.

## E7: GRANDE

The claim “first security application” is contradicted by the original ICLR 2024 paper itself: section 4.3 is a PhishingWebsites case study. GRANDE remains a legitimate alternative model to test; parity on one selected grid cell would not by itself demonstrate a new method or useful improvement. [Author-hosted conference paper](https://s-marton.github.io/files/paper_grande.pdf)

The official repository currently recommends a newer PyTorch implementation, while the PyPI package remains a legacy TensorFlow release. The author also notes weaker multiclass than binary/regression results. The repository is MIT licensed and describes its implementation as experimental. [Official repository](https://github.com/s-marton/GRANDE)

## Implementation readiness

These are metadata observations, not successful installation/smoke-test claims. Exact URLs, revisions, dependencies and checkpoint hashes are recorded in [SOURCES_FOUNDATION.json](SOURCES_FOUNDATION.json).

| Arm | Current observation | Run recommendation |
|---|---|---|
| TabICLv2 | Package 2.2.0; Python >=3.10, PyTorch >=2.2. Public, ungated BSD-3-Clause checkpoint, approximately 110 MB. | First foundation-model arm; explicitly pin checkpoint and ensemble size. Start with a small fit/predict smoke test and record peak GPU memory. |
| TabPFN 2.5 | Package release 9.0.0 currently defaults to a different model generation. Version-2.5 checkpoints are public/ungated in the HF API but carry a separate noncommercial license. | Pin model file explicitly; verify runtime compatibility. Research use is described in the model license/card. Preserve attribution and license separately from code. |
| GRANDE | Git implementation 0.2.0 uses PyTorch; PyPI 0.1.6 uses TensorFlow. Git runtime requires AutoGluon and narrower Torch/sklearn versions. | Optional, isolated environment. Do not label latest Git results as an exact reproduction of the original implementation. |

TabICL's authors provide a peer-reviewed ICML 2025 paper; TabICLv2 appears in the official ICML 2026 downloads listing. Its official code supports cached context, explicit devices and CPU/disk offloading. Actual memory requirements depend on rows, features, ensemble size and query batching; no fixed minimum GPU was verified for our task. [ICML 2025 paper](https://proceedings.mlr.press/v267/qu25d.html), [ICML 2026 listing](https://icml.cc/Downloads/2026), [official implementation](https://github.com/soda-inria/tabicl)

The TabPFN-2.5 model card distinguishes the default classifier, which is finetuned on real datasets, from `tabpfn-v2.5-classifier-v2.5_default-2.ckpt`, its synthetic-only alternative. Prefer the latter for a clearly documented pretraining-contamination control, or inspect the real-data training list before claiming dataset independence. This is a protocol choice, not evidence that contamination occurred. The official TabPFN README recommends GPU execution and mentions approximately 8 GB VRAM for many tasks, 16 GB for some larger tasks. [Version-2.5 model card](https://huggingface.co/Prior-Labs/tabpfn_2_5), [official runtime README](https://github.com/PriorLabs/TabPFN/blob/main/README.md)

## Bounded first run

1. E0 must establish accessible bytes, license, valid target semantics, independent split units and sufficient per-class counts.
2. Freeze one development split and a modest label budget. Fit matched-budget Random Forest and gradient-boosting controls plus TabICLv2; add explicit TabPFN-2.5 only after a smoke test.
3. Record all arms, including failures, macro-F1, per-class recall, ROC-AUC/PR-AUC where defined, inference cost and peak memory. Confirm stage predictions are really supported before using “APT stage” in the result title.
4. Expand seeds/budgets only after the data and executable path pass. Preserve a genuinely unused confirmation set; existing exposed tests remain development evidence.
5. E2 follows measured latency feasibility; E7 follows environment feasibility. Neither is required to interpret E1.

This audit does not validate the attachment's conformal/open-set guarantee claims in E4–E6; those require a separate statistical review.

## Runnable backend handoff

[model_backend.py](model_backend.py) supplies `create_foundation_classifier(name, cache_dir, seed=..., device="auto")`, returning an unfitted estimator and a receipt. Model IDs are `tabicl_v2` and `tabpfn_2_5_synthetic`. Immutable revision, byte count and SHA256 checks precede model loading. The default four-member ensemble is a fixed feasibility setting for both arms. TabICL uses one ensemble member per internal batch, disables Flash Attention 3 and mixed precision, and keeps its context cache off; these conservative settings are not an optimized throughput configuration. TabPFN explicitly requests the 2.5 configuration with the synthetic-only checkpoint.

[requirementsfoundation.txt](requirementsfoundation.txt) pins top-level package versions for an isolated environment, including PyTorch 2.5.1. It is not a full transitive lock: the runner must record `pip freeze`. The release-wheel constructor signatures were checked directly, and cached-file corruption is rejected. **Dependency resolution, checkpoint loading and fit/predict runtime compatibility remain untested by this audit.** CPU timing is unmeasured; use a bounded smoke test before expanding. An explicitly requested CUDA device fails when unavailable; automatic CPU fallback is disclosed in the receipt.
