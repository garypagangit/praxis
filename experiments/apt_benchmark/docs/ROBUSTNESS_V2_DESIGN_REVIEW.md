# Design review: learning with absent audit record types

Reviewed September 20, 2026, before fitting or inspecting any v2 outcomes. This independent agent review covers the proposed design, the original replay implementation, the v1 protocols/results, and current primary literature. It is not a human label audit or a certification of unfinished v2 code.

## Decision

**Proceed as a bounded development experiment.** The v1 failure under loss of EXECVE/PROCTITLE records provides a concrete reason to compare training on entire missing record types with training on randomly missing records. The comparison can answer whether this mismatch explains a recoverable part of the failure. It cannot, by itself, establish novelty, robust deployed APT detection, or performance on unseen campaigns.

AIT and CasinoLimit test outcomes have already informed this design. Their existing splits remain useful for controlled development but are no longer external confirmation. Preserve the previous results and protocol; publish this experiment as a separately frozen follow-up.

## Proposed arms and what they isolate

All arms keep fixed feature hashing, logistic regression settings, the 120-second strictly prior history, and its 32-event limit.

| Arm | Training views | Meaning of the comparison |
|---|---|---|
| Semantic event | Clean, current event only | Current-evidence control. |
| Entity context | Clean, current event and prior linked events | Context control. |
| Random dropout | Clean, 25% random loss, 50% random loss | Reproduce the v1 robust-training control. |
| Record-type dropout | Clean, no EXECVE, no PROCTITLE, neither | Practice losing named record types. |
| Mixed dropout | All six distinct condition definitions above | Cover both random and structured loss with one model. |
| Observed router | Four available-command-pattern experts trained from mixed views, with a mixed-model fallback | Test whether different classifiers help for different observed evidence patterns. |

Each original event has total augmentation weight one. Distinct condition definitions can produce identical feature vectors for some events; this is expected and must not be described as six independent observations. A router has more fitted parameters and potentially different class composition within routes, so a gain would establish the usefulness of this policy as a whole, not isolate routing from extra capacity.

## Items to freeze before fitting

1. **Support for router experts counts distinct source target events.** Count unique fit event IDs among observed rows assigned to a route. Six views of one positive are still one positive. The minimum of five positive and 25 negative targets is a numerical feasibility rule, not independent attack support. Also record supporting execution counts. Route membership and fallback must depend only on fit data, never calibration/test outcomes. Root accepted this before freezing: completely unobserved rows do not enter expert fits, retained mixed-view rows keep weight 1/6, and the base mixed model retains the original empty-view training convention.
2. **Routing uses visible current-event records.** Read EXECVE/PROCTITLE presence from the current observed metadata. Neither the original event's full channel inventory nor a corruption-condition name is a permitted router input. Presence in historical context is a different policy and should not silently replace this definition.
3. **One clean-calibrated threshold governs the complete router.** First produce its routed scores on clean calibration data, then compute one threshold exactly as for the other arms. Keep that threshold fixed for every loss and delay. Report route/fallback usage and route support in clean calibration and each stress condition. Some routes can be common under corruption and absent from clean calibration; the 1% clean budget gives no guarantee for those routes.
4. **The primary success gate protects recall explicitly.** The accepted pre-fit comparison uses mixed minus random dropout under combined command-record loss: calibrated F1 at least +0.05, command-loss recall no worse than -0.02, clean F1 no worse than -0.02, mean random-50% F1 no worse than -0.02, and other-label flag rate no worse than +0.005. Root accepted the additional recall floor before freezing. These are descriptive development gates, not population noninferiority claims; report any absolute recall loss prominently.
5. **Keep all targets and all condition/seed outcomes.** Do not define overall success by whichever target or secondary arm happens to win. Declare per-target outcomes and then the count passing every primary gate. Three removal seeds describe perturbation variability, not three independent datasets.
6. **Freeze held-out stress conditions.** EXECVE-only, PROCTITLE-only, and combined command loss are represented in structured training. SYSCALL-only and PATH-only loss are unseen perturbation types, but the underlying executions remain exposed development data. No tuning on those scores or claims of external confirmation.

