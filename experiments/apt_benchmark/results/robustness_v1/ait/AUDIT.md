# Independent audit: AIT event robustness pilot

**PASS for reported metrics, source joins, coverage and frozen calibration.** This is an independent AI/code audit, not human label adjudication or a finding of novelty. All 68 held-out condition/model results retain the same **6,293 events: 44 source-labeled positives and 6,249 other-label negatives**.

## What was checked

- Rejoined all 22,924 original audit fragments to author annotations, rebuilt event identities/label unions, and matched every event and saved test-roster position.
- Recomputed confusion counts, precision, recall, F1, continuous-score ROC-AUC/average precision and observation coverage with independent sklearn/direct calculations, pooled and for each run, at both operating points. All reported values matched.
- Independently rebuilt target-observation masks for every condition/seed. Completely hidden events remain in the denominator and receive no alarm.
- Verified source/label member hashes, event data, manifest, original normalizer/adapter, all four model bytes, protocol and pre-fit receipt. Operative bytes matched source commit `174cbea6d15d09c098273d6792b47a4b309fce36` at audit.
- With explicit authorization, loaded only the hash-verified saved local models and inferred clean calibration scores. All four thresholds and calibration confusion matrices reproduced exactly using an independent sorted-negative rank: 2,819 negative calibration events, 28 allowed flags, zero-based index 2,790 and strict `score > threshold`. No refitting, test inference, tuning or threshold changes. Derivative scores remain private.

File times are consistent with pre-fit receipt, saved models, predictions, then final results. They are supporting local provenance, not independent timestamp attestation. The calibration feature matrices reuse the reviewed frozen replay code; metric/rank arithmetic does not reuse the evaluated metric or calibration functions.

## Results at a fixed 0.5 threshold

Random-loss entries are the mean of three fixed deletion masks. They are not three independent training runs or confidence intervals.

| Condition | Generic event F1 | Semantic event F1 | Entity-context F1 | Context + dropout F1 | Observed target coverage |
|---|---:|---:|---:|---:|---:|
| clean | 0.6324 | 0.6833 | 0.7321 | 0.7130 | 100.00% |
| random_25 | 0.5813 | 0.6109 | 0.6231 | 0.6043 | 74.89% |
| random_50 | 0.4740 | 0.4882 | 0.4818 | 0.4680 | 49.92% |
| random_75 | 0.3719 | 0.3549 | 0.3432 | 0.3364 | 25.08% |
| support_burst_60 | 0.6324 | 0.6833 | 0.6165 | 0.5985 | 100.00% |
| command_records_absent | 0.6324 | 0.6833 | 0.7321 | 0.7130 | 100.00% |

Compared with generic text (43 TP / 49 FP / 1 FN), semantic features reduce false alarms but lose two detections. Clean semantic features give **41 TP / 35 FP / 3 FN**; entity context gives **41 TP / 27 FP / 3 FN**. All eight fewer false positives occur in Wilson. Its F1 improves from 0.4932 to 0.5538; Harrison stays at 0.9787. Thus the pooled clean gain is a useful development observation, with no extra detected positives and no gain in the second run.

The 60-second support-loss stress test retains the current event but removes recent context separately for each query. Context then produces **48 FP**, versus semantic features' **35 FP**, with the same 41 TP. Its F1 falls to 0.6165. Random-loss context improves mean F1 only at 25% removal; it is slightly below semantic-only at 50% and 75%. Dropout training has lower fixed-threshold F1 than ordinary context on clean data and at all three random-loss rates. It does not establish an additional robustness benefit.

## Separately frozen calibration thresholds

| Clean model | Recall | Other-label flag rate | F1 |
|---|---:|---:|---:|
| generic_event | 100.00% | 1.552% | 0.4757 |
| semantic_event | 93.18% | 0.944% | 0.5694 |
| entity_context | 93.18% | 0.560% | 0.6833 |
| context_dropout | 93.18% | 0.592% | 0.6721 |

These are different operating points from the 0.5 table. Under support loss, calibrated context F1 is 0.5734 versus semantic-only 0.5694 (58 versus 59 FP, equal 41 TP), rather than a large improvement or a worse score. The clean context model's pooled other-label flag rate is 0.560%, but Wilson alone is 1.017%; the calibration budget is an empirical choice, not a guarantee under run shift.

## What E3 and missing records establish

Only **five PROCTITLE fragments in five test events**, including one positive event, are delayed or removed. AIT has no EXECVE fragments here; its seven test USER_CMD fragments are not targeted by this condition. Removing PROCTITLE changes five scores per model but changes no decisions at either operating point. This is limited perturbation coverage, not evidence of broad missing-command resilience.

At a waiting deadline equal to the injected delay, every model's saved score/label/observation arrays exactly match clean arrays. That recovery is guaranteed by the replay construction; it is a buffering control with a waiting cost, not a learned improvement.

**6,288 of 6,293 test events are singletons** (22,873 of 22,890 across all runs). Random fragment removal therefore mostly hides whole events. The offline evaluator knows their roster and counts them as misses; an operational system would still need a defensible way to recognize or infer missing events. Source epochs stand in for availability, so these are synthetic delays rather than measured collection latency.

## Conclusion

The completed experiment supports a narrow finding: better event semantics and short prior context can reduce false alarms on these exposed escalation records, while context is vulnerable when its supporting records disappear. The tested dropout control supplies no consistent additional gain. Nothing here certifies operational false alarms, recovery from invisible attacks, general APT detection, independent campaign transfer or a novel praxis method. The 44 positives are correlated author-labeled events, not 44 independent attacks.

Full independently recomputed aggregates, per-run/seed details, hashes, scope and calibration verification are in [AUDIT.json](AUDIT.json).
