# PX-083 — Does a context-selection policy transfer between security datasets?

## Result: no added decision benefit from the cost-sensitive selector

**The cost-sensitive selector reproduced the context expert's hard decisions in all 42 evaluation views.** It switched between score sources, so its probabilities were not identical, but those switches created no additional decision improvement at the frozen strict 0.5 threshold. The ordinary selector reproduced current-event decisions in all 21 Casino views and 9 of 21 CAM-LDS views; its remaining CAM-LDS changes affected at most eight rows per view.

Two Ridge policies were trained on **1,494 CasinoLimit calibration examples** and transferred unchanged to CAM-LDS. The underlying classifiers remained separately trained on their native datasets. This is transfer of a score-selection policy, not transfer of a feature model.

### Clean-condition results at the frozen operating point

| Dataset / method | T1105 recall | F1 | Other-technique labels flagged |
|---|---:|---:|---:|
| Casino / current event | 82.35% | 0.7368 | 7 |
| Casino / ordinary selector | 82.35% | 0.7368 | 7 |
| Casino / context expert | 82.35% | 0.5957 | 16 |
| Casino / cost-sensitive selector | 82.35% | 0.5957 | 16 |
| CAM-LDS / current event | 87.00% | 0.0495 | 3,329 |
| CAM-LDS / ordinary selector | 87.00% | 0.0495 | 3,325 |
| CAM-LDS / context expert | 88.00% | 0.0534 | 3,108 |
| CAM-LDS / cost-sensitive selector | 88.00% | 0.0534 | 3,108 |

CAM-LDS cost-sensitive average precision was **0.02773**, close to the context expert's **0.02774** and the target prevalence of **0.02376**. These scores offer little evidence of useful transferred discrimination. The original native thresholds also performed poorly on this clean CAM-LDS evaluation: current-event recall 0%, context recall 1%, mixed-dropout recall 0%. Those older thresholds are preserved as a descriptive supplement; they were not used to fit or tune the new policies.

## What the experiment can establish

The policies learn the difference between using history and using current evidence. One treats every error equally; the other gives T1105 errors four times the cost. These costs are research choices. No hyperparameter or threshold was changed after evaluation.

A post-result explanation found only **11 calibration examples with different expert errors**. There was little direct evidence from which to learn when one expert should replace the other. This does not prove that all context selectors fail; it shows that this simple, declared policy did not supply an additional decision benefit under the tested conditions.

All **15 conditions / 21 perturbation views** are retained, including current evidence, context, fusion, confidence gating, both learned policies, and previously fitted mixed dropout. The missing-record results show tradeoffs, not a universal remedy. For example, with command records absent on CAM-LDS, context and the cost selector detect 15% of T1105 targets while flagging 666 other-technique labels; mixed dropout detects 84% while flagging 2,976.

## Scope matters

- **T1105 is Ingress Tool Transfer, not lateral movement or exfiltration.** No early warning of data theft is measured.
- Negatives are other annotated techniques, not verified benign activity. The table does not measure production false alarms.
- Casino evaluates 920 targets/17 positives across 18 runs; CAM-LDS evaluates 4,209 targets/100 positives across 18 runs from one held-out family.
- Casino uses annotation-onset proxy events; CAM-LDS uses labeled interval states. The units differ and must not be pooled into one accuracy claim.
- Both sources were previously examined. This is secondary development evidence, not untouched confirmation or an algorithm-novelty result.
- Missing/delayed logs are replay interventions. The offline target roster is not a deployable detection trigger, and invisible targets remain in the denominator as missed cases.

## Evidence and integrity

**Completed: two Ridge fits, no native classifier retraining, 294 saved prediction tables, 27.24 CPU seconds.** AWS was not used for these small fits. Four invariant tests passed. The computational audit passed: 220 qualified source prediction files, 294 exact inference replays, 5,586 independently calculated metric tables and 126 original-threshold control tables.

The scientific freeze was committed as `c116410` before fitting. Private row-linked results and fitted selectors remain under `C:/w/apt_benchmark_data_20260920/praxis_next/px083/run_v1`.

[All results](results/REPORT.md) · [Metrics](results/METRICS.json) · [Post-result decision diagnostic](results/DIAGNOSTICS.json) · [Audit](results/AUDIT.json) · [Frozen protocol](PROTOCOL.md) · [Qualified inputs](INPUTS.json) · [Source binding](FREEZE.json)

From the repository root:

```powershell
python -m pytest experiments/praxis_next/px083_policy_transfer/test_policy.py -q
python -m experiments.praxis_next.px083_policy_transfer.run run --output <fresh_private_run> --freeze-commit c116410
python -m experiments.praxis_next.px083_policy_transfer.audit --run <private_run> --output <private_run>/AUDIT.json
python -m experiments.praxis_next.px083_policy_transfer.report --run <private_run> --output experiments/praxis_next/px083_policy_transfer/results
```
