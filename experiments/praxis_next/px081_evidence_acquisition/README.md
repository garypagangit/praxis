# PX-081: Choosing which evidence to inspect next

## Plain-language result

This development experiment asks whether selecting extra information by its expected reduction in dangerous-stage errors improves decisions over selecting information by uncertainty reduction. All costs, delivery delays and channel failures below are simulated offline. The source data are real captured traffic with author stage annotations, from one previously examined UNRAVELED campaign. These results do not measure live collection, independent attack generalization or early exfiltration prediction.

Completed 60 classifier and 24 selector fits across three seeds. Evaluation: 208,094 flows; benign/other/movement/exfiltration counts = [192193, 12424, 35, 3442]. Calibration labels were not used. Seed averages below are descriptive fitting sensitivity, not independent-campaign confidence intervals.

## All matched comparisons

Movement/exfiltration recall measures exact author-stage recognition. False alerts count benign rows assigned any attack. Weighted errors use the prespecified illustrative true-class costs 1/1/4/4; this is not a published acceptance standard. Spend is simulated units per decision.

### clean

| Budget | Policy | Macro-F1 | Movement recall | Exfiltration recall | Benign false alerts | Weighted errors | Mean spend | Query rate |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | none | 0.7523 | 78.10% | 67.52% | 164.0 | 5065.7 | 0.000 | 0.00% |
| 1 | roles_first | 0.7136 | 85.71% | 67.52% | 179.7 | 5069.3 | 1.000 | 100.00% |
| 1 | history_first | 0.7136 | 85.71% | 67.52% | 179.7 | 5069.3 | 1.000 | 100.00% |
| 1 | random | 0.7136 | 85.71% | 67.52% | 179.7 | 5069.3 | 1.000 | 100.00% |
| 1 | entropy | 0.7139 | 81.90% | 67.52% | 174.0 | 5068.7 | 0.621 | 62.09% |
| 1 | harm | 0.7500 | 81.90% | 67.52% | 169.7 | 5064.0 | 0.410 | 41.04% |
| 2 | none | 0.7523 | 78.10% | 67.52% | 164.0 | 5065.7 | 0.000 | 0.00% |
| 2 | roles_first | 0.7136 | 85.71% | 67.52% | 179.7 | 5069.3 | 1.000 | 100.00% |
| 2 | history_first | 0.7594 | 58.10% | 67.13% | 86.7 | 5041.0 | 2.000 | 100.00% |
| 2 | random | 0.7213 | 76.19% | 67.34% | 133.7 | 5052.0 | 1.500 | 100.00% |
| 2 | entropy | 0.7181 | 63.81% | 67.29% | 101.3 | 5025.7 | 1.282 | 92.86% |
| 2 | harm | 0.7551 | 61.90% | 67.25% | 107.3 | 5044.3 | 1.030 | 68.28% |
| 3 | none | 0.7523 | 78.10% | 67.52% | 164.0 | 5065.7 | 0.000 | 0.00% |
| 3 | roles_first | 0.7153 | 68.57% | 67.15% | 115.3 | 5040.3 | 3.000 | 100.00% |
| 3 | history_first | 0.7153 | 68.57% | 67.15% | 115.3 | 5040.3 | 3.000 | 100.00% |
| 3 | random | 0.7153 | 68.57% | 67.15% | 115.3 | 5040.3 | 3.000 | 100.00% |
| 3 | entropy | 0.7148 | 65.71% | 67.29% | 111.3 | 5032.7 | 2.535 | 92.86% |
| 3 | harm | 0.7379 | 69.52% | 67.18% | 122.3 | 5056.0 | 1.717 | 68.28% |

### delayed_unavailable

| Budget | Policy | Macro-F1 | Movement recall | Exfiltration recall | Benign false alerts | Weighted errors | Mean spend | Query rate |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | none | 0.7523 | 78.10% | 67.52% | 164.0 | 5065.7 | 0.000 | 0.00% |
| 1 | roles_first | 0.7167 | 83.81% | 67.52% | 173.3 | 5067.7 | 1.000 | 100.00% |
| 1 | history_first | 0.7167 | 83.81% | 67.52% | 173.3 | 5067.7 | 1.000 | 100.00% |
| 1 | random | 0.7167 | 83.81% | 67.52% | 173.3 | 5067.7 | 1.000 | 100.00% |
| 1 | entropy | 0.7168 | 80.95% | 67.52% | 169.7 | 5068.0 | 0.621 | 62.09% |
| 1 | harm | 0.7509 | 80.95% | 67.52% | 167.7 | 5064.7 | 0.410 | 41.04% |
| 2 | none | 0.7523 | 78.10% | 67.52% | 164.0 | 5065.7 | 0.000 | 0.00% |
| 2 | roles_first | 0.7167 | 83.81% | 67.52% | 173.3 | 5067.7 | 1.000 | 100.00% |
| 2 | history_first | 0.7547 | 71.43% | 67.39% | 135.0 | 5052.0 | 2.000 | 100.00% |
| 2 | random | 0.7223 | 77.14% | 67.46% | 156.7 | 5063.0 | 1.500 | 100.00% |
| 2 | entropy | 0.7187 | 76.19% | 67.44% | 143.3 | 5046.7 | 1.282 | 92.86% |
| 2 | harm | 0.7544 | 74.29% | 67.42% | 144.3 | 5054.7 | 1.029 | 68.28% |
| 3 | none | 0.7523 | 78.10% | 67.52% | 164.0 | 5065.7 | 0.000 | 0.00% |
| 3 | roles_first | 0.7172 | 80.00% | 67.48% | 160.0 | 5054.7 | 2.200 | 100.00% |
| 3 | history_first | 0.7273 | 75.24% | 67.41% | 141.7 | 5048.0 | 2.600 | 100.00% |
| 3 | random | 0.7202 | 78.10% | 67.44% | 153.3 | 5053.7 | 2.400 | 100.00% |
| 3 | entropy | 0.7180 | 75.24% | 67.43% | 144.0 | 5050.0 | 1.946 | 92.86% |
| 3 | harm | 0.7427 | 75.24% | 67.43% | 146.3 | 5054.0 | 1.438 | 68.28% |

