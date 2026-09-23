# Praxis opportunities after the context experiments

**Research review: September 23, 2026.** Main literature window: September 23, 2024 through September 23, 2026. This is a bounded primary-source review and research recommendation, not a systematic review, novelty certificate, new experimental result, or guarantee of publication. No models were fitted for this review.

## Recommendation in plain language

The strongest near-term candidate is **learning when historical context helps an attack-stage decision and when to ignore it**. Our work supplies a concrete failure to investigate: contextual information can improve one score while hiding movement, and a model can learn a repeated workflow rather than recognize the current operation. A publishable contribution would require a specific remedy and stronger evaluation, not merely another ensemble.

Proposed title: **Preserving APT Stage Detection When Historical Context Becomes Unreliable**.

Proposed research question: **Can a model estimate the additional error caused by historical context and use current evidence or request review when that context becomes misleading, preserving movement and exfiltration recognition under changed workflows and missing logs?**

The documented literature problems are incomplete provenance, uneven operational generalization, and benchmark shortcuts. The specific conditional-history remedy below is **our research synthesis**; the cited authors do not establish that it is an untouched topic.

## What the completed work contributes

| Actual finding | Research implication | Limit |
|---|---|---|
| Stage-specialist averaging raised lateral-stage F1 from 0.6111 to 0.6327, while lateral any-attack recall slipped slightly. | Overall improvements can conceal harm to an operationally important stage. | Previously exposed SCVIC development rows; no temporal forecasting. |
| Authentication context raised movement recall from 40.00% to 58.10% against matched context, with false alerts rising from 46 to 60. Traffic-only recall was 69.52%. | Added information is useful conditionally, not uniformly. | Only 35 discovery-labeled movement flows, one campaign; Windows context excluded. |
| The controlled lab reached 1.000 macro-F1 on deliberately repeated workflows, matching a simple rule; complete-crossing F1 changed from 0.4288 to 0.4167. | Test the dependence on historical correspondence explicitly. | Harmless process transactions; the complete crossing deliberately makes prior/current requests independent. It does not prove that enterprise history is useless. |

Evidence: [stage ensemble](../exfil_stage_experiments/INTERPRETATION.md), [authentication study](../host_auth_context/README.md), [controlled lab](../verified_stage_lab/README.md). None measured detected lateral movement as a predictor of future exfiltration.

## Recent literature: problems and prior art