## Counterexamples and qualification checks

| Failure example | Required check and expected outcome |
|---|---|
| A target contains EXECVE before deletion but only SYSCALL afterward. | Its route must indicate no observed EXECVE, regardless of the condition label and original event metadata. |
| An EXECVE-free event happens naturally; another loses EXECVE and has exactly the same remaining observations. | Both must get the same route and prediction. The system cannot claim to distinguish a true outage from source inactivity without additional evidence. |
| One positive appears in six augmented rows in the same route. | Expert support remains one positive and triggers the specified fallback. |
| A route has only one fit class, or no qualifying distinct positive events. | No expert fit; use the frozen mixed-model fallback. Changing test labels must not alter that choice. |
| Current fragments are all missing, but a full-event process key could locate useful history. | Keep the target in the denominator, give no alarm, and do not use hidden linkage to recover context. |
| The only process-link key is in a deleted fragment. | Prior-event lookup must not use that key. Removing SYSCALL/PATH can remove linkage as well as text; report that combined effect. |
| A record type is removed, but its command/path meaning is duplicated in remaining SYSCALL, PATH, USER_CMD, or other text. | This is a record-type-loss test, not proof that all command information was lost or reconstructed. Report the exact removed types and remaining coverage. |
| An earlier event lacks PROCTITLE while the target has it. | Current-event route remains unchanged by that history fact; historical text can still affect the classifier normally. |
| Future records or future labels are appended. | Earlier causal feature vectors and routes remain unchanged. |
| Augmentation is duplicated without dividing sample weights. | A weight-total test must fail; otherwise effective regularization changes and the comparison is confounded. |
| Router scores improve after recalibrating on degraded test negatives. | Reject that run: thresholds may only use the frozen clean calibration split. |
| Most negative-only executions improve while a rare positive-bearing execution loses all detections. | Publish pooled confusion counts and every execution's counts; do not infer widespread recognition from aggregate F1. |

The existing replay already checks current-fragment visibility, fragment-local entity linkage, strict prior timestamps, and no-observation targets. New tests should specifically verify routing, distinct-event support, fallback behavior, weight totals, and calibration isolation. The reviewer did not run v2 models or inspect their outputs.

## Dataset-specific interpretation

**CasinoLimit:** its annotation-onset targets distinguish one author-annotated technique from other annotated techniques. A gain is improved technique assignment on these targets, not benign-versus-malicious classification. The 18 test executions share one challenge; target support is small and correlated. An improvement at a calibrated operating point should be accompanied by raw true/false flag changes, recall, AP/ROC-AUC, and per-execution results.

**AIT:** nearly all targets are single-record events, and command-type deletion affects very few test events. Report how many targets, positives, and routes actually change. Identical scores under absent or rare record types cannot establish broad robustness.

**CAM-LDS:** a later confirmation stage needs qualified raw joins, causal labels, family-held-out splits, and target support before model scoring. Freeze the selected policy before examining its confirmation outcomes. If family counts or labels cannot support that design, say so rather than weakening the split until favorable results appear. This review does not qualify CAM-LDS data acquisition or its adapter.

## Nearest literature, checked against primary sources

