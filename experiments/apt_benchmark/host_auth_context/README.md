# Authentication context: prior art and a completed partial experiment

**The broad idea overlaps published work. The completed experiment finds a limited movement-detection improvement, with explicit costs; it does not establish a novel algorithm or solve movement versus theft.**

## Novelty verdict

[Powell (2022)](https://doi.org/10.1016/j.iswa.2022.200106) already uses host roles and earlier process behavior for lateral-movement detection; the author manuscript also proposes correlating that information with NetFlow and transferred bytes. Authentication-history models, temporal provenance, multimodal stage detection and uncertain outputs have additional prior art. [Full review: 21 primary references, access limits and publication status](NOVELTY_REVIEW.md).

The defensible next question was narrower: does correctly timed authentication add stage information beyond matched flow, role, history and observed-log controls when exfiltration changes destination role? The current run tests only part of that question.

## Important data limitation

Windows clock-change records exposed approximately seven-hour backward jumps. The display timezone was identifiable, but its alignment to the network sensor was not. **All Windows records were excluded before fitting.** Linux audit context remained usable for recorded-time analysis.

All **35 movement-stage test flows** have a covered Linux source. All **3,442 exfiltration-stage test flows** have the excluded Windows source. Thus the full hypothesis about Windows authentication improving exfiltration remains **untested**, not disproved. [Qualification and exact counts](HOST_EVENT_QUALIFICATION.md).

## Actual findings

Three fitting seeds share the same 208,094 later-period test flows. These are means across fits, not independent campaigns. The two context arms receive identical observed-log volume, timing and availability indicators; the added feature is authentication event type/outcome.

| Ordinary stage classification | Traffic alone | Context + matched log controls | Context + authentication | Context + wrong-host authentication |
|---|---:|---:|---:|---:|
| Four-class macro-F1 | 0.7552 | 0.7543 | **0.7752** | 0.7633 |
| Movement recall | **69.52%** | 40.00% | 58.10% | 45.71% |
| Movement F1 | 0.2861 | 0.2723 | **0.3547** | 0.3082 |
| Exfiltration average precision | 0.6363 | **0.8964** | 0.8687 | 0.8890 |
| Exfiltration F1 | 0.7561 | 0.7637 | **0.7645** | 0.7637 |
| Normal flows falsely flagged as attacks | 157.33 | 46.00 | 60.00 | **45.33** |

**Positive:** compared with the matched context arm, authentication details raised movement recall by **18.10 percentage points**, movement F1 by 0.0824 and macro-F1 by 0.0208. Correctly linked authentication also outperformed the wrong-host control on mean movement recall and F1. This suggests useful local movement-stage information.

**Costs:** normal false alerts increased from 46 to 60; exfiltration ranking fell from 0.8964 to 0.8687. Movement recall still trailed traffic alone. Adding authentication to the current-flow-only arm also did not reproduce the context benefit: movement recall fell from 63.81% to 60.00%, and exfiltration F1 fell from 0.7523 to 0.7394. These are not universally beneficial features.

**Unresolved:** all thirteen ordinary classifiers still assigned zero correct exfiltration labels to the **1,101 exfiltration-stage flows in the changed department-to-private-service destination context**. Higher ranking quality does not resolve that group automatically.

## Keeping separate alerts

We evaluated all arms under the same nine fixed decision settings. Keeping the original detector's alert while adding an exfiltration flag preserves existing alerts by construction. It is an operational choice, not learned detection improvement. Both-stage flags and unsupported role contexts remain unresolved reviews.

At the calibration-F1 rule, the context/authentication review union retained the original 69.52% movement coverage, but did not improve exfiltration F1 over the traffic-only rule (0.7624 versus 0.7653). More permissive or role-conditioned rules recovered additional exfiltration flags with more false or ambiguous alerts. Every setting is in the [policy tables](../results/host_auth_context_v1/POLICIES.md); none is selected as a deployment winner.

## Recommendation

**Do not present this combination as a new APT algorithm or a proven movement-versus-theft solution.** Retain the Linux-context result as development evidence. A stronger praxis requires independently synchronized, event-verified executions in which the same hosts and destination roles perform both stages, including benign administration and transfers. That would let us test stage semantics rather than fixed source, role or logging differences.

The current data are one previously exposed UNRAVELED campaign. Movement annotations here are Remote System Discovery, not independently confirmed successful remote access; exfiltration annotations are not receipt-verified stolen files. Thirty-five movement flows and three fitting seeds do not establish campaign-level reliability.

## Evidence and reproduction

- [Full numerical report](../results/host_auth_context_v1/REPORT.md)
- [All policies and their costs](../results/host_auth_context_v1/POLICIES.md)
- [Calculation audit](../results/host_auth_context_v1/AUDIT.json)
- [Frozen design](DESIGN.md), [protocol](protocol.json), [run receipt](RUN_RECEIPT.json)
- [Host-event qualification](HOST_EVENT_QUALIFICATION.json)

Completed: **21 new models, 18 saved model-arm replays and 22 passing tests**. CPU model fitting and scoring took about 267 seconds; AWS was unnecessary for this small comparison.

```powershell
python -m experiments.apt_benchmark.host_auth_context.host_events --source <raw-host-logs> --out <fresh-events> --linux-only
python -m experiments.apt_benchmark.host_auth_context.freeze --base-prepared <prior-prepared> --base-run <prior-run> --events <fresh-events> --output <fresh-protocol.json>
python -m experiments.apt_benchmark.host_auth_context.run prepare --protocol <protocol.json> --output <fresh-auth-prepared>
python -m experiments.apt_benchmark.host_auth_context.run fit --protocol <protocol.json> --prepared <auth-prepared> --output <fresh-run>
python -m experiments.apt_benchmark.host_auth_context.audit --protocol <protocol.json> --prepared <auth-prepared> --run <run> --output <fresh-audit.json>
python -m pytest experiments/apt_benchmark/host_auth_context/test_followup.py experiments/apt_benchmark/host_auth_context/test_host_events.py -q
```

The publisher uses the protocol beside its script and verifies that hash against the run. To publish this preserved run, use `python -m experiments.apt_benchmark.host_auth_context.report --run <run> --output <public-directory> --audit <audit.json>`.
