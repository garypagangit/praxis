# PX-105 — Novelty test: trace versus intervention replay

## Decision

**The proposed addition did not demonstrate an advantage over ordinary complete traces. Do not claim a new explanation technique from this experiment.** General ML-pipeline debugging also provides substantial prior art for provenance plus intervention-based failure verification. A narrowly applied APT audit contribution remains possible, but novelty is unconfirmed.

## What was run

Used saved UNRAVELED model probabilities to construct four known failure mechanisms: aggregation suppresses a member warning (64 cases); selection chooses the silent current-flow expert despite an available roles warning (21); the same 21 records fail because roles evidence arrives after the deadline; both examined experts are silent (64). Total: 170 scenarios drawn from 90 unique event hashes. Some records occur in several mechanisms. These are controlled software scenarios over real scores, not 170 independent observed attacks.

Protocol and source were frozen in commit f6ce0ce before computing outcomes. Deterministic hash ordering selected at most64 records per cohort; only21 qualifying selection records existed. No replacement samples, new fits or cloud jobs.

| Method | Correct diagnoses | Feasible-repair outcomes correctly predicted |
|---|---:|---:|
| Final-score-only reviewer | Abstains on170/170 | Abstains on510/510 |
| Ordinary complete trace | 170/170 | 510/510 |
| Trace plus intervention replay | 170/170 | 510/510 |

The final-score reviewer is intentionally conservative: its abstentions are not a measured error rate of a trained diagnostic model. The decisive comparison is the tie between the two complete-trace methods. Both know the same small pipeline logic and receive the same metadata. Replay checks the trace-derived explanation but supplies no accuracy benefit on these simple mechanisms. This result does not establish equivalence on complex pipelines.

The three proposed actions are restoring an available warning, extending the deadline, and doing nothing. A repair that changes the original one-second deadline is explicitly outside the original contract. The evaluator checks whether a warning is feasible within that contract, not whether a late warning could ever be useful. All-silent means only the two experts in this constructed experiment; it is not a claim about every possible detector.

## Useful findings, with limits

- Twenty-one paired cases have identical inputs to the final expert, identical expert scores and identical final predictions, but different software failure mechanisms: selection versus late evidence. A deterministic explanation of that same expert/input cannot distinguish the two without pipeline information.
- This is an information-limit demonstration, not an empirical win over SHAP. No new SHAP baseline was run and no SHAP diagnosis accuracy is claimed. Prior PX-101 attributions are a separate experiment.
- Removing timing from the106 expert-routing scenarios produces106 abstentions from the conservative trace checks. Both approaches depend on evidence completeness. No claim is made that every partial trace is inherently undecidable.
- A separate audit reconstructs the causes and checks all1530 proposal records across the three methods. It shares the known pipeline specification, not independent campaign data.
- This does not identify new attack episodes, improve detection, measure SOC workload, or establish human usefulness.

## Closest literature and access status

| Work | What overlaps | Assessment/access |
|---|---|---|
| [Debugging Machine Learning Pipelines](https://arxiv.org/html/2002.04640) | Uses previous-run provenance, proposes new configurations and executes them to test explanations of pipeline failure | Full HTML accessed. Strong prior art against a generic claim that provenance plus intervention verification is new. It studies general pipeline failures; our narrower warning-destination application is different but not automatically novel. |
| [mlinspect: a Data Distribution Debugger for Machine Learning Pipelines](https://ssc.io/pdf/mlinspect-demo.pdf) | Instruments pipelines and inspects intermediate data and provenance | Full PDF text accessed. Supports the ordinary tracing/instrumentation baseline. |
| [EXP-SEC](https://arxiv.org/html/2607.12203v1) | Isolates suspect traffic, explains dependent feature groups and maps explanations to security concepts | Full HTML accessed. Different explanation target, but analyst-facing IDS explanation is established. |
| [CyberShapley](https://doi.org/10.1016/j.cose.2024.104270) | Explanation and alert prioritization using coordinated APT datasets | Publisher-indexed methods/dataset sections available; direct full-page access failed. Full-text exclusion of overlap remains unfinished. It already invalidates a broad first-on-APT prioritization claim. |
| [AlertPro](https://doi.org/10.1016/j.cose.2023.103583) | Context-aware prioritization for multi-step attacks under limited review resources | Publisher abstract/indexed sections available; full-text access failed. Not implemented as a comparator here. |
| [Reliability auditing of explanations for machine-learning-based intrusion detection systems](https://link.springer.com/article/10.1007/s11416-026-00664-7) | Tests IDS attribution reliability, including stability and functional checks | Full text accessed in earlier experiments. Generic explanation reliability is already covered. |

This is a targeted overlap review, not an exhaustive systematic literature review. No absence-of-prior-work claim is justified. Literature comparison is not empirical superiority testing of these published systems.

## Recommendation for the Praxis

Keep the primary contribution as a reproducible audit of hidden warning loss, with exact decision explanations as an implemented component. The concrete application evidence and operational limits can be valuable without claiming a new XAI algorithm. Discuss with the committee whether that applied contribution meets the Praxis novelty requirement.

Do not spend on larger versions of this deterministic diagnosis pilot merely to increase the case count. Advancing a stronger method claim would require a specific unresolved failure that ordinary complete traces cannot handle, a justified method for addressing it, and independently reserved evaluation. No such advantage has been established here. The proposed human utility study remains unperformed; bot checks do not resolve it.

## Reproduce

Use the existing Praxis Python environment and private input paths in FREEZE.json:

```
python run.py run
python audit.py
```

The runner refuses to overwrite existing RESULTS.json. CASES.json contains reviewer inputs without answer labels; EVALUATION.json contains scoring outcomes. Both remain in the same research repository, so no organizational blinding or adversarial answer-key isolation is claimed.
