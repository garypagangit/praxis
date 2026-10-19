# Literature supporting Identifying Autonomous AI APT

**Reviewed:** October 19, 2026. [Project tracker](PRAXIS_STATUS_TRACKER.md) · [Research design](PRAXIS_RESEARCH_DESIGN.md)

This is a selected reading list for the problem statement, proposed contribution and RQ1–RQ3. Sources are linked to their original document or official record. Industry reports provide operational context; academic studies provide research comparisons; software documentation supports implementation. Those roles are not interchangeable. Publication dates below come from the source records; undated documentation is labeled accordingly.

## The strongest reference for explaining the proposed novelty

**Start with L01: Ashley Alt, _Beyond Anomaly Detection_ (April 2026).** Its human/automation/AI-assisted behavioral classification task is the closest starting comparison in this selected set. The proposed extension is a matched human-versus-autonomous-AI experiment using multi-host target-side host and network evidence, with explicit transfer and shortcut tests.

**This is our gap inference from the compared study designs.** Alt does not certify this Praxis as novel. L02 and L03 are essential counterchecks because autonomous-agent detection and AI-family fingerprinting already exist. A contribution claim must explain what the combined design adds and then deliver evidence. Simply using XGBoost, features or a transformer is not the novelty.

### Proposed contribution wording

This Praxis evaluates whether behavioral attributes in matched multi-host target-side telemetry distinguish human operators from autonomous AI agents and remain useful on unseen operators and AI configurations after timing and tool-related shortcuts are controlled. Its proposed contribution is the controlled dataset, transferable feature evidence and reproducible comparative evaluation in this setting.

Use “proposed” until the experiments are complete. Do not claim the first AI attacker detector, universal APT attribution, or demonstrated operational benefit from this literature review alone.

## Closest research and novelty comparison

