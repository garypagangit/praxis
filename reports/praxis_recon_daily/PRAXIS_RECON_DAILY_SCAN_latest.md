# Praxis Recon Daily Literature Scan

Generated: 2026-11-17 19:27 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 3

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 8 | Adaptive evaluation of deterministic agent defenses | 2026-11-16 | Faogf: Auditable Evidence Provenance ForAutonomous Financial Ai Agents On Opentelemetry | International journal of data science and machine learning. | [source](https://doi.org/10.55640/ijdsml-06-02-16) |
| 2 | 5 | Mixture-of-experts router observability | 2026-11-16 | CliniCIRCA: LLM-powered Clinical Timeline Generation and Summarization from Unstructured EHR Texts for Mental Health Patients | Research Square | [source](https://doi.org/10.21203/rs.3.rs-11472328/v1) |
| 3 | 2 | Agentic package hallucination and tool-boundary gates | 2026-11-15 | Context-aware forecasting of inter-firm competitive dynamics with graph learning and multi-agent reasoning | Scientific Reports | [source](https://doi.org/10.1038/s41598-026-79480-4) |

## Triage Notes

### 1. Faogf: Auditable Evidence Provenance ForAutonomous Financial Ai Agents On Opentelemetry

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Sowmith Javvaji
- Published: 2026-11-16
- Venue/type: International journal of data science and machine learning. / article
- DOI: https://doi.org/10.55640/ijdsml-06-02-16
- URL: https://doi.org/10.55640/ijdsml-06-02-16
- Opportunity score: 8
- Matched tags: agent, benchmark, provenance
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Autonomous AI agents now read regulatoryfilings, compute figures and distribute reports inside financial firms, but their telemetry cannot tell an auditor which filing versions a decision rested on, under which authority and policy version an action ran, or whether untrusted content was in the model’s context. We present FAOGF (Financial Agent Observability and Governance Framework), an OpenTelemetry-compatible audit layer. Its core architectural contribution is context-bound evidence provenance recorded on two paths: a gateway binds every modelcall and action to the version-exact, content-hashed evidence actually in the model’s context, and writes that binding synchronously to a hash-chained evidence store before exporting standard spans, so audit completeness no longer depends on what the tracing pipeline keeps. We evaluate nine audit queries. In 15 controlled experiments with a scripted agent (200 workflows × 5 seeds, and a real OpenTelemetry Collector on two machines), all nine queries were evaluated: FAOGF answered the seven answerability queries (Q1–Q7) exactly in every configuration, detected 88–97% of spans lost to export-queue overflow (Q8) and 100% of audit attributes stripped by a Collector processor (Q9). Standard OpenTelemetry tracing recovered only 9–12% of protected actions at 10% head sampling and was silently stripped by a common Collector configuration; full p

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. CliniCIRCA: LLM-powered Clinical Timeline Generation and Summarization from Unstructured EHR Texts for Mental Health Patients

- Topic: Mixture-of-experts router observability
- Authors: Aiwei Ivy Zhang, Nimra Ishfaq, Mohit Chandra, Santiago Alvarez Lesmes, et al.
- Published: 2026-11-16
- Venue/type: Research Square / preprint
- DOI: https://doi.org/10.21203/rs.3.rs-11472328/v1
- URL: https://doi.org/10.21203/rs.3.rs-11472328/v1
- Opportunity score: 5
- Matched tags: benchmark, evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Background: Mental health care often requires clinicians to reason over patient journeys: longitudinal patterns of symptoms, diagnoses, treatments, behaviors, social context, and responses to care. Yet these journeys are rarely documented as readily available, explicit timelines. Clinically important temporal information is often embedded in unstructured discharge narratives, where events may be repeated, narrated out of order, or expressed through vague and relative time references. This makes temporal recovery difficult for clinicians and computational systems, and can limit the reliability of downstream summarization. Methods: We present CliniCIRCA, a multi-stage large language model (LLM) framework for Calendar-anchored, Imprecision-aware Reconstruction of Clinical Annals. CliniCIRCA decomposes patient-journey reconstruction into three stages: extracting atomic clinical events from raw discharge summaries, assigning calendar-grounded temporal labels with explicit uncertainty, and rendering the verified timeline as a date-grouped clinical summary. The framework is designed to make temporal reasoning inspectable rather than hidden inside a single summarization step. Results: From 14,882 MIMIC-III mental-health-coded admissions, we construct a benchmark of 52 discharge summaries on which CliniCIRCA produces 15,891 temporally tagged events. Following clinician-defined 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. Context-aware forecasting of inter-firm competitive dynamics with graph learning and multi-agent reasoning

- Topic: Agentic package hallucination and tool-boundary gates
- Authors: Daeseung Park, Yonghwan Kwon, Seongil Han, Paul D. Yoo
- Published: 2026-11-15
- Venue/type: Scientific Reports / article
- DOI: https://doi.org/10.1038/s41598-026-79480-4
- URL: https://doi.org/10.1038/s41598-026-79480-4
- Opportunity score: 2
- Matched tags: agent
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract The evolution of competitive dominance in technology-intensive industries is shaped by complex interactions among research activity, media visibility, strategic disclosures, public attention, and market signals. Understanding these dynamics is critical for strategic intelligence, yet existing predictive models often treat firms as isolated entities and provide limited support for contextualizing long-horizon firm-to-firm competitive forecasts. Here, we introduce an integrated framework that captures the relational nature of market competition by extending our prior Bayesian Multivariate Time-series Graph Neural Network with a newly designed, post hoc, lookahead-free multi-agent reasoning layer. The framework infers inter-firm relational dependencies endogenously from multimodal signals to forecast latent firm competitiveness and pairwise competitive gap trajectories with quantified predictive uncertainty. To evaluate strategic plausibility, specialized persona-driven language model agents critique the forecasted trajectories across technological, financial, and regulatory lenses using retrieved evidence. Evaluated under a rigorous date-based temporal protocol with strictly withheld test horizons, the framework consistently outperforms competitive structural baselines and yields well-calibrated prediction intervals. When applied to thirty leading AI-oriented technology 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

