# Interpreting the original TimesFM 2.5 runtime

Read-only source analysis requested during the first frozen run, September14,2026. No model call, cohort change, rerun or worker edit was made for this analysis.

At the pinned [official TimesFM revision](https://github.com/google-research/timesfm/tree/8cb0628371af142e16b8c232cc9fbf667ffb12f9), the released June script's short forecasts carry substantial default overhead:

1. `ForecastConfig.per_core_batch_size` defaults to1 (`src/timesfm/configs.py`, line55). The base `forecast` method flushes a decode whenever that one-item batch fills (base implementation lines174–193). Three sensor histories therefore produce three serialized batches, rather than one batch of three.
2. `max_context=512` pads each50-value history to512 values, or16 input patches of32 (`timesfm_2p5_base.py`, lines175–183). Fifty observed values occupy only two patches, but padded patches still enter the fixed-shape preprocessing/network workload with masks.
3. `force_flip_invariance=True` is the default. The Torch implementation evaluates both the original and negated input (`timesfm_2p5_torch.py`, lines444–470). Thus each logical three-channel forecast entails six decoder/network passes.
4. `decode` performs a Python loop over the16 running-stat patches and allocates fresh per-layer caches before the compiled network forward (lines116–170). Small operations and CPU/GPU transitions can limit utilization even when model weights fit comfortably in memory.
5. The model forward computes its full point and quantile projection heads (lines104–105), with128-point and1024-quantile output lengths, before the wrapper returns the requested one-step horizon. Disabling continuous-quantile use does not remove the head's computation in this source.

The frozen run makes8,020 logical forecast calls:20 calibration calls,2,000 historical attacked/clean calls, and6,000 deployable comparator calls. The default settings imply approximately48,120 decoder/network passes. Finishing within2,400 seconds requires an average no greater than0.299 seconds per logical forecast, approximately49.9ms per pass before accounting for preprocessing and initialization. This is a budget calculation, not a measured forecast latency.

The source's historical progress prints are buffered. Our first explicit flushed comparator progress line occurs after roughly2,120 logical calls. Absence of stdout during the first several minutes therefore does not alone establish a stalled process. Initial lazy Torch compilation can further concentrate cost at startup. The root-observed active GPU and low memory footprint were consistent with an under-batched workload; they do not by themselves prove useful progress or predict completion.

The declared40-minute process cap remains in force. A timeout is a resource/implementation qualification result, not evidence that the detector failed to recognize attacks. Changing batch size, context padding, symmetry settings, or compilation would require a separately recorded compatibility/optimization study: some settings can alter forecasts and cannot be treated as scientifically identical without comparison. No such change is made to this run.
