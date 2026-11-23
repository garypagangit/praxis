# Praxis Recon Daily Literature Scan

Generated: 2026-11-23 22:16 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 2

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 11 | Adaptive evaluation of deterministic agent defenses | 2026-11-21 | Graph Neural Networks for Interprocedural Vulnerability Detection Using Software Dependency and Program-Flow Graphs | Kashmir Journal of Academic Research and Development | [source](https://doi.org/10.71317/kjard.2.11.2026.1093) |
| 2 | 8 | Adaptive evaluation of deterministic agent defenses | 2026-11-21 | Small Language Models as Industrial Incident Investigators: A Verifier-Checked Negative Result on a Simulated Oil-and-Gas Separator | Unknown venue | [source](https://doi.org/10.66977/xsci.2611.003k) |

## Triage Notes

### 1. Graph Neural Networks for Interprocedural Vulnerability Detection Using Software Dependency and Program-Flow Graphs

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Talha Hussain, Farhan Bashir Shaikh
- Published: 2026-11-21
- Venue/type: Kashmir Journal of Academic Research and Development / article
- DOI: https://doi.org/10.71317/kjard.2.11.2026.1093
- URL: https://doi.org/10.71317/kjard.2.11.2026.1093
- Opportunity score: 11
- Matched tags: benchmark, dataset, evaluation, future research
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Software vulnerabilities remain a critical threat to modern computing infrastructure, with reported flaws increasing annually and attack surfaces expanding rapidly through open-source ecosystems. Traditional detection approaches static rule-based analyzers, dynamic fuzzing, and symbolic execution suffer from high false-positive rates, path explosion, and poor scalability. Early machine learning methods treating code as flat token sequences fail to capture structural and semantic dependencies, experiencing severe performance degradation on realistic benchmarks. Graph Neural Networks (GNNs) have emerged as a powerful paradigm, modeling programs as structured graphs including Abstract Syntax Trees, Control Flow Graphs, Data Flow Graphs, and Program Dependence Graphs. However, most existing GNN-based detectors operate intraprocedurally, missing cross-function vulnerabilities such as buffer overflows and use-after-free that depend on interprocedural data flows. This review provides a comprehensive evaluation of GNN architectures, software dependency graph representations, and program-flow models for interprocedural vulnerability detection. We examine theoretical foundations of Code Property Graphs and System Dependence Graphs, analyze advanced architectures including relational, hyperbolic, quantum-enhanced, and hybrid language-graph models, and explore interprocedural flow mechanic

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Small Language Models as Industrial Incident Investigators: A Verifier-Checked Negative Result on a Simulated Oil-and-Gas Separator

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Mustafa S. Aljumaily
- Published: 2026-11-21
- Venue/type: Unknown venue / preprint
- DOI: https://doi.org/10.66977/xsci.2611.003k
- URL: https://doi.org/10.66977/xsci.2611.003k
- Opportunity score: 8
- Matched tags: provenance, security, verifier
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Language models are proposed for alert investigation in operational-technology (OT) security, but fluent explanations establish neither evidential fidelity nor decision reliability. We evaluate small open-weight models (Qwen2.5-1.5B, 3B and 7B) as incident investigators on a stylised two-phase oil-and-gas separator simulation, using a deterministic claim verifier with a known-true control arm and verdicts scored against simulator ground truth. On a held-out split no model exceeded an always-“attack” baseline (78% of episodes) by more than two episodes. The 1.5B and 3B models emitted one verdict almost throughout; the 7B model, given synthetic provenance, fell from 0.626 to 0.356 accuracy, treating a silent IDS as evidence of benign activity. All three models followed one injected operator note on every attack episode (69/69, 69/69, 136/136). Of the 7B model’s structured claims, 16.7% cited a nonexistent evidence item or attached a metric to the wrong item, against 1.6% for the control; a further 14.5% asserted a direction for a non-delta feature, a category the control shows to be largely a schema-use artefact. Headline defect rates on identical generations ranged from 18% to 45% depending on the counting rule. A physics-consistency twin detected weak attacks that rules and an isolation forest missed (0.983; 0.996 on independent seeds), but only while its model was nearly exact

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

