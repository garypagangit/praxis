# D0: cross-channel forecast-harm mechanism screen

Status: **prospective design; experiment not run; executable runtime not frozen**. This internal research protocol is separate from Q1. It records no new defense, favorable result, untouched confirmation cohort or academic approval.

## Research question and hypothesis

**RQ-D0:** In the pinned native TimesFM 3 model, does perturbing only one input channel cause a practically measurable change and increased forecast error on unchanged channels, and does that effect persist under simple context preprocessing?

**H-D0 (raw-joint mechanism criterion):** On the predefined semisynthetic public-data contexts, raw joint forecasting produces off-channel displacement of at least 0.05 standardized units in at least eight of 32 contexts in at least two perturbation variants, and positive mean off-channel error inflation of at least 0.02 units in those same variants. Separate-channel forecasts stay within the numerical repeat tolerance. The preprocessing comparison is a separate complexity/investment gate. These are proposed investment thresholds, not values guaranteed by literature. All variants and negative findings will be retained.

This tests a mechanism that would motivate development. It does not test persistent attack detection, infer malicious intent, or establish a novel algorithm. A successful architectural check alone is insufficient to advance to a full efficacy campaign.

## Literature and source basis

- [Attack Detection using Time Series Foundation Models](https://arxiv.org/html/2606.06347v1), Section IV / Algorithm 1: forecast-residual detection and protected context updates already exist. Q1 separated the released historical oracle-onset calculation from deployable policies.
- [GITCO](https://arxiv.org/html/2606.05332v1), Sections 3.1-3.3 and 6: input-context gating, routing and smoothing already exist; robustness under distribution shift remains an open direction in that paper. Its published forecasting objective is distinct from a demonstrated persistent-cyberattack defense. An SMA control below is not a reproduction of GITCO's learned gate, router or critic.
- [Adaptive Conformal Anomaly Detection with Time Series Foundation Models for Signal Monitoring](https://arxiv.org/abs/2604.20122) and the [pinned public implementation](https://github.com/ibm-granite/granite-tsfm/tree/fe7a35697723e2a2f5246ae979474bfc554e26c0/notebooks/hfdemo/adaptive_conformal_tsad): the selected NAB/TSB-AD public example is the same one used in Q1's executable base reproduction.
- [TimesFM 3 evaluator](https://github.com/google-research/timesfm/blob/8cb0628371af142e16b8c232cc9fbf667ffb12f9/src/timesfm3/torch/evaluator.py) and [transformer](https://github.com/google-research/timesfm/blob/8cb0628371af142e16b8c232cc9fbf667ffb12f9/src/timesfm3/torch/transformer.py): the joint path permits attention across variates; independent unrolling is an explicit alternative. Q1 verified execution, not the magnitude or harmfulness of off-channel influence.

No claim of priority follows from this bounded source review. Directional access to trusted measurements, feature isolation, clipping and multiple reference windows all require comparison with close prior methods before a novelty argument.

## Public-data base and fixed construction

Use `001_NAB_id_1_Facility_tr_1007_1st_2014.csv`, pinned TSB-AD tree `6beac72e11d1155ade40870492c00d0d1cfdcaaf`, file SHA-256 `e3e67660bbaa840ef24e70b38f0b384d41c7e2bce71bf0edbab65565a40a7584`. The first numeric value column supplies data; labels do not enter transformations, context selection or forecasting. The entire series has already been used for Q1 development. This screen is not a fresh test set.

Only value rows 0 through 1006 are allowed. Compute mean and population standard deviation from rows 0 through 255; stop if values are nonfinite or the standard deviation is below 1e-6. Set `z[t] = (value[t] - mean) / sd`. Construct three channels for t >= 4:

```text
y0[t] = z[t] + noise[t,0]
y1[t] = 0.8*z[t] + 0.2*z[t-1] + noise[t,1]
y2[t] = 0.6*z[t] + 0.4*z[t-4] + noise[t,2]
```

Noise is 0.01 times independent standard-normal draws using NumPy Generator/PCG64 seed 20260915, generated in time-major order with shape (1007,3). The first four derived rows are unused. This creates related artificial channels from public observations; it does not turn a univariate facility series into measured industrial sensors.

Construct and transform values in float64, including perturbations and preprocessing, then cast each final model input once to float32. Keep unmodified targets in float64. Convert saved forecasts to float64 for metric arithmetic. Save exact model-input and target arrays and hashes. Pin NumPy, Torch, model dtype and device behavior in the later executable freeze; do not silently change this operation order.

Define 32 forecast origins `e[j] = 384 + floor(j*622/31)`, j=0..31. Input is `y[e-128:e]`, target is `y[e]`, horizon one. Commissioning precedes every context. Windows overlap and share one underlying public series. Report descriptive within-series measurements, not confidence intervals treating windows or perturbations as independent incidents.

Channel 0 is the only modified input. Channels 1 and 2 and all future targets remain byte-identical across paired conditions. The experimenter-defined protected-channel assumption is synthetic; it is not inferred from a dataset label or claimed for HAI hardware.

## Perturbations, model and controls

Six fixed perturbation variants affect the final 64 context positions of channel 0: positive steps of 1, 3 or 6 standardized units; positive ramps with 64 inclusive equally spaced values from zero to 1, 3 or 6. No adaptive queries, favorable-window selection, attack-onset oracle in a detector, or outcome-driven amplitude changes are allowed.

Use TimesFM source commit `8cb0628371af142e16b8c232cc9fbf667ffb12f9` and `google/timesfm-3.0-pytorch` revision `43046b85ec22d584a13f8098c2ed39c889e129c2`. Model-file SHA-256 is `a7592b0a8432baee54483254e5647856911ce69e09d09a9bb65904b2d98f17da`. Preserve Q1's model options: horizon one, symmetric averaging off, z-normalization off, positivity off, sorted quantiles on, return quantiles, per-core batch size one. No weight training or adaptive calibration is part of D0.

Explicitly set `ModelConfig(use_variate_attention=True)` and `predict_batch(..., padding_mode="none", univariate=False)` for joint pipelines; set `univariate=True` for the independent pipeline. Do not rely on defaults to establish the intended routing.

Four pipelines receive exactly the same base contexts and perturbations:

1. **Joint native TimesFM 3.** One (3,128) context.
2. **Independent native TimesFM 3.** The same checkpoint and options, with the evaluator's independent univariate path. This is the structural negative control for off-channel changes.
3. **Joint plus clipping.** Clip only channel 0 to [-3,3] in the standardized input, using the same rule on clean and perturbed contexts.
4. **Joint plus causal SMA-5.** Replace each channel-0 context position with the mean of itself and up to four preceding positions within that context. Other channels are unchanged. Apply the identical transformation to clean and perturbed contexts. This is a simple smoothing baseline, not GITCO.

Each pipeline has its own matched clean forecast; comparisons never substitute another pipeline's clean prediction. Save every forecast and quantile array, including one extra clean repeat per pipeline/context. Budget: 4*32*(1 clean + 6 perturbed + 1 clean repeat) = **1,024 pipeline evaluations**. Independent univariate evaluations contain three channel sequences, so report actual tensor sequences, forward calls, wall time and memory separately. D0 makes no equal-compute efficacy or speed claim.

## Metrics, audit and decision

For each context/variant/pipeline, let `f_clean` and `f_perturbed` be paired forecasts. On unchanged channels c=1,2:

```text
spillover = mean_c(abs(f_perturbed[c] - f_clean[c]))
error_inflation = mean_c(abs(f_perturbed[c] - target[c])
                         - abs(f_clean[c] - target[c]))
```

Every variant-level mean error inflation is the arithmetic mean over **all 32 contexts equally**, including contexts below the spillover threshold. Clean off-channel MAE is the mean absolute error over **all 32 times two unchanged-channel targets** for that pipeline. Never condition either mean on the eight or more high-spillover contexts.

The numerical floor is `max(1e-5, 10*maximum clean-repeat discrepancy)` in output units. Any clean-repeat discrepancy above 1e-5 is an operational HOLD. Independent-channel off-channel changes above that floor are also HOLD and require diagnosis, not a scientific effect claim. Verify untouched inputs/targets, source hashes, all 1,024 assigned evaluations, finite outputs and complete identities. Audit from saved arrays; no summary-only evidence is sufficient.

H-D0's two numerical conditions must hold in the same at least two variants, and qualifying spillover must exceed the numerical floor. If they do not, **hold scale-up of the cross-channel-harm hypothesis**. Do not substitute another dataset/window/amplitude to rescue this fixed screen.

If either simple preprocessing baseline brings mean off-channel error inflation to <=0.005 in every variant that qualified under joint forecasting, and increases its clean off-channel MAE by <=0.01 relative to raw joint forecasting, **hold the proposed complex defense**: this screen has not demonstrated a need beyond that simpler control. Otherwise D0 may justify a separate prospective retention/recovery design. That is a research decision, not a positive defense result.

## What a later D1 must establish

A later protocol would test directional access: protected-target forecasts exclude untrusted histories; untrusted-target forecasts may use protected histories. Compare equally informed independent forecasts, trusted-channel linear reconstruction, dual-reference controls, clipping and qualified prior methods. Structural exclusion can guarantee absence of a particular input path; it does not guarantee correct predictions or cyber safety.

D1 must fix benign physical changes, persistent/stealthy corruptions, compromised-trust and identical-observation controls before outcomes. Primary late-episode retention must improve over the strongest feasible comparator while meeting fixed clean-alarm and recovery constraints. The previous proposal of at least five percentage points is an investment choice, not a literature-derived effect. D0 supplies no evidence for those outcomes; their exact dataset, margins, independent units and implementation must be frozen separately.

## Execution boundary

A document-integrity PASS does not satisfy the experiment's technical launch gate. Before actual processing, commit the executable worker and pin its environment; independently check routing, paired transforms, source identity and evaluation accounting; then use the existing authorized AWS workflow with one host, external stop protection, a **30-minute total host cap and $10 combined reserve**. This is an engineering launch requirement under the user's existing authorization. Preserve failures, download evidence and verify stopped state.

No HAI files are accessed in D0. Future HAI work must cite [Q1-D1](https://github.com/garypagangit/praxis/blob/cdf59507b588972b9a0f6879daa1184eadcf08e6/final_praxis/010_attack_aware_forecasting/completed_qualification/HAI_METADATA_SCOPE_DEVIATION.json) and freeze roles before sensor/label analysis. Preserve the [NAB/TSB-AD notices](https://github.com/garypagangit/praxis/tree/cdf59507b588972b9a0f6879daa1184eadcf08e6/final_praxis/010_attack_aware_forecasting/completed_qualification/licenses) for derived data and TimesFM 3's noncommercial/nonproduction weight terms. The final Praxis still needs a defensible public-data evaluation beyond this semisynthetic mechanism screen.
