# Explanation experiments: results and Praxis recommendation

## Recommendation

Develop **Verifiable Explanations of Lost Attack Warnings in APT Detection Pipelines** as an auditable-AI extension of the existing Praxis. PX-100 is the strongest candidate; PX-101 supplies supporting evidence. Publication novelty remains unconfirmed. The completed work verifies software decisions; it does not prove causal attack explanations, improved analyst performance, or universal detection improvement.

## Completed experiments

| Experiment | Actual result | Interpretation |
|---|---|---|
| PX-100: verifiable warning-loss explanations | 54 acquisition cells, 11,237,076 row-condition replays, zero state/spend/time/probability mismatches | Saved actions explain the recorded routing exactly. These are repeated observations of 208,094 flows, not 11 million independent samples. |
| PX-100: fixed-member aggregation intervention | Saved OR/mean decisions reproduced on UNRAVELED, Wilson and Harrison | Identifies warnings discarded by averaging. Benefit and false-alert cost depend strongly on execution. |
| PX-101: feature-explanation stability | 512 diagnostic rows, three saved models; probabilities match within 3e-8; attribution sums match raw scores within 1.7e-14 | Explanations are numerically consistent with the fitted models. This is necessary but does not establish causal or behavioral fidelity. |
| PX-102: human-review utility | 12 cases, local review form, response exporter, answer key and scoring program prepared; zero participants | Whether these explanations help people remains unanswered. |

No new fits, cloud jobs or paid inference. The core replay and attribution run took 11.625 seconds, excluding preparation, hashing and separate audit.

## Detection and workload: mean versus OR

These are new verified reanalyses of existing predictions, not new detector results. Members are the three saved seeds. Exfiltration warning means any attack-stage prediction on an author-labeled exfiltration flow.

| Source | Mean exfil warnings | OR exfil warnings | Extra exfil warnings | Extra benign alerts | Extra benign alerts per extra exfil warning |
|---|---:|---:|---:|---:|---:|
| UNRAVELED | 2,342 / 3,442 (68.04%) | 3,400 / 3,442 (98.78%) | 1,058 | 14 | 0.013 |
| AIT Wilson | 21,211 / 21,219 (99.96%) | 21,216 / 21,219 (99.99%) | 5 | 1 | 0.20 |
| AIT Harrison | 23,362 / 23,457 (99.595%) | 23,364 / 23,457 (99.604%) | 2 | 547 | 273.5 |

OR benign totals are 196, 54 and 1,404, respectively; mean totals are 182, 53 and 857. The ratios count flows, not distinct incidents or analyst investigations. Wilson/Harrison were previously exposed execution-disjoint evaluations; they are not new untouched test sets. Comparison here is against mean, not best single expert. Prior work already found no strict gain over the best single seed on Wilson.

Across all attack stages, mean suppresses 1,067 available warnings on UNRAVELED, 24 on Wilson, and 7 on Harrison. All three members are silent on 75, 1,059 and 534 attack rows, respectively. A gate cannot recover those rows without another source of evidence or an explicit rule.

## What the feature explanations show

Three-seed mean top-five Jaccard overlap (intersection divided by union):

| Diagnostic cohort, 128 rows each | Overlap |
|---|---:|
| Exfiltration missed by seed 8103 | 0.658 |
| Exfiltration warned by seed 8103 | 0.776 |
| Correctly benign under seed 8103 | 0.458 |
| Benign false alerts under seed 8103 | 0.635 |

The benign cohort's warning decisions agree across all seeds, yet the top-feature lists differ. The missed-exfiltration cohort has 123/128 warning disagreements between seeds 8101 and 8103, and 120/128 between 8102 and 8103. These selected examples illustrate why both decision agreement and explanation agreement need reporting. They are not representative prevalence estimates or significance tests.

For missed exfiltration, prominent margin contributions include destination role, source-to-destination reset-packet count, and mean packet interarrival time. These describe model dependence, not why an adversary acted or which feature change would safely repair detection. Attributions explain benign versus exfiltration raw scores, not the entire attack-versus-benign rule. Other attack classes can win.

