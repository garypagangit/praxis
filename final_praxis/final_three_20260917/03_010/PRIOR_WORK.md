# Candidate 010: primary-source comparison and claim boundary

**Reviewed September 17, 2026.** This is a focused comparison against three research papers and the pinned implementation, not an exhaustive novelty search or an academic originality determination. Sources were opened directly during report preparation. The comparisons below support the narrow framing in PAPER.md.

## 1. Attack detection with forecast models

**Source:** Anand, Nguyen, and Pappas, [Attack Detection using Time Series Foundation Models, arXiv:2606.06347v1](https://arxiv.org/html/2606.06347v1).

**Inspected:** Section II-C, Section IV, Algorithm 1, and Section IV-A. Section II-C describes forecasting each output channel independently. Section IV presents residual-based detection and a protected context buffer; Algorithm 1 makes buffer updating conditional on the alarm calculation.

**Boundary for D0:** Forecast-based attack detection and context protection are established motivations. D0 changes one artificial channel and measures the consequences for other forecasts in native TimesFM 3. It supplies no detector, alarm calibration, attack-identification result, or head-to-head detection comparison. Its negative result does not refute the paper's separately specified simulations.

## 2. Inference-time context intervention

**Source:** Pandey et al., [GITCO: Gated Inference-Time Context Optimization in TSFMs, arXiv:2606.05332v1](https://arxiv.org/html/2606.05332v1).

**Inspected:** Sections 3.1–3.3, Algorithm 1, and Section 6. The method combines a gate, router, and critic with localized SMA-based intervention. The limitations discuss architecture-specific validation and future robustness evaluation under distribution shift.

**Boundary for D0:** Generic input-context gating and smoothing cannot be claimed as new here. D0 applies a fixed causal SMA-5 to channel 0 throughout each context; it omits the learned selection components. This is a simple baseline, not a GITCO reproduction. D0 also does not independently assess GITCO's benchmark performance or convert its forecasting objective into demonstrated cyber-defense efficacy.

## 3. Forecast residuals and adaptive calibration

**Source:** Martinez Gil, O'Donncha, Gifford, Zhou, Patel, and Vaculin, [Adaptive Conformal Anomaly Detection with Time Series Foundation Models for Signal Monitoring, arXiv:2604.20122v1](https://arxiv.org/abs/2604.20122).

**Inspected:** The primary arXiv title, author, abstract, and version record. The abstract describes pretrained-model forecasts feeding adaptive conformal anomaly scoring with learned weighting of past predictions.

**Boundary for D0:** This establishes an existing monitoring/calibration approach. D0 computes paired absolute errors without conformal scoring or adaptive calibration. It claims no false-alarm guarantee, anomaly-detection improvement, or replication of the paper's full benchmarks. Review of the abstract supports this narrow comparison; this packet does not claim a fresh full implementation review of that method.

## 4. Native TimesFM route semantics

**Source:** Google Research, [TimesFM 3 evaluator at source revision 8cb0628371af142e16b8c232cc9fbf667ffb12f9](https://github.com/google-research/timesfm/blob/8cb0628371af142e16b8c232cc9fbf667ffb12f9/src/timesfm3/torch/evaluator.py); [raw primary source](https://raw.githubusercontent.com/google-research/timesfm/8cb0628371af142e16b8c232cc9fbf667ffb12f9/src/timesfm3/torch/evaluator.py).

**Inspected:** `TimesFM3Evaluator.predict_batch`, including the `univariate` argument and the branch that unrolls each channel into a separate context before delegating forecasting. This is the actual native alternative used by the structural negative control. Local execution evidence independently binds the loaded module hash to the pinned source ZIP.

**Boundary for D0:** Native route availability supports implementation fidelity, not novelty or safety. The inference from D0's paired outputs is limited to influence and error changes under the selected perturbations. The measured zero independent-channel displacement is an observed control result, not a universal forecast-accuracy guarantee.

## Contribution decision

| Question | Defensible answer from the completed evidence |
|---|---|
| What was tested? | A fixed pair of displacement and average-harm conditions in one native multivariate model configuration. |
| What was learned? | Cross-channel influence occurred; none of six raw-joint variants met the registered average-harm requirement. |
| What was added beyond generic prior techniques? | A source-bound, fully retained negative mechanism screen and explicit stopping decision in this particular setup. No new algorithm is asserted. |
| What remains unsupported? | A novel defense, independent cyber replication, attack detection, retention/recovery improvement, or universal robustness. |
| Does the result support D1? | No. The registered gate says to hold scale-up; the simple-control adequacy gate was not reached. |
| Is this an approved Praxis contribution? | Not established by this packet. Human authorship, originality, and program-fit judgments remain unrecorded. |

A narrower technical report can remain useful when its proposed mechanism fails an investment threshold. Whether that contribution satisfies a particular degree requirement is a separate decision; writing a manuscript does not make the failed gate pass.
