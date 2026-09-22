# What the exfiltration and stage-specialist pilot actually showed

**September 22, 2026.** All three seeds completed: 216 base fits including cross-fitting, 54 retained final base models, and 15 learned fusion models. CPU only. This note interprets saved results; it introduces no new fits, thresholds, success criteria, or preferred-model selection rule.

**Evidence:** [EVIDENCE.json](../results/exfil_stage_v1/EVIDENCE.json), [complete report](../results/exfil_stage_v1/REPORT.md), and [computational audit](../results/exfil_stage_v1/AUDIT.json). At review, the audit reports `PASS` and the run `COMPLETE`. That audit checks saved-output integrity and arithmetic; it does not independently refit models, adjudicate labels, or establish reliability on new attacks.

## The answer in simple language

**There is a small positive stage-classification result, but the proposed exfiltration specialist did not consistently improve exfiltration ranking.** Simply averaging the general models with stage specialists improved the overall six-stage score and reduced normal false alarms. More elaborate learned fusion made the six-stage result worse. The added features had mixed effects.

The most useful diagnosis is that **the detector often mistakes pivoting for exfiltration**. At the calibration-selected exfiltration threshold, the general-model average made 57.67 false exfiltration alerts per fit: 51.00 were pivoting and none were normal. Better separation of two malicious activities is a different problem from distinguishing an attack from ordinary traffic.

These are development findings on previously exposed data, not a proven novel solution. All methods use fixed configurations; the study does not establish superiority over thoroughly tuned alternatives. [The literature note](LITERATURE.md) documents direct precedent for exfiltration features, expert models, and fusion.

## How to read the numbers

The same 30,787 evaluation rows are reused in all three fitting seeds: 106 exfiltration, 15 initial compromise, 144 lateral movement, 29,929 normal, 425 pivoting, and 168 reconnaissance. Means below average the three per-seed metrics; fractional counts are average counts over fits, not fractional events. A mean F1 or precision is not recomputed from the averaged confusion matrix. The three fits are not independent incidents, and there is no population confidence interval or universal pass/fail gate.

There are two different decisions:

- **Experiment 1:** rank exfiltration versus everything else. Average precision (AP) is primary. F1/precision/recall use a threshold chosen on calibration data and then locked for evaluation.
- **Experiment 2:** choose the largest of six stage scores. Macro-F1 is primary. Calling exfiltration “pivoting” is wrong-stage recognition even though both labels are malicious.

The fixed combined scores also differ across experiments. Experiment 1 averages general exfiltration probabilities and binary specialist scores. Experiment 2 first normalizes each specialist family's six-score vector and averages those vectors with the general outputs. Thus the combined model's exfiltration AP is **0.5687 in Experiment 1 and 0.5829 in Experiment 2**. Neither value can silently replace the other endpoint.

## 1. What improved in the six-stage experiment

The most direct comparison is fixed general-plus-specialist averaging against averaging the two engineered general models. Both use the same fitting rows and engineered inputs.

| Outcome | General-model average | General + specialist average | Change |
|---|---:|---:|---:|
| Six-class macro-F1 | 0.6749 | 0.6841 | +0.0092 |
| Normal any-attack false-positive rate | 0.2929% | 0.2372% | −0.0557 percentage points |
| Normal false attack labels /29,929 | 87.67 | 71.00 | −16.67; 19.01% fewer |
| Overall any-attack recall /858 attack rows | 95.42% | 95.45% | +0.04 percentage points |
| Exact exfiltration F1 | 0.6125 | 0.6197 | +0.0072 |
| Exact exfiltration recall /106 | 80.19% | 80.82% | +0.63 percentage points |

Macro-F1 increased in each fit, by **0.000238, 0.014707, and 0.012666**, respectively. Normal false attack labels fell from **56 to 50**, **60 to 43**, and **147 to 120**. The smallest macro-F1 gain is nearly zero; three positive differences on shared cases do not establish dependable improvement across campaigns.

### Every stage, including the costs

| True stage | General precision | Combined precision | General exact recall | Combined exact recall | General F1 | Combined F1 |
|---|---:|---:|---:|---:|---:|---:|
| Exfiltration | 49.61% | 50.31% | 80.19% | 80.82% | 0.6125 | 0.6197 |
| Initial compromise | 21.88% | 22.28% | 95.56% | 95.56% | 0.3474 | 0.3521 |
| Lateral movement | 58.24% | 62.13% | 64.35% | 64.58% | 0.6111 | 0.6327 |
| Normal | 99.87% | 99.87% | 99.71% | 99.76% | 0.9979 | 0.9982 |
| Pivoting | 88.35% | 90.32% | 61.49% | 62.43% | 0.7250 | 0.7381 |
| Reconnaissance | 69.98% | 71.10% | 82.74% | 83.13% | 0.7554 | 0.7637 |

