# SOC visibility and environment checks

## Summary

The existing Study 3 logs contain a label-associated signal even when the
model cannot read terminal commands or use the two modeled process-creation
event types. The flow-only model scored slightly higher than the original
combined model on the same attack windows, but the difference is uncertain.
The models trained on outside-login flow windows did not perform well at
predicting session labels. That does **not** establish that the attack-window
signal is independent of the lab environment.

These are exploratory reanalyses, not new attack trials. All windows are 30
seconds; train/test splits hold out entire sessions. All feature sets exclude
terminal commands and command-line content. The recorded login boundaries
remain known for selecting attack and surrounding windows.

## Experiment 1: reduce behavioral visibility

These results use the same 1,225 attack windows (930 human-labeled and 295
AI-labeled) from five human and four AI sessions. XGBoost uses the same fixed
configuration and training-fold processing as the original combined model.
The port-filtered flow-only model is a later, post hoc sensitivity check.

| Model | Macro-F1 | AI recall | Human attack-window false-positive rate | Session accuracy |
|---|---:|---:|---:|---:|
| Original combined model | 0.676 | 47.8% | 13.7% | 8/9 |
| Without two process-creation event types | 0.672 | 47.5% | 14.0% | 8/9 |
| VPC flow features only | 0.691 | 50.8% | 13.5% | 8/9 |
| VPC flow only, after UDP port filtering | 0.568 | 43.1% | 27.5% | 6/9 |
| Host-only, from the prior audit | 0.514 | 28.5% | 25.5% | 6/9 |

The process-creation test removes Windows Security Event ID 4688 and Sysmon
Event ID 1 from event counts **and** five-second activity bins, then
recalculates timing and co-activity features. It removed 738 Security and 739
Sysmon event records. Original counts were verified for every matched window.
Other process-related, task, service and correlated signals remain; this is not
a test with all behavioral information removed.

The flow-only model uses record, packet and byte counts, protocol and
accept/reject counts, plus flow-bin timing features. It does not use Windows
or IIS features. Its 0.015 higher macro-F1 than the combined model does not
establish that flow-only is better: the 95% paired session-bootstrap interval
for the difference was -0.016 to +0.045. The process-event-removal difference
was -0.004, with an interval of -0.009 to +0.002. Intervals resample fixed
held-out predictions, without refitting or capturing selection uncertainty.

For the flow-only sensitivity check, we removed UDP records with either
source or destination port 41641 or 3478, recomputed flow counts and
five-second bins, and retrained the same flow-only model. Before filtering,
all flow features and bins were independently reproduced against the earlier
extraction. The filter removed 12,701 of 344,862 human and 8,302 of 93,927
AI flow records in the matched attack windows.

The flow-only macro-F1 fell by 0.123, from 0.691 to 0.568; the 95% paired
fixed-prediction session-bootstrap interval for that change was -0.358 to
+0.098. The interval includes zero and does not capture refitting or
selection uncertainty. The filtered model was refit for all 126
class-preserving session-label assignments; its unadjusted association
p-value was 0.0952. This tests label association, not the change from the
unfiltered model, and does not correct for previous exploration.

The result reinforces the concern that some apparent performance may rely on
environment-related traffic. The filter was selected after inspecting the
data, can also remove unrelated UDP traffic, and does not identify a process
or eliminate other possible environment signals. It cannot prove the source
of the signal or establish that the remaining performance generalizes.

Window-level performance varied substantially between sessions. For the
unfiltered flow-only model, the fraction of windows called AI across the four AI-labeled
sessions ranged from 8.6% to 97.8%; across five human-labeled attack
sessions it ranged from 2.0% to 19.8%. Session accuracy is based on the mean
held-out probability for each session, not an independent sample of nine
additional trials.

## Experiment 2: outside-login environment checks

We extracted available flow-covered 30-second windows up to five minutes
before the first included login and after the last included login. These
windows inherit the **session label**, not a verified label for whoever or
whatever was active in that window. They are not confirmed benign, and
post-login activity may include continuing attacks or their effects.

First, each flow-only XGBoost model was trained and evaluated within the
indicated period, holding out each session:

| Outside-login sample | Windows, human / AI | Sessions, human / AI | Macro-F1 | AI-labeled positive rate | Human-labeled positive rate | Session accuracy |
|---|---:|---:|---:|---:|---:|---:|
| Before | 36 / 35 | 4 / 4 | 0.323 | 28.6% | 63.9% | 1/8 |
| After | 35 / 23 | 5 / 4 | 0.496 | 52.2% | 51.4% | 3/9 |
| Before and after | 71 / 58 | 5 / 4 | 0.403 | 32.8% | 52.1% | 2/9 |

Under this model and threshold, outside-login prediction did not reproduce
the attack-window performance. This is not a matched comparison: there are
far fewer outside windows, one human session lacks covered before windows,
and training and activities differ.

As a second, descriptive check, the flow-only models trained on **other
sessions' attack windows** were applied to the held-out session's
outside-login windows. Held-out attack predictions were verified against the
first experiment.

| Outside-login sample | AI-labeled windows called AI | Human-labeled windows called AI |
|---|---:|---:|
| Before | 5.7% (2/35) | 16.7% (6/36) |
| After | 26.1% (6/23) | 11.4% (4/35) |
| Before and after | 13.8% (8/58) | 14.1% (10/71) |

The combined outside-period rates are similar, but these short periods do
not rule out setup signals during attacks, other kinds of environment
confounding, or a more capable shortcut model. Flow records are assigned by
their end time, and timestamp extent and `SKIPDATA` are imperfect coverage
measures. Different logging, topology, tools, activities or session lengths
may still be associated with the class labels.

## Statistical and operational limits

The first five new models were each refit for every class-preserving
session-label assignment: 126 for nine sessions and 70 for the eight-session
before-only sample. The process-event-removal and attack-flow-only models each
had raw p = 0.0079 and Holm-adjusted p = 0.0397 **within this five-test
exploratory family only**. The before, after and pooled outside-login models
had raw p-values 0.9429, 0.2698 and 0.6190, respectively. These p-values
assess association with session labels, not differences between models.
They do not correct for prior experiments, assume exchangeable sessions, and
are not independent confirmation. The attack-trained transfer check is
descriptive; no transfer permutation test was performed.

The previous [flow audit](SOC_TELEMETRY_AUDIT.md) also found that removing
UDP records involving ports 41641 or 3478 reduced the combined model's
macro-F1 to 0.540; the interval for that change included zero and the filter
was selected after inspecting the data. The ports do not identify a process.
Taken together, the results motivate further scrutiny, not a conclusion that
the model has isolated intrinsic AI behavior.

Human false-positive rates in attack windows are not benign-traffic alert
rates. No independent environment, unknown attack-period detection, real-time
latency or deployment performance was evaluated. With only these existing
logs, operator and environment effects may remain inseparable. The
[runbook](../../scripts/DEFENDER_SOC_AUDIT.md) describes reproduction.
