# PX-080: Does learning context harm preserve attack-stage recognition?

**Completed development pilot.** Every fixed comparison is shown, including failures. This is a previously exposed, single-campaign UNRAVELED evaluation, not independent confirmation. No exfiltration forecast was performed.

The run fitted 39 models and saved 105 arm/condition/seed probability tables. Evaluation counts (benign, other attack, movement, exfiltration): [192193, 12424, 35, 3442]. CPU experiment runtime: 547.6 seconds. Three seeds reuse the same events.

## What changed

The current expert and context expert share current flow summaries and coarse roles. The proposed selector learns whether using context increases stage errors, giving movement/exfiltration errors four times the training cost. An ordinary selector learns unweighted error differences on exactly the same forward-held-out predictions. Costs are design choices, not standards or safety guarantees. All selectors use observable model scores and evidence age/availability at deployment.

History is prior completed-flow activity. The five-minute condition is a simulated stale snapshot; missing and wrong-host conditions are simulated interventions. Current decisions still use completed-flow measurements and are not early warnings.

## All comparisons

Values are means across three fits. Counts may be fractional because these are means. Stage-weighted error is lower-is-better; the other detection metrics are higher-is-better. Interpret false-alarm and movement costs alongside any aggregate improvement.

### clean

| Arm | Macro F1 | Movement recall | Movement F1 | Exfil recall | Exfil F1 | Normal false alarms | Weighted error |
|---|---:|---:|---:|---:|---:|---:|---:|
| current_roles | 0.7545 | 78.10% | 0.2799 | 67.50% | 0.7578 | 139.33 | 0.024225 |
| context | 0.7658 | 52.38% | 0.3183 | 67.21% | 0.7636 | 48.33 | 0.024044 |
| fixed_fusion | 0.7655 | 60.00% | 0.3174 | 67.42% | 0.7631 | 76.00 | 0.023960 |
| confidence_gate | 0.7650 | 60.00% | 0.3153 | 67.42% | 0.7630 | 77.00 | 0.023964 |
| ordinary_gate | 0.7659 | 64.76% | 0.3195 | 67.36% | 0.7621 | 85.67 | 0.023988 |
| stage_harm_gate | 0.7560 | 69.52% | 0.2797 | 67.28% | 0.7625 | 109.00 | 0.024122 |
| context_dropout | 0.7589 | 51.43% | 0.2918 | 67.41% | 0.7621 | 68.67 | 0.023965 |

### missing_half

| Arm | Macro F1 | Movement recall | Movement F1 | Exfil recall | Exfil F1 | Normal false alarms | Weighted error |
|---|---:|---:|---:|---:|---:|---:|---:|
| current_roles | 0.7545 | 78.10% | 0.2799 | 67.50% | 0.7578 | 139.33 | 0.024225 |
| context | 0.6626 | 29.52% | 0.2523 | 66.99% | 0.7668 | 28.67 | 0.053393 |
| fixed_fusion | 0.7602 | 44.76% | 0.2989 | 67.33% | 0.7638 | 54.33 | 0.024391 |
| confidence_gate | 0.7592 | 44.76% | 0.2989 | 67.33% | 0.7643 | 54.33 | 0.024896 |
| ordinary_gate | 0.7598 | 52.38% | 0.2969 | 67.30% | 0.7612 | 74.33 | 0.024132 |
| stage_harm_gate | 0.7561 | 60.95% | 0.2822 | 67.17% | 0.7610 | 93.67 | 0.024249 |
| context_dropout | 0.7595 | 62.86% | 0.2955 | 67.43% | 0.7609 | 95.00 | 0.024031 |

### missing_all

| Arm | Macro F1 | Movement recall | Movement F1 | Exfil recall | Exfil F1 | Normal false alarms | Weighted error |
|---|---:|---:|---:|---:|---:|---:|---:|
| current_roles | 0.7545 | 78.10% | 0.2799 | 67.50% | 0.7578 | 139.33 | 0.024225 |
| context | 0.4339 | 0.00% | 0.0000 | 66.75% | 0.7693 | 0.00 | 0.082373 |
| fixed_fusion | 0.7285 | 18.10% | 0.1752 | 67.30% | 0.7642 | 29.67 | 0.024872 |
| confidence_gate | 0.7265 | 18.10% | 0.1752 | 67.29% | 0.7655 | 29.67 | 0.025852 |
| ordinary_gate | 0.7419 | 36.19% | 0.2272 | 67.23% | 0.7601 | 62.33 | 0.024316 |
| stage_harm_gate | 0.7422 | 42.86% | 0.2289 | 67.02% | 0.7594 | 77.00 | 0.024483 |
| context_dropout | 0.7587 | 68.57% | 0.2939 | 67.50% | 0.7597 | 116.00 | 0.024079 |

### stale_5min

