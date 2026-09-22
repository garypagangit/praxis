# Can host roles and earlier activity distinguish movement from exfiltration?

**Yes, we can test this on a different dataset—and the first alternative-dataset experiment is complete.** Host roles plus earlier traffic substantially improved ranking of exfiltration-labeled flows. The operating decisions still show a movement-detection cost and a failure when the exfiltration destination changes role.

## Dataset used: UNRAVELED

[UNRAVELED, Computer Networks (2023)](https://doi.org/10.1016/j.comnet.2023.109688) provides time-stamped flows, host identities, static network topology, benign traffic and attack-stage annotations. We prepared **382,229 rows from eleven complete IT-sensor captures**. Earlier captures supply fitting/calibration; later captures supply evaluation, including **3,442 exfiltration and 35 movement-stage rows**.

The source was used in prior GML work and describes one APT campaign. It is a different dataset from SCVIC, but not an untouched, independent-campaign confirmation set. All movement-stage rows in this sensor are annotated Remote System Discovery on one host pair, so the task measures author-defined stage recognition, not proof that every labeled event is successful movement or theft.

## What was tested

The same LightGBM model and fitting examples receive current-flow features, coarse host roles, preceding 5/30-minute activity, or their combination. Controls use roles alone or a different host's earlier activity. Every history event must finish before the current connection starts. No labels, future activity, literal host identifiers or absolute dates enter the predictors.

### Exfiltration ranking improves

Average precision summarizes how well exfiltration events rise toward the top of the scored list; higher is better. Means cover three fits on the same later-period cases.

| Information available | Exfiltration average precision |
|---|---:|
| Current flow only | 0.6363 |
| Current flow + roles | 0.6782 |
| Current flow + earlier activity | 0.7300 |
| Current flow + roles + earlier activity | **0.8823** |
| Current flow + roles + wrong-host history | 0.6629 |

The combination beats the wrong-host control, providing a useful signal that correctly linked prior activity matters in this development setting. It does not establish causal attribution or generalization to another campaign.

### Detection can improve, with explicit costs

At the **predeclared nominal 1% non-exfiltration calibration-tail setting**, the comparison is:

| Later-period result | Current flow only | Roles + earlier activity |
|---|---:|---:|
| Exfiltration recall | 67.56% | **90.46%** |
| Exfiltration F1 | 0.6729 | **0.7450** |
| Exfiltration precision | **67.11%** | 63.63% |
| False exfiltration alerts, all non-exfil classes | **1,148.33** | 1,774.00 |
| Movement rows wrongly called exfiltration /35 | **0.00** | 17.33 |

These are mean counts across fits, not fractional independent events. This threshold is one of four published descriptive settings, not a selected deployment policy or a universal 1% guarantee. The default four-class decision behaves differently: normal false attack alerts fall from 157.33 to 47, but movement any-attack recall falls from **69.52% to 40.95%**. Both decision rules and all other settings remain in the report.

### The unresolved issue is now specific

The later data include **1,101 exfiltration-stage flows toward private-service hosts**, a role context absent from fitting/calibration exfiltration examples. Every arm gives **zero correct exfiltration labels** for that group under the ordinary four-class decision. A useful ranking signal does not automatically transfer into a reliable decision rule.

The next method should test how to use that context without suppressing movement evidence, and how to flag unfamiliar role contexts for a separate decision. It also needs event-level verification of the source labels before claiming successful movement-versus-theft detection. [Next experiment](NEXT_EXPERIMENT.md) separates those requirements.

## Why a newer dataset was not automatically better

We reviewed primary papers and inspected additional raw artifacts. Windows-APT2025 explicitly lacks observable exfiltration telemetry; UWF-ZeekData24 lacks a released lateral-movement class. We acquired and examined all 24 Comprehensive APT2025 archives: malformed records, duplicated campaigns and failed/preparatory transfers among tactic tags prevent treating that release as confirmed movement/theft truth. These are dataset qualification findings, not failed ML experiments.

[Dataset literature and options](DATASET_LITERATURE.md) | [Actual Comprehensive APT2025 archive inspection](COMPREHENSIVE_PROBE.md) | [UNRAVELED inventory and parser correction](DATA_INVENTORY.md)

## Results and reproducibility

- [Plain-language interpretation](INTERPRETATION.md)
- [Full report, every arm, threshold and role stratum](../results/host_history_exfil_v1/REPORT.md)
- [Ranking and movement tradeoff chart](../results/host_history_exfil_v1/CONTEXT_TRADEOFF.png)
- [Independent audit: PASS](../results/host_history_exfil_v1/AUDIT.json)
- [Frozen design](DESIGN.md), [protocol](protocol.json), [source inputs](PILOT_INPUTS.json), [run receipt](RUN_RECEIPT.json)

**18 models completed; 15 tests passed.** The independent audit reparsed all 382,229 source rows, recomputed saved metrics and checked 98 historical-feature anchors, including every movement row. It verifies calculation/provenance integrity, not the truth of the author's attack labels. CPU fitting took approximately 117 seconds; no AWS compute was started.

From the repository root:

```powershell
python -m experiments.apt_benchmark.host_history_exfil.run prepare --inputs experiments/apt_benchmark/host_history_exfil/PILOT_INPUTS.json --output <fresh_prepared_dir>
python -m experiments.apt_benchmark.host_history_exfil.run fit --prepared <prepared_dir> --protocol experiments/apt_benchmark/host_history_exfil/protocol.json --output <fresh_run_dir>
python -m experiments.apt_benchmark.host_history_exfil.report --run <run_dir> --prepared <prepared_dir> --output <public_dir>
python -m experiments.apt_benchmark.host_history_exfil.audit --run <run_dir> --prepared <prepared_dir> --protocol experiments/apt_benchmark/host_history_exfil/protocol.json --output <new_audit_json>
python -m pytest experiments/apt_benchmark/host_history_exfil/test_context.py -q
```