## Verification and boundaries

- Frozen protocol/source/input hashes precede these analyses: commit `4dcf9a7`.
- Independent replay reconstructs actions' consequences. It does not regenerate the learned selector's acquisition scores or prove optimal acquisition.
- The four-expert recoverability split includes experts whose evidence may not be available within a particular budget. It is an upper-bound diagnostic, not a feasible-repair promise.
- Exhaustive output-bit inversion is rejected against trusted member scores on 1,275,305 ensemble rows. This is a basic integrity check, not adversarial security evidence.
- Separate audit verifies 18 genuine explanation cases, rejects 18 flipped claims, and abstains on 54 missing-member cases. It independently recomputes all 36 attribution-overlap cells.
- The environment emitted a scikit-learn deserialization version warning. Native LightGBM inference reproduces saved probabilities within 3e-8 on the explanation sample; that resolves this sample's numerical compatibility check, not arbitrary artifact compatibility.
- No confidence interval over independent campaigns is justified by these three executions. No analyst workload or incident benefit is inferred from flow counts.

## Literature overlap and publication decision

**Direct overlap:** Maseno, Sun and Wang, [Reliability auditing of explanations for machine-learning-based intrusion detection systems](https://link.springer.com/article/10.1007/s11416-026-00664-7), published August 24, 2026, already evaluates attribution agreement, retraining stability and functional explanation tests. A generic SHAP-reliability audit is not a new contribution; PX-101 is supporting evidence.

[Kalakoti et al., Evaluating explainable AI for deep learning-based network intrusion detection system alert classification](https://arxiv.org/abs/2506.07882) also evaluates explanation quality for security alerts. Merely attaching explanations or conducting an analyst comparison does not establish novelty.

[Lundberg et al., From local explanations to global understanding with explainable AI for trees](https://arxiv.org/abs/1905.04610) is the established attribution-method foundation. [NIST's Four Principles of Explainable Artificial Intelligence](https://nvlpubs.nist.gov/nistpubs/ir/2021/NIST.IR.8312.pdf) provides the framing: explanations must be meaningful, accurate and explicit about knowledge limits.

The narrower candidate contribution is an evidence-backed account of **where warnings disappear across a multi-step pipeline, which fixed-score intervention restores them, and what that intervention costs**. The OR rule and numerical reconstruction are established methods. A paper must distinguish this applied contribution from existing decision provenance and forensic-ready IDS work; the present search does not establish first-of-kind status.

## Human pilot and remaining work

Open `PX102_REVIEW.html` locally after consent and applicable university review. Counterbalanced conditions display identical member scores, with or without an explanatory sentence. The first pilot contains six UNRAVELED and six Wilson cases; no Harrison case or policy override is included. No source labels, answer keys or researcher diagnosis are displayed as a correct answer. The browser form is generated; interactive usability has not yet been tested with participants.

Score genuine exported responses with `python reviewer.py score response_files...`. Scores are descriptive; participant-level paired analysis and a power plan are required before a confirmatory study. The explanation supplies relevant derived information, so improved accuracy would establish presentation assistance on this task, not general SOC expertise or causal understanding. Form source contains both arms; this is a supervised pilot instrument, not a secure blinded platform.

Next publication gates: (1) targeted comparison against decision-provenance and forensic-ready IDS literature, (2) one independently reserved evaluation before adapting the method further, (3) genuine reviewer pilot if human usefulness is claimed. A full end-to-end selector-score and policy-rule explanation audit remains additional work. Do not replace the primary manuscript's claims with stronger claims until these gates are met.

## Reproduction

Use the saved inputs listed in `FREEZE.json` and Python environment `C:/w/praxis_full_release_20260927_env/Scripts/python.exe`.

```
python run.py run
python audit.py
python reviewer.py build
```

Large private attributions and reviewer answer key reside in `C:/w/explanation_trials_20261003`; their checksums are recorded in `ARTIFACTS.json`. Public code and aggregate results are in Git. Data/model availability remains a prerequisite for reproduction.
