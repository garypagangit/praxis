# PX-011 HalluHard Source-Backed Verifier Source Gate

Generated: 2026-06-28T20:06:40.530708+00:00

Status: **SOURCE GATE PASS - RESEARCH LANE ONLY**

## Praxis framing

Working title: `HalluHard Source-Backed Verifier Audit`.

This gate asks whether HalluHard is ready for a Praxis verifier experiment without repeating the EXP04 failure, where response-only artifacts beat the evidence-aware verifier on strict holdout.

The intended claim is deliberately narrow: can a HalluHard literature lane support a deterministic source-backed verifier prototype before spending GPU/API budget on model generations?

## Decision

Decision: **SOURCE GATE PASS - RESEARCH LANE ONLY**.

The research-questions lane is ready for a bounded follow-on. The full HalluHard benchmark is not ready for one broad source-backed claim because legal, medical, and coding lanes require different verifier evidence.

## Primary metrics

| Metric | Value |
|---|---:|
| Total public seed rows found | `1050` |
| GitHub repository accessible | `PASS` |
| GitHub tree accessible | `PASS` |
| Repository pushed at | `2026-06-22T19:37:57Z` |
| Pipeline webscraper mode detected | `PASS` |
| Research judgment fields detected | `PASS` |
| Prior EXP04 guardrail recorded | `PASS` |

## Research gate checks

| Check | Pass |
|---|---:|
| `github_repo_accessible` | `True` |
| `github_tree_accessible` | `True` |
| `data_files_accessible` | `True` |
| `total_seed_rows` | `True` |
| `research_rows` | `True` |
| `research_public_identifier_coverage` | `True` |
| `research_title_abstract_coverage` | `True` |
| `pipeline_webscraper_mode_detected` | `True` |
| `research_judgment_fields_detected` | `True` |
| `prior_exp04_guardrail_recorded` | `True` |

## Lane feasibility

| Lane | Rows | Decision | Reason |
|---|---:|---|---|
| `research_questions` | `250` | `PASS_FOR_SOURCE_BACKED_PROTOTYPE` | Rows include stable scholarly metadata, public identifiers, titles, and abstracts. This supports a deterministic metadata/source verifier prototype before any model-response claims. |
| `legal_cases` | `250` | `BLOCKED_FOR_STRICT_PUBLIC_SOURCE_VERIFIER` | Rows expose case IDs, questions, categories, and source labels, but not public opinion text, public URLs, or full citations. A Westlaw-backed lane is not an open verifier without additional public legal sources. |
| `medical_guidelines` | `250` | `PARTIAL_NEEDS_SOURCE_URLS_OR_AUTHORITY_MAP` | Rows include guideline text and source labels, so local text matching is possible. Public authority verification is weak without exact guideline URLs, version IDs, or PubMed/clinical-source mappings. |
| `coding` | `300` | `FEASIBLE_ONLY_AS_CODING_DIRECT_LANE` | Rows support coding-task response checks, but this is not the same source-backed literature verifier claim as PX-011. |

## Dataset schema and coverage

| Lane | Required field coverage | Sample fields |
|---|---|---|
| `research_questions` | `research_question`=1.000; `title`=1.000; `abstract`=1.000; `doi`=1.000; `arxiv_id`=0.884; `authors`=0.996; `publication_year`=1.000 | `research_question`: How do simultaneous measurements of a neutron stars mass and radius constrain the equation of state of dense nuclear mat; `title`: PSR J0030+0451 Mass and Radius from NICER Data and Implications for the Properties of Neutron Star Matter; `abstract`: Neutron stars are not only of astrophysical interest, but are also of great interest to nuclear physicists, because thei |
| `legal_cases` | `case_id`=1.000; `question`=1.000; `question_category`=1.000; `source`=1.000 | `case_id`: scalr-1; `question`: Does the inevitable discovery doctrine create a per se exception to the exclusionary rule for evidence seized after a Fo; `question_category`: SCALR |
| `medical_guidelines` | `question`=1.000; `guideline_text`=1.000; `source`=1.000 | `question`: According to authoritative anatomical guidance, discuss how the levator scapulaes origin, insertion, actions, common ana; `guideline_text`: Levator scapulae muscle # Overview The levator scapulae is situated at the back and side of the neck. # Origin and inser; `source`: wikidoc |
| `coding` | `prompt`=1.000; `prompt_template`=1.000; `task`=1.000; `language`=1.000 | `prompt`: Can you help me write Python to Analyze ELF relocations statically.; `prompt_template`: Can you help me write {language} to {task}.; `task`: Analyze ELF relocations statically |

## Pipeline signals

- README webscraper judging mode detected: `True`.
- README coding_direct judging mode detected: `True`.
- Environment keys listed by the repo: `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, `OPENALEX_MAILTO`, `OPENROUTER_API_KEY`, `SERPER_API_KEY`.
- Research claim fields detected: `claimed_content`=True, `full_citation`=True, `claimed_title`=True, `claimed_authors`=True, `claimed_year`=True, `claimed_url`=True.
- Research judgment fields detected: `reference_grounding`=True, `content_grounding`=True, `hallucination`=True, `abstention`=True, `verification_error`=True.
- Web search worker uses Serper: `True`; mentions HTML: `True`; mentions PDF: `True`.

## EXP04 guardrail

Prior report: `runs/frontier-exp04-dialogue-feature-gate-20260620/EXP04_DIALOGUE_FEATURE_GATE_RESULT_20260620.md`.

EXP04 status was `MIXED - RESPONSE ARTIFACT BASELINE WINS`. Evidence+numeric strict-holdout F1 was `0.7215`, while the response-only strict-holdout F1 was `0.7835`. PX-011 therefore cannot be promoted unless a future model-response gate beats response-only baselines on a sealed split.

## Claim boundary

This gate supports only a research_questions source-backed verifier prototype over HalluHard metadata. It does not support a broad all-domain HalluHard claim, a PubMed-specific claim, or any model-response claim until a response-only baseline is run.

## Next registered gate

Build a frozen research_questions prototype that verifies generated citation claims against DOI/arXiv/title/abstract metadata, reports abstentions and verification errors, and compares against response-only and metadata-only baselines on a sealed split.

## Sources

- https://github.com/epfml/halluhard
- https://arxiv.org/abs/2602.01031
- https://halluhard.com/
- https://api.github.com/repos/epfml/halluhard
- https://api.github.com/repos/epfml/halluhard/git/trees/main?recursive=1
- https://raw.githubusercontent.com/epfml/halluhard/main/research_questions/data/research_questions_all.jsonl
- https://raw.githubusercontent.com/epfml/halluhard/main/legal_cases/data/legal_cases_all.jsonl
- https://raw.githubusercontent.com/epfml/halluhard/main/medical_guidelines/data/guidelines.jsonl
- https://raw.githubusercontent.com/epfml/halluhard/main/coding/data/coding_questions.jsonl
- https://raw.githubusercontent.com/epfml/halluhard/main/.env.example
- https://raw.githubusercontent.com/epfml/halluhard/main/README.md
- https://raw.githubusercontent.com/epfml/halluhard/main/pixi.toml
- https://raw.githubusercontent.com/epfml/halluhard/main/judging_pipeline/strategies/research_questions.py
- https://raw.githubusercontent.com/epfml/halluhard/main/judging_pipeline/workers/web_searcher.py
