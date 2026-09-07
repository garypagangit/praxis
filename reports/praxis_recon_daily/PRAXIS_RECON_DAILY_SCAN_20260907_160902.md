# Praxis Recon Daily Literature Scan

Generated: 2026-09-07 16:09 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 1

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 4 | Agentic package hallucination and tool-boundary gates | 2026-09-05 | HYBRID LLM AND DETERMINISTIC SEVERITY ENGINE FOR NIST SP 800-53 COMPLIANCE DECISION SUPPORT | INTERNATIONAL JOURNAL OF COMPUTER ENGINEERING & TECHNOLOGY | [source](https://doi.org/10.34218/ijcet_17_05_001) |

## Triage Notes

### 1. HYBRID LLM AND DETERMINISTIC SEVERITY ENGINE FOR NIST SP 800-53 COMPLIANCE DECISION SUPPORT

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: M.S Rakesh Babu Rapolu
- Published: 2026-09-05
- Venue/type: INTERNATIONAL JOURNAL OF COMPUTER ENGINEERING & TECHNOLOGY / article
- DOI: https://doi.org/10.34218/ijcet_17_05_001
- URL: https://doi.org/10.34218/ijcet_17_05_001
- Opportunity score: 4
- Matched tags: evaluation, security
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Cloud compliance reviews require people to read architecture information, understand security controls, and decide how serious a finding is.This paper presents a hybrid system for NIST SP 800-53 Rev. 5 compliance decision support, using FedRAMP High as the main cloud-security context.The system combines a pinned machine-readable NIST OSCAL catalog, tool-based control lookup, structured LLM evidence assessment, and a deterministic Python severity engine.The LLM organizes the evidence, but Python rules make the final risk decision using four levels: LOW, MODERATE, HIGH, and CRITICAL.The prototype runs on AWS Lambda, has a public Streamlit interface, and is deployed from GitHub Actions to AWS through OpenID Connect (OIDC).The final evaluation used 100 previously unseen synthetic scenarios across all 20 NIST SP 800-53 Rev. 5 control families, balanced across the four risk classes.The system achieved 92% exact agreement for the combined compliance-status and risk result (Wilson 95% confidence interval: 85.0%-95.9%),98% status accuracy, and 92% risk accuracy.CRITICAL recall was 100%, while HIGH recall was 72%.Six of the eight mismatches were HIGH cases classified as CRITICAL.Mean audit latency was 7.70 seconds, with a median of 7.43 seconds and a p95 of 10.13 seconds.Hybrid LLM and Deterministic Severity Engine for NIST SP 800-53 Compliance Decision Support https://iaeme.com/Home/jou

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

