# When Retrieved Cyber-Threat Evidence Helps and When It Hurts

## A paired study of relationship evidence, source compatibility, and failed external routing

**Gary Pagan**  
Completed empirical manuscript · Evidence release: September 14, 2026  
Study lineage: PX-003/PX-034 full CTIBench evaluation and PX-068 external router evaluation

## Executive summary

This study asked a practical question: **Does giving an AI model cybersecurity reference material make its answers more reliable?** The answer depended on whether that material matched the question.

Two models answered the same public set of 2,500 multiple-choice questions. On the 1,578 questions linked to MITRE ATT&CK techniques, carefully selected relationship facts helped substantially. When the correct source technique was supplied, accuracy improved by about 23 percentage points for Llama and 20 points for Qwen. Those gains also exceeded a simpler technique-description baseline. When retrieval had to find material using the question and its displayed choices, the gains were smaller but still substantial: about 18 and 14 points.

The same automatic retrieval process made answers worse on the other 922 questions: accuracy fell by about 15 and 17 points. A later attempt to learn when to use the evidence failed its external test. That test also exposed serious answer-format problems, so its apparent accuracy gains over a weak baseline cannot establish better cybersecurity reasoning.

The useful result is a measured boundary: **relevant relationship evidence can help, but a positive average score does not make unrestricted retrieval safe.** The completed contribution is an empirical comparison and a reproducible account of where it failed. It is not a successful new defense, an independently validated deployment policy, or a claim that the models reasoned through a knowledge graph.

The accompanying package contains the original CTIBench predictions, frozen analysis code, protocols, external-test derived observations, and an offline reproduction command. A further external study, PX-071, has no completed scientific result in this release and contributes no efficacy evidence.

## Abstract

Retrieval can improve a language model's access to cybersecurity knowledge while also introducing persuasive evidence from an incompatible source. This study evaluated a fixed relationship-evidence treatment on all 2,500 CTIBench CTI-MCQ questions with Qwen2.5-7B-Instruct and Llama-3.1-8B-Instruct. A prospective internal protocol separated 1,578 ATT&CK-technique questions from 922 source-mismatch questions, compared six source-known evidence conditions, and tested question-and-options retrieval without access to the correct label or source pointer. Source-known relationship evidence improved frozen option-parser accuracy over vanilla by 23.07 and 19.58 percentage points and over technique-only evidence by 20.34 and 17.43 points. Query-only retrieval improved eligible-question accuracy by 18.19 and 13.88 points but reduced mismatch accuracy by 14.97 and 17.46 points, failing the registered noninferiority gate for both models. An external source-compatibility router evaluation on 2,997 AthenaBench questions failed its registered precision, false-positive, coverage, and harm-mitigation requirements. Severe output-format failures limit semantic interpretation of that extension. The evidence supports a bounded relationship-evidence effect and a reproducible mismatch failure, without establishing a deployable protective router. Prior item exposure, answer-option access, parser behavior, and the limits of statistical reproduction are disclosed. The contribution is empirical and procedural; no new theorem or state-of-the-art retrieval claim is made.

**Keywords:** cyber threat intelligence; retrieval-augmented generation; MITRE ATT&CK; source compatibility; multiple-choice evaluation; reproducibility.

## Chapter 1. Research problem and contribution

### 1.1 Why evidence selection matters

A cybersecurity assistant may need knowledge that is incomplete or out of date in its parameters. Supplying reference material is an attractive response, but the presence of authoritative text does not establish that it answers the current question. An ATT&CK description can be correct and still be a poor basis for answering a question about software weaknesses or another source family. The research problem is therefore both an effectiveness problem and a compatibility problem.

CTIBench provides public tasks for evaluating language models in cyber threat intelligence. Its CTI-MCQ component offers a fixed-label outcome suitable for paired experiments: the same question can be answered under several evidence conditions and compared against the released answer. This supports a more transparent outcome measure than an unconstrained model judging another model's response, although benchmark labels and multiple-choice formatting introduce their own limits. [Alam et al., 2024](https://arxiv.org/abs/2406.07599)

The present study modified the information supplied to a model. The central evidence experiment did not fine-tune language-model weights; the external extension trained a separate source classifier. The central treatment selected facts about mitigations, detection, procedures, tactics, and related technique metadata from a pinned ATT&CK knowledge source. The evaluation distinguished selecting facts after the benchmark's source technique was known from retrieving them globally using the question and all displayed answer choices. That distinction prevents an oracle-assisted experiment from being presented as ordinary deployment retrieval.