| Primary source and status | Relevant finding or method | Consequence for this praxis |
|---|---|---|
| Bilot et al., **Sometimes Simpler is Better**, USENIX Security 2025, peer reviewed. [Paper](https://www.usenix.org/conference/usenixsecurity25/presentation/bilot) | Unified eight PIDS implementations; simple models can compete with complex graph systems, and evaluation/design shortcomings affect practical use. | Include strong simple controls and a measured operational objective. A new architecture alone is insufficient. |
| Kimm, Mishra, and Sekar, **Minding the Gap**, PRISM 2026 workshop, peer reviewed. [Paper](https://www.ndss-symposium.org/wp-content/uploads/prism2026-23.pdf) | Documents missing, spurious, and disordered provenance; IMPROV repairs collection context through OS information. | Missing evidence is a documented issue. Our target would be decision behavior when evidence remains unreliable, not a claim to invent provenance repair. |
| Meng et al., **KnowHow**, NDSS 2026, peer reviewed. [Paper](https://www.ndss-symposium.org/wp-content/uploads/2026-s199-paper.pdf) | Maps CTI knowledge to low-level events and reasons over attack steps; missing critical stages or ordering violations affect confidence. | Temporal/semantic APT reasoning already exists. Test skipped steps and delayed evidence; do not assume this prior system fails those conditions. |
| Phan and Bauschert, **StageFinder**, March 2026 preprint, revised May 5; authors report GLOBECOM 2026 acceptance. [Paper](https://arxiv.org/abs/2603.07560) | Fuses provenance structure and temporal modeling for attack-stage estimation. | Generic host/network/history fusion is occupied. Stage estimation must remain distinct from future-stage forecasting. |
| **DAPNet**, Expert Systems with Applications, 2026 publisher record; abstract-level review. [Publisher](https://www.sciencedirect.com/science/article/abs/pii/S0957417425045087) | Uses learned gating among temporal, cross-variable, and hybrid experts. | An ordinary learned expert gate is a required comparator, not a novelty claim. Full-text access limits the completeness of this comparison. |
| Nweke, **Tail-calibrated mixture of experts**, Discover Computing, July 11, 2026, peer reviewed. [Paper](https://link.springer.com/article/10.1007/s10791-026-10343-2) | Combines availability, integrity, and timing evidence at low false-alarm operating points. | Expert fusion and false-alarm calibration are existing methods. Its substation task differs from movement/exfiltration recognition. |
| Guney et al., **Active feature acquisition via explainability-driven ranking**, ICML 2025, peer reviewed. [Paper](https://proceedings.mlr.press/v267/guney25a.html) | Learns a sequential acquisition policy from instance-specific explanatory rankings. | Useful recent method for an evidence-selection comparison; generic adaptive acquisition is not new. |
| Norcliffe et al., **Stochastic Encodings for Active Feature Acquisition (SEFA)**, ICML 2025, peer reviewed. [Paper](https://proceedings.mlr.press/v267/norcliffe25a.html) | Models complementary evidence that greedy acquisition can miss; its formulation assumes features can eventually be acquired under a feature-count budget. | A useful modern comparator for evidence selection; operational availability and deadline constraints require additional evaluation. |
| Kobayashi et al., **Learning-To-Measure**, October 2025 preprint, revised May 31, 2026; listed in the official ICML 2026 poster program. [Full text](https://arxiv.org/html/2510.12624v2), [conference listing](https://icml.cc/virtual/2026/poster/63119) | Sections 3 and 6 assume time-invariant features and uniform costs; future work includes time-varying dynamics and fuller cost-sensitive planning. Missing-data identification also depends on MAR and coverage assumptions. | This supplies an explicit recent ML limitation, but a cyber extension must also confront existing budgeted logging systems. Do not claim to solve arbitrary missingness. |
| Basak and Shin, **A Framework for Budget-Constrained Zero-Day Cyber Threat Mitigation**, Sensors 26(1),21, published December 19, 2025, peer reviewed. [Paper](https://www.mdpi.com/1424-8220/26/1/21) | Sim-CTKG chooses logging/sensing actions under resource and latency constraints with knowledge-guided reinforcement learning. | Choosing the next log source under a budget already has direct cyber prior art. Actual arrival variation and stage-specific error are narrower possible extensions. |
| **GridPRISM**, International Journal of Critical Infrastructure Protection 53, July 2026 issue. [Publisher](https://www.sciencedirect.com/science/article/pii/S1874548226000211) | Budgets provenance expansion and evidence selection. | Evidence budgeting itself cannot be the contribution; distinguish obtaining missing evidence from selecting evidence already stored. |
| **APTStop**, IEEE Access, October 21, 2025, peer reviewed. [Paper](https://ieeexplore.ieee.org/abstract/document/11214142/) | Forecasts subsequent attacker behavior within a detection/prediction/response framework. | Generic next-attack forecasting is already published. A new study needs a specific forecast target, operating costs, and independent episodes. |
| Guerra et al., **How Benchmarks and Evaluation Protocols Shape Conclusions in PIDS**, August 2026 preprint, revised September 9; authors report NDSS 2027 acceptance. [Paper](https://arxiv.org/abs/2608.01454) | On four primary datasets, simple executable-name/path allowlists match or exceed selected learned baselines on key operating-point metrics. | Merely reporting chronological splits or lexical shortcuts is already covered. Our study needs a specific additional failure and remedy. |

Additional boundaries: [ProvX, USENIX Security 2026](https://www.usenix.org/conference/usenixsecurity26/presentation/wu-weiheng) already studies counterfactual core edges for actionable alerts. [CAM-LDS, IJIS 2026](https://link.springer.com/article/10.1007/s10207-026-01318-x) explicitly discusses preceding-step context and label/benign-workload limitations. These are useful motivations, not unoccupied broad contributions.

## Candidate 1: learn when history makes a stage decision worse

**Priority: first. Novelty potential: plausible and narrow; unestablished. Feasibility: development pilot possible, independent confirmation still required.**

Use a current-evidence model and a context-assisted model. On held-out training folds, compare their stage-specific errors. Train a selector to estimate whether adding history will help, using observable evidence age, coverage, disagreement, and current-event features. At inference, labels and completion receipts are unavailable to the selector. It may use context, retain the current-evidence decision, or return an unresolved review case.

The proposed distinction is the **estimated harm caused by context for a particular stage**, trained and tested against workflow changes. This must demonstrate value beyond an ordinary confidence/MoE gate; a different name for learned weighting is insufficient. No mathematical no-harm guarantee is asserted.

Recent model option: [TabM, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/c1ba41c694834aeef91ae161711d4939-Abstract-Conference.html), an efficient ensemble-like tabular neural model. Use it as a tested component alongside boosted trees, not the novelty headline. [Official code](https://github.com/yandex-research/tabm).

Minimum comparison: current only; fixed fusion; ordinary learned gate; confidence gate; missingness-aware/context-dropout training; proposed context-harm selector. Keep fitting data, information, tuning budget, false-alert operating points, and review allowance matched. Hold out whole executions/workflow families. Report per-stage F1/AP/recall, missed dangerous actions, false alarms, unresolved cases, and clean-condition costs. Do not assume a missing channel is recoverable or count abstention as a correct classification.

**Data gate:** usable current evidence must distinguish the target actions in at least some cases. Our previous dummy lab deliberately removed decisive current information; no selector can reconstruct information absent from every input. UNRAVELED supports development only, with its existing label/clock limits. Full movement-versus-exfiltration confirmation requires qualified new executions.

## Candidate 2: choose the next evidence that resolves a stage disagreement

**Priority: second, as an extension. Novelty potential: conditional; substantial direct overlap.**

Plain-language example: network traffic is consistent with both remote administration and file transfer. Decide whether a session record, process event, or file-access record is the most useful next observation, accounting for its cost and whether it will arrive before the decision deadline.

A possible method extension replaces generic uncertainty reduction with expected reduction in **stage-specific decision error**, and handles grouped queries, unequal costs, late arrivals, and permanently unavailable evidence. This is a proposed adaptation of existing acquisition ideas, not the invention of budgeted logging. L2M's explicit static-feature limitation motivates the dynamic setting; Sim-CTKG and GridPRISM must be included in the related-work comparison.

Start with fixed-order, random, greedy information-gain, ICML-2025 acquisition, all-evidence and no-additional-evidence controls. Record what was available at every decision. Charge unsuccessful or late queries where appropriate. Measure stage errors at the same resource budget and deadline; disclose simulated costs/delays as simulated. Feature values, SHAP rankings, and labels hidden from a query policy must not leak in at test time.

An offline replay is feasible only after channel joins are qualified. It does not establish real collection overhead or live early warning. A full method claim needs validation with measured acquisition behavior.

Implementation options are the author releases for [explainability-driven acquisition](https://github.com/vkola-lab/icml2025), [SEFA](https://github.com/a-norcliffe/SEFA), and [L2M](https://github.com/reAIM-Lab/Learning-To-Measure). These are alternative methods for this one research question. L2M's training code is public, but a ready checkpoint was not verified; its pretraining makes it a larger implementation than the first two. The literature-gap statement for Candidate 2 is more explicit than for Candidate 1; its data and acquisition-infrastructure requirements are also greater. Candidate 1 is ranked first for continuity and practical testability, not because its novelty is already established.

## Candidate 3: forecast exfiltration from detected movement and intervening activity

**Priority: later. Operational value: high. Current confirmation readiness: insufficient.**

Example target: probability of verified exfiltration onset during the next 5, 15, or 30 minutes, using only evidence available now. These are illustrative horizons to choose before testing, not literature standards.

Use predicted movement evidence, sensitive-resource access where observable, and subsequent activity. Compare simple conditional-risk/transition rules, logistic or boosted models, temporal models, and a time-to-event model that represents an attack ending or observation ending without exfiltration. APTStop and earlier forecasting systems are direct prior art.

The proposed contribution would be calibrated, bounded-horizon warning under missing evidence with cases that never progress to exfiltration. Evaluate missed episodes, false warnings per monitored host-time, calibration and warning lead time. Include detector errors rather than supplying true stage labels. Keep all post-onset exfiltration statistics out of predictors.

Our currently qualified data do not supply enough independently verified positive and negative progression episodes. Millions of flows from one campaign cannot substitute for independent campaigns. This is not the fastest route to a defensible paper today.

## Data options checked today

| Source | Current status | Permitted next use |
|---|---|---|
| Existing SCVIC / UNRAVELED | Available, already examined; existing stage, chronology and clock limitations remain. | Development baselines and controlled ablations; not fresh confirmation. |
| [ProvICS, July 2026 preprint](https://arxiv.org/abs/2607.05989), [author release](https://huggingface.co/datasets/trucyberlab/multimodal-ICS-provenance) | Lists host/PLC/protocol/physical modalities, 48 benign hours and one 22-hour attack recording with four scripts. Small ground truth was accessible; full signal acquisition unverified. | Conditional pilot for ICS phase/context fusion. This changes the application scope; it does not validate enterprise exfiltration forecasting. |
| [Windows-APT2025 paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12950481/), [July 2026 artifact](https://data.mendeley.com/datasets/b8fmtzvpy8/4) | Peer-reviewed dataset description; acquisition/run grouping still to qualify; released telemetry lacks observable exfiltration. | Conditional movement study, not future-exfiltration confirmation. |
| [LMDG 2025](https://arxiv.org/abs/2508.02942), [LMTrace](https://github.com/WASPLab/LMTrace) | Promising published description, but linked repository currently empty. | Literature only until an actual licensed release is available. |
| [KIT MasterCyberrange, October 2025](https://radar.kit.edu/radar/en/dataset/pr9mkg4tmm0m50ab) | Thesis-associated 6 GB archive, two repetitions of a chain; collection failures limit coverage. | Conditional external case study; not broad independent confirmation. |
| [PIDSMaker](https://github.com/ubc-provenance/PIDSMaker) | Public framework linked to recent peer-reviewed PIDS work. | Strong comparison infrastructure for a provenance-detection scope; attack-stage mappings and subset suitability still require qualification. |

**ProvICS annotation finding:** its released C4 record describes failed credential retrieval in a lateral-movement interval and a skipped impact step. The 32 labeled intervals therefore cannot automatically be interpreted as 32 successful actions. See the [source CSV](https://huggingface.co/datasets/trucyberlab/multimodal-ICS-provenance/resolve/main/attack22h/ground_truth/c4_ground_truth.csv). Distinguish attempted/completed/skipped outcomes before fitting; do not rename failed attempts as benign. Its license badge and access/reuse wording should be preserved and resolved before redistribution.

## Concrete next decision

Proceed toward Candidate 1, with a data qualification milestone before another large fitting batch. Define one attack-stage target, identify observable current evidence and context, and count independent successful/failed/benign executions. If the usable new data support ICS phases or movement-only analysis, name that narrower scope explicitly.

Freeze simple and learned-gate controls, train the context-harm selector without test labels, then measure paired clean/shifted performance on held-out executions. Advance to Candidate 2 only if missing information, rather than model choice, remains the demonstrated bottleneck. Keep Candidate 3 behind its independent-episode gate.

A paper from the existing results can document stage tradeoffs and workflow shortcuts, but related 2025–2026 evaluation papers make a generic benchmark critique a crowded contribution. A stronger method paper requires a reproducible improvement on the narrow question above, with its operational cost and limits visible.
