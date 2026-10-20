# Real-record feasibility screen — October 20, 2026

**Decision: proceed to a small matched telemetry pilot, not a large collection commitment.** Real archived commands contain some transferable signal. This screen cannot establish that the signal survives matching the environment, task, tools and sensors. It cannot guarantee that collection will produce a positive thesis result.

Unlike the earlier synthetic experiment, every feature here is extracted directly from real archived command strings. No class offsets, simulated timing, DAPT flow pairing or fabricated host events are used. This is a separate command-only feasibility analysis; its feature definitions and metrics differ from the synthetic RQ harness.

## What was tested

- GAMBiT: 111 participant-day windows from 57 human participants.
- Honey for the Agent: 1,315 windows from 9 AI model identifiers, retained from a seeded sample of 1,800 session files.
- COCHISE: 38 windows from 15 AI model/configuration identifiers.
- Exactly the first 10 non-placeholder commands per eligible episode. Entire short episodes excluded. Human records ordered by timestamp within participant-day; AI commands retain archive order.
- Global exact command-window deduplication before splitting. Semantic/near-duplicate behavior is not deduplicated. Raw model identifiers are grouping variables only, never predictors.
- Five fixed 70/30 group splits (seeds 19, 29, 39, 49, 59). Human participants and AI model identifiers never overlap train/test within a run. All destination AI records are held out in each cross-archive experiment. Test humans are held-out participants from GAMBiT, **not a new human source**.
- Fixed logistic regression, random forest and RBF SVM configurations. No test-driven tuning or winner selection. A group-label-shuffled logistic reference accompanies each task and feature set.
- Training weights give equal total weight to each class and each group within class. Evaluation does the same, so prolific participants/models cannot dominate the metric.

Only aggregate scores, source file hashes, counts, code and methodology are published. Raw commands, episode features, participant identifiers, model predictions and credentials are not published.

## Main results

The table uses **group-balanced accuracy**, averaging human specificity and AI sensitivity with equal weight per participant/configuration within class. Chance is 50%. These are five-split averages, not conventional row-level accuracy or the earlier synthetic macro-F1. Parentheses give the split range, **not a confidence interval**. The splits reuse observations and are not five independent replications.

| Training AI source → test AI source | Logistic, all features | Logistic, structural only | Random forest, all | SVM, all |
| --- | ---: | ---: | ---: | ---: |
| Honey → held-out Honey models | 88.7% (84.9–92.7) | 62.9% (53.4–78.1) | 90.0% | 88.7% |
| COCHISE → held-out COCHISE models | 93.2% (85.8–98.6) | 89.5% (75.8–100) | 87.5% | 94.3% |
| Honey → COCHISE | 70.8% (66.2–73.2) | 73.4% (69.4–82.5) | 60.0% | 71.3% |
| COCHISE → Honey | 66.2% (62.9–69.0) | 61.8% (58.1–65.8) | 56.8% | 64.3% |

The consistent drop from within-archive tests to cross-archive tests matters more than the high within-archive score. Transfer is asymmetric. For full logistic regression, Honey→COCHISE AI recall is only 51.7%, with a 10.0% human false-AI rate. In reverse, AI recall is 38.0%, with a 5.6% human false-AI rate. Thus a 66–71% balanced score does **not** mean most unfamiliar AI executions are detected.

Structural-only Honey→COCHISE logistic recall rises to 67.9%, but human false-AI classifications also rise to 21.1%. This tradeoff would matter in an operational detector.

## Confounding and negative controls

A separate diagnostic classifies **Honey versus COCHISE, both AI**. Logistic regression gets 98.8% balanced accuracy using all features and 84.5% using structural features. The sources are highly distinguishable even without executable/tool vocabulary. That makes source/environment confounding a serious alternative explanation for human-versus-AI scores.