### 1.2 Research questions and registered hypotheses

**RQ1:** On questions whose published source is an ATT&CK technique, does relationship evidence improve option-parser accuracy over vanilla answering and technique-only evidence, consistently across two model families?

The registered source-known hypothesis required at least a five-point gain over vanilla and a three-point gain over technique-only evidence for each model, with positive paired interval lower bounds and adjusted exact tests below .05. Comparisons with random facts, empty evidence, and broad seed terms tested whether the result depended on the selected evidence treatment rather than simply adding cybersecurity text.

**RQ2:** Does the gain survive retrieval without the published source pointer, and does this retrieval preserve performance on questions outside the supported source domain?

The eligible-question hypothesis required at least a three-point gain for each model. The mismatch hypothesis required the lower bound of the paired 95% interval to exceed minus five percentage points. Both were required for the full source-and-query confirmation claim.

**RQ3:** Can a separately calibrated source-compatibility router preserve useful evidence effects and reduce harm on an external question collection?

PX-068 tested that extension under its own frozen protocol. Its outcome is included as a failed external validation, not pooled with CTIBench or used to revise the primary thresholds. The [primary protocol](protocol/FULL_2500_PREREGISTRATION.md) and [external protocol](protocol/PX068_PROSPECTIVE_PROTOCOL.md) preserve the original rules.

### 1.3 Contribution and scope

The contribution is a completed paired empirical study separating evidence form, source provenance, mismatch behavior, and model family. It also documents an unsuccessful routing extension and an evaluation-format failure. The work does not establish that relationship retrieval is new, that the selected scoring formula is optimal, or that the observed gains arise from latent multi-hop reasoning. It supplies a reproducible test of a concrete process modification and a boundary on its use.

## Chapter 2. Literature and conceptual framework

### 2.1 Retrieval and CTI-specific precedents

