# New cybersecurity Praxis opportunities from forecasting and tabular foundation models

Research checked September 14, 2026. These are proposed studies, not completed experiments or certified novelty claims. No inference or cloud jobs were launched for this review. The companion [compression review](LITERATURE_COMPRESSION.md) covers SOUP, Colibri, quantization, and memory management.

## Executive summary

Google's forecasting models are relevant to cybersecurity because security systems produce streams of measurements: authentication counts, network activity, sensor readings, and resource use. Predicting normal measurements can help identify unusual activity. It does not mean predicting an unknown attack before it happens. A forecast can also become dangerously accurate after an ongoing attack becomes part of the recent history.

The strongest forecasting opportunity here is to test a process modification that prevents suspicious history from quietly becoming the detector's new normal, while still allowing ordinary operational changes. The study needs to outperform existing alarm-based context freezing and adaptive calibration, not just a naive detector. Google's new multivariate model makes the question timely because contamination in one channel may affect other channels through joint prediction.

A second opportunity comes from compact models for tables: choosing which past labeled examples a model is allowed to consult when classifying new malware. The research contribution would be a constrained selection policy evaluated across time, with delayed labels and a fixed memory budget. Merely applying a tabular foundation model to malware would repeat existing work.

For a new investment, I would first qualify the SOUP/Colibri systems idea in the companion review if small-hardware operation is the priority. For a specifically cybersecurity-focused new study, I would qualify the persistent-attack/context-adaptation idea below. Neither should displace writing the completed CTI paper while its feasibility is still uncertain.

## What Google has actually released

