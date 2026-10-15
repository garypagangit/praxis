# Praxis Recon Daily Literature Scan

Generated: 2026-10-15 15:22 UTC
Lookback window: 2 day(s)
Minimum score: 2
New flagged works: 4

## Flagged Works

| Rank | Score | Topic | Published | Title | Venue | Link |
| --- | ---: | --- | --- | --- | --- | --- |
| 1 | 10 | Provenance-aware tool-boundary monitoring | 2026-10-13 | Proof carrying agent actions enable verifiable licensing of language model tool use | Scientific Reports | [source](https://doi.org/10.1038/s41598-026-74900-x) |
| 2 | 9 | Provenance-aware tool-boundary monitoring | 2026-10-13 | Large language model multiagent systems for industrial problem discovery and prioritization | Discover Artificial Intelligence | [source](https://doi.org/10.1007/s44163-026-02468-6) |
| 3 | 5 | Adaptive evaluation of deterministic agent defenses | 2026-10-13 | A cascaded probabilistic framework for stealth-aware MITRE ATT&CK path prediction in active directory adversary emulation | Scientific Reports | [source](https://doi.org/10.1038/s41598-026-71934-z) |
| 4 | 5 | Source-locked citation and hallucination verification | 2026-10-13 | From plausible menus to trustworthy nutrition: a risk-proportionate VALID-Diet framework for artificial intelligence-generated dietary advice | Frontiers in Nutrition | [source](https://doi.org/10.3389/fnut.2026.1957211) |

## Triage Notes

### 1. Proof carrying agent actions enable verifiable licensing of language model tool use

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Nurgali Kadyrbek, Madina Mansurova
- Published: 2026-10-13
- Venue/type: Scientific Reports / article
- DOI: https://doi.org/10.1038/s41598-026-74900-x
- URL: https://doi.org/10.1038/s41598-026-74900-x
- Opportunity score: 10
- Matched tags: agent, benchmark, safety, tool use
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract LLM agents increasingly call tools and take irreversible actions, yet the reasoning that licenses an action is rarely checked before execution. We present Proof-Carrying Agent Actions (PCAA) : each governed action carries a typed Action Certificate that a planner-independent checker must accept before execution. A trusted execution shim derives the obligation set and the irreversibility classification from an authoritative tool contract and binds the certificate to the exact invocation with a canonical SHA-256 commitment. The checker compares that context with the certificate, re-derives typed support (proof, belief, hypothesis, contingency, conflict, or no-progress), and validates formula-level inference rules. Irreversible actions require Proof for every declared licensing obligation. The checker accepts the two valid certificates and rejects all fifteen unsafe certificates in a semantic battery; four additional structural cases confirm rejection of argument substitution, precondition omission, and risk-flag downgrade. A microbenchmark of a three-obligation payment certificate measures 53.7 μs median and 65.7 μs p95 for construction, checking, serialization, and buffered local persistence. A stateful guardrail with the same certified-state predicate matches PCAA on safety; PCAA’s distinct contribution is a typed, replayable decision artifact. Guarantees are relative 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 2. Large language model multiagent systems for industrial problem discovery and prioritization

- Topic: Provenance-aware tool-boundary monitoring
- Authors: Mohammed Amin Adoul, Abdelhamid Ghoul
- Published: 2026-10-13
- Venue/type: Discover Artificial Intelligence / article
- DOI: https://doi.org/10.1007/s44163-026-02468-6
- URL: https://doi.org/10.1007/s44163-026-02468-6
- Opportunity score: 9
- Matched tags: agent, evaluation, safety, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract A persistent gap separates academic research priorities from the operational challenges faced by manufacturing firms. Established identification methods, among them Failure Mode and Effects Analysis (FMEA) workshops, Lean audits and consultant engagements, are episodic, bounded by participant expertise and organised along departmental lines, which makes cross-departmental issues hard to surface. Multi-agent systems built on large language models (LLMs) have meanwhile shown collaborative problem-solving ability in software engineering and, more recently, in shopfloor scheduling and supply chain coordination. This article is a Perspective. It develops a framework and a research agenda; implementation and empirical evaluation fall outside its scope and are set out as its first research priorities. Three contributions are offered. The first is a synthesis of literature from industrial problem identification, LLM-based autonomous agents and manufacturing AI, which positions the proposal against existing industrial LLM agent work. The second is a framework in which six domain-specialised agents (production, quality, maintenance, supply chain, safety, energy) would collaborate through a five-phase protocol: worker-driven discovery, cross-departmental analysis, candidate-relationship detection, consensus-based financial assessment and debate-driven prioritisation. The prioriti

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 3. A cascaded probabilistic framework for stealth-aware MITRE ATT&CK path prediction in active directory adversary emulation

- Topic: Adaptive evaluation of deterministic agent defenses
- Authors: Mahmoud Youssef, Nagwa L. Badr, Alshaimaa Abo‐alian
- Published: 2026-10-13
- Venue/type: Scientific Reports / article
- DOI: https://doi.org/10.1038/s41598-026-71934-z
- URL: https://doi.org/10.1038/s41598-026-71934-z
- Opportunity score: 5
- Matched tags: MITRE ATT&CK, evaluation
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Abstract Proactive adversary emulation requires anticipating multi-step attack trajectories, yet existing approaches rely on static attack graphs or single-signal models that cannot jointly satisfy coherence, tactical realism, and evasiveness. We propose a cascaded probabilistic framework for MITRE ATT&CK technique-path prediction in Active Directory environments, where exhaustive enumeration is intractable. Its contribution is a three-stage architecture that decouples these objectives instead of blending them. Stage 1, a two-layer unidirectional LSTM trained on observed threat-actor chains, emits a five-candidate pool rather than one technique. Stage 2, an empirical Markov tactic-transition gate, admits only attested transitions, including self-loops and backward moves a strict linear kill chain excludes. Stage 3 re-ranks survivors against a detection-rule corpus, favoring evasive over merely probable techniques. Candidates are masked at inference to Windows-applicable techniques, so outputs are technique chains, not instantiated paths. Under a prefix-disjoint protocol in which no evaluation context occurs in training, the true continuation is retained in the five-candidate pool more often than by a first-order predictor or an exact prefix-lookup table on identical pairs. Because Stage 3 both selects on and is scored by detection-rule density, the chains are re-scored against 

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

### 4. From plausible menus to trustworthy nutrition: a risk-proportionate VALID-Diet framework for artificial intelligence-generated dietary advice

- Topic: Source-locked citation and hallucination verification
- Authors: Jingyi Xu, Weina Xing, Lili Jia, Xi Li, et al.
- Published: 2026-10-13
- Venue/type: Frontiers in Nutrition / article
- DOI: https://doi.org/10.3389/fnut.2026.1957211
- URL: https://doi.org/10.3389/fnut.2026.1957211
- Opportunity score: 5
- Matched tags: safety, verification
- Why flagged: Matches Praxis topic terms and opportunity language.

Abstract excerpt:

> Generative artificial intelligence can produce menus, recipes, shopping lists, and dietary explanations that appear individualized and clinically informed. Fluency alone, however, provides little evidence of nutritional accuracy, safety, feasibility, or benefit. We propose VALID-Diet, a staged framework for evaluating systems that generate actionable dietary recommendations as sociotechnical interventions. Its domains are Verification of nutritional targets and composition; Adversarial safety and boundary testing; Linkage between user inputs and recommendation changes; Implementation feasibility and inclusion; and Documentation, versioning, and reproducibility. Stage 0 defines intended use, input integrity, and a structured risk profile based on harm severity, exposure, autonomy, reversibility, and enforceable oversight. Stage 1 separates target validity, menu achievement, and arithmetic agreement and, for integrated systems, tests retrieval, calculation, and generation as distinct components. Stage 2 evaluates safety, substantive personalization, feasibility, and inclusion using pre-specified case blueprints. Stage 3 evaluates human oversight, workflow utility, and prospective outcomes only after earlier gates are passed. A retrospective worked application to a published retrieval-augmented personalized-nutrition system illustrates risk assignment and progression decisions. VA

Praxis next step: review the paper, inspect future-work/limitations sections, and decide whether it should become a new PX candidate or update an existing experiment lane.

