# PX-093 — Plan B decision

H1: **SUPPORTED_BY_CONSTRUCTION**; H2: **NOT_SUPPORTED**; H3: **NOT_SUPPORTED**. The original PX-092 Part C / H3 remains **not supported**; this extension is a separate, later development study.

**Recommendation: do not adopt the proposed repair-first thesis in its current form.** The heterogeneous gate improved recall on both AIT executions, but failed the overlap and fixed false-alert limits on both. It also failed the fixed false-alert limit on UNRAVELED. The useful result is an audited warning-retention/workload tradeoff; it does not establish a generally affordable repair or make the earlier failed hypothesis pass.

## What was run

Two new logistic-regression fits with train-only imputation/scaling and fixed parameters, one per source. The existing current-only LightGBM was reused. Eight ensemble sets were evaluated across nine UNRAVELED condition/budget settings and Wilson, Harrison and pooled AIT. Both fits converged; no held-out rows entered training. No cloud or model API was used.

## Main comparison

| Source | Base-three OR recall | Full heterogeneous OR recall | Base false alerts | Full false alerts | Recovered exfiltration flows | Added false alerts per recovered exfiltration flow |
|---|---:|---:|---:|---:|---:|---:|
| UNRAVELED | 98.779779% | 99.244625% | 196 | 1991 | 16 | 112.188 |
| wilson | 99.985862% | 100.000000% | 54 | 1751 | 3 | 565.667 |
| harrison | 99.603530% | 99.607793% | 1404 | 15420 | 1 | 14016.000 |
| pooled | 99.785120% | 99.794073% | 1458 | 17171 | 4 | 3928.250 |

Recovery is not limited to exfiltration: the full gate adds 26 attack-labeled flow warnings across all stages on UNRAVELED, 619 on Wilson and 157 on Harrison (776 pooled AIT). The table focuses on the declared primary exfiltration outcome; it does not count those other recoveries as zero. The fixed false-alert guard still fails. These research guard values are not measured analyst-capacity limits, and no claim about actual analyst utility follows from flow counts alone.

## Overlap is not a success criterion by itself

The duplicate control leaves UNRAVELED's 196 false alerts and 98.779779% exfiltration warning recall unchanged, yet lowers overlap from 0.363636 to 0.270345. It adds no information. The full heterogeneous set's overlap is 0.743188; its absolute false-alert count and marginal recovery must be examined separately.

Adding only the existing current model to the three roles models also lowers the UNRAVELED overlap ratio to 0.277620 without adding any attack warning or false alert. On AIT that addition recovers the same four pooled exfiltration flows as the full heterogeneous set, with fewer false alerts (14,077 versus 17,171), but still exceeds the fixed workload limit. The logistic member adds no further pooled AIT exfiltration recovery beyond the current-model addition. This ablation is retained rather than crediting the full ensemble for a simpler member's gain.

## A defensible Plan B framing

Working title: **Auditing Warning Retention and Alert Workload in APT Classifier Ensembles**.

1. When do classifier-combination choices discard warnings that constituent models already produced?
2. Which apparent improvements remain useful when evaluated against a fixed false-alert budget and marginal recovered-warning counts?
3. How do those conclusions change between the exposed UNRAVELED campaign and the adapted AIT executions?

The practical deliverable is the frozen replay and independent audit that reports retained/lost warnings, unavailable evidence, unique recoveries, absolute false alerts and workload acceptance together. A duplicate-member control demonstrates why a favorable overlap statistic alone is insufficient. These questions organize completed exploratory evidence; they are not new hypotheses retrospectively labeled preregistered.

This would reuse the evaluation-focused Praxis already developed. A distinct positive-detector Plan B is not established by PX-092/PX-093. Before committing to the title as a new contribution, compare the specific audit contribution with the closest prior aggregation/error-diversity studies and obtain committee feedback on that scope. Additional tuning on these same test rows would not supply independent confirmation.

## Mechanism and limits

OR structurally preserves constituent warnings. Mean can erase warnings through competing class scores; a confident benign member is one possible cause, not an absolute veto. A synthetic boundary test also demonstrates mean selecting benign when all members warn on different attack classes. Empirical counts for both cases are retained in RESULTS.csv. These mechanisms alone are not a novel ensemble algorithm.

The all-members-warn vote-splitting counterexample did not occur in the evaluated cells; it is a mathematical boundary test, not an observed cause in this run. All observed mean-loss cases had at least one benign-voting member.

The heterogeneous members use existing features and shared training observations. They provide algorithm/input differences, not independent campaigns. UNRAVELED and AIT test results had already been examined. AIT retains its adapted three-class/history contract. No analyst outcome, safe-deployment guarantee, universally bounded operational burden or unique superiority over every alternative has been established.

Audit: 24,239 checks, 96 cells and 288 result rows. The independent script reproduced every saved gate decision and both LR models' full evaluation probabilities; source hashes, row identities, training separation and per-row costs were checked.

## Evidence

[Full comparison](RESULTS.md) | [Every arm CSV](RESULTS.csv) | [Frozen protocol](PROTOCOL.md) | [Audit and hypothesis components](AUDIT.json) | [Literature and claim corrections](LITERATURE_AND_CLAIMS.md)
