# Praxis Recon Daily Literature Scan

Generated: 2026-08-30 15:06 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 2

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 16 | Source-locked citation and hallucination verification | 2026-08-28 | A Domain-Agnostic Agentic Architecture for Structured Extraction of Engineering Knowledge | Applied Artificial Intelligence | [source](https://doi.org/10.1080/08839514.2026.2712892) |
| 2 | 10 | Source-locked citation and hallucination verification | 2026-08-28 | Mapping Structured Absences in Scientific Papers: An Auditable LLM-Assisted Workflow Demonstrated on Cross-Coupling Chemistry | ChemRxiv | [source](https://doi.org/10.26434/chemrxiv.15007996/v1) |

## Triage Notes

### 1. A Domain-Agnostic Agentic Architecture for Structured Extraction of Engineering Knowledge

- Topic: Source-locked citation and hallucination verification
- Authors: Oscar Chigozie Ikechukwu, Mehdi Tarkian, Sanjay Nambiar, Marie Jonsson, et al.
- Published: 2026-08-28
- Venue/type: Applied Artificial Intelligence / article
- DOI: https://doi.org/10.1080/08839514.2026.2712892
- URL: https://doi.org/10.1080/08839514.2026.2712892
- Opportunity score: 16
- Matched tags: agent, evaluation, hallucination, provenance, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> LLM-based retrieval systems can execute queries and produce fluent answers, yet they rarely preserve a traceable record of what evidence was retrieved, how it was validated, or what reasoning led to synthesis. The lack of provenance and auditability limits debugging, compliance verification, and operational trust, particularly in engineering applications where correctness depends on interpreting structured specifications within revision-controlled documentation. This work presents the Relational Control Plane (RCP), a SQL-backed agentic architecture that persists orchestration state as queryable relational records. RCP enforces a six-stage verify-then-summarize control loop in which synthesis is permitted only after retrieved evidence satisfies validation constraints, so that unmet conditions surface as explicit, auditable failures rather than silent errors. Domain behavior is defined by reusable Strategy and Function libraries, enabling adaptation through declarative templates without modifying the orchestration logic. Evaluation across two industrial applications shows substantial gains: answer correctness increases from 45% to 85% with hallucination reduced from 55% to 5% in one case study; and from 23% to 81% with hallucination reduced from 47% to 11% in another, despite using a lightweight language model. Results show that reliable agentic AI systems emerge from architectu

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Mapping Structured Absences in Scientific Papers: An Auditable LLM-Assisted Workflow Demonstrated on Cross-Coupling Chemistry

- Topic: Source-locked citation and hallucination verification
- Authors: Y. Ôno, Masaharu Yoshioka, Tetsuya Taketsugu
- Published: 2026-08-28
- Venue/type: ChemRxiv / preprint
- DOI: https://doi.org/10.26434/chemrxiv.15007996/v1
- URL: https://doi.org/10.26434/chemrxiv.15007996/v1
- Opportunity score: 10
- Matched tags: benchmark, future work
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Scientific papers record what was discovered and communicated, but the resolution at which evidence relations are made explicit—a paper’s documentary resolution—often falls short of what later computational reuse, benchmarking, or data-driven synthesis requires. We present UQS (Unasked Question Structuring), an auditable LLM-assisted pipeline that takes scientific papers as input and produces structured absence records with evidence chains, an Evidence Pack (EP) dictionary specifying the evidence needed to reach the next evidential level, a bounded filling-status map across later literature under pre-locked criteria, and cross-paper research-question briefs. Applied to Kumada’s 1972 Ni-catalysed cross-coupling communication over a 54-year record window (1972–2026), UQS derives ten EPs and reveals a VQ-hierarchy inversion: methodology-level documentation is addressed early, whereas system-matched mechanistic documentation (VQ-3) appears only after 49 years (Mazet 2021), and quantitative-reliability documentation (VQ-4) remains a bounded non-detection—a pattern consistent with publication-incentive structure. The paper claims auditability, configuration-pinned rerun consistency, and internal robustness (four-model cross-comparison, N=6 multi-run aggregation); external expert validation is registered as future work.

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