[TimesFM-3](https://research.google/blog/timesfm-3-a-zero-shot-foundation-model-for-multivariate-forecasting/) was announced August 31, 2026. It has 330 million parameters and native multivariate forecasting, including related targets and covariates. It produces point and quantile forecasts in one forward pass. These are forecasting capabilities; the announcement does not establish cybersecurity detection performance.

The [official implementation](https://github.com/google-research/timesfm) and [PyTorch checkpoint](https://huggingface.co/google/timesfm-3.0-pytorch) are public. Source code uses Apache 2.0; version 3 weights have noncommercial, nonproduction terms. Version 2.5 remains useful as a comparison and has different weight licensing. Pin both the model revision and license before an experiment. The released version 3 F32 parameter payload is roughly 1.32 GB by parameter-count arithmetic, before runtime working memory. That is not a measured whole-process RAM requirement.

Google already provides [forecast-based anomaly detection examples](https://cloud.google.com/dataflow/docs/notebooks/anomaly_detection_timesfm). A residual threshold around TimesFM is therefore an implementation baseline, not a novel thesis contribution.

Google also introduced [TabFM](https://research.google/blog/introducing-tabfm-a-zero-shot-foundation-model-for-tabular-data/) on June 30, 2026. It predicts from tables using labeled examples supplied in context. Avoiding task-specific gradient training does not remove the need for labels. Its input and research questions differ from forecasting ordered telemetry.

## Closest literature that limits a novelty claim

| Primary work | What already exists | Consequence for a new Praxis |
|---|---|---|
| [Attack Detection using Time Series Foundation Models](https://arxiv.org/abs/2606.06347), June 2026 preprint; [code](https://github.com/balajianand1994/Attack_detection_using_TFM) | TimesFM as a secondary detector in dynamical systems, with a context buffer updated only when no alarm occurs | Freezing context after an alarm is already a baseline. Its conclusion explicitly proposes better characterization of adversaries with black-box access. |
| [Exploring Zero-Shot Foundation Models for Multivariate Time Series Anomaly Detection](https://arxiv.org/abs/2607.12454), July 2026 preprint | A TimesFM study on SWaT; persistent abnormal patterns can become predictable, and simple baselines can outperform the tested methods | The opportunity is a measured remedy with suitable controls, not discovery that forecast quality differs from attack detectability. Its future work calls for genuinely multivariate models and broader evaluation. |
| [Adaptive Conformal Anomaly Detection with Time Series Foundation Models for Signal Monitoring](https://proceedings.iclr.cc/paper_files/paper/2026/hash/f54c9fc57aa6e1c72400cc127917fcf8-Abstract-Conference.html), ICLR 2026; [paper](https://arxiv.org/abs/2604.20122) | Adaptive weighted conformal calibration with pretrained forecasters; public implementation and benchmark data | Adding conformal intervals is already established. Temporal or adversarial guarantees require their assumptions, not just the word conformal. |
| [Are Time-Series Foundation Models Deployment-Ready?](https://arxiv.org/abs/2505.19397), initially May 2025 | Adversarial robustness evaluation of time-series foundation models | A generic claim that these models are vulnerable is insufficient. |
| [TimeRadar](https://arxiv.org/abs/2602.19068), February 2026 | Zero-shot time-series anomaly detection, including cybersecurity evaluation | Applying a foundation detector to a public intrusion dataset is not automatically new. |

The adaptive-calibration paper links its [implementation](https://github.com/ibm-granite/granite-tsfm/tree/main/notebooks/hfdemo/adaptive_conformal_tsad). Its original experiments include NAB and other public time-series benchmarks. A replication should start with one dataset and model actually used by that paper before changing either. A generic server anomaly in NAB is not automatically a malicious cyberattack.

## Candidate T1: Preserve attack detection while allowing benign adaptation

**In simple words:** Can we stop a detector from learning an ongoing attack as normal, without making it ring constantly whenever the system changes legitimately?

**RQ:** At a fixed false-alarm budget and compute budget, does a trust-partitioned multivariate context update preserve persistent-attack detection better than naive rolling context, alarm-triggered freezing, and adaptive conformal calibration, without materially slowing recovery after benign regime changes?

**Proposed H1:** On held-out attack episodes, the modified policy improves episode recall by at least five percentage points over the strongest development-selected baseline, with a paired episode-level confidence interval excluding zero, while adding no more than one false alarm per day on held-out normal runs. The extra-one-per-day rule is a noninferiority margin, not the total acceptable alarm rate. All methods must also meet a common absolute alarm-rate ceiling selected from the application requirements before testing. These are proposed practical thresholds, not literature-derived universal standards. Final thresholds must be fixed before test outcomes are accessed.

**Proposed H2:** On separately designated benign regime changes, recovery delay is noninferior to the strongest adaptive baseline under a prospectively chosen time margin. An approach that achieves H1 by never adapting fails the intended contribution.

### Base paper, public data, and the modification

First reproduce the public dynamical-system scenarios from the June attack-detection paper, preserving its detector, warmup, and alarm-gated context update. These scenarios are generated by published code; they are not a downloaded real-world incident dataset. Separately reproduce one public-data result from the ICLR calibration paper using its original model and dataset. That provides the requested base-paper/public-dataset foundation before moving to cyber data.

For the cyber evaluation, use a pinned release of the [HAI industrial-control security dataset](https://github.com/icsdataset/hai), which provides downloadable time-stamped normal and attack runs, including versions 21.03 and 23.05. HAI is collected from a physical/testbed simulation environment, not a sample of production attacks. HAI and HAIEnd from the same version share experimental episodes and cannot count as independent replications. Later files use Git LFS; verify that downloads contain data rather than pointer files. Preserve the license statement at the pinned revision and do not infer rights from inconsistent mirror metadata. SWaT is useful prior art, but its access-request process makes it a weaker first choice for unrestricted reproduction.

The proposed process uses a fixed reference context plus a separately updated operational context. The initial reference comes from a designated commissioning/training run assumed normal; that assumption must be explicit. A separate contamination sensitivity tests the cost of violating it. Reference selection cannot use attack labels from the held-out stream. Each channel's update weight depends only on information available at that time: prior residuals, declared sensor provenance, and a fixed development-selected dependency graph. The policy excludes future labels and post-incident analyst judgments. Suspicious channels have limited influence on the shared context, and a declared recovery rule eventually allows benign changes to enter it.

One testable mathematical restriction is a bound on the mass of newly admitted, untrusted observations in a context:

$$\sum_{j\in U_t} w_{t,j}\leq \rho,\qquad w_{t,j}\geq0,\qquad \sum_jw_{t,j}=1.$$

Here U is defined by an observable provenance/risk rule, not the hidden attack label. This is a design constraint, not a proven detection guarantee. Compare actual observation replacement or interpolation with a model-native attention-mask implementation only if that implementation preserves the intended attention semantics. Do not silently treat filling a value with zero as removing it from attention.

The candidate novelty is the interaction between constrained cross-channel context updates, persistent attacks, and legitimate recovery in a newly multivariate forecaster. Weighted updates, robust statistics, graph constraints, and context freezing all have substantial prior art. The combination needs a targeted literature comparison and an ablation showing which component contributes before claiming novelty.

### Design that can support a defensible result

1. Pin source code, model revisions, preprocessing, sampling interval, and dataset hashes. Reproduce the base-paper result before tuning the modification.
2. Split by complete chronological runs and attack episodes. Keep normalization, channel selection, thresholds, graph fitting, and recovery rules within development data. Never shuffle overlapping windows across train and test.
3. Compare seasonal/last-value forecasting, PCA or a simple change detector, the original TimesFM alarm-freeze policy, the adaptive conformal baseline, TimesFM-3 rolling context, and the proposed update. Use the same telemetry and comparable parameter-selection effort.
4. Report event recall, time to first detection, detection retention over the full attack, alarms per normal day, recovery delay, memory, and latency. Include raw pointwise scores; avoid point-adjusted F1 as the sole result because one alert should not automatically turn a whole episode into perfect detection.
5. Ablate immutable reference, per-channel gating, cross-channel restriction, and recovery. Use matched benign changes to expose a detector that merely treats any sustained change as hostile.
6. Bootstrap complete episodes or runs, retain model separation, and disclose shared episodes across HAI variants. Specify one primary comparison and a correction for secondary comparisons. Hold the final test once the protocol is frozen.

**Stop gate:** If the base implementation cannot be reproduced, there are too few independent attack episodes for useful precision, or the full method only beats naive rolling context but not published alarm freezing, do not scale the claim. A negative result remains useful if the boundary and mechanism are measured, but it is not a validated new defense.

## Candidate T2: Memory-limited, provenance-aware support selection for malware classification

**In simple words:** A compact table model consults a small notebook of past examples. Can we choose a better notebook when attacks change and reliable labels arrive late?

The recent [Mitra-v2 technical report](https://arxiv.org/abs/2609.04540), September 3, 2026, offers a timely compact tabular-model base. Its [classification checkpoint](https://huggingface.co/autogluon/mitra-classifier-2) and [fine-tuning package](https://huggingface.co/autogluon/mitra-finetune) are public. The current package already has class-balanced support subsampling, support caps, and an optional support cache. These cannot be claimed as new. Its published large-context recipe uses CUDA and H100-class benchmark hardware; parameter count alone does not demonstrate a laptop memory footprint.

Use [EMBER2024](https://github.com/FutureComputing4AI/EMBER2024) and its [base paper](https://arxiv.org/abs/2506.05074). It supplies public executable features and metadata, chronological partitions, multiple tasks, and a difficult challenge set. The initial study can use released feature vectors without executing malware. First reproduce the provided LightGBM baseline and a supported tabular-model task. A second public table dataset from the foundation-model paper should establish ordinary model reproduction before making a cybersecurity transfer claim.

**RQ:** Under a fixed total memory budget and a prospective label-availability schedule, does selecting support examples by provenance, age, and coverage of underrepresented classes improve future-malware recall at a fixed benign false-positive rate over random, class-balanced, recent, and nearest-neighbor support selection?

**Proposed H1:** At the development-fixed benign false-positive target, the selection policy improves recall by at least three percentage points on held-out future weeks, with a week-block confidence interval excluding zero and no violation of the memory budget. Require comparison with the strongest simple baseline, including LightGBM, to establish whether the foundation model is worth using at all.

An explicit candidate objective selects a bounded support set S using relevance and diversity while penalizing stale or weakly established labels:

$$\max_{|S|\leq B}\;\sum_{i\in S} r_i+\lambda D(S)-\mu\sum_{i\in S} a_i,$$

subject to label availability and a minimum benign-reference allocation. Relevance, diversity, and age functions must be specified from development data. This family of objectives is established; novelty would require the constrained malware setting, an identifiable improvement over appropriate selection baselines, and a targeted search of support-selection work.

The full feature space may exceed a checkpoint's supported input width. Fit dimensionality reduction or feature selection using past training data only, keep identical transformed features across comparable baselines, and report information lost. Measure process RAM, accelerator allocation, support cache, preprocessing state, and storage rather than just model weights. Weekly observations sharing malware families require appropriate clustered sensitivity analysis.

EMBER labels are retrospective. If real analyst label-arrival times are unavailable, a delayed-label schedule is a declared simulation; it must not be described as historical operational availability. Audit and override Mitra's defaults that reintroduce fold-held-out rows into prediction support: every support label must satisfy the simulated availability time. Also fix whether a cached support set is reused or redrawn across query chunks, since that changes the sampling policy. Hold the challenge set aside until the primary protocol is fixed.

Related work already includes [tabular foundation models for IoT intrusion detection](https://arxiv.org/abs/2604.11394) and [memory-based malware detection with TabPFN](https://arxiv.org/abs/2601.07305). Generic malware classification, simple memory use, and adding a conformal rejection gate are crowded directions. Prioritize the time/provenance constraint and reject the project if it reduces to a routine benchmark substitution.

## Investment recommendation

The completed CTI, 008, and PX055 manuscripts should proceed as their own bounded results. For new work, qualify one systems proposal from SOUP/Colibri and one cybersecurity proposal from T1 using small, reproducible pilots. T2 is a reserve direction if the forecasting modification cannot beat the published context-freezing baseline.

Before any paid run, archive the precise base reproduction, closest prior-art comparison, RQ, primary hypothesis, independent sampling unit, dataset and model licenses, hardware measurement plan, and stopping rule. This review supplies candidate designs; it does not retroactively register them or assert their outcomes.
