# Cross-Channel Forecast Displacement Without Mean Error Inflation

## A frozen negative mechanism screen with native TimesFM 3

**Research report for author and committee review — September 17, 2026**

**Status:** Completed D0 experiment; technical audit PASS; cross-channel-harm scale-up held. This AI-assisted report synthesizes preserved experimental evidence. It does not record human authorship approval, committee acceptance, or validation of a new defense. The accompanying [human review worksheet](HUMAN_REVIEW.md) remains uncompleted.

## Abstract

Joint forecasting can allow a changed input channel to influence predictions for unchanged channels. That architectural possibility does not establish that the influence worsens predictions. We report a frozen development screen testing these two properties separately in native TimesFM 3. Three related channels were constructed from one previously inspected public NAB/TSB-AD series. At 32 overlapping forecast origins, six positive step or ramp perturbations changed only channel 0. Four pipelines—joint forecasting, independent forecasting, joint forecasting with clipping, and joint forecasting with causal smoothing—completed all 1,024 assigned evaluations. The registered mechanism criterion required at least two variants to produce displacement of at least 0.05 standardized units in eight or more contexts and mean error inflation of at least 0.02 on unchanged channels. Five raw-joint variants met the displacement-count condition; none met the harm condition. All six mean error changes were negative, ranging from −0.017816 to −0.006084. Individual contexts nevertheless experienced increased error. Independent-channel forecasts exhibited zero off-channel displacement, and clean point forecasts and quantiles repeated exactly. The result closes this screen with a hold on the proposed cross-channel-harm scale-up. The conditional simple-control adequacy gate was not reached. These descriptive measurements establish neither general robustness nor a cyberattack defense. [E1–E8]

## 1. Research question and bounded contribution

The practical question motivating candidate 010 was whether an untrusted sensor history could impair forecasts of other, protected sensors enough to justify restricting information flow. Before designing such a defense, a smaller question required evidence: when one history changes, do other predictions merely move, or do they become materially less accurate?

**RQ-D0:** In the pinned native TimesFM 3 configuration, does perturbing one input channel cause practically measurable forecast displacement and increased error on unchanged channels, and would that effect survive simple preprocessing?

The screen separates an input-output mechanism from its proposed engineering consequence. A nonzero change in an unchanged channel's forecast demonstrates influence under the tested intervention. A positive paired error change establishes harm for that observation. Neither observation alone establishes the predefined aggregate harm criterion. This distinction prevents a visually striking forecast change from becoming an unsupported defense claim.

The contribution is a reproducible, fully retained negative mechanism screen with an explicit stopping decision. The experiment demonstrates cross-channel influence in this setup but does not support the preregistered average-harm premise for further investment. Its deliverable is the evidence and reasoning needed to close that premise under the chosen conditions. No priority claim for context protection, forecasting-based detection, or channel separation is made. [E1–E4]

## 2. Relationship to prior work