### wrong_host_history

| Budget | Policy | Macro-F1 | Movement recall | Exfiltration recall | Benign false alerts | Weighted errors | Mean spend | Query rate |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | none | 0.7523 | 78.10% | 67.52% | 164.0 | 5065.7 | 0.000 | 0.00% |
| 1 | roles_first | 0.7136 | 85.71% | 67.52% | 179.7 | 5069.3 | 1.000 | 100.00% |
| 1 | history_first | 0.7136 | 85.71% | 67.52% | 179.7 | 5069.3 | 1.000 | 100.00% |
| 1 | random | 0.7136 | 85.71% | 67.52% | 179.7 | 5069.3 | 1.000 | 100.00% |
| 1 | entropy | 0.7139 | 81.90% | 67.52% | 174.0 | 5068.7 | 0.621 | 62.09% |
| 1 | harm | 0.7500 | 81.90% | 67.52% | 169.7 | 5064.0 | 0.410 | 41.04% |
| 2 | none | 0.7523 | 78.10% | 67.52% | 164.0 | 5065.7 | 0.000 | 0.00% |
| 2 | roles_first | 0.7136 | 85.71% | 67.52% | 179.7 | 5069.3 | 1.000 | 100.00% |
| 2 | history_first | 0.5449 | 23.81% | 66.89% | 39.7 | 13179.7 | 2.000 | 100.00% |
| 2 | random | 0.6577 | 58.10% | 67.22% | 110.3 | 9105.0 | 1.500 | 100.00% |
| 2 | entropy | 0.5687 | 40.00% | 67.20% | 66.0 | 12379.3 | 1.282 | 92.86% |
| 2 | harm | 0.6921 | 40.95% | 67.08% | 81.0 | 8115.3 | 1.030 | 68.28% |
| 3 | none | 0.7523 | 78.10% | 67.52% | 164.0 | 5065.7 | 0.000 | 0.00% |
| 3 | roles_first | 0.6793 | 43.81% | 66.96% | 74.0 | 7817.3 | 3.000 | 100.00% |
| 3 | history_first | 0.6793 | 43.81% | 66.96% | 74.0 | 7817.3 | 3.000 | 100.00% |
| 3 | random | 0.6793 | 43.81% | 66.96% | 74.0 | 7817.3 | 3.000 | 100.00% |
| 3 | entropy | 0.6873 | 40.00% | 67.22% | 73.0 | 7279.7 | 2.369 | 92.86% |
| 3 | harm | 0.6763 | 43.81% | 67.01% | 87.0 | 7791.3 | 1.716 | 68.28% |

## Unrestricted full-context reference

This reference always reveals both groups. It violates replay acquisition constraints when evidence is late, unavailable or unaffordable, so it is not eligible for same-budget superiority claims. Its cost is listed as3; elapsed time is0 only because this is an instantaneous-information reference, not a collection measurement.

| Condition | Macro-F1 | Movement recall | Exfiltration recall | Benign false alerts |
|---|---:|---:|---:|---:|
| clean | 0.7153 | 68.57% | 67.15% | 115.3 |
| delayed_unavailable | 0.7153 | 68.57% | 67.15% | 115.3 |
| wrong_host_history | 0.6793 | 43.81% | 66.96% | 74.0 |

## Prespecified contrasts: harm minus entropy

A negative weighted-error difference favors harm selection. A positive movement-recall difference favors harm selection. These contrasts retain all budgets and conditions; none is designated successful after observing the table.