All six mean stage F1s improve in this comparison, but that does **not** mean every safety-relevant quantity improves:

- **Lateral any-attack recall falls from 81.713% to 81.481%.** Mean lateral rows mislabeled normal rise from 26.33 to 26.67 out of 144. Seed 20260924 misses one additional lateral row; the other two seeds have unchanged lateral any-attack recall. Exact lateral recognition improves slightly at the same time. These are different endpoints.
- Reconnaissance AP falls from **0.8235 to 0.8143**, despite improved argmax F1. Improvement at one decision rule does not imply uniformly better ranking.
- Exfiltration precision remains only **50.31%** at the six-class decision. About half the flows called exfiltration still belong to another class. Initial-compromise precision remains **22.28%**, with only 15 true evaluation examples.
- Any-attack recognition of true exfiltration is **100% for both methods**. The modest gain concerns correct stage names, not previously undetected exfiltration flows becoming malicious alerts.

### Which flows were incorrectly called exfiltration?

These are mean entries in the **exfiltration prediction column** of the six-class confusion matrix. They are separate from Experiment 1's thresholded alerts.

| True class | General-model average | General + specialist average |
|---|---:|---:|
| Exfiltration: correctly labeled | 85.00 | 85.67 |
| Initial compromise: wrong exfiltration label | 0.00 | 0.00 |
| Lateral movement: wrong exfiltration label | 2.33 | 2.67 |
| Normal: wrong exfiltration label | 2.00 | 1.67 |
| Pivoting: wrong exfiltration label | 73.33 | 71.67 |
| Reconnaissance: wrong exfiltration label | 9.00 | 9.00 |
| **All wrong exfiltration labels** | **86.67** | **85.00** |

Pivoting accounts for **84.31%** of the combined method's wrong exfiltration labels. This is a descriptive error concentration, not proof that a particular new feature will resolve it.

## 2. What did not improve as hoped

### Exfiltration specialization did not deliver a consistent primary-endpoint gain

| Experiment 1 comparison | Reference AP | Candidate AP | Difference |
|---|---:|---:|---:|
| Engineered versus raw general XGBoost | 0.5705 | 0.5740 | +0.0036 |
| Engineered versus raw general LightGBM | 0.5686 | 0.5601 | −0.0085 |
| Engineered XGBoost specialist versus same-feature general | 0.5740 | 0.5565 | −0.0176 |
| Engineered LightGBM specialist versus same-feature general | 0.5601 | 0.5608 | +0.0007 |
| Fixed combined versus general-model average | 0.5734 | 0.5687 | −0.0047 |
| Learned combined versus general-only learned fusion | 0.5778 | 0.5742 | −0.0035 |

The additions re-express existing measurements; they provide no new host or temporal observations. Their mixed effects do not establish that the missing information has been supplied. The engineered general models also have lower six-class macro-F1 than their raw counterparts: **0.6720→0.6620** for XGBoost and **0.6740→0.6675** for LightGBM.

At the calibration-selected F1 threshold, fixed combination changes mean exfiltration F1 from **0.6490 to 0.6419**. It gains only **0.33 true exfiltration alerts** per fit, from 78.67 to 79.00 out of 106, while adding **4.00 wrong exfiltration alerts**, from 57.67 to 61.67.

| Experiment 1 arm | Wrong initial | Wrong lateral | Wrong normal | Wrong pivoting | Wrong recon | Total wrong exfil alerts |
|---|---:|---:|---:|---:|---:|---:|
| General-model average | 0.00 | 1.00 | 0.00 | 51.00 | 5.67 | 57.67 |
| Specialist average | 0.00 | 0.00 | 0.33 | 41.33 | 2.33 | 44.00 |
| Fixed general + specialist average | 0.00 | 1.00 | 0.67 | 53.33 | 6.67 | 61.67 |
| General-only learned fusion | 0.00 | 1.00 | 0.00 | 52.00 | 6.00 | 59.00 |
| General + specialist learned fusion | 0.00 | 0.67 | 0.33 | 48.67 | 3.67 | 53.33 |

The specialist average has fewer wrong alerts, but also finds fewer true exfiltration flows: **68.33/106 versus 78.67/106** for the general average. Lower false alerts alone are not an exfiltration improvement. All 13 exfiltration arms and their complete operating points remain in the evidence; this table highlights the fusion comparisons rather than selecting a winner.

### Learned stage fusion performed worse