Anand, Nguyen, and Pappas study forecast-residual attack detection and context-buffer protection. Their paper describes channelwise forecasting in Section II-C and an alarm-dependent buffer-update procedure in Section IV. D0 asks a different, narrower question about native multivariate forecasting: whether changing one history worsens forecasts of unchanged histories. It does not reproduce their attack-detection performance or test a replacement detector. [Attack Detection using Time Series Foundation Models](https://arxiv.org/html/2606.06347v1)

Pandey and colleagues' GITCO already uses a gate, router, and critic to select context interventions, including SMA-based smoothing. Its limitations explicitly identify architecture-specific behavior and robustness under distribution shift as issues requiring further study. D0's fixed causal SMA-5 baseline is a simple comparator; it does not implement GITCO's learned selection procedure. Consequently, an effect here could not establish novelty for generic context gating or smoothing. [GITCO](https://arxiv.org/html/2606.05332v1)

Martinez Gil and colleagues propose adaptive conformal anomaly scoring using pretrained forecast models. That work situates forecast errors within calibration and monitoring. D0 uses paired absolute forecast errors directly and includes no adaptive conformal scoring, alarm-rate calibration, or anomaly-detection endpoint. [Adaptive Conformal Anomaly Detection with Time Series Foundation Models for Signal Monitoring](https://arxiv.org/abs/2604.20122)

The pinned TimesFM evaluator provides joint evaluation and explicit univariate unrolling. This implementation makes the route comparison possible; code support for a route is not evidence that a particular perturbation is harmful. The [prior-work comparison](PRIOR_WORK.md) records the inspected sources and the claims they support. [Pinned evaluator](https://github.com/google-research/timesfm/blob/8cb0628371af142e16b8c232cc9fbf667ffb12f9/src/timesfm3/torch/evaluator.py)

## 3. Methods

### 3.1 Frozen design and public-data construction

The September 15 protocol and machine-readable specification were preserved unchanged. The executable runtime was frozen on September 16 at 21:06:13 UTC, before pretrained D0 inference, and bound to source commit `6f8b650b98b8ed9af0816f7ebc46628fe864d74c`. Their historical plan-only labels describe their creation state; the separate outcome and execution records document completion. No post-outcome changes to windows, amplitudes, or decision thresholds enter this report. [E9]

The source was `001_NAB_id_1_Facility_tr_1007_1st_2014.csv` at TSB-AD tree `6beac72e11d1155ade40870492c00d0d1cfdcaaf`. Only value rows 0–1006 were permitted. Labels did not enter context selection, transformations, or forecasting. The full series had already been used in earlier qualification work, so these observations are development data rather than a fresh confirmation sample. [E10]

The mean and population standard deviation of value rows 0–255 were 44.675765625000004 and 1.6129887267331906. Values were standardized as z[t] = (value[t] − mean) / standard deviation. Three channels were constructed for t ≥ 4:

```text
y0[t] = z[t] + noise[t,0]
y1[t] = 0.8*z[t] + 0.2*z[t-1] + noise[t,1]
y2[t] = 0.6*z[t] + 0.4*z[t-4] + noise[t,2]
```

Noise consisted of independent normal draws with standard deviation 0.01, generated in time-major order with shape (1007,3) by NumPy Generator/PCG64 seed 20260915. Construction, perturbation, and preprocessing used float64; each final model input was cast once to float32. Targets remained float64, and saved predictions were converted to float64 for metric arithmetic. These related artificial channels are not measurements of three industrial sensors. [E10–E11]

The 32 origins were e[j] = 384 + floor(j × 622 / 31), for j = 0,…,31. Each input used the 128 preceding values and predicted the single value at e[j]. Origins spanned 384–1006, following the commissioning interval. Their windows overlapped and shared one underlying series. Channel 0 was the only modified input; channels 1 and 2 and every target remained unchanged across paired conditions. The word “protected” denotes this experimental construction, not a claim about authenticated hardware. [E10–E12]

### 3.2 Model, perturbations, and comparisons

The model was `google/timesfm-3.0-pytorch`, revision `43046b85ec22d584a13f8098c2ed39c889e129c2`, using TimesFM source revision `8cb0628371af142e16b8c232cc9fbf667ffb12f9`. Complete weight, source-ZIP, input, and artifact hashes are recorded in the evidence map. Parameters executed in float32 on one NVIDIA A10G with Python 3.10.12, NumPy 2.2.6, and Torch 2.6.0+cu124. Deterministic algorithms were enabled; TF32 and cuDNN benchmarking were disabled. These choices document this execution environment; they do not guarantee identical outputs on other hardware. [E13]

Six fixed interventions affected channel 0's final 64 context positions: constant positive steps of 1, 3, or 6 standardized units, and inclusive linear ramps from zero to the same amplitudes. There were no adaptive attack queries, outcome-selected windows, weight updates, or amplitude tuning. Four pipelines received the same constructed contexts:

1. **Joint:** native multivariate forecasting with variate attention enabled and `univariate=False`.
2. **Independent:** the same checkpoint with `univariate=True`, unrolling channels into separate series.
3. **Clip:** joint forecasting after clipping only channel 0 to [−3,3].
4. **SMA-5:** joint forecasting after replacing each channel-0 position with the mean of itself and up to four preceding positions within that context.

Clipping and smoothing were applied identically to clean and perturbed inputs. Each pipeline had its own matched clean reference. All pipelines used horizon one, per-core batch size one, no padding, no symmetric averaging, no external z-normalization, no positivity constraint, and sorted quantiles. Nine quantiles from 0.1 to 0.9 were retained; the point forecast was the median, index four. [E14]

### 3.3 Endpoints and decision rules

For a pipeline, origin, and variant, let f0 denote its clean forecast, f1 its perturbed forecast, and y its unchanged target. On channels c = 1,2:

```text
displacement = mean_c |f1[c] - f0[c]|
error change = mean_c (|f1[c] - y[c]| - |f0[c] - y[c]|)
```

Negative error change means lower absolute error. Variant means average **all 32 origins equally**, including origins below the displacement threshold. Clean off-channel mean absolute error (MAE) averages all 64 protected scalar targets. These denominators avoid selecting only conspicuous or harmful observations. [E15]

A raw-joint variant qualified only if displacement was at least 0.05 and above the numerical floor in at least eight contexts, while its all-context mean error inflation was at least 0.02. At least two qualifying variants were required. The numerical floor was max(0.00001, ten times the largest clean-repeat point discrepancy). Excessive clean-repeat discrepancy or independent-channel off-channel change caused a technical hold. Quantile repeats received an additional technical check. [E3, E7]

Only after raw-joint qualification would the protocol ask whether clipping or SMA-5 reduced mean error inflation to at most 0.005 in every qualifying variant while increasing clean MAE by no more than 0.01. These thresholds were research-investment choices, not calibrated probabilities or literature-established clinical or engineering safety margins. [E3, E8]

### 3.4 Accounting and evidence review

Each pipeline/origin pair had a clean evaluation, six perturbed evaluations, and a clean repeat: 4 × 32 × 8 = 1,024 evaluations. Joint pipelines used one native forward call per evaluation; independent evaluation required three. The resulting 1,536 forward calls comprised 1,536 tensor batch sequences and 3,072 scalar channel sequences. Equal evaluation counts therefore do not imply equal compute. [E1]

Source-bound tests, saved-array audits, and a separate raw-evidence review checked identities, finite outputs, untouched input channels and targets, actual native routing, and metric denominators. The separate review calculated from NPZ and JSONL evidence without importing the experiment worker or auditor. It checked 100 pinned Python source files and 11 loaded model modules. These are computational evidence checks, not human peer review or independent laboratory replication. [E12, E16]

## 4. Results

### 4.1 Raw joint forecasting: influence without the required average harm

All 1,024 evaluations completed. Table 1 reports every raw-joint variant. “Displaced” counts contexts meeting the practical threshold and numerical floor; “increased error” counts contexts with strictly positive mean error change across the two protected channels. The latter is a descriptive calculation from the saved per-origin results, not a replacement decision rule. Values are rounded to six decimal places. [E1–E6]

**Table 1. Complete raw-joint results; every context denominator is 32.**

| Variant | Mean displacement | Displaced | Mean error change | Increased error |
|---|---:|---:|---:|---:|
| Step 1 | 0.035381 | 6 | −0.007942 | 11 |
| Step 3 | 0.044683 | 8 | −0.006084 | 14 |
| Step 6 | 0.045013 | 11 | −0.007084 | 14 |
| Ramp 1 | 0.073928 | 22 | −0.017816 | 13 |
| Ramp 3 | 0.080256 | 23 | −0.013414 | 15 |
| Ramp 6 | 0.079158 | 23 | −0.008986 | 15 |

Five variants met the displacement-count condition. None reached mean error inflation of +0.02; each instead had a negative mean. Thus **zero of six variants qualified**, below the required two. The technical audit returned PASS and the scientific decision was `HOLD_CROSS_CHANNEL_HARM_SCALE_UP`. [E2–E4]

The average result does not erase individual harm. For example, Ramp 6 increased mean protected-channel error at 15 of 32 origins, with a maximum increase of 0.127042; its mean across all origins was nevertheless −0.008986. Beneficial and harmful changes coexist within the fixed population. Neither selecting only the harmful origins nor treating the negative mean as universal robustness would represent the protocol's endpoint. [E6]

### 4.2 Complete control results

Table 2 retains all control variants, including unfavorable values. Each change is relative to that pipeline's own clean forecast. No control was substituted for the raw-joint hypothesis pipeline. [E17]

**Table 2. Control results; “displaced” and “increased error” are counts out of 32.**

| Pipeline | Variant | Mean displacement | Displaced | Mean error change | Increased error |
|---|---|---:|---:|---:|---:|
| Independent | Step 1 | 0.000000 | 0 | 0.000000 | 0 |
| Independent | Step 3 | 0.000000 | 0 | 0.000000 | 0 |
| Independent | Step 6 | 0.000000 | 0 | 0.000000 | 0 |
| Independent | Ramp 1 | 0.000000 | 0 | 0.000000 | 0 |
| Independent | Ramp 3 | 0.000000 | 0 | 0.000000 | 0 |
| Independent | Ramp 6 | 0.000000 | 0 | 0.000000 | 0 |
| Clip | Step 1 | 0.038099 | 5 | −0.006243 | 15 |
| Clip | Step 3 | 0.049711 | 14 | −0.004997 | 13 |
| Clip | Step 6 | 0.060340 | 22 | 0.001468 | 18 |
| Clip | Ramp 1 | 0.073617 | 23 | −0.015427 | 13 |
| Clip | Ramp 3 | 0.064838 | 19 | −0.001019 | 17 |
| Clip | Ramp 6 | 0.050415 | 17 | 0.000187 | 16 |
| SMA-5 | Step 1 | 0.037786 | 7 | 0.006780 | 20 |
| SMA-5 | Step 3 | 0.048207 | 12 | −0.000733 | 16 |
| SMA-5 | Step 6 | 0.053673 | 14 | 0.000964 | 15 |
| SMA-5 | Ramp 1 | 0.041873 | 8 | −0.010705 | 11 |
| SMA-5 | Ramp 3 | 0.057301 | 20 | −0.002401 | 19 |
| SMA-5 | Ramp 6 | 0.059425 | 19 | 0.004445 | 19 |

**Table 3. Matched clean accuracy and numerical controls.**

| Pipeline | Clean off-channel MAE | Change from raw-joint clean MAE |
|---|---:|---:|
| Joint | 0.491926 | 0.000000 |
| Independent | 0.483922 | −0.008004 |
| Clip | 0.491075 | −0.000851 |
| SMA-5 | 0.486857 | −0.005070 |

Clean point forecasts and all nine quantiles repeated exactly. The independent pipeline's maximum protected scalar displacement and mean displacement were both zero; the numerical floor was consequently 0.00001. Clean MAEs in Table 3 describe these same 64 scalar targets and do not establish a general ordering of the methods. [E7, E18]

Because no raw-joint variant qualified, the conditional simple-control adequacy gate was **not reached**. The audit's empty `adequate_simple_controls` list cannot be interpreted as evidence that simple controls failed or that a more complex defense is necessary. The positive mean changes in some control cells remain visible but do not rescue the unmet raw-joint criterion. [E8]

### 4.3 Runtime and closeout

Worker wall time was 207.83 seconds, with 2.464 GiB peak allocated and 2.674 GiB peak reserved GPU memory. The frozen cloud tests recorded 16 worker tests and 42 auditor tests passing. Cloud and local full-audit JSON values matched exactly; their serialized bytes differed. One host and one processing attempt were used, with no inference rerun. [E19–E20]

The host was observed stopped after 620.57 seconds from the start request. The conservative estimate was $0.1734 at $1.006 per hour, counting the entire interval through stopped observation. Adding the $5 incidental allowance gives $5.1734 against the $10 reserve. This is a budget estimate, not an invoice; the allowance is not measured spending. Stop protection was removed only after shutdown verification. [E21]

## 5. Discussion

The evidence supports a specific distinction: joint forecasts were sensitive to one channel's history, yet the tested changes did not produce the registered aggregate harm. A perturbation can move an initially imperfect forecast toward its target. The recorded measurements demonstrate that possibility here; they do not identify which model component caused the improvement or justify using corruption as a forecasting strategy.

The independent route supplies a useful structural negative control. Its unchanged predictions are consistent with the absence of the modified channel from the other channels' forecast inputs. Combined with exact clean repeats and observed native routing, this makes generic execution noise or accidental channel sharing an inadequate explanation for the observed joint displacement. It still does not prove that independent forecasting is safer or more accurate for arbitrary real systems.

The research decision follows the frozen criterion: close D0 and hold scale-up of the cross-channel-harm hypothesis. D0 supplies no warrant for a D1 efficacy study. Replacing this dataset, changing amplitudes, or selecting harmful origins after seeing these outcomes would answer a different question and could not turn this screen into a positive result. Its value is preserving a completed investigation and avoiding a defense proposal whose motivating average-harm result was absent.

## 6. Limitations

This is one previously inspected public series transformed into three channels. Thirty-two overlapping windows and six paired variants are not 192 independent incidents. Accordingly, results are descriptive; no significance tests, confidence intervals based on independent windows, or population prevalence estimates are reported.

The interventions are fixed positive steps and ramps on one channel. Negative changes, adaptive attacks, multiple corrupted channels, longer horizons, and naturally measured multivariate relationships are outside scope. Their omission limits generalization; it does not authorize changing the completed screen to obtain a favorable outcome. The practical thresholds determine an investment decision and are not equivalence bounds or a guarantee of safety.

The protected-channel assumption was constructed by the experimenter. No attack attribution, authenticity mechanism, operational alarm, retention metric, or benign-recovery process was tested. No HAI data was accessed. Pretraining exposure to public observations remains unresolved. Results apply to a pinned checkpoint and numerical configuration; they do not establish behavior across versions or hardware. Finally, artifact verification confirms the retained calculations and provenance, while human understanding, originality assessment, and academic suitability remain separate judgments. [E10, E12–E16]

## 7. Reproducibility and evidence availability

[EVIDENCE.json](EVIDENCE.json) maps the report's numbered claims to repository paths, SHA-256 hashes, exact JSON pointers, and explicitly labeled derived counts. The preserved package contains exact input and target arrays, all forecasts and quantiles, per-evaluation observations, native-call counters, environment inventory, source identities, and both audit outputs. The result archive has SHA-256 `119ed5a294260acb2ce188a721e23759a49e778a357c9a44af66f564ffc20e36`; independently downloaded copies matched. Model weights and private operational configuration are excluded from Git. [E22]

To reproduce the measurements without new inference, use the frozen `code/audit_d0.py` with the saved `completed_run/run` directory, the pinned source CSV and source ZIP, and a new output directory. The auditor rebuilds the assigned inputs, verifies identities, and recalculates the metrics. NumPy 2.2.6 is the recorded audit dependency. Regenerating forecasts is a separate GPU execution requiring the pinned packages, model weights, and complete numerical configuration; this report does not claim that such a rerun occurred during manuscript preparation.

The [NAB/TSB-AD notices](../../010_attack_aware_forecasting/completed_qualification/licenses/NOTICE.md) accompany derived data. The pinned TimesFM 3 weight terms must be reviewed separately from source-code licensing. Historical protocol, runtime-freeze, and outcome records are retained as separate artifacts so a reviewer can distinguish intended criteria, executed configuration, and observed findings.

## 8. Conclusion

All assigned evaluations completed and passed technical audit. Perturbing channel 0 influenced joint forecasts for unchanged channels, but every raw-joint variant reduced average protected-channel error and zero variants met the registered harm criterion. Individual harmful contexts remained present. The appropriate closeout is a negative mechanism result, an unreached simple-control adequacy gate, and a hold on D1 scale-up—not a claim of general robustness or a validated cyber defense.

## References

1. Anand, Nguyen, and Pappas. *Attack Detection using Time Series Foundation Models*. arXiv:2606.06347, version 1, 2026. [Primary paper](https://arxiv.org/html/2606.06347v1).
2. Pandey et al. *GITCO: Gated Inference-Time Context Optimization in TSFMs*. arXiv:2606.05332, version 1, 2026. [Primary paper](https://arxiv.org/html/2606.05332v1).
3. Martinez Gil et al. *Adaptive Conformal Anomaly Detection with Time Series Foundation Models for Signal Monitoring*. arXiv:2604.20122, version 1, 2026. [Primary record](https://arxiv.org/abs/2604.20122).
4. Google Research. *TimesFM: native TimesFM 3 evaluator*, source revision `8cb0628371af142e16b8c232cc9fbf667ffb12f9`. [Pinned primary implementation](https://github.com/google-research/timesfm/blob/8cb0628371af142e16b8c232cc9fbf667ffb12f9/src/timesfm3/torch/evaluator.py).
5. Praxis D0. [Frozen protocol](../../010_development_20260915/D0_PROTOCOL.md), [specification](../../010_development_20260915/D0_SPEC.json), and [completed execution](../../010_d0_execution_20260915/OUTCOME.md), September 2026. Primary evidence is indexed in [EVIDENCE.json](EVIDENCE.json).