Retrieval-augmented generation combines a generator with information retrieved from external memory. The general method predates this study and is its foundation, not its invention. [Lewis et al., 2020](https://arxiv.org/abs/2005.11401) MITRE ATT&CK supplies structured descriptions of adversarial behavior, with maintained versions and relationships useful for constructing an explicit evidence source. That provenance supports auditability; it does not itself guarantee that retrieval improves a model's answers. [Strom et al., 2020](https://www.mitre.org/news-insights/publication/mitre-attck-design-and-philosophy)

TechniqueRAG is a close CTI precedent. It combines retrieval, reranking, and generation for adversarial-technique annotation. Its existence rules out a claim that this study introduces CTI retrieval or ATT&CK-oriented retrieval. Its annotation task and training choices differ from the fixed CTI-MCQ evidence-condition comparison conducted here. No head-to-head reproduction of TechniqueRAG was performed, so this manuscript makes no superiority claim against it. [Lekssays et al., 2025](https://aclanthology.org/2025.findings-acl.1076/)

A 2026 preprint compares vector, graph, agentic, and hybrid retrieval on 3,300 CTI question-answer pairs. It further narrows any claim of novelty based merely on graph relationships or a CTI retrieval comparison. The distinction here is the paired source-known/query-only design with prespecified mismatch gates and preserved failed external evidence. This is a specific empirical contribution rather than a claim to cover every retrieval architecture. [Hamzic et al., 2026](https://arxiv.org/abs/2604.11419)

| Primary source | Established foundation | What this study evaluates | Boundary |
|---|---|---|---|
| CTIBench | Public CTI tasks and released answer labels | Fixed paired evidence conditions on the full CTI-MCQ artifact | The benchmark was not created here |
| RAG | External retrieval as model context | A deterministic CTI evidence-selection process | No general RAG invention |
| MITRE ATT&CK | Versioned behavioral knowledge and relationships | Relationship facts versus description-only and negative controls | Authority of the source is not answer relevance |
| TechniqueRAG | CTI retrieval for technique annotation | Multiple-choice answering with explicit provenance and mismatch strata | No direct performance comparison |
| Beyond RAG for CTI | Graph and agentic retrieval comparisons | Bounded evidence-form and compatibility experiment | No claim to state-of-the-art retrieval |
| AthenaBench | External CTI evaluation resource | A prospectively specified source router | External confirmation failed |

### 2.2 Evidence compatibility as the organizing concept

Let a question be q, its displayed options be O, a knowledge source be K, and a retrieval policy be R. The model answers from q, O, and the selected context R(q, O, K). A useful context must both contain relevant facts and be applicable to the question. These are separate properties: overlap with an answer phrase may make a context influential without making its source appropriate.

The source-known experiment approximates an upper bound in which a relevant source technique is already identified. The query-only experiment introduces source selection error. The external router attempts to make an additional decision about whether to use the evidence at all. These stages motivated the experimental controls, but the study does not identify every intermediate causal mechanism. In particular, it does not measure internal reasoning trajectories or prove that the model used a retrieved relationship in the intended way.

## Chapter 3. Method

### 3.1 Dataset, strata, and chronology

The primary analysis retained all 2,500 released CTI-MCQ questions. The public artifact's SHA-256 is `42f8cb0c1d804945cbdcf890411ca6ede3a1e0222fb91966804fed7dc1a19acb`. The authors' [dataset release](https://huggingface.co/datasets/AI4Sec/cti-bench) is the base data source. The study fixed two strata using the published source URL: 1,578 ATT&CK-technique-eligible questions and 922 questions without an ATT&CK-technique source pointer. The latter includes 543 CWE-domain rows and 379 other-source rows. These are source-compatibility labels, not judgments of question quality.

The source-pointer evidence builder found evidence for 1,550 of the 1,578 eligible questions. The remaining 28 stayed in the denominator. All 922 mismatch questions also remained in the full intention-to-treat table. The released artifact determines the count: a discrepancy in finer source-family subtotals printed in the base paper was not resolved by deleting questions or inventing missing categories.

An earlier 500-question study used the first 500 questions of this same artifact; all were ATT&CK-eligible. The full-study protocol was internally frozen on July 31, 2026, at 13:36:32 UTC. It records that the earlier 500-row outcomes had not yet been inspected, although those outputs already existed. The all-2,500 inference followed the freeze. This is internal prospective documentation, not an independently registered untouched benchmark. Development had already involved overlapping items, and model pretraining exposure to the public benchmark cannot be ruled out.

A later sensitivity analysis excluded those 500 IDs, leaving 1,078 eligible and 922 mismatch questions. That analysis was specified after the full outputs existed and is explicitly descriptive. It is included for transparency, not relabeled as a new confirmatory holdout. [Exposure sensitivity](evidence/EXPOSED_ITEM_SENSITIVITY.json)

### 3.2 Evidence construction

The full experiment used the combined Enterprise, Mobile, and ICS ATT&CK 19.1 STIX source, SHA-256 `bca81a8d69218ace1f7b5c706c605d22ad77d64425375b3d7804fdaf87c2ded9`. Earlier exploratory work used a different ATT&CK version and is not pooled into the full-study estimates. The versioned source is obtainable through [MITRE's ATT&CK STIX repository](https://github.com/mitre-attack/attack-stix-data).

The builder converted active knowledge objects and relationships into compact textual candidates. It scored a candidate fact (f) using token overlap with the question and displayed options, a hand-specified fact-kind bonus, and phrase matches against each displayed option:

$$
s(f;q,O)=|T(q,O)\cap T(f)|+b(\operatorname{kind}(f),q,O)
 +7.5\sum_{o\in O}\mathbf{1}\{N(o)\text{ occurs in }N(f)\}.
$$

Here T is the frozen tokenization rule and N is the frozen normalization rule. The kind bonus favors mitigation, detection, procedure, or tactic facts when corresponding lexical cues appear. Both the cues and their weights were fixed. The top six candidates were retained with deterministic tie-breaking. This formula describes the implemented heuristic; it is not a new theorem, an optimized estimator, or a learned causal model. The exact [source-known builder](frozen/builders/build_sec_lord_relationship_evidence_gate.py) and [query-only builder](frozen/builders/build_px003_query_only_prompts.py) are included.

Source-known selection restricted candidates using the technique encoded in the published source URL. Query-only selection searched globally and read the question plus all four option texts. It did not read the correct option label, source URL, or source technique when ranking candidates. Permuting the answer labels changed zero query prompts in the recorded construction audit. This check establishes independence from the label field; it does not remove access to answer-bearing text among the displayed choices.

### 3.3 Conditions, models, and observation units

The six source-known conditions were vanilla answering; selected relationship evidence; technique-description/tactic evidence; facts sampled from another technique; an empty evidence block; and broad cybersecurity seed terms. Each ran on all 2,500 questions. The query-only table ran vanilla and selected relationship evidence on the same questions. Differences in wording and evidence length remain part of these compound treatments; the design is not an exactly token-matched isolation of a single graph relation.

| Model | Frozen revision | Inference settings |
|---|---|---|
| Qwen/Qwen2.5-7B-Instruct | `a09a35458c702b33eeacc393d103063234e8bc28` | Greedy decoding, float16, 4,096 input-token limit, 8 new-token limit, batch size 2 |
| meta-llama/Llama-3.1-8B-Instruct | `0e9e39f249a16976918f6564b8830bc894c89659` | Same settings |

There were 40,000 recorded inferences: 35,000 distinct model/question/condition cells and 5,000 repeated vanilla cells across the source-known and query-only tables. The inferential unit was the paired question within a model and stratum. Repeated vanilla cells and the two model families were not treated as independent additional questions.

### 3.4 Outcome definition and parser correction

The primary outcome is **frozen option-parser accuracy**: the extracted option equals the released correct label. Invalid outputs count as wrong and remain in the denominator. The historical protocol and draft used the shorthand “strict accuracy,” but the executed parser is more permissive than an exact one-line format check. This manuscript corrects that wording without changing the saved results or the frozen code.

The parser removes a leading assistant prefix, inspects the first nonempty line, and first attempts to extract A–D from an option-like prefix. It also accepts a standalone A–D token within the first 20 characters as a fallback. Thus `Answer: B.` is accepted. An invalid count indicates failure to extract an option under those rules, not every departure from the requested output template. The release verifies this parser against all 40,000 raw outputs using the pure function extracted from the [frozen inference runner](frozen/inference/run_sec_lord_relationship_evidence_cloud.py).

### 3.5 Statistical analysis and decision rules

For paired question i, define $D_i=Y_i^{\mathrm{treatment}}-Y_i^{\mathrm{control}}$, where $Y_i$ is binary parser correctness. The estimated difference is $\widehat\Delta=n^{-1}\sum_iD_i$. Question IDs are sorted before deterministic sampling. The frozen implementation reports 95% Wilson intervals for each arm, paired bootstrap intervals from 20,000 resamples for differences, and a two-sided exact McNemar test on the discordant cells. With b treatment-only and c control-only successes, the implemented tail is

$$
p=\min\left(1,\;2\sum_{j=0}^{\min(b,c)}{b+c\choose j}2^{-(b+c)}\right).
$$

Source-known treatment/control p values receive Holm correction across five contrasts within each model and scope. The eligible query-only primary contrast receives Holm correction across the two model tests. These are standard statistical methods, not proposed mathematical contributions. Intervals quantify variation under question-level resampling of the observed table; they do not capture all uncertainty from benchmark construction, source clusters, training contamination, or alternative model configurations.

The decisive primary gates were the effect sizes and interval/test rules stated in Chapter 1, together with an invalid-rate increase limit of three percentage points in each stratum. Full success required both eligible gains and mismatch noninferiority for both models. The analysis retained a separate source-known-only terminal status so that failure of deployment-oriented gates could not be hidden by a favorable pooled average.

### 3.6 External router evaluation

PX-068 used the publicly accessible AthenaBench CKT source at repository revision `39d3a74eaf84b93e21dde0a4b60ddd4f08620eaf`. Of 3,000 questions, three previously inspected during schema work were prospectively excluded from the primary analysis; 2,997 remained, comprising 998 eligible and 1,999 ineligible questions. The router and prompt process were frozen separately before target metrics were opened. [AthenaBench paper](https://arxiv.org/abs/2511.01144), [pinned repository](https://github.com/Athena-Software-Group/athenabench/tree/39d3a74eaf84b93e21dde0a4b60ddd4f08620eaf)

The router trained on the 2,500 CTIBench questions using source-domain labels, without model-answer correctness. It combined word TF-IDF (one- and two-grams) and character TF-IDF (three- to five-grams) with balanced L2 logistic regression and five-fold sigmoid calibration. Each calibration fold refit the complete feature/classifier pipeline. A fixed calibrated eligibility probability of at least .90 selected evidence. Target answers, source labels, and model outputs were excluded from the router input. The [frozen training code](frozen/builders/train_px068_source_router.py) records the implementation. Because AthenaBench extends the CTIBench research lineage, this is external-item testing rather than independent benchmark-producer replication.

Two model outputs per question—vanilla and relationship evidence—supported four evaluated policies: always vanilla, always evidence, router-selected evidence, and an oracle eligibility policy used only as a diagnostic. Routing selected between existing outputs; derived policy rows were not new independent model calls. The source router had to achieve precision at least .90, recall at least .45, false-positive rate at most .05, and treatment coverage between .15 and .45, with additional interval requirements. The harm-mitigation gate required a routed-minus-ungated gain of at least five points on ineligible questions, a positive interval lower bound, and adjusted p below .05.

Athena's source licenses permit attributed noncommercial academic use but do not establish unrestricted raw-data redistribution. This package therefore includes per-question derived correctness, validity, eligibility, and routing indicators, source hashes, code, and reports. It does not republish Athena's question text, sealed answer labels, or raw responses. That permits statistical reproduction while limiting independent raw-to-label verification from this package alone. [License review](licenses/ATHENABENCH_LICENSE_REVIEW.md)

## Chapter 4. Results

### 4.1 Complete primary accounting

All 2,500 questions and every required primary condition were present. Each model's repeated vanilla records agreed on the extracted answer and correctness for all 2,500 questions. This is a useful execution-consistency check under the same setup, not a new scientific replication. Table 1 gives complete-table counts so that the eligible subset cannot substitute for the full artifact.

**Table 1. Correct answers on the complete 2,500-question table.**

| Condition | Llama correct / 2,500 | Qwen correct / 2,500 |
|---|---:|---:|
| Vanilla | 1,618 | 1,571 |
| Source-known relationship evidence | 1,961 | 1,879 |
| Source-known technique-only evidence | 1,634 | 1,590 |
| Random facts | 1,420 | 1,339 |
| Empty evidence | 1,594 | 1,503 |
| Broad seed terms | 1,562 | 1,527 |
| Query-only relationship evidence | 1,767 | 1,629 |

Counts and all intervals are recorded in the [full machine analysis](evidence/FULL_2500_ANALYSIS.json). The pooled query-only difference is positive for each model, but it averages a large eligible benefit with a large mismatch loss. It is therefore insufficient for the registered full-success claim.

### 4.2 Source-known evidence effect

**Table 2. ATT&CK-eligible source-known results, n = 1,578 per model. Differences are percentage points.**

| Model | Vanilla | Rel. evidence | Technique-only | Relationship − vanilla, 95% paired CI | Relationship − technique-only, 95% paired CI |
|---|---:|---:|---:|---:|---:|
| Llama | 970 | 1,334 | 1,013 | +23.07 [20.53, 25.67] | +20.34 [18.00, 22.69] |
| Qwen | 970 | 1,279 | 1,004 | +19.58 [16.92, 22.18] | +17.43 [15.02, 19.84] |

The Llama vanilla comparison had 436 treatment-only successes and 72 control-only successes; Qwen had 411 and 102. Adjusted exact p values were $3.14\times10^{-64}$ and $1.16\times10^{-44}$, respectively. The technique-only adjusted p values were $7.15\times10^{-60}$ and $3.47\times10^{-42}$. Both models passed the registered main-effect and relationship-specificity thresholds.

**Table 3. Relationship evidence minus source-known negative controls, eligible stratum.**

| Model | Random facts, difference [95% CI] | Empty evidence, difference [95% CI] | Broad seeds, difference [95% CI] |
|---|---:|---:|---:|
| Llama | +30.42 [27.76, 33.02] | +23.70 [21.17, 26.24] | +24.65 [22.12, 27.19] |
| Qwen | +30.10 [27.38, 32.83] | +22.18 [19.65, 24.78] | +21.17 [18.50, 23.83] |

Every negative-control comparison had a positive paired lower bound. The strongest interpretable result remains the comparison with technique-only evidence: it reduces the explanation that any useful source description would have produced the same gain. It still does not isolate relation structure from the accompanying fact selection, text content, and prompt wording.

### 4.3 Query-only benefit and mismatch failure

**Table 4. Query-only evidence versus vanilla.**

| Model and stratum | n | Vanilla correct | Evidence correct | Difference, points [95% paired CI] |
|---|---:|---:|---:|---:|
| Llama, eligible | 1,578 | 970 | 1,257 | +18.19 [15.53, 20.85] |
| Qwen, eligible | 1,578 | 970 | 1,189 | +13.88 [10.96, 16.73] |
| Llama, mismatch | 922 | 648 | 510 | −14.97 [−18.00, −11.93] |
| Qwen, mismatch | 922 | 601 | 440 | −17.46 [−20.82, −14.10] |

The eligible query-only contrasts passed their registered threshold and cross-model Holm test: $p=3.81\times10^{-39}$ for Llama and $p=1.11\times10^{-20}$ for Qwen. The mismatch lower bounds were far below the permitted minus-five-point margin. Both models failed noninferiority.

These losses were not driven by unparseable answers: mismatch vanilla and relationship arms had zero invalid outputs for both models. On eligible questions, source-known vanilla/relationship invalid counts were 0/0 for Llama and 1/1 for Qwen; query-only counts were 0/1 and 1/2. All registered relative invalid-rate safety gates passed. The primary terminal decision was therefore **PASS_SOURCE_KNOWN_ONLY**, with eligible query benefit reported separately and full deployment-oriented confirmation denied.

### 4.4 Retrieval and exposure diagnostics

Query-only retrieval recovered the published source technique first for 813 of 1,578 eligible questions and within the six retrieved facts for 1,105. The correct displayed option phrase appeared in retrieved evidence for 785 eligible questions and 94 mismatch questions. These diagnostics were evaluated after construction; the correct label was not a retrieval input. They show that answer-bearing lexical material is a plausible contributor to the effect, and prevent the gain from being described solely as improved abstract reasoning.

The later 1,078-question eligible sensitivity retained the same directional pattern. Source-known gains over vanilla were 22.45 points for Llama and 19.76 for Qwen; query-only gains were 16.88 and 13.08 points. The mismatch table was unchanged. Because this subset analysis was specified after the full outcomes existed, it strengthens descriptive robustness but does not create an untouched confirmatory sample.

### 4.5 External routing did not validate

**Table 5. PX-068 router classification on 2,997 primary questions.**

| Quantity | Observed | Registered requirement | Outcome |
|---|---:|---:|---|
| True positives / false negatives | 904 / 94 | Used in recall | — |
| False positives / true negatives | 1,050 / 949 | Used in precision and false-positive rate | — |
| Precision | 46.26% [44.06%, 48.48%] | At least 90%; lower bound at least 87% | Fail |
| Recall | 90.58% [88.61%, 92.24%] | At least 45%; lower bound at least 40% | Pass |
| False-positive rate | 52.53% [50.33%, 54.71%] | At most 5%; upper bound at most 7% | Fail |
| Treatment coverage | 65.20% | 15%–45% | Fail |

The external router frequently selected evidence for source-ineligible questions. Its source-compatibility gate failed, independent of model-answer formatting. It also failed the registered harm-mitigation comparison.

**Table 6. PX-068 frozen parser-correct counts and failed ineligible harm-mitigation contrast.**

| Model | All-primary vanilla / evidence / routed, n = 2,997 | Ineligible evidence / routed, n = 1,999 | Routed − evidence, points [95% paired CI] |
|---|---:|---:|---:|
| Llama | 434 / 1,255 / 1,127 | 815 / 705 | −5.50 [−6.85, −4.20] |
| Qwen | 62 / 1,663 / 1,109 | 1,060 / 566 | −24.71 [−26.61, −22.81] |

The respective adjusted exact p values were $1.56\times10^{-16}$ and $4.37\times10^{-139}$. Statistical significance here describes a difference in the wrong direction for the proposed policy. It cannot rescue the required positive harm-mitigation effect. The recorded terminal status is **FAIL_ROUTER_CONFIRMATION**. [External machine analysis](evidence/PX068_ANALYSIS.json)

### 4.6 External output-format failures and incomplete follow-up

PX-068 requested `Answer: <A|B|C|D|E>`, an ambiguous template under the executed strict five-option format rule. Many responses repeated pipe-separated labels or included rejected punctuation. Under the intended A–E validity criterion, vanilla invalid rates were 78.98% for Llama and 97.76% for Qwen. These failures make the very large routed-versus-vanilla parser-accuracy gains an inadequate basis for claiming improved semantic cybersecurity knowledge.

A separate historical analyzer defect made the summary validity criterion depend on whether the expected label was E. It classified some syntactically valid E answers as invalid when the gold label differed. The release preserves that legacy summary for exact reproduction and separately provides the intended A–E validity indicators. Correctness and routing classification are not repaired by silently replacing the historical metric. The disclosed issues do not turn the failed router classification or negative harm-mitigation contrast into success. [Incident 04](evidence/PX068_INCIDENT_04.md), [validity diagnostic](evidence/reproduced_counts/PX068_VALIDITY_DIAGNOSTIC.json)

The relative invalid-rate gate also lacked an absolute validity floor. A policy could satisfy that gate against a severely malformed baseline. Passing the recorded gate therefore means only that its formula passed; it does not certify a usable answer process. The three excluded schema-inspected questions did not produce an estimable frozen sensitivity appendix because one had an invalid truth label. They were not imputed or replaced by a post hoc two-question analysis. [Incident 03](evidence/PX068_INCIDENT_03.md)

PX-071 has no completed efficacy result. Its prepared inventory contains 709 CTI questions and 167 CWE controls (141 without duplicate distractors). Technical freezes and probes supply no scientific observations for this paper. [Study status](evidence/STUDY_STATUS.json)

## Chapter 5. Discussion, reproducibility, and conclusion

### 5.1 What the results support

The source-known comparison answers RQ1 positively within the tested artifact, model revisions, and prompts. The observed effect exceeds the registered practical thresholds and remains above the technique-only and negative controls. RQ2 has a split answer: useful eligible-query gains coexist with substantial, reproducible mismatch losses. RQ3 is unsupported: the external router failed its source-compatibility and harm-mitigation requirements.

This pattern gives the study a defensible empirical contribution without requiring every intervention to succeed. A system can benefit from relevant context while being made worse by a broadly applied retrieval rule. Reporting both effects is more useful for evaluating an implementation than selecting whichever pooled or subgroup average happens to be favorable. The external failure also shows why later extensions must satisfy their own decision rules instead of inheriting a positive status from an earlier study.

For practice, the study supports treating source compatibility as an explicit evaluation requirement. It does not supply a validated compatibility detector or authorize deployment of the tested router. The source-known setup assumes provenance that an ordinary system may not possess. Neither source authority, low invalid-output rate, nor a positive full-table average substitutes for a successful mismatch evaluation.

### 5.2 Threats to validity

**Construct validity.** The endpoint is released-label agreement after a particular parser, not open-ended analytical quality or incident-response success. Public questions may contain errors or ambiguous labels. The release reproduces these labels rather than adjudicating each question independently. Retrieved text can contain option phrases directly, so higher scores need not imply stronger internal reasoning. Prompt wording, context length, fact content, and evidence form vary together to some extent.

**Internal validity.** The paired design controls question identity, but earlier work exposed overlapping items and informed the process before the full protocol was frozen. The recorded noninspection statement is internal documentation. The later 1,078-question analysis is post hoc. Deterministic decoding and duplicate vanilla agreement reduce some execution ambiguity but do not create a new external replication.

**Statistical validity.** Question-level bootstrap intervals do not model clustering by source technique or authoring template. The two models answered the same questions, so cross-model agreement is not equivalent to twice as many independent benchmark units. Multiplicity correction covers the registered contrast families; descriptive retrieval diagnostics and later sensitivity analyses must not be treated as additional confirmatory wins.

**External validity.** Only two 7B–8B instruction-tuned model revisions, one inference configuration, one principal public multiple-choice artifact, and one failed external router experiment were completed. Training exposure is unknown. The findings do not establish behavior for current larger models, real-time intelligence reports, multilingual work, long-form decisions, or a deployed agent with tools. A contemporary ATT&CK source may also differ from the knowledge version used when a benchmark question was written.

**Extension validity.** AthenaBench's severe format failures constrain interpretation of its answer statistics, while its licensing constrains what raw material can be redistributed. PX-071 remains unfinished as a scientific test. Neither limitation is cured by the completeness of the primary CTIBench table.

### 5.3 Reproducibility and evidence availability

The accompanying [README](README.md) describes one offline reproduction command. Four gzip files preserve the exact bytes of the original 40,000 CTIBench prediction rows, including prompts, released labels, parsed answers, and raw output. The package includes the frozen analyzers, primary protocol, builder code, and cryptographic provenance. The [provenance inventory](PROVENANCE.json) identifies source commits, original hashes, and every transformation; the package manifest covers release files.

The default reproduction verifies hashes and all CTIBench raw-to-parser correctness, then recomputes every arm count, Wilson interval, paired cell, exact test, adjustment, and decision rule. It explicitly takes archived bootstrap intervals as inputs. A separate `--bootstrap all` mode regenerates all 156 bootstrap intervals from packaged observations with the frozen 20,000-resample procedure. The distinction is recorded in each receipt; a quick arithmetic check is never described as an independent bootstrap rerun.

For PX-068, the included 23,976 policy rows describe 2,997 questions for two models and four derived policies. These permit exact statistical reconstruction and router-assignment checks without republishing restricted question text or answer labels. They do not independently regenerate correctness from Athena raw responses. The archived [terminal audit](evidence/PX068_TERMINAL_AUDIT.json) and source hashes preserve that derivation's provenance. Reproduction here is also not an authorship-independent reimplementation: it intentionally uses the same frozen analysis functions.

No model calls, remote services, or paid inference were used to assemble or statistically reproduce this release. Historical GPU execution is described by the pinned inference configuration, but a complete invoiced historical cost total is not reconstructed here. No cost-efficiency claim follows from the study. Repeating inference requires obtaining the public source material and model weights under their applicable terms and provisioning a compatible environment; the bundled command performs statistical reproduction only.

### 5.4 Conclusion

On the complete CTIBench artifact, selected ATT&CK relationship evidence materially improved option-parser accuracy for compatible technique questions in two tested model families. The improvement exceeded technique-only evidence, while automatic retrieval substantially reduced performance on source-mismatch questions. A separately evaluated external router failed to resolve that problem and suffered additional output-format limitations.

The completed Praxis contribution is a reproducible account of evidence benefit, applicability limits, and a failed attempted remedy. A broader claim of reliable deployment or a successful new defense is unsupported. Any subsequent work on source-compatible retrieval should preserve this paper's positive and negative evidence while establishing a valid external outcome protocol before collecting new efficacy results.

## References

Alam, M. T., Bhusal, D., Nguyen, L., & Rastogi, N. (2024). *CTIBench: A benchmark for evaluating LLMs in cyber threat intelligence*. Advances in Neural Information Processing Systems, 37, 50805–50825. [Primary paper](https://arxiv.org/abs/2406.07599). [Official data](https://huggingface.co/datasets/AI4Sec/cti-bench).

Alam, M. T., Bhusal, D., Ahmad, S., Rastogi, N., & Worth, P. (2025). *AthenaBench: A dynamic benchmark for evaluating LLMs in cyber threat intelligence*. Annual Computer Security Applications Conference Workshops, 443–450. [DOI](https://doi.org/10.1109/ACSACW69556.2025.00072). [Open paper](https://arxiv.org/abs/2511.01144).

Hamzic, D., Skopik, F., Landauer, M., Wurzenberger, M., & Rauber, A. (2026). *Beyond RAG for cyber threat intelligence: A systematic evaluation of graph-based and agentic retrieval*. Preprint. [Primary source](https://arxiv.org/abs/2604.11419).

Lekssays, A., Shukla, U., Sencar, H. T., & Parvez, M. R. (2025). *TechniqueRAG: Retrieval augmented generation for adversarial technique annotation in cyber threat intelligence text*. Findings of ACL 2025, 20913–20926. [DOI and paper](https://aclanthology.org/2025.findings-acl.1076/).

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). *Retrieval-augmented generation for knowledge-intensive NLP tasks*. Advances in Neural Information Processing Systems, 33. [Primary paper](https://arxiv.org/abs/2005.11401).

Strom, B. E., Applebaum, A., Miller, D. P., Nickels, K. C., Pennington, A. G., & Thomas, C. B. (2020). *MITRE ATT&CK: Design and philosophy* (MP180360R1). The MITRE Corporation. [Primary report](https://www.mitre.org/news-insights/publication/mitre-attck-design-and-philosophy).

## Data and software attribution

CTIBench data are attributed to the original authors and provided under the source release's CC BY-NC-SA 4.0 terms. ATT&CK material is attributed to The MITRE Corporation and retains its applicable source terms. **This research utilized software developed by Athena Security Group.** AthenaBench raw source redistribution is not assumed. See [source and license notes](licenses/SOURCES_AND_LICENSES.md) for artifact-specific boundaries. This manuscript and package report completed experiments; neither publication acceptance nor institutional thesis approval is claimed.