General-only, specialist-only, and combined learned stage fusion reach macro-F1 **0.6026, 0.6272, and 0.5706**, respectively, versus **0.6749** for the general-model average. Combined learned fusion raises normal any-attack FPR to **1.0581%**, versus **0.2929%**. Its higher any-attack recall, **97.24% versus 95.42%**, comes with substantially worse stage precision and more false alarms.

Choosing one expert family per stage using fit-only out-of-fold AP also does not improve the general average: macro-F1 **0.6742 versus 0.6749**. Additional model-selection machinery did not produce the hoped-for advantage here. Sparse fitting labels, score calibration, prior differences, or limited complementary information are possible explanations; this pilot does not identify their causal contributions or prove that learned fusion always fails.

## 3. A normal-only false-alarm budget misses most wrong-stage alerts

For the general-model average, the nominal **0.1% normal-calibration budget** gives evaluation exfiltration recall **91.82%**, but precision only **25.13%**. Its 294.00 mean wrong exfiltration alerts include 29.67 normal, 184.67 pivoting, 33.67 lateral, 45.67 reconnaissance, and 0.33 initial-compromise rows.

Calibrating against **all non-exfiltration classes** at a nominal 0.1% instead yields **30.67** wrong alerts and precision **64.47%**, but recall falls to **52.52%**. These thresholds constrain different populations and are not interchangeable. They illustrate a tradeoff, not a guaranteed operating point or proof of a better classifier. Most remaining errors at the stricter point are still pivoting: 29.33 of the 30.67 wrong alerts.

## 4. Is there a plausible praxis here?

**A limited applied direction remains plausible; a successful novel exfiltration method has not been demonstrated.** The positive finding is modest stage-score improvement with fewer normal false alarms from fixed averaging. The important unresolved problem is explaining the adversary's activity correctly, especially distinguishing pivoting from exfiltration, while preserving visibility of lateral movement.

A defensible research question is: **Can additional, causally available host/transfer context reduce pivoting-to-exfiltration confusion beyond equally informed general models, without increasing missed lateral activity or false episode alerts?** Generic fusion is already prior art, as are transfer-rate features and APT stage classification. Its value would come from demonstrated error reduction, transparent tradeoffs, and independent executions—not from naming a model combination.

## 5. Most useful next tests, in order

1. **Target the measured confusion before adding more model families.** On a newly frozen development design, compare an exfiltration-versus-pivoting specialist with a general model given the same labels/features, an exfiltration-versus-all specialist, and a simple score adjustment. Define how normal and other-stage flows are handled; a pairwise classifier alone cannot safely relabel every flow. Inspect fitting/calibration errors for consistent distinguishing behavior. This is motivated by the current results and must be disclosed as a follow-up, not presented as a prespecified success from this pilot.
2. **Add observations rather than more algebraic transformations.** After source/target schema qualification, test victim-relative transfer direction, past-only per-host/destination transfer totals, destination novelty, and repeated-transfer context. The current 73-feature table cannot supply verified host roles or cross-flow chronology. Compare general-plus-context against specialist-plus-context to isolate the specialist contribution. Bound context at the actual time the complete flow becomes observable; completed totals cannot demonstrate earlier warning.
3. **Use DEDALE as a chronological worked example, not confirmation.** Its acquired subset has only two exfiltration flows from one execution/campaign. A source-locked timeline can show scores, evidence availability, host links, wrong-stage predictions, and missing context. It cannot support fitting or validating a general temporal exfiltration detector. Independent executions with exfiltration, pivoting, lateral movement, and realistic benign transfers remain necessary.
4. **Only then test feature-view loss separately.** Give general and specialist methods the same missingness indicators and training conditions, remove dependent feature aliases consistently, and retain simple averaging controls. Simulated feature removal measures feature-view robustness, not actual missing/delayed logs. That extension has not been run here.

Do not retune on these evaluation outcomes and call the result confirmation. Preserve the fixed pilot and all unfavorable arms. Stronger tuning controls and new independent campaign data would be needed before claiming an operational advantage.

## Review provenance

- EVIDENCE SHA-256: `62f6e552946da24b99594fdb26f43554b83ef10d567f6fad200fbf9f43b13751`.
- Its source-summary binding: `eb9859150370eff10f35e90b7b99e399e2a759aea5ded1ca1ae14bb69ab116a9`, matching the public audit's summary hash.
- This note independently reads the aggregate/per-seed metrics and derives the stated confusion-column counts and paired differences. It does not rerun inference or substitute for the saved-output audit.
- No temporal reconstruction, feature-loss condition, fresh-data confirmation, model novelty, or analyst outcome was measured by this pilot.