Shuffling training labels at group level produces unstable results because there are few AI groups. Full-feature logistic null averages are 39.1% for Honey→COCHISE and 52.2% in reverse; individual null split results can reach 72.4% in reverse. The same-source AI diagnostic null averages 69.4% and ranges 37.0–90.9%. Do **not** describe these controls as a clean significance pass. One permutation per split is not a permutation test; additional independent groups and a prespecified multi-permutation analysis are needed before inferential claims.

## Features and limitations

All features: executable-token diversity, transition entropy, immediate executable repetition, discovery vocabulary count, tool vocabulary fraction, plus seven structural statistics. Structural-only uses command-length mean/CV, flag fraction, pipe fraction, chain fraction, redirection fraction and unique-command fraction. Parsing uses coarse first tokens; wrappers and nested commands are not fully parsed. Command length can reflect paths, arguments, task complexity and environment. Removing vocabulary does not remove source confounding.

Sources have different tasks, machines, command wrappers and operator policies. No APT-stage equivalence or autonomous execution compliance was independently established here. Ten-command prefixes emphasize initial behavior, not complete campaigns. GAMBiT is a normalized local export, not independently re-extracted for this test. Model identifiers are weaker than truly independent provider/scaffold families. COCHISE has few traces and groups. These are controller command observations, **not validated target-side Windows/Sysmon/Zeek features**; availability from the proposed defender sensors remains unproven.

No raw data were sent to external services, no commands were executed, and no new live attacks or AWS resources were started. See the [dataset evaluation](../../../PRAXIS_DATASET_EVALUATION.md) for source descriptions and the [input audit](real_feasibility_20261020/audit.json) for exact files, hashes, exclusions, group counts and split sizes.

## Small pilot to decide whether to scale

Use the existing planned 12–24-trial pilot; aim for **24 executions: 12 human and 12 autonomous AI**, with at least four human operators and four AI configurations, across matched tasks. Repeated runs from one operator/configuration do not create additional independent groups. This is an engineering screen, not a statistically powered final study.

1. Confirm collection readiness first: isolated authorized lab, identical starting snapshot, objectives, access, allowed tools and observation budgets; reset between trials. Record interventions, success/failure and collection loss.
2. Capture the actual proposed target-side sensors. Verify that command/process features can be reconstructed in both arms. Keep controller logs for provenance, not as undeclared substitutes for defender evidence.
3. Match scenarios across arms and balance collection order. Include scripted automation controls to check whether detection merely recognizes automation. Additional control runs sit outside the 24 binary pilot executions.
4. Freeze features, grouped splits, one simple primary model and a practical criterion before looking at pilot labels/results. A possible **discussion target**, not an approved hypothesis: balanced accuracy at least 0.70 with human false-AI rate at most 0.20, retained after timing/tool ablation. With this small pilot, point estimates alone cannot justify scale-up; inspect group uncertainty, per-group failures and task/source shortcuts.
5. Scale only if telemetry is usable, effects persist across held-out operators/configurations, and the estimated collection effort can meet the schedule. Otherwise revise the feature/collection design before committing more time. A negative result can still be valuable, but it would need a clearly scoped thesis and adequate evidence.

The existing tracker targets collection readiness October 23 and pilot/protocol freeze October 26, ahead of AI Review November 14 and defense December 1. This screen informs the October 21 feasibility discussion; it does not mark any collection gate complete.

## Reproduce and inspect

[All 200 score records](real_feasibility_20261020/scores.csv) · [40 aggregate comparisons](real_feasibility_20261020/summary.csv) · [Audit](real_feasibility_20261020/audit.json) · [Runner](real_archive_feasibility.py)

```powershell
python real_archive_feasibility.py --human PATH/commands.json --honey PATH/Logs_final.zip --cochise PATH/current/examples/run-trajectories --output NEW_OUTPUT_DIRECTORY
python -m pytest -q
```

Use the existing pipeline requirements. The output directory must be new. Source paths are explicit; no raw records are exported. This exploratory design and the proposed pilot criteria are not a preregistration, power calculation or final hypothesis decision.
