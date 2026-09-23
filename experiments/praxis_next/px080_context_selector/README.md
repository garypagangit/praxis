# PX-080 — Learning when historical context hurts

## Result: better movement recall than ordinary gating, with explicit costs

**The proposed stage-harm selector did not establish an overall advantage.** It recovered more movement-stage labels than the matched ordinary selector in all five conditions, but produced more normal false alarms and worse stage-weighted error in all five. The simpler dropout-trained model was stronger when history was entirely missing or linked to the wrong host. Current evidence alone retained the highest movement recall.

This is a completed, frozen development experiment: **39 fits, three seeds, five conditions, seven arms, and 105 saved probability tables**. Runtime was 547.6 seconds on local CPU. AWS authentication could not be refreshed by the parent workflow, so no AWS compute was used for this run.

| Condition / comparison | Movement recall | Normal false alarms | Macro F1 |
|---|---:|---:|---:|
| Clean / ordinary learned selector | 64.76% | 85.67 | 0.7659 |
| Clean / proposed stage-harm selector | 69.52% | 109.00 | 0.7560 |
| Missing all history / ordinary selector | 36.19% | 62.33 | 0.7419 |
| Missing all history / proposed selector | 42.86% | 77.00 | 0.7422 |
| Missing all history / context dropout | 68.57% | 116.00 | 0.7587 |
| Current evidence and roles alone, every condition | 78.10% | 139.33 | 0.7545 |

These are means across fits on the same later-period events. In the five-minute stale condition, movement recall rose from 49.52% under ordinary gating to 63.81% under the proposed selector, while normal false alarms rose from 85 to 113.33. With hidden wrong-host history, the proposed selector achieved 44.76% movement recall versus 35.24% for ordinary gating and 68.57% for context dropout.

## What was tested

A current-evidence model and a current-plus-history model make stage predictions. A selector learns which one to use from strictly earlier, held-out prediction comparisons. The proposed target assigns movement and exfiltration errors four times the cost of other errors; a matched ordinary selector uses equal costs. The cost ratio is a declared design choice, not a literature requirement. Fixed fusion, confidence gating and missingness/dropout training are retained controls.

The selector sees only model probabilities and observable history age/availability at deployment. No true stage, absolute clock, capture identifier or future log is a predictor. The five-minute condition is a simulated stale snapshot reconstructed using only events completed before its earlier cutoff. Missing and wrong-host histories are replay interventions, not observed production outages.

## Why this remains preliminary

- The data are an already-examined UNRAVELED campaign. Evaluation has only **35 movement-labeled flows**. The author's movement annotation is Remote System Discovery on one host pair, not verified successful intrusion into another host.
- Forward selector fitting contains only **18 distinct movement flows**, replicated across three synthetic conditions. Repeated views and seeds are not additional independent attacks.
- The ordinary selector receives identical forward examples and augmentation to the proposed selector. It is the appropriate comparison for isolating the new loss target. The dropout classifier sees missingness augmentation but no stale augmentation.
- Current completed-flow measurements are used. **No exfiltration prediction before theft, lead time, independent-campaign confirmation, or missing-information recovery was measured.**
- Higher movement recall alone does not establish superiority; costs and stronger simple controls remain visible. No arbitrary 90% criterion was applied.

## Praxis decision

The useful finding is a measured failure mode: an apparently successful reduction in normal alarms can conceal loss of movement-stage recognition when context is missing or incorrectly linked. Stage-sensitive gating partly changes that tradeoff, but this implementation does not outperform the matched ordinary selector overall. A defensible method claim requires better verified and more independent movement examples, a stronger remedy, and comparisons against straightforward dropout and fallback policies. These results do not establish algorithm novelty.

## Evidence and reproducibility

[Full report](results/REPORT.md) · [All metrics and strata](results/METRICS.json) · [Three-seed means](results/MEANS.json) · [Frozen protocol](PROTOCOL.md) · [Scientific source binding](FREEZE.json) · [Calculation and inference audit](results/AUDIT.json)

The scientific freeze was committed as `06c5037` before fitting. Private row-linked probabilities, fold supervision, fitted models and source references are retained under `C:/w/apt_benchmark_data_20260920/praxis_next/px080/run_v1`. The audit checks calculations and causal partition/inference integrity; it is not independent verification of the dataset's attack truth.

From the repository root:

```powershell
python -m pytest experiments/praxis_next/px080_context_selector/test_selector.py -q
python -m experiments.praxis_next.px080_context_selector.run run --data <qualified_DATA.npz> --output <fresh_private_run> --freeze-commit 06c5037
python -m experiments.praxis_next.px080_context_selector.audit --data <qualified_DATA.npz> --run <private_run> --output <private_run>/AUDIT.json
python -m experiments.praxis_next.px080_context_selector.report --run <private_run> --output experiments/praxis_next/px080_context_selector/results
```
