# Results: which remaining fixes helped?

**None established a generally superior detector.** Explicit warning retention helped the failure mechanism; constraints and calibration alone did not remove it. All comparisons use previously exposed UNRAVELED data, three seeds and clean budget-2 evidence. Warnings mean any non-benign prediction, not necessarily the correct attack stage. These are flow counts, not independent attacks or campaigns.

| Experiment | Completed work | Practical finding |
|---|---|---|
| PX-088 | Independent selector/risk-calibration split; capacity ledger; 126 arms | Review queues can exceed capacity. Strong recall among automatically handled rows can hide attacks waiting for review. |
| PX-089 | Three recalibration modes, three simulated delays, five later captures; 1,620 arms | Updating thresholds recovers warnings but can produce very large false-alert loads. Delayed labels can leave no calibration support. |
| PX-090 | Six matched constrained/unconstrained fits; 24 arms | Monotonicity did not prevent demotion. Explicit union veto retained constituent warnings, with additional false alerts. |
| PX-091 | Renewed source qualification | No newly qualified exact four-class/two-evidence independent replication. |

## PX-088: deferral is a queue, not a detection

Illustrative fixed slice: seed 8101, roles-first policy, supported-stage alpha .05. All registered slices are in [ALL_ARMS.csv](results/ALL_ARMS.csv).

| Review budget per 100,000 flows | Review requests | Served within endpoint capacity | Unresolved | Automatic exfiltration rows | Automatic exfiltration misses |
|---|---:|---:|---:|---:|---:|
| 100 | 1,631 | 206 | 1,425 | 2,353 | 39 |
| 1,000 | 4,848 | 2,078 | 2,770 | 2,326 | 18 |
| 5,000 | 8,388 | 8,388 | 0 | 2,317 | 12 |

There are 3,442 exfiltration-labeled test flows. At the smallest budget, 1,089 went to review; 1,057 remained unresolved. The 98.34% warning recall among automatic exfiltration decisions therefore does not mean 98.34% of all exfiltration flows were detected. Served reviews do not imply correct human decisions. The ledger gives per-capture endpoint capacity totals, not measured analyst response times. Movement was absent from the original calibration data.

## PX-089: recalibration trades misses for workload

Fixed slice: harm policy, supported-stage alpha .05. Recall is pooled over the five captures and three seeds; false alerts are whole-test totals averaged over seeds. The test contains 192,193 benign flows. Delays are simulated assumptions.

| Calibration mode | Label delay (hours) | Exfiltration warning recall | Mean benign false alerts |
|---|---:|---:|---:|
| Frozen | 0 | 67.33% | 107.33 |
| Frozen | 24 | 100.00% | 192,193.00 |
| Frozen | 72 | 100.00% | 192,193.00 |
| Cumulative | 0 | 96.40% | 90,785.67 |
| Cumulative | 24 | 82.63% | 101,374.67 |
| Cumulative | 72 | 93.41% | 156,948.67 |
| Most recent eligible capture | 0 | 99.86% | 129,819.00 |
| Most recent eligible capture | 24 | 93.15% | 108,050.00 |
| Most recent eligible capture | 72 | 93.41% | 156,948.67 |

With delayed frozen calibration, no attack labels qualify before the first test boundary; the conservative fallback warns on everything. Its perfect warning recall is not a useful detector improvement. Later calibration can add movement support, but support depends on capture and delay. Labels were restricted to completed earlier flows available before each evaluation capture; the underlying models were never refitted. These results do not establish a deployment guarantee or an optimal update interval.

## PX-090: increasing scores monotonically is insufficient

Means over three seeds, fixed threshold .5. Demotions are attack flows warned on by either within-seed expert but called benign by the indicated arm, summed over seeds (repeated evaluations of the same flows).

| Arm | Exfiltration warning recall | Movement warning recall | Mean false alerts | Summed attack-warning demotions |
|---|---:|---:|---:|---:|
| Current expert | 67.52% | 78.10% | 164.00 | 2,165 |
| Roles expert | 88.34% | 85.71% | 179.67 | 6 |
| Within-seed expert warning union | 88.35% | 85.71% | 180.33 | 0 |
| Unconstrained score model | 67.94% | 86.67% | 204.67 | 2,114 |
| Monotone score model | 67.94% | 86.67% | 204.67 | 2,114 |
| Monotone model plus union veto | 88.41% | 86.67% | 209.67 | 0 |

The secondary alpha .05 calibration left both fitted models' hard outcomes unchanged. All constrained models passed the numerical monotonicity grid check. The constraint controls how the combined score responds to each input score; it does not require a warning whenever an expert warns. The explicit veto supplies that requirement.

The simple within-seed union is the lower-false-alert comparator here. Adding the constrained model improves movement recall slightly, with more false alerts. Only 35 movement flows are present, so small percentage differences deserve caution. Both experts must be evaluated; the combining model adds computation. These outcomes must not be confused with PX-086's **cross-seed roles union**, which reached 98.78% exfiltration recall in a different comparison.

## Meaning for the primary praxis

The defensible finding remains: a better aggregate stage score can hide more attacks classified as benign. Separately measuring warning loss exposes that behavior. A deterministic retention rule directly prevents constituent-warning demotion, but cannot recover attacks missed by all constituent models and can preserve their false alerts.

The next evidence requirement is a frozen comparison on qualified independent executions, with a preselected false-alert/review budget. Repeated tuning on this campaign cannot supply that evidence. No significance claim, novel algorithm claim or independent generalization claim is made. [Qualification and prior work](QUALIFICATION.md) explain the remaining limits.