| Arm | Macro F1 | Movement recall | Movement F1 | Exfil recall | Exfil F1 | Normal false alarms | Weighted error |
|---|---:|---:|---:|---:|---:|---:|---:|
| current_roles | 0.7545 | 78.10% | 0.2799 | 67.50% | 0.7578 | 139.33 | 0.024225 |
| context | 0.7261 | 21.90% | 0.1590 | 67.22% | 0.7640 | 37.67 | 0.024196 |
| fixed_fusion | 0.7491 | 41.90% | 0.2513 | 67.41% | 0.7632 | 67.67 | 0.024032 |
| confidence_gate | 0.7485 | 41.90% | 0.2490 | 67.42% | 0.7631 | 69.00 | 0.024034 |
| ordinary_gate | 0.7456 | 49.52% | 0.2377 | 67.30% | 0.7627 | 85.00 | 0.024113 |
| stage_harm_gate | 0.7472 | 63.81% | 0.2435 | 67.33% | 0.7630 | 113.33 | 0.024125 |
| context_dropout | 0.7514 | 48.57% | 0.2618 | 67.39% | 0.7620 | 77.67 | 0.024024 |

### wrong_host

| Arm | Macro F1 | Movement recall | Movement F1 | Exfil recall | Exfil F1 | Normal false alarms | Weighted error |
|---|---:|---:|---:|---:|---:|---:|---:|
| current_roles | 0.7545 | 78.10% | 0.2799 | 67.50% | 0.7578 | 139.33 | 0.024225 |
| context | 0.4559 | 0.00% | 0.0000 | 66.80% | 0.7599 | 0.00 | 0.079286 |
| fixed_fusion | 0.7286 | 19.05% | 0.1759 | 67.31% | 0.7635 | 32.33 | 0.024837 |
| confidence_gate | 0.7267 | 19.05% | 0.1753 | 67.30% | 0.7652 | 32.67 | 0.025734 |
| ordinary_gate | 0.7406 | 35.24% | 0.2217 | 67.24% | 0.7605 | 61.67 | 0.024313 |
| stage_harm_gate | 0.7430 | 44.76% | 0.2319 | 67.03% | 0.7597 | 81.33 | 0.024478 |
| context_dropout | 0.7589 | 68.57% | 0.2981 | 67.50% | 0.7573 | 114.67 | 0.024165 |

## Selector decisions

These are counts of selected context that changes an otherwise correct decision into an error (harm), or corrects a current-only error (help). They are descriptive test outcomes, never inputs to the selector.

| Condition | Selector | Context used | Harm count | Help count |
|---|---|---:|---:|---:|
| clean | confidence_gate | 70.17% | 13.00 | 94.33 |
| clean | ordinary_gate | 0.35% | 12.33 | 89.67 |
| clean | stage_harm_gate | 0.28% | 14.00 | 67.33 |
| missing_half | confidence_gate | 66.97% | 190.00 | 103.33 |
| missing_half | ordinary_gate | 0.35% | 18.67 | 86.00 |
| missing_half | stage_harm_gate | 0.25% | 20.33 | 67.33 |
| missing_all | confidence_gate | 63.88% | 363.33 | 109.67 |
| missing_all | ordinary_gate | 0.33% | 24.00 | 77.00 |
| missing_all | stage_harm_gate | 0.21% | 29.00 | 62.33 |
| stale_5min | confidence_gate | 60.39% | 19.67 | 105.33 |
| stale_5min | ordinary_gate | 0.20% | 20.33 | 94.67 |
| stale_5min | stage_harm_gate | 0.24% | 14.67 | 68.33 |
| wrong_host | confidence_gate | 61.35% | 338.00 | 107.00 |
| wrong_host | ordinary_gate | 0.32% | 24.00 | 77.67 |
| wrong_host | stage_harm_gate | 0.21% | 27.67 | 58.00 |

## Limits and next scientific decision

- Only 35 evaluation movement rows, representing the author's Remote System Discovery progress annotation on one pair of hosts; 27 movement fitting rows and no movement calibration rows. These are not 35 independently verified intrusions.
- Forward selectors learn from only four development captures; the same dataset was examined in earlier work. Chronology and held-out predictions prevent direct in-fit leakage but do not make this an untouched confirmatory experiment.
- Coarse role shift, capture-level results and all per-class AP/ROC metrics are retained in METRICS.json. Seeds measure fitting variability, not independent-campaign uncertainty.
- No arbitrary pass threshold and no tuned test operating point. A positive aggregate metric is insufficient if dangerous-stage recognition worsens or benefits do not exceed ordinary gating/dropout.
- A strong next claim requires independent executions with verified event outcomes and matched benign controls. Novelty must be assessed against existing gating, temporal fusion and context-ablation work.

## Reproducibility

[Frozen protocol](../PROTOCOL.md) · [Source binding](../FREEZE.json) · [All metrics](METRICS.json) · [Summary CSV](METRICS.csv) · [Audit](AUDIT.json)

Private row-linked probabilities, forward-fold targets, source identities and saved fitted models are retained under the private run directory. Public receipts bind input and scientific source hashes.
