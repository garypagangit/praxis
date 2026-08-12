# Praxis Recon Daily Literature Scan

Generated: 2026-08-12 11:36 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 3

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 17 | Adaptive evaluation of deterministic agent defenses | 2026-08-10 | Development of the SecurePromptTrace Algorithm for Detecting Prompt Injection, Data Exfiltration, and Tool Misuse in Generative Artificial Intelligence Systems with Comparative Evaluation Against Keyword Filters, Classifier-Based Defenses, and Static Access Controls | International Journal of Innovative Science and Research Technology (IJISRT) | [source](https://doi.org/10.38124/ijisrt/26aug331) |
| 2 | 5 | Provenance-aware tool-boundary monitoring | 2026-08-10 | Assurance by design: embedding the SAGE Defend step in AI-integrated higher education assessment | Frontiers in Education | [source](https://doi.org/10.3389/feduc.2026.1872630) |
| 3 | 2 | Adaptive evaluation of deterministic agent defenses | 2026-08-10 | Breaking and Defending LLM-Powered Social Media Bot Detection Systems † | Pragmatic Cybersecurity | [source](https://doi.org/10.53941/pc.2026.100010) |

## Triage Notes

### 1. Development of the SecurePromptTrace Algorithm for Detecting Prompt Injection, Data Exfiltration, and Tool Misuse in Generative Artificial Intelligence Systems with Comparative Evaluation Against Keyword Filters, Classifier-Based Defenses, and Static Access Controls

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Praise Elojo Attah, Lawrence Anebi Enyejo
- Published: 2026-08-10
- Venue/type: International Journal of Innovative Science and Research Technology (IJISRT) / article
- DOI: https://doi.org/10.38124/ijisrt/26aug331
- URL: https://doi.org/10.38124/ijisrt/26aug331
- Opportunity score: 17
- Matched tags: agent, alignment, evaluation, provenance, security, tool call
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Generative artificial intelligence systems increasingly operate as autonomous agents capable of retrieving external information, accessing confidential resources, invoking application programming interfaces, and executing consequential actions. These capabilities introduce substantial security risks because malicious instructions embedded in user prompts, retrieved documents, webpages, emails, tool outputs, or persistent memory may alter an agent’s intended behaviour. Conventional keyword filters, standalone prompt classifiers, and static access-control mechanisms provide limited protection against semantically obfuscated attacks, multi-stage data exfiltration, manipulated tool arguments, and attacks that remain within formally permitted privileges. This paper develops SecurePromptTrace, a novel runtime security algorithm for detecting and controlling prompt injection, sensitive-data exfiltration, and tool misuse in generative artificial intelligence systems. SecurePromptTrace constructs a Dynamic Prompt Provenance Graph that represents trusted instructions, untrusted content, model-generated plans, retrieved data, confidential variables, tool calls, tool arguments, and execution outcomes as provenance-labelled nodes and causal edges. A relation-aware graph attention network analyses instruction dependencies and identifies conflicts between the authenticated user objective and 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Assurance by design: embedding the SAGE Defend step in AI-integrated higher education assessment

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Mahmoud Elkhodr, Ergun Gide
- Published: 2026-08-10
- Venue/type: Frontiers in Education / article
- DOI: https://doi.org/10.3389/feduc.2026.1872630
- URL: https://doi.org/10.3389/feduc.2026.1872630
- Opportunity score: 5
- Matched tags: security, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> This paper conceptualises the SAGE Defend step, the sixth stage of the Structured AI-Guided Education framework, as a format-agnostic assurance checkpoint for AI-integrated higher education assessment. The study responds to a verification gap identified in earlier SAGE research, in which process documentation and AI interaction logs were found to support transparency but not, by themselves, to verify individual ownership of reasoning in group-based AI-integrated submissions. Adopting a design-informed conceptual approach grounded in design-based research principles, the paper integrates a multi-year programme of empirical SAGE studies, a structured synthesis of the assurance-task literature, and diagnostic observations from three Defend-proximate assessment implementations across undergraduate and postgraduate units at Central Queensland University. It distinguishes between assurance tasks that directly require students to demonstrate reasoning or performance, controlled assurance conditions that restrict the assessment environment, and corroborative assurance signals that provide corroborating but non-stand-alone evidence. On this basis the paper proposes a three-class assurance-task typology, an epistemic matching framework, and six design principles for embedding SAGE Defend within assessment sequences. It further argues that assurance should be distributed across the assess

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Breaking and Defending LLM-Powered Social Media Bot Detection Systems †

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Yoni Birman, Nof Orenstein
- Published: 2026-08-10
- Venue/type: Pragmatic Cybersecurity / article
- DOI: https://doi.org/10.53941/pc.2026.100010
- URL: https://doi.org/10.53941/pc.2026.100010
- Opportunity score: 2
- Matched tags: security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> The rise of social media bots poses a persistent threat, enabling misinformation, public opinion manipulation, and erosion of trust in online platforms. To combat this, machine learning systems have been developed to detect and limit bot activity. However, attackers continuously adapt through adversarial optimization, behavior imitation, and semantic manipulation strategies, creating an escalating arms race with detection tools. Recent advances in LLMs have significantly improved bot detection by enabling deeper semantic and contextual analysis. However, this shift also introduces new attack surfaces, allowing adversaries to craft exploits that directly target LLM reasoning and generation mechanisms. Industry tools like Anthropic’s Claude Code Security similarly leverage LLMs for security, motivating our study of their attack surfaces. In this work, we explore both offensive and defensive aspects of LLM-powered, threat-specific cybersecurity applications. While centered on the challenge of social media bot detection, our methodology and insights generalize to a broad class of LLM-powered cybersecurity systems, including phishing detection, email classification, fraud analysis, and more. We introduce two novel adversarial attack strategies that systematically exploit semantic and contextual weaknesses of LLM-based classifiers, degrading LLM performance in bot detection by up to 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