| Source | Relevant overlap | Consequence |
|---|---|---|
| [Reza, Prater-Bennette, and Asif, IEEE TPAMI, 2025](https://doi.org/10.1109/TPAMI.2024.3476487); [author manuscript](https://arxiv.org/abs/2310.03986) | Missing-modality training, dedicated models for available input combinations, and parameter-efficient adaptation are explicit existing methods. | Type dropout and available-evidence specialists are controls. Their use alone does not establish a new algorithm. |
| [Almakhamreh and Bozkir, CrossPhire, Applied Sciences 16(2), 751, 2026](https://doi.org/10.3390/app16020751) | Publisher section 6.6 describes structured modality dropout for phishing; the paper also discusses expert-based multimodal fusion. | Even the general combination of cybersecurity, missing inputs, dropout, and experts already has prior art. Linux audit record types and attack-step targets differ, but that application difference is not automatic novelty. |
| [Lo et al., LOTL-hunter, Future Generation Computer Systems 180, 108382, 2026](https://doi.org/10.1016/j.future.2026.108382); [authors' code/data](https://github.com/carolsworld/LOTL-Hunter) | Multi-stage CPS/ICS threat detection uses two-level fusion of host/network/process evidence. The paper describes confidence-aware logic for gaps caused by logging failures or limited visibility. | Multi-source fusion to tolerate visibility gaps in attack detection is existing work. Its physical-process and temporal-aggregation setting differs from current audit-event replay. |
| [Phan and Bauschert, StageFinder, May 2026 author version](https://arxiv.org/abs/2603.07560v2) | Graph encoders and temporal history estimate attack stages; authors report GLOBECOM 2026 acceptance. | History-based stage recognition is established. A separate proceedings record was not verified here. |
| [Bilot et al., USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/bilot) | A unified evaluation highlights weaknesses of complex provenance detectors and the strength of a simpler baseline. | Keep the fixed simple model, matched operating points, and full failure reporting. |

The CrossPhire publisher page was available as indexed primary full text; direct opening returned HTTP 429 during this check. The LOTL-hunter publisher text and author repository were available, while the institutional PDF exceeded the browser extraction size limit. These sources establish methodological overlap, not a reproduction of their reported performance.

## What a useful outcome would mean

A positive mixed-training result would show that the v1 failure was partly a mismatch between simulated training losses and test losses. A router improvement would motivate studying conditional decision policies with adequate route support and calibration. A null result would leave open whether the remaining evidence is insufficient or the fixed representation/classifier cannot use it.

None of those outcomes alone supports a novel praxis claim. A defensible next contribution needs a precise additional mechanism, meaningful nearest-method comparisons, and a pre-frozen result on qualified new scenarios. This follow-up is a practical way to decide whether that further investment has supporting evidence.

## Additional CAM-LDS source review before its model fitting

Reviewed `camlds/events.py`, `camlds/acquire.py`, the source README, and the pinned author extractor before CAM model outcomes. The nine CAM qualification tests passed. No implementation-level future-feature or hidden-linkage leak was found in this bounded review. The fixed UTC-bin roster precedes label lookup; the earliest-window-minus-120-second envelope preserves the preceding context of every supervised query; host/run identity scopes joins without entering text features; attacker chronology is used only for source-label verification.

**A material supervision correction was identified and accepted before CAM fitting.** In the author's [`extract_attack_logs.py` at commit 44028d8](https://github.com/ait-aecid/attack-manifestations-interpretation/blob/44028d8bd40a4a1d8bbbc6ee33261d47cb433827/extract_attack_logs.py), line 583 constructs windows from command start minus two seconds and completion plus four seconds. Lines 455-457 extend the previous window for sleeps; lines 578-582 apply selected manual offsets. These are **author-designated manifestation windows**, not exact intervals when an attack command is active. The correct task name is manifestation-window membership. Positive queries can include pre-command, idle, unrelated-host, and delayed activity; this cannot establish early warning or malicious-event recognition.

The author's membership test is half-open at line 268, matching our `start <= timestamp < end`. Their extraction rejects overlapping non-collectd windows beginning at line 269; our overlap-union rule is therefore an explicit local convention, not a claim of identical author extraction. Source qualification should report actual overlapping windows and affected eligible queries. The reviewed author extractor SHA256 is `1b3751655af07e37887210568f8c29dda18b216ee3a33993e02ea3635dc71deb`.

The implementation checks source interval/technique joins, repeated step identifiers, raw member hashes, and label anchors in attacker chronology. Those checks validate artifact consistency; they do not adjudicate each queried host event's causal role. T1105's family-separated result will supply an external dataset check of this weaker window-membership task, with one calibration and one test family. It must not be described as directly confirming all Casino technique-onset results.
