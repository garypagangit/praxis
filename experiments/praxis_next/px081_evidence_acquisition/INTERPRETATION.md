# PX-081 interpretation — the acquisition policy is executable, but not a robust improvement

## Answer in simple language

We built and ran a system that decides whether to inspect host roles or earlier traffic before assigning an attack stage. It can spend less on those hypothetical information requests. **The tested error-focused selector did not reliably improve dangerous-stage recognition.** Some apparently better scores hid a different problem: more true exfiltration flows received benign labels instead of an incorrect attack-stage label.

This conclusion does not depend on a self-imposed 90% success requirement. It follows from comparisons against the current-only model and the uncertainty-focused selector, using the same rows and permitted budgets.

## Completed work

- Frozen protocol and code at Git `2da1a1c512e022a849c20a01f2b9b01c9f6f314d`, before fits.
- Three seeds; 60 classifiers and 24 selector regressors; 171 overall result rows and 810 capture-level rows.
- 208,094 evaluation flows: 192,193 benign; 12,424 other attack-stage; 35 movement; 3,442 exfiltration.
- Forward out-of-fold selector training, with no test outcomes supplied to selectors. Only 18 movement rows were available in the selector training folds.
- Local CPU execution took 619.8 seconds. AWS authentication was unavailable to the coordinating agent; no cloud job was created for this experiment.
- Acquisition costs, late delivery and unavailability are **simulated**. No measured cloud or operational cost saving is claimed.
- Ten pre-fit tests passed. The [independent audit](AUDIT.json) passed all 981 metric tables, 162 sequential acquisition traces and 12 forward-fold checks; it hashed 175 private prediction/input files.

## Results at the largest permitted budget

Means across three fitting seeds; these seeds are not independent attack campaigns. Full tables for budgets 1, 2, 3 remain in [README.md](README.md) and [RESULTS.json](RESULTS.json).

| Condition | Policy | Macro-F1 | Exact movement recall | Benign false alerts | Weighted stage errors | Mean simulated spend |
|---|---|---:|---:|---:|---:|---:|
| Clean | Current only | .7523 |78.10%|164.0|5,065.7|0|
| Clean | Entropy selection | .7148 |65.71%|111.3|5,032.7|2.535|
| Clean | Error-focused selection | .7379 |69.52%|122.3|5,056.0|1.717|
| Delayed/unavailable | Current only | .7523 |78.10%|164.0|5,065.7|0|
| Delayed/unavailable | Entropy selection | .7180 |75.24%|144.0|5,050.0|1.946|
| Delayed/unavailable | Error-focused selection | .7427 |75.24%|146.3|5,054.0|1.438|
| Wrong-host history | Current only | .7523 |78.10%|164.0|5,065.7|0|
| Wrong-host history | Entropy selection | .6873 |40.00%|73.0|7,279.7|2.369|
| Wrong-host history | Error-focused selection | .6763 |43.81%|87.0|7,791.3|1.716|

The error-focused policy reduced simulated spending against entropy selection by 32.24% in clean replay and 26.12% under delayed/unavailable replay. It nevertheless had **more weighted stage errors** than entropy in those largest-budget comparisons. Its movement recall also remained below the current-only model. The deliberate wrong-host corruption increased its weighted errors 53.81% over current-only.

There are isolated favorable results. At budget 1, error-focused selection had slightly lower weighted errors than entropy and current-only. At budget 2 under wrong-host corruption, it avoided some of entropy's damage. These are all retained. Budget 1 cannot retrieve history at all, so its clean and wrong-history comparisons are identical by construction. No single favorable operating point establishes robustness.

## Why a higher F1 score is not enough

The following descriptive check was added after inspecting seed 8101; it derives directly from the frozen confusion matrices, without changing models or primary objectives.

At budget 3, true exfiltration recognized as **any attack** was:

| Condition | Current only | Entropy selection | Error-focused selection |
|---|---:|---:|---:|
| Clean |67.52%|85.18%|76.25%|
| Delayed/unavailable |67.52%|81.00%|69.20%|

Entropy often called exfiltration “movement,” which is a wrong stage but still an attack warning. The error-focused selector sometimes avoided this confusion by reverting to a benign prediction. That can improve macro-F1 while suppressing a useful warning. The frozen loss assigns the same true-class penalty to both mistakes. A future asymmetric cost matrix distinguishing a missed attack from the wrong attack stage would be a **new experiment**, not a repaired claim about this run.

The first seed alone appeared more favorable to error-focused selection. The complete three-seed result demonstrates why reporting that early result as a success would have been misleading.

## What this contributes to a praxis

This is a defensible development finding about the interaction between acquisition objectives and stage metrics. It is **not** a proven novel detector, proof that modern active-acquisition methods fail, or a final publishable method contribution. The implementation is a modest greedy probe, not a reproduction of SEFA, Learning-To-Measure or Sim-CTKG. Existing acquisition methods and cybersecurity logging systems remain necessary related work.

The next technical question is narrower: can an acquisition-and-validation policy preserve an attack warning when added evidence changes the estimated stage? That would combine evidence selection with a post-acquisition trust decision and explicitly distinguish benign false negatives from inter-stage confusion. Its value and novelty remain untested. Independent qualified executions and measured channel behavior are required before a strong application claim.

## Boundaries of the evidence

The source is one previously examined UNRAVELED campaign; author movement annotations in this sensor concern discovery on one host pair. Current-flow features are available after flow completion. All policies use existing summaries whose real collection cost is unknown. Wrong-host history is a deliberate correspondence perturbation, not an independent real incident. Thus these results do not establish successful APT lateral movement, theft, exfiltration forecasting, field latency savings or cross-campaign performance.
