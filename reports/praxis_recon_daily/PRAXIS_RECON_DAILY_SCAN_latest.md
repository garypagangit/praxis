# Praxis Recon Daily Literature Scan

Generated: 2026-11-22 18:06 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 4

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 6 | Provenance-aware tool-boundary monitoring | 2026-11-20 | The Expanding Perimeter: A Maturity Model for Agentic AI Attack Surfaces | Unknown venue | [source](https://doi.org/10.68607/jaisb.v1i1.25) |
| 2 | 5 | Agentic package hallucination and tool-boundary gates | 2026-11-20 | Reconstructing Objects for Software Testing | ACM Transactions on Software Engineering and Methodology | [source](https://doi.org/10.1145/3864372) |
| 3 | 4 | Adaptive evaluation of deterministic agent defenses | 2026-11-21 | Dual-Role Evaluation of Large Language Models in Cybersecurity: A Unified Framework for Offensive Generation and Defensive Intelligence | Journal of Engineering Research and Sciences | [source](https://doi.org/10.55708/js0511007) |
| 4 | 2 | Agentic package hallucination and tool-boundary gates | 2026-11-20 | LLM4FL: Multi-Agent Fault Localization via Graph Navigation and Verbal Reasoning | ACM Transactions on Software Engineering and Methodology | [source](https://doi.org/10.1145/3871043) |

## Triage Notes

### 1. The Expanding Perimeter: A Maturity Model for Agentic AI Attack Surfaces

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Ganiyu Oladimeji
- Published: 2026-11-20
- Venue/type: Unknown venue / article
- DOI: https://doi.org/10.68607/jaisb.v1i1.25
- URL: https://doi.org/10.68607/jaisb.v1i1.25
- Opportunity score: 6
- Matched tags: agent, evaluation, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Enterprise security programs are built on the assumption that defended systems stay fixed between periodic reviews. Autonomous AI agents break that assumption because they decide at runtime which tools, peers, and data to access, and so redraw their own attack surface. Existing maturity instruments, including the Capability Maturity Model, COBIT-based assessment, and the NIST Cybersecurity Framework, were built to grade human-run practices that change slowly. Newer agent-specific governance models treat adaptive control as the top of a single scale rather than as an independently scored dimension. Two documented incidents, an external agent that reportedly reached McKinsey’s production database within about two hours, and a zero-click Microsoft 365 Copilot flaw that enabled data exfiltration through a single email, show that periodic assessment cannot keep pace with a system that redraws its own scope in the moment. This paper proposes a four-dimension, five-level maturity model comprising Visibility, Containment, Accountability, and Adaptability, each anchored to an observable test rather than a self-reported survey response. Applied to a composite financial advisory firm, the model scores each dimension independently rather than averaging them, surfacing an imbalance (strong detection, weak prevention) that a composite score would conceal, and yielding a prioritized remediati

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Reconstructing Objects for Software Testing

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Ketai Qiu, Luca Di Grazia, Alessio Gambi, Mattia Fazzini, et al.
- Published: 2026-11-20
- Venue/type: ACM Transactions on Software Engineering and Methodology / article
- DOI: https://doi.org/10.1145/3864372
- URL: https://doi.org/10.1145/3864372
- Opportunity score: 5
- Matched tags: benchmark, evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Software testing requires developers to build nontrivial object states to thoroughly exercise programs that process data structures. Manually building these test cases is an effort-demanding activity. The execution of software in production is an enormous source of program states, which can be serialized to synthesize test inputs. Unfortunately, most serialization approaches prioritize performance over transparency, making it difficult to generate useful and maintainable test cases. We present X2J , an approach that captures objects from runtime and automatically generates human-readable code that reconstructs those objects. X2J leverages Large Language Models, enhanced with an AST-aware Retrieval-Augmented Generation component, and an iterative Validation-Driven Repair pipeline that seamlessly aligns the generated code with the captured state. We evaluated X2J across two benchmarks that include 10,794 objects from 21 Java projects, achieving \(80.7\%\) reconstruction accuracy, that significantly outperforms ProDJ , the closest approach based on program analysis, and six LLM baselines. We further validated X2J on a closed-source industrial application, and X2J achieved \(89.5\%\) accuracy, which confirms the results obtained using open-source software and supports the practical applicability of the approach. Overall, our evaluation shows that X2J successfully transforms product

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Dual-Role Evaluation of Large Language Models in Cybersecurity: A Unified Framework for Offensive Generation and Defensive Intelligence

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Vaibhavi Tiwari, Ola Suaifan, Ramy Othman
- Published: 2026-11-21
- Venue/type: Journal of Engineering Research and Sciences / article
- DOI: https://doi.org/10.55708/js0511007
- URL: https://doi.org/10.55708/js0511007
- Opportunity score: 4
- Matched tags: evaluation, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> The rapid advancement of large language models (LLMs) is reshaping cybersecurity by strengthening defensive capabilities while simultaneously enabling increasingly sophisticated offensive threats. Despite this dual-use nature, existing evaluation methodologies remain fragmented and commonly assess LLMs in isolation as either offensive or defensive systems. This work presents a unified dual-role evaluation framework that characterizes LLM behavior within a shared cybersecurity context through a multi-dimensional taxonomy encompassing role, capability, intent, and contextual use. The framework is empirically evaluated under a strictly single-turn setting (T = 1), in which each offensive input is independently assessed through one corresponding defensive response. The evaluation covers phishing detection, prompt injection, log analysis, malware reasoning, vulnerability exploitation, and incident response using malicious, benign, and ambiguous scenarios. Experimental results demonstrate strong overall detection performance, low error rates, and effective handling of dual-use and borderline cases through ambiguity-aware classification. The findings further reveal the difficulty of distinguishing malicious intent from structurally similar benign inputs, underscoring the importance of context-sensitive evaluation and uncertainty-aware decision making in cybersecurity applications. Ove

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 4. LLM4FL: Multi-Agent Fault Localization via Graph Navigation and Verbal Reasoning

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Md Nakhla Rafi, Dong Jae Kim, Tse-Hsun Peter Chen, Shaowei Wang
- Published: 2026-11-20
- Venue/type: ACM Transactions on Software Engineering and Methodology / article
- DOI: https://doi.org/10.1145/3871043
- URL: https://doi.org/10.1145/3871043
- Opportunity score: 2
- Matched tags: agent
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Locating and fixing software faults is challenging. Traditional Spectrum-Based Fault Localization (SBFL) uses test coverage and failure data but often suffers from low accuracy due to a lack of semantic understanding of code. Deep-learning approaches can improve localization, but require extensive training data and computational resources. Recent Large Language Models (LLMs) offer a promising alternative with stronger code reasoning capabilities. However, existing LLM-based fault localization techniques still struggle at the repository level due to large context windows and positional bias, in which important debugging signals may be buried in large contexts. In this work, we introduce LLM4FL , a multi-LLM-agent-based fault localization technique designed to address these challenges. LLM4FL uses three specialized agents. The Context Extraction Agent divides and prioritizes covered methods into token-fitting groups using an order-aware strategy based on Ochiai suspiciousness scores. The Debugger Agent navigates the repository through graph-based retrieval to generate failure reasoning and rank suspicious methods. The Reviewer Agent then re-evaluates and re-ranks the results through iterative self-refinement and verbal reasoning. Evaluated on Defects4J, LLM4FL improves Top-1 accuracy over prior LLM-based approaches, including AutoFL and SoapFL , by 14.5% and 4.58%, respectively. 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

