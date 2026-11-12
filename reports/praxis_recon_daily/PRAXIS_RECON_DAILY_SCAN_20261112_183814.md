# Praxis Recon Daily Literature Scan

Generated: 2026-11-12 18:38 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 6

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 10 | Cyber threat intelligence evidence routing | 2026-11-10 | Forensiq - Intelligent Security Operations & Investigation Platform | International Journal of Innovative Research in Engineering | [source](https://doi.org/10.59256/ijire.20260706006) |
| 2 | 8 | Adaptive evaluation of deterministic agent defenses | 2026-11-10 | Surveying cyber-physical honeynets: Realism, attractiveness, and emerging applications | Journal of Information Security and Applications | [source](https://doi.org/10.1016/j.jisa.2026.104698) |
| 3 | 8 | Provenance-aware tool-boundary monitoring | 2026-11-10 | When Does Hallucination Propagate? Reconciling Six Formalizations of Error Spread in Multi-Agent LLM Systems | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11536507/v1) |
| 4 | 7 | Source-locked citation and hallucination verification | 2026-11-11 | Evaluating AI performance on end-to-end data science projects | PLoS ONE | [source](https://doi.org/10.1371/journal.pone.0361887) |
| 5 | 6 | Provenance-aware tool-boundary monitoring | 2026-11-10 | The architecture of Responsible Autonomy in biological and artificial systems: the Distributed Adaptive Control of volition and agency | Philosophical Transactions of the Royal Society B Biological Sciences | [source](https://doi.org/10.1098/rstb.2025.0156) |
| 6 | 2 | Cyber threat intelligence evidence routing | 2026-11-10 | Next-Generation Cyber Defense Powered by Graph-Based Threat Intelligence and Automated Attack Path Analysis | International Journal of Technology Management and Humanities | [source](https://ijtmh.com/index.php/ijtmh/article/view/522) |

## Triage Notes

### 1. Forensiq - Intelligent Security Operations & Investigation Platform

- Topic: Cyber threat intelligence evidence routing
- Authors: Kumbhar Ayush Shankar, Patil Sharayu Nilesh, Patil Sakshi Chandrakant, Anil Morti Sakshi, et al.
- Published: 2026-11-10
- Venue/type: International Journal of Innovative Research in Engineering / article
- DOI: https://doi.org/10.59256/ijire.20260706006
- URL: https://doi.org/10.59256/ijire.20260706006
- Opportunity score: 10
- Matched tags: MITRE ATT&CK, agent, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Security Operations Centers process security alerts from many different systems. Analysts must match events gather evidence add data and evaluate risk before deciding. Forensiq is a platform that uses AI agents to help with these tasks. It works inside Splunk. Handles alert ingestion, event exploration, alert triage, threat-intelligence enrichment of indicators of compromise, mapping to MITRE ATT&CK correlating events calculating risk reasoning through investigations checking claims with facts and producing reports for analysts. A multi-agent design splits the work into tasks but the original data stays for analysts to check. Tests will look at how alerts are sorted how well ATT&CK mapping works how much threat data is added, how well evidence supports claims how many unsupported claims appear, how good event correlation is, how efficient investigations become, how good reports are and how the system scales. The final test will compare the Forensiq workflow to a baseline under the same data. Forensiq is meant to help analysts; the system gives reasoning support. Does not replace human checking and response decisions.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Surveying cyber-physical honeynets: Realism, attractiveness, and emerging applications

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Mathis Durand, Yvon Kermarrec, Marc‐Oliver Pahl
- Published: 2026-11-10
- Venue/type: Journal of Information Security and Applications / article
- DOI: https://doi.org/10.1016/j.jisa.2026.104698
- URL: https://doi.org/10.1016/j.jisa.2026.104698
- Opportunity score: 8
- Matched tags: evaluation, future research, safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Cyber-physical systems play a central role in critical infrastructures, particularly in power plants, factories, and water treatment facilities. These systems face increasingly sophisticated threats that can have severe operational and societal consequences. A Cyber-Physical Honeynet (CPHoneynet) is a network of honeypots designed to replicate the operation of a real cyber-physical environment. When attackers interact with it, a CPHoneynet enables the collection of valuable threat intelligence regarding attacker methods, tools, and attack vectors. The domain lacks a recent and comprehensive structuring. Therefore, this survey identifies, reviews, and analyzes the central publications published between 2010 and June 2026 through a Systematic Literature Review methodology. The survey analyzes 451 publications and focuses on three major themes: realism, attractiveness, and emerging applications of CPHoneynets. The analysis reveals that IoT and ICS are the dominant application domains, realism remains the primary research challenge, and attractiveness remains comparatively underexplored despite its direct impact on threat-intelligence collection. The survey synthesizes a reference architecture, proposes a comprehensive taxonomy, and identifies evaluation metrics for both realism and attractiveness. It further highlights emerging directions such as Artificial Intelligence, Digital T

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. When Does Hallucination Propagate? Reconciling Six Formalizations of Error Spread in Multi-Agent LLM Systems

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Shaoxuan Zhang
- Published: 2026-11-10
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11536507/v1
- URL: https://doi.org/10.21203/rs.3.rs-11536507/v1
- Opportunity score: 8
- Matched tags: agent, hallucination, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Multi-agent LLM systems are deployed on the assumption that agents checking one another reduce hallucination. Two studies of the same linear topology contradict it in opposite directions, and both are right: one measures prevalence, the other detectability, and a claim can become rarer and less visible at once. Whether a false claim grows is set by two structural variables: how correlated the agents' errors are, and whether any channel supplies evidence independent of them. Topology bounds the number of carriers a chain can produce; it says nothing about the other channel. Six formalisms proposed in the past year describe this process. Each defines a state space, a transition rule and a measurable quantity; none is stated in terms another can absorb. Taking the travelling claim as the unit of analysis, we show that the six are projections of one process onto different observables. In a purposive sample of 42 papers, 10 of 32 included studies report a propagation-level metric, 9 report a verification channel independent of the agents, and 7 report a graph with a recoverable out-degree. The two features never co-occur: all nine studies with such a channel report attenuation, and both studies that report amplification lack one. One prediction runs against design intuition: raising the initial diversity of agents' answers increases false adoption. We specify the experiment

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 4. Evaluating AI performance on end-to-end data science projects

- Topic: Source-locked citation and hallucination verification
- Authors: Evelyn Hughes, Rohan Alexander
- Published: 2026-11-11
- Venue/type: PLoS ONE / article
- DOI: https://doi.org/10.1371/journal.pone.0361887
- URL: https://doi.org/10.1371/journal.pone.0361887
- Opportunity score: 7
- Matched tags: dataset, evaluation, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Generative AI is used for knowledge work but many current AI evaluations focus on isolated tasks and constituent parts such as writing code, rather than end-to-end workflows. We test whether AI models can generate end-to-end data science projects. This requires AI models to select a dataset, develop a research question, write code to download, clean, and test data, create figures, and write a reproducible paper. To do this we collect 40 real end-to-end data science projects, then grade them according to a rubric. We use these to build an automated grading pipeline that evaluates data science projects and aligns with the grades that human graders give. For each of nine AI models we then generate five projects and use the automated grader to evaluate them. We find the extent to which generative AI models can complete end-to-end data science projects varies considerably by model. Most recent models did well on structured tasks, but there were considerable differences on tasks that needed judgment such as explaining measurement, writing abstracts, and citing sources. Anthropic’s Claude Opus 4.8 averaged 87 per cent and OpenAI’s GPT-5.4 averaged 85 per cent, both around the level of an A for an undergraduate. No model was consistently the best across all aspects of the rubric. These findings suggest that while AI models could soon approximate entry-level data scientists on routine t

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 5. The architecture of Responsible Autonomy in biological and artificial systems: the Distributed Adaptive Control of volition and agency

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Paul F. M. J. Verschure
- Published: 2026-11-10
- Venue/type: Philosophical Transactions of the Royal Society B Biological Sciences / article
- DOI: https://doi.org/10.1098/rstb.2025.0156
- URL: https://doi.org/10.1098/rstb.2025.0156
- Opportunity score: 6
- Matched tags: agent, evaluation, safety
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> This paper proposes the Distributed Adaptive Control theory of volition and agency (DACva), which parses biological and artificial free will into six capacities that close the agency gap between a reflex and an act: active decoupling, endogenous drive, leeway, normative self-governance, diachronic integrity and experiential ownership. Together they constitute Responsible Autonomy. The DACva architecture spans five layers, somatic to reflective, coordinated by a decoupled model-predictive controller, the compression-expansion-selection-projection (CESP) cascade. It constructs, rather than presupposes, the causal models counterfactual control requires, under the evolutionary pressure of survival in social worlds pervaded by hidden intentional states. The computational principles and neurobiological substrate of DACva are specified in a 12-equation formalism, with an assay and a refutation condition for each capacity. The formalism closes on one equation, the CESP cascade, and yields an explicit definition of freedom: the degree to which an act is the committed trajectory of the agent's own cascade, read on six conditions, one per capacity. From this follows the Evaluation Suite for Responsible Autonomy (ESRA), a perturbational test of architectural competence rather than mimicry, proposed to replace the imitation game; ESRA-S assesses the safety constraints a deployer of AI must 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 6. Next-Generation Cyber Defense Powered by Graph-Based Threat Intelligence and Automated Attack Path Analysis

- Topic: Cyber threat intelligence evidence routing
- Authors: Amit Kumar Jain
- Published: 2026-11-10
- Venue/type: International Journal of Technology Management and Humanities / article
- DOI: not provided
- URL: https://ijtmh.com/index.php/ijtmh/article/view/522
- Opportunity score: 2
- Matched tags: security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> The increasing complexity of modern cyber threats, distributed enterprise infrastructures, and interconnected digital environments has created significant challenges for conventional cybersecurity defense mechanisms. Traditional security solutions often operate independently, making it difficult to identify relationships between vulnerabilities, malicious activities, compromised assets, and potential attack routes. This research proposes a next-generation cyber defense framework powered by graph-based threat intelligence and automated attack path analysis to improve enterprise cybersecurity capabilities. The proposed framework integrates security event monitoring, threat intelligence enrichment, graph-based knowledge representation, vulnerability correlation, and automated attack path identification. Graph structures are utilized to represent relationships among users, devices, applications, network resources, vulnerabilities, and threat indicators, enabling security analysts to identify complex attack patterns across distributed environments. Automated graph traversal and risk assessment mechanisms prioritize critical attack paths based on vulnerability severity, asset importance, threat activity, and potential business impact. The framework further incorporates machine learning techniques to improve threat classification and predictive attack detection. By combining contextua

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

