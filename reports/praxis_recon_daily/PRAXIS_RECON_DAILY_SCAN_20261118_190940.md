# Praxis Recon Daily Literature Scan

Generated: 2026-11-18 19:09 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 2

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 4 | Agentic package hallucination and tool-boundary gates | 2026-11-17 | How Safe Are AI-Generated Patches? A Large-scale Study on Security Risks in LLM and Agentic Automated Program Repair on SWE-bench | ACM Transactions on Software Engineering and Methodology | [source](https://doi.org/10.1145/3861341) |
| 2 | 4 | Adaptive evaluation of deterministic agent defenses | 2026-11-16 | Software Engineering for Large Language Models: Research Status, Challenges, and the Road Ahead | ACM Transactions on Software Engineering and Methodology | [source](https://doi.org/10.1145/3860527) |

## Triage Notes

### 1. How Safe Are AI-Generated Patches? A Large-scale Study on Security Risks in LLM and Agentic Automated Program Repair on SWE-bench

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Amirali Sajadi, Kostadin Damevski, Preetha Chatterjee
- Published: 2026-11-17
- Venue/type: ACM Transactions on Software Engineering and Methodology / article
- DOI: https://doi.org/10.1145/3861341
- URL: https://doi.org/10.1145/3861341
- Opportunity score: 4
- Matched tags: agent, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Large language models (LLMs) and agentic frameworks are increasingly used for development tasks such as automated program repair (APR). Prior work has identified security risks in LLM-generated code, but most studies focus on synthetic, simplified, or isolated tasks. We present a large-scale security analysis of LLM-generated patches using 20,000+ GitHub issues from SWE-bench. We evaluate developer-written patches, two standalone LLMs (Llama 3.3 Instruct-70B and GPT-5.4 nano), and four agentic frameworks (OpenHands, AutoCodeRover, HoneyComb, and SWE-agent). We also analyze code, issue, and project-level factors associated with insecure patches. Under our evaluated SWE-bench setup, Llama 3.3 introduced 135 manually confirmed vulnerabilities across the train and test sets, compared with 12 in developer-written patches for the same issues. On the SWE-bench test set, GPT-5.4 nano introduced 3 vulnerabilities compared with 2 in developer patches. All four evaluated agentic frameworks also introduced vulnerabilities. OpenHands had the highest retained count, with 44 vulnerabilities across 11 issue instances. Vulnerabilities are associated with broader code modifications and with issues missing specific information. These results suggest that APR systems require proactive risk assessment methods that consider both generated code and issue context.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Software Engineering for Large Language Models: Research Status, Challenges, and the Road Ahead

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Hongzhou Rao, Yanjie Zhao, Xinyi Hou, Shenao Wang, et al.
- Published: 2026-11-16
- Venue/type: ACM Transactions on Software Engineering and Methodology / article
- DOI: https://doi.org/10.1145/3860527
- URL: https://doi.org/10.1145/3860527
- Opportunity score: 4
- Matched tags: dataset, evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> The rapid advancement of large language models (LLMs) has redefined artificial intelligence (AI), pushing the boundaries of AI research and enabling unbounded possibilities for both academia and industry. However, LLM development faces increasingly complex challenges throughout its lifecycle, while existing research has not systematically investigated these challenges and solutions from the perspective of software engineering (SE) approaches. To fill the gap, we systematically analyze the research status throughout the LLM development lifecycle, which is divided into six phases: requirements engineering, dataset construction, model development and enhancement, testing and evaluation, deployment and operations, and maintenance and evolution. We conclude by identifying the key challenges in each phase and presenting potential research directions to address them. In general, we provide valuable insights from an SE perspective to facilitate future advances in LLM development.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