| ID / role | Title | Author(s) | Publication date | Document | Why it matters to this Praxis |
| --- | --- | --- | --- | --- | --- |
| **L01 — PRIMARY NOVELTY COMPARISON; research gap; RQ1/RQ3** | Beyond Anomaly Detection: Classifying Attacker Automation Level from SSH Honeypot Behavioral Signatures | Ashley Alt | April 2026 | [RIT thesis record and download](https://repository.rit.edu/theses/12605/) | Studies human, conventional automation and AI-assisted behavior in a Cowrie SSH setting using session features and multiple classifiers. Establishes relevant prior work; motivates testing the different autonomous, multi-host and transfer setting proposed here. The reviewed abstract does not establish our contribution's uniqueness. |
| **L02 — PRIOR AUTONOMOUS-AGENT DETECTION; problem gap; RQ1/RQ2** | LLM Agent Honeypot: Monitoring AI Hacking Agents in the Wild | Reworr; Dmitrii Volkov | October 17, 2024; revised February 10, 2025 | [Paper and PDF](https://arxiv.org/abs/2410.13919) | Uses an SSH honeypot with timing analysis and prompt injection to identify potential LLM agents. Motivates a timing baseline and shows that autonomous-agent detection is already a research topic. Our passive target-side, controlled comparison asks a different question. Potential agents observed in the wild are not equivalent to verified matched-trial ground truth. |
| **L03 — GENERALIZATION / FINGERPRINTING COUNTERCHECK; RQ2** | Trace: Unmasking AI Attack Agents Through Terminal Behavior Fingerprinting | Murali Ediga; Sudipta Chattopadhyay | May 2, 2026 | [Paper and PDF](https://arxiv.org/abs/2605.01186) | Attributes terminal behavior to attacker AI model families. Reported macro-F1 falls from 0.981 to 0.815 under unseen scaffolds. Supports testing whether attributes transfer or instead reveal model/scaffold identity. Its main prediction target is AI family, whereas ours is human versus autonomous AI. |

### Evidence needed to establish the extension

| Proposed distinction | Closest comparison | Evidence this project must produce |
| --- | --- | --- |
| Matched human versus autonomous-AI trials | L01's human/automated/AI-assisted classification | Verified autonomy, shared access conditions, intervention records and independent human trial groups |
| Combined multi-host target-side evidence | L01/L02 SSH settings; L03 terminal behavior | Validated host/network coverage, reproducible feature definitions and host-only/network-only/combined ablations |
| Generalization beyond attacker model or scaffold details | L03 explicitly studies family/scaffold behavior | Reserved human and AI groups, appropriate family/configuration distinctions, nuisance controls and uncertainty |
| Robustness beyond timing and tool signatures | L02 timing methods; L01 behavioral families | Explicit timing-derived and tool-derived feature removal, paired results and qualified limits |

This matrix describes planned differences, not completed findings. The literature search is focused rather than exhaustive; full-text comparison and continued overlap checks remain part of tracker P06.

## References that make up the problem statement

**Use L04 for evidence that AI can execute substantial attack activity; L05 for growth in observed AI-enabled attacks; L06 for general breach-cost context. Use L01–L03 for the research gap.** The three industry reports alone do not prove that defenders cannot distinguish human and AI activity.

| ID / role | Title | Author(s) | Publication date | Document | Why it matters and claim boundary |
| --- | --- | --- | --- | --- | --- |
| **L04 — PROBLEM: real-world AI-orchestrated activity** | Disrupting the first reported AI-orchestrated cyber espionage campaign | Anthropic | November 13, 2025; announcement corrected November 14, 2025 | [Official report announcement](https://www.anthropic.com/news/disrupting-AI-espionage) · [Report PDF](https://assets.anthropic.com/m/ec212e6566a0d47/original/Disrupting-the-first-reported-AI-orchestrated-cyber-espionage-campaign.pdf) | Provides a provider-reported case of largely AI-executed espionage with human direction at some decisions. Supports motivation to study operator attribution. It is a case report, not a population prevalence estimate or validation of a defender-side classifier. |
| **L05 — PROBLEM: growth of AI-enabled attacks** | 2026 CrowdStrike Global Threat Report; accompanying findings article, The Evasive Adversary Wields AI | CrowdStrike; findings article by Adam Meyers | February 24, 2026 | [Official report release](https://www.crowdstrike.com/en-us/press-releases/2026-crowdstrike-global-threat-report/) · [Author's findings article](https://www.crowdstrike.com/en-us/blog/crowdstrike-2026-global-threat-report-findings/) | Reports an 89% increase in observed attacks by AI-enabled adversaries compared with 2024. Supports operational urgency. It does not establish 89% growth in autonomous APT actors or fully autonomous campaigns. |
| **L06 — PROBLEM: economic stakes, contextual only** | Cost of a Data Breach Report 2025 | IBM; research conducted by Ponemon Institute | July 30, 2025 release | [Official release and report access](https://newsroom.ibm.com/2025-07-30-ibm-report-13-of-organizations-reported-breaches-of-ai-models-or-applications,-97-of-which-reported-lacking-proper-ai-access-controls) | Reports average breach costs of $4.44 million globally and $10.22 million in the United States. Provides broad economic context; these are not autonomous-AI/APT-specific costs and do not quantify benefits of this proposed classifier. |

### Supported problem-statement formulation

AI-orchestrated cyber operations have been reported by Anthropic [L04](https://www.anthropic.com/news/disrupting-AI-espionage), and CrowdStrike reports increased attacks by AI-enabled adversaries [L05](https://www.crowdstrike.com/en-us/blog/crowdstrike-2026-global-threat-report-findings/). Existing studies investigate SSH attacker classification, potential LLM-agent detection and AI-family fingerprinting [L01](https://repository.rit.edu/theses/12605/), [L02](https://arxiv.org/abs/2410.13919), [L03](https://arxiv.org/abs/2605.01186). This Praxis therefore asks whether target-side host and network behavior can reliably distinguish human from autonomous-AI operators in matched multi-host trials and transfer to unseen operators/configurations. The open question is our synthesis of the compared settings, not a claim that these authors prove detection impossible.

**Optional economic-context sentence:** IBM's 2025 study reports average breach costs of $4.44 million globally and $10.22 million in the United States; these figures concern breaches generally [L06](https://newsroom.ibm.com/2025-07-30-ibm-report-13-of-organizations-reported-breaches-of-ai-models-or-applications,-97-of-which-reported-lacking-proper-ai-access-controls).

### Corrections to carry into the next advisor/defense revision

| Wording to avoid | Source-grounded replacement |
| --- | --- |
| “Defenders cannot distinguish human from autonomous AI operators” | “Reliable attribution under the proposed matched multi-host and unseen-group conditions remains to be evaluated.” Prior detection research already exists |
| “An adversary class growing 89%” | “CrowdStrike reports 89% growth in attacks by AI-enabled adversaries compared with 2024.” |
| “Autonomous AI attacks cost $4.44 million per breach” | “IBM reports a $4.44 million global average across studied breaches.” |
| “First controlled evidence” without a qualified literature comparison | State the specific matched-data and transfer contribution being tested |
| Treating all prior work as AI-assisted rather than autonomous | Distinguish Alt's AI-assisted class from L02's autonomous-agent detection and L03's attack-agent fingerprinting |

The archived V001 presentation is unchanged. These corrections guide the working research design and the next presentation revision.

## Model selection and experimental methodology

| ID / role | Title | Author(s) | Publication date | Document | Why it matters |
| --- | --- | --- | --- | --- | --- |
| **L07 — RQ3: strong tabular baselines** | Why do tree-based models still outperform deep learning on tabular data? | Léo Grinsztajn; Edouard Oyallon; Gaël Varoquaux | July 18, 2022 | [Paper and PDF](https://arxiv.org/abs/2207.08815) | Broad benchmark evidence motivates XGBoost and random forest as serious comparators for engineered tabular telemetry. Supports fair tuning and attention to irrelevant features; does not predict a winner on this small, grouped dataset. |
| **L08 — RQ3: appropriate transformer comparator** | Revisiting Deep Learning Models for Tabular Data | Yury Gorishniy; Ivan Rubachev; Valentin Khrulkov; Artem Babenko | June 22, 2021; revised October 26, 2023 | [Paper and PDF](https://arxiv.org/abs/2106.11959) | Provides the tabular transformer approach used to define a meaningful same-input comparator. Reports no universally superior family versus boosted trees. Supports comparing architectures on the same feature table rather than confounding architecture with raw-sequence input. |
| **L09 — RQ1: feature interpretation** | Permutation feature importance | scikit-learn developers | Undated living documentation; accessed October 19, 2026 | [Official documentation](https://scikit-learn.org/stable/modules/permutation_importance) | Supports validation-based importance analysis and warns that correlated features can hide importance. Motivates feature-family ablation and careful interpretation of model reliance rather than causal claims. |
| **L10 — RQ2/RQ3: independent evaluation** | Cross-validation: evaluating estimator performance | scikit-learn developers | Undated living documentation; accessed October 19, 2026 | [Official documentation](https://scikit-learn.org/stable/modules/cross_validation.html) | Provides group-aware split methods. Supports keeping trial windows together and designing operator/configuration holdouts around the intended transfer claim. |
| **L11 — ALL RQs: leakage prevention** | Common pitfalls and recommended practices | scikit-learn developers | Undated living documentation; accessed October 19, 2026 | [Official documentation](https://scikit-learn.org/stable/common_pitfalls) | Explains preprocessing/selection leakage and training-only fitting through pipelines. Directly informs the feature-selection and tuning protocol. |

## Reading and review priority

1. **L01, L02, L03:** establish the closest prior tasks and challenge the proposed novelty.
2. **L04, L05, L06:** support the problem's operational context with correctly scoped claims.
3. **L07, L08:** justify the model comparison without promising an outcome.
4. **L09–L11:** implement reproducible feature and generalization tests.

Review basis: academic summaries use the primary institutional/arXiv records and abstracts; operational claims use official announcements/findings; methodological guidance uses official documentation. The RIT download did not resolve through the research browser, so detailed thesis limitations beyond the inspected abstract are not asserted here. Publication versions and any new competing work should be checked again before the manuscript freeze.