| Condition | Budget | Weighted error difference | Macro-F1 difference | Movement recall difference | Exfiltration recall difference | Spend difference |
|---|---:|---:|---:|---:|---:|---:|
| clean | 1 | -4.7 | +0.0361 | +0.00% | +0.00% | -0.211 |
| clean | 2 | +18.7 | +0.0370 | -1.90% | -0.04% | -0.252 |
| clean | 3 | +23.3 | +0.0231 | +3.81% | -0.11% | -0.817 |
| delayed_unavailable | 1 | -3.3 | +0.0342 | +0.00% | +0.00% | -0.211 |
| delayed_unavailable | 2 | +8.0 | +0.0357 | -1.90% | -0.02% | -0.253 |
| delayed_unavailable | 3 | +4.0 | +0.0247 | +0.00% | +0.00% | -0.508 |
| wrong_host_history | 1 | -4.7 | +0.0361 | +0.00% | +0.00% | -0.211 |
| wrong_host_history | 2 | -4264.0 | +0.1234 | +0.95% | -0.12% | -0.252 |
| wrong_host_history | 3 | +511.7 | -0.0110 | +3.81% | -0.21% | -0.653 |

## Supplementary safety check: recognized as any attack

This descriptive check was added after inspecting the first seed, using the already-preserved confusion matrices. It does not replace the frozen exact-stage objectives. Calling an exfiltration flow movement is an exact-stage error but still an attack warning; calling it benign removes that warning. A higher macro-F1 can therefore coexist with lower attack recognition.

| Condition | Budget | Policy | Movement recognized as any attack | Exfiltration recognized as any attack |
|---|---:|---|---:|---:|
| clean | 1 | none | 78.10% | 67.52% |
| clean | 1 | entropy | 81.90% | 87.95% |
| clean | 1 | harm | 81.90% | 67.83% |
| clean | 2 | none | 78.10% | 67.52% |
| clean | 2 | entropy | 63.81% | 87.58% |
| clean | 2 | harm | 61.90% | 67.33% |
| clean | 3 | none | 78.10% | 67.52% |
| clean | 3 | entropy | 65.71% | 85.18% |
| clean | 3 | harm | 69.52% | 76.25% |
| delayed_unavailable | 1 | none | 78.10% | 67.52% |
| delayed_unavailable | 1 | entropy | 80.95% | 81.54% |
| delayed_unavailable | 1 | harm | 80.95% | 67.73% |
| delayed_unavailable | 2 | none | 78.10% | 67.52% |
| delayed_unavailable | 2 | entropy | 76.19% | 81.41% |
| delayed_unavailable | 2 | harm | 74.29% | 67.46% |
| delayed_unavailable | 3 | none | 78.10% | 67.52% |
| delayed_unavailable | 3 | entropy | 75.24% | 81.00% |
| delayed_unavailable | 3 | harm | 75.24% | 69.20% |
| wrong_host_history | 1 | none | 78.10% | 67.52% |
| wrong_host_history | 1 | entropy | 81.90% | 87.95% |
| wrong_host_history | 1 | harm | 81.90% | 67.83% |
| wrong_host_history | 2 | none | 78.10% | 67.52% |
| wrong_host_history | 2 | entropy | 40.00% | 87.46% |
| wrong_host_history | 2 | harm | 40.95% | 67.13% |
| wrong_host_history | 3 | none | 78.10% | 67.52% |
| wrong_host_history | 3 | entropy | 40.00% | 77.52% |
| wrong_host_history | 3 | harm | 43.81% | 77.37% |

## Limits and next decision

- This is a simple greedy expected-error-reduction probe, not a reproduction of SEFA, Learning-To-Measure, Sim-CTKG or a novelty claim.
- Acquisition policies inspect only already observed features/probabilities. Simulated hidden availability and arrival become known only after a charged query.
- Static roles and existing history summaries are hypothetical query groups. Actual collection/cache costs were not measured. Dynamic feature-value evolution is not tested.
- A wrong-host summary is deliberate correspondence corruption, not a new real workflow or independently sampled incident.
- Only35 evaluation movement flows exist, and their source annotations concern remote-system discovery on one host pair. The forward-fold selector targets contain only18 movement rows. There is no movement case in the unused calibration capture.
- Exact-stage loss charges the same error weight for assigning the wrong attack stage and assigning benign. The supplementary any-attack table exposes this limitation; a future asymmetric loss would require a separate frozen experiment.
- OOF training protects selector targets against in-fold fitting, but all source captures belong to an exposed campaign. A positive score cannot establish external generalization.
- Before a method-based praxis claim: qualify independent executions, implement stronger recent acquisition baselines, measure true channel availability/latency, and compare at operational false-alarm and review workloads.

## Reproduce and inspect

[Protocol](PROTOCOL.md), [implementation notes](METHOD_NOTES.md), [freeze](FREEZE.json), [run receipt](RUN_RECEIPT.json), [audit](AUDIT.json), [all results](RESULTS.json), [capture breakdown](CAPTURE_RESULTS.json). Private per-row probability/action/availability traces are at the path in the run receipt. They are omitted from Git to avoid publishing source event linkage.

```powershell
& 'C:/w/tabular_batch_env_20260921/Scripts/python.exe' -m pytest experiments/praxis_next/px081_evidence_acquisition/test_px081.py -q
& 'C:/w/tabular_batch_env_20260921/Scripts/python.exe' experiments/praxis_next/px081_evidence_acquisition/audit.py
```
