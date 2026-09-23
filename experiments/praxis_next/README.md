# New praxis experiments: September 23, 2026

**Completed measurement praxis:** [When Better APT Scores Hide Missed Attack Warnings](measurement_praxis/README.md) - [Word](measurement_praxis/apt_evaluation_praxis.docx), [PDF](measurement_praxis/apt_evaluation_praxis.pdf), [evidence index](measurement_praxis/EVIDENCE_INDEX.md). Includes the complete retrospective paired reanalysis and independently verified benchmark-support audit.

This completed development batch follows the two requested method ideas and the attached recommendation to study evaluation itself. Each experiment has its own number, frozen protocol, source, actual outputs, and interpretation. The studies produced measurable tradeoffs and an evaluation finding; they did not establish a novel superior detector.

| ID | Question | Initial evidence scope |
|---|---|---|
| PX-080 | Can a learned selector recognize when historical context increases attack-stage errors? | Forward training and later-period development on qualified UNRAVELED data; missing and misleading context interventions. |
| PX-081 | Can selecting extra evidence reduce stage errors under acquisition limits? | Offline replay with declared simulated costs, delays, and unavailable evidence. |
| PX-082 | How much do time-mixed training and ordinary row splits change measured stage recognition? | Same-anchor and conventional random-versus-temporal comparisons, with explicit duplicate and class-support audits. |
| PX-083 | Can a CasinoLimit-trained selector transfer between native experts on CAM-LDS? | Secondary T1105 score-policy replication across all 21 views per dataset; the base models do not transfer. |
| [PX-084 / D1](d1_benchmark_audit/README.md) | Can the temporal audit and paired stage/warning measures be extended to four requested APT releases? | Preregistered core and completed data/support qualification; no new fits, and no source yet qualifies for the unchanged temporal comparison. |

## Results in plain language

- **History selection:** weighting important stages recovered more movement labels than ordinary gating in all five conditions, but also produced more false alerts and worse weighted errors. Current evidence alone still had higher movement recall.
- **Evidence acquisition:** clean maximum-budget simulated spending fell 32.24% against entropy selection, but detection was not consistently better. Some improved F1 scores accompanied fewer exfiltration cases recognized as any attack.
- **Temporal evaluation:** using later training examples raised macro-F1 by .0632 or .0383 on the same evaluation rows, depending on features. This demonstrates evaluation sensitivity, not a usable deployment gain.
- **Policy transfer:** at the fixed threshold, weighted gating reproduced the context expert's decisions across all 42 views. It did not add a useful transferred decision rule.

The bounded positive chronological comparison in PX-082 improved macro-F1 from .7365 to .7582 and reduced mean benign false alerts from 24.0 to 14.3 with history. It also increased exfiltration-to-benign mistakes in every seed. There is no across-metric winner.

## Paper and evidence

[Full manuscript](paper/manuscript.md) | [Word paper](paper/historical_context_praxis.docx) | [PDF paper](paper/historical_context_praxis.pdf)

[PX-080 results](px080_context_selector/results/REPORT.md) | [PX-081 results](px081_evidence_acquisition/INTERPRETATION.md) | [PX-082 results](px082_temporal_audit/REPORT.md) | [PX-083 results](px083_policy_transfer/README.md)

The existing UNRAVELED artifact contains 382,229 flows from one previously examined campaign. Its author-defined movement stage is Remote System Discovery; its exfiltration labels do not independently verify stolen files. These experiments are development studies, not new independent campaign confirmation or exfiltration forecasting. Full current-flow statistics are available only after the flow; no early-warning result is claimed.

The 143 new lightweight model fits ran locally on CPU. AWS was used for a separately bounded new-data acquisition and qualification attempt after authentication succeeded; see the [compute record](compute/README.md) for actual outcomes and verified shutdown. No GPU acceleration is claimed for these fits.

See [attachment assessment](ATTACHMENT_ASSESSMENT.md), [registry](REGISTRY.json), and each experiment directory. Scientific evidence is preserved regardless of result direction. No historical experiment is overwritten.

The [D1 extension](d1_benchmark_audit/README.md) develops the measurement-praxis contribution. It keeps the completed four studies intact, verifies the proposed dataset expansion and documents actual support limitations before any new model training. Paired warning/stage reporting uses established metrics; the contribution being developed is the controlled evidence and reproducible audit.
