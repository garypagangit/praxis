# Source Compatibility Governs the Value of Retrieved Cyber-Threat Evidence

## A paired CTIBench study with a failed external routing test

**Research project: Gary Pagan | Final experiment report: September 17, 2026**

**Provenance and review status.** This AI-assisted report consolidates completed experiments and their archived evidence for author and advisor review. The statistical findings are complete within the stated scope. Human authorship review, originality assessment, academic eligibility, and submission approval remain **PENDING**. No new model inference was performed for this closure. The report preserves the source study's failed endpoints.

## Abstract

Retrieved cybersecurity information can improve an answer while remaining unsuitable for other questions served by the same system. This study evaluated relationship evidence on all 2,500 released CTIBench CTI-MCQ questions using fixed Llama-3.1-8B-Instruct and Qwen2.5-7B-Instruct models. The design distinguished source-known evidence selection from retrieval using only the question and displayed options, and separated 1,578 ATT&CK-technique-eligible questions from 922 source-mismatch questions. Source-known relationship evidence improved parser accuracy over vanilla by 23.07 percentage points for Llama and 19.58 for Qwen; gains over technique-only evidence were 20.34 and 17.43 points. Query-only evidence improved eligible accuracy by 18.19 and 13.88 points but reduced mismatch accuracy by 14.97 and 17.46 points. Both models failed the mismatch noninferiority requirement. An external source router tested on 2,997 AthenaBench questions achieved only 46.26% precision and a 52.53% false-positive rate and failed its registered confirmation criteria. Severe external output-format failures further restrict answer-quality interpretation. The result is a bounded empirical finding about evidence access and applicability, not a successful protective router. Offline statistical reproduction verified the archived observations and decisions. Prior exposure of 500 items, answer-option access, correlated benchmark units, and public external-data limitations remain explicit.

**Keywords:** cyber threat intelligence; retrieval; source compatibility; evidence selection; paired evaluation; reproducibility.

## 1. Problem and research questions

An analyst-facing language model may benefit from authoritative reference material that its parameters do not reliably recall. The engineering difficulty is deciding which material applies. A correct ATT&CK fact about a technique does not necessarily help answer a question drawn from another knowledge source. A favorable average across all questions can conceal a harmful subgroup, and a system that recognizes a source in one benchmark may fail after the question distribution changes.

This work asks three questions. **RQ1:** Given the published source technique, does selected relationship evidence improve accuracy beyond vanilla answering and a technique-description baseline? **RQ2:** When retrieval loses that source pointer, does the eligible-question benefit remain, and is performance preserved outside the supported source domain? **RQ3:** Can an independently frozen source-compatibility router make evidence use reliable on an external collection?

The applied object is an evidence-selection process. The main experiment changes the context delivered to fixed language models. A later extension trains a separate source classifier. Neither stage establishes a new general retrieval architecture. The defensible contribution is the measured combination of access advantage, treatment-specific comparisons, mismatch harm, and failed transport of the attempted remedy. Whether that bounded empirical contribution satisfies a particular Praxis requirement is an academic scope decision, not a consequence of a statistical PASS.

The terminal outcomes are `PASS_SOURCE_KNOWN_ONLY` for the primary study and `FAIL_ROUTER_CONFIRMATION` for PX-068. PX-071 has no completed scientific result in the released evidence. These states constrain every claim in this report. [Study status](../../papers/20260914/01_cti/evidence/STUDY_STATUS.json)

## 2. Related work and contribution boundary

Retrieval-augmented generation already combines external information with a generator. CTIBench supplies the public CTI tasks used here; AthenaBench extends that benchmark lineage. This study claims neither benchmark authorship nor the invention of retrieval. The contribution concerns a particular controlled experiment over those resources. [Lewis et al., 2020](https://arxiv.org/abs/2005.11401); [Alam et al., 2024](https://arxiv.org/abs/2406.07599v3); [Alam et al., 2025/2026](https://arxiv.org/abs/2511.01144v2)

**TechniqueRAG** already uses retrieval, LLM reranking, and generator fine-tuning for adversarial-technique annotation. Its Sections 3.1–3.4 therefore preclude novelty claims based on CTI retrieval or ATT&CK-aware context alone. The present endpoint is released-label multiple-choice accuracy with explicit source-access and mismatch conditions; no head-to-head superiority comparison was run. [Lekssays et al., 2025](https://aclanthology.org/2025.findings-acl.1076.pdf)

**Beyond RAG for CTI** compares vector, graph, agentic, and hybrid retrieval and reports question-type-dependent gains, losses, and abstention failures. Section 4.1.2 and Tables 11–14 directly overlap a generic “retrieval helps and hurts” argument. The narrower distinction here is a paired source-known versus question-and-options design with frozen compatibility gates and an unsuccessful external router. Distinction does not by itself certify originality. [Hamzić et al., 2026](https://arxiv.org/html/2604.11419v1#S4.SS1.SSS2)

The September 2026 **Ahlert** preprint combines hybrid evidence retrieval, stored provenance, and environment grounding to generate hunt leads. Provenance-aware CTI assistance is therefore also established territory. Its hunt-lead task differs from this study's fixed-choice compatibility experiment; that difference supplies scope, not proof of superiority or priority. [Prakash et al., 2026, Sections II-A–II-D](https://arxiv.org/html/2609.08790v1#S2)

The [closest-prior comparison](PRIOR_WORK.md) records exact source locations and unresolved overlap. The practical contribution retained here is evidence about when one implemented process fails, with enough observations and code to inspect that conclusion.

## 3. Methods

### 3.1 Data, strata, and chronology

The analysis retained all **2,500** questions in the pinned CTIBench CTI-MCQ artifact. Published source URLs defined **1,578 ATT&CK-technique-eligible** questions and **922 source-mismatch** questions before the full evaluation's outcomes were inspected according to its internal freeze record. The artifact, ATT&CK source, prompts, runner, and builder hashes are preserved in the [freeze](../../papers/20260914/01_cti/evidence/FULL_2500_FREEZE.json). Source compatibility is a design stratum, not an adjudication of whether an individual question is good.

The chronology requires qualification. Earlier development had exposed **500** overlapping question IDs. The full evaluation was therefore not an untouched first encounter with every item. A later analysis excluded those IDs, leaving 1,078 eligible and the same 922 mismatch questions; it was specified after full outputs existed. Its role is sensitivity analysis, not a newly created confirmatory holdout. [Exposure record](../../papers/20260914/01_cti/evidence/EXPOSED_ITEM_SENSITIVITY.json)

There were **40,000 recorded CTIBench responses**, representing 35,000 distinct model/question/condition cells and 5,000 repeated vanilla cells. Each model contributed six source-known conditions and two query-only conditions on every question. The inferential unit is the paired question within a model and stratum. Repeated conditions and two model families do not turn the study into 40,000 independent questions.

### 3.2 Evidence access and comparison conditions

The evidence builder selected ATT&CK relationship facts, including procedure, mitigation, detection, and tactic information. Its frozen heuristic combines token overlap, fact-kind bonuses, and option-phrase matches, retaining six candidates with deterministic tie-breaking. The source-known route restricts candidates using the technique supplied by the benchmark's published source URL. It therefore receives information unavailable to ordinary question-only retrieval.

Query-only retrieval instead searches globally using the question and **all displayed answer options**. It does not read the correct answer label or source pointer when ranking candidates. A recorded label-permutation check changed zero query prompts. This is label-field independence; it does not remove answer-bearing lexical information from the options. The correct displayed option phrase appeared in retrieved material for 785 eligible and 94 mismatch questions, a diagnostic that limits reasoning claims. [Construction disclosure](../../papers/20260914/01_cti/evidence/FULL_2500_FREEZE.json)

The six source-known conditions were vanilla, selected relationship evidence, technique-only evidence, random facts from another technique, an empty evidence block, and broad cybersecurity seed terms. The query-only experiment compared vanilla with selected relationship evidence. The technique-only comparison tests whether the relationship treatment adds value beyond a simpler relevant description. Negative controls test weaker explanations involving arbitrary or empty cybersecurity context. Evidence length, selected content, and wording are not perfectly matched, so this is a compound treatment rather than an isolated test of graph structure.

### 3.3 Models, decoding, and outcome definition

The frozen models were Qwen/Qwen2.5-7B-Instruct revision `a09a35458c702b33eeacc393d103063234e8bc28` and meta-llama/Llama-3.1-8B-Instruct revision `0e9e39f249a16976918f6564b8830bc894c89659`. Historical inference used greedy decoding, float16, a 4,096-token input limit, eight new tokens, and batch size two. No generator weights were trained by the primary evidence experiment.

The outcome is **frozen option-parser accuracy**: the extracted A–D option equals the released label. Invalid responses count as wrong and stay in the denominator. The historical shorthand “strict accuracy” is corrected here because the executed parser accepts some punctuation and fallback forms. It examines the first nonempty line, tries an option-like prefix, and may accept a standalone option token within the first 20 characters. Consequently, an invalid-output count does not count every format deviation. The [reproduction driver](../../papers/20260914/01_cti/reproduce.py) extracts the executed parser from the frozen inference source and checks all archived raw outputs.

### 3.4 Statistical tests and decision rules

For each paired question, the analysis subtracts control correctness from treatment correctness. Mean differences use every question in the specified stratum. The frozen analysis provides Wilson arm intervals, paired bootstrap difference intervals using 20,000 resamples, and exact two-sided McNemar tests of discordant pairs. Holm corrections cover the registered contrast families. These standard methods describe question-level variability; they do not model every source or template dependency.

For each model, the source-known main gate required at least a **five-percentage-point** advantage over vanilla and a **three-point** advantage over technique-only evidence, positive paired interval lower bounds, and adjusted tests below .05. Eligible query-only retrieval required at least a three-point gain. Mismatch noninferiority required its paired lower bound to exceed **−5 points**. Relative invalid-rate safety was also checked. Full confirmation required the eligible benefit and mismatch safety conditions in both models. The source-known-only terminal state preserves a positive restricted finding when deployment-oriented criteria fail. [Primary protocol](../../papers/20260914/01_cti/protocol/FULL_2500_PREREGISTRATION.md)

### 3.5 External router test

PX-068 evaluated **2,997** primary AthenaBench questions after excluding three items inspected during schema work. The primary set contained 998 eligible and 1,999 ineligible questions. The source classifier learned CTIBench source-domain labels using word and character TF-IDF features, balanced logistic regression, and five-fold sigmoid calibration. Its threshold was fixed at .90. Model-answer correctness and external answer labels were not training inputs.

Two saved model outputs per external question—vanilla and evidence—supported four derived policies: always vanilla, always evidence, routed selection, and a diagnostic oracle. The policy rows do not constitute four fresh model executions. The source gate required precision of at least .90, recall of at least .45, false-positive rate at most .05, and coverage between .15 and .45, together with interval requirements. The ineligible harm-mitigation gate required routed accuracy to exceed ungated evidence by at least five points with supporting interval and test criteria. [External protocol](../../papers/20260914/01_cti/protocol/PX068_PROSPECTIVE_PROTOCOL.md)

## 4. Results

### 4.1 Compatible evidence improved accuracy

Both models passed the source-known benefit and relationship-specificity gates. Table 1 reports paired effects; intervals are the archived deterministic bootstrap intervals, previously fully regenerated and retained unchanged here.

**Table 1. Source-known results on 1,578 eligible questions per model.**

| Model | Vanilla / relationship / technique-only correct | Relationship minus vanilla, points [95% CI] | Relationship minus technique-only, points [95% CI] |
|---|---:|---:|---:|
| Llama | 970 / 1,334 / 1,013 | +23.07 [20.53, 25.67] | +20.34 [18.00, 22.69] |
| Qwen | 970 / 1,279 / 1,004 | +19.58 [16.92, 22.18] | +17.43 [15.02, 19.84] |

All relationship comparisons against the random-fact, empty-block, and broad-seed controls had positive paired lower bounds. This supports the selected evidence treatment within the source-known setup. It does not identify relationship structure as the sole active ingredient. [Primary analysis](../../papers/20260914/01_cti/evidence/FULL_2500_ANALYSIS.json)

**Trace of one eligible improvement.** Llama's paired vanilla/relationship table contains 898 questions correct under both, 436 correct only with relationship evidence, 72 correct only under vanilla, and 172 wrong under both. These cells total 1,578. They produce 970 vanilla successes and 1,334 treatment successes, so the net gain is `100 × (436 − 72) / 1,578 = 23.0672` percentage points. The stored paired interval is [20.53, 25.67] points. The new [count trace](COUNT_TRACE.json) independently reconstructs these cells from packaged prediction rows.

### 4.2 Query-only gains did not satisfy mismatch safety

**Table 2. Query-only relationship evidence versus vanilla.**

| Model and stratum | Questions | Vanilla → evidence correct | Difference, points [95% CI] |
|---|---:|---:|---:|
| Llama, eligible | 1,578 | 970 → 1,257 | +18.19 [15.53, 20.85] |
| Qwen, eligible | 1,578 | 970 → 1,189 | +13.88 [10.96, 16.73] |
| Llama, mismatch | 922 | 648 → 510 | −14.97 [−18.00, −11.93] |
| Qwen, mismatch | 922 | 601 → 440 | −17.46 [−20.82, −14.10] |

Both eligible-query gates passed and both mismatch noninferiority gates failed. The four mismatch arm/model combinations had zero invalid responses. Thus the mismatch loss cannot be dismissed as a consequence of unparseable answers under the frozen parser.

**Trace of one mismatch loss.** Llama's paired mismatch table contains 467 both-correct, 43 evidence-only-correct, 181 vanilla-only-correct, and 231 both-wrong questions. The arm totals are 510 and 648, and `100 × (43 − 181) / 922 = −14.9675` percentage points. Its interval lower bound, −18.00 points, fails the registered −5-point margin. The treatment sometimes helps individual mismatch questions, but those gains do not offset the larger number it harms. [Count trace](COUNT_TRACE.json)

On all 2,500 questions, query-only correct counts increased from 1,618 to 1,767 for Llama and 1,571 to 1,629 for Qwen. Those positive pooled differences combine eligible gains with mismatch losses. They cannot satisfy a separate harm constraint by averaging it away. The terminal primary result remains **source-known-only confirmation**.

### 4.3 The external router failed

**Table 3. PX-068 source classification and policy outcomes.**

| Measure | Observed | Registered requirement | Outcome |
|---|---:|---:|---|
| Precision | 904 / 1,954 = 46.26% | At least 90% | Fail |
| Recall | 904 / 998 = 90.58% | At least 45% | Pass |
| False-positive rate | 1,050 / 1,999 = 52.53% | At most 5% | Fail |
| Evidence coverage | 1,954 / 2,997 = 65.20% | 15%–45% | Fail |
| Llama ineligible routed minus evidence accuracy | −5.50 points [−6.85, −4.20] | At least +5 points | Fail |
| Qwen ineligible routed minus evidence accuracy | −24.71 points [−26.61, −22.81] | At least +5 points | Fail |

The ineligible routed/evidence counts were 705/815 for Llama and 566/1,060 for Qwen, each over 1,999 questions. The classification failure is visible without interpreting model answers. The harmful direction of the policy contrast also fails its intended purpose. Neither favorable comparisons against vanilla nor statistical significance in an unfavorable direction repairs those gates. [External analysis](../../papers/20260914/01_cti/evidence/PX068_ANALYSIS.json)

### 4.4 External format defects and unfinished work

Under the intended A–E validity criterion, external vanilla invalid counts were 2,367/2,997 for Llama (**78.98%**) and 2,930/2,997 for Qwen (**97.76%**). The ambiguous requested answer template and rejected response forms make gains over that baseline unreliable evidence of improved semantic CTI understanding. The historical analyzer also had a gold-label-dependent E-validity defect. The package reproduces its legacy summary while separately reporting intended A–E validity. It does not silently substitute a corrected summary and declare success. [Validity diagnostic](../../papers/20260914/01_cti/evidence/reproduced_counts/PX068_VALIDITY_DIAGNOSTIC.json); [incident record](../../papers/20260914/01_cti/evidence/PX068_INCIDENT_04.md)

The relative invalid-rate gate lacked an absolute validity floor. Its passage therefore cannot establish a usable external answer process. PX-071's prepared inventory and operational freezes contribute no completed efficacy estimate. Its status remains unfinished, and no table treats it as independent confirmation.

## 5. Discussion and limitations

RQ1 receives a bounded positive answer. Selected relationship evidence improved source-known option-parser accuracy beyond vanilla and technique-only controls in both tested families. RQ2 receives a split answer: removing the source pointer retained eligible benefit while exposing substantial mismatch harm. RQ3 receives a negative answer under the registered test: the router failed source compatibility and harm mitigation.

The actionable implication is a requirement for evaluation, not a validated deployment policy. A system assessment should distinguish the information granted to retrieval, test compatibility strata separately, and preserve failed intervention gates. Source-known gains should not be advertised as gains achievable when source selection is unresolved. Nor should an aggregate score replace an explicit noninferiority constraint on questions outside the source domain.

Several limitations constrain the contribution. First, the outcome is agreement with released multiple-choice labels after a particular parser. It does not measure analyst productivity, open-ended explanation quality, or incident-response safety. Benchmark ambiguity and labeling errors were not independently adjudicated. Second, access to all option texts and retrieved option phrases means lexical answer support can explain part of the gain. Internal reasoning, multi-hop inference, and relationship-specific causation were not isolated.

Third, 500 questions had prior development exposure. The later exclusion analysis cannot retroactively create untouched confirmation. Fourth, question-level resampling does not account for source-technique or authoring-template clusters. The same questions answered by two models remain correlated observations. Fifth, only two frozen 7B–8B model revisions and one principal multiple-choice artifact were tested. Training contamination, changing source versions, alternative prompts, larger models, and deployed tool workflows remain unmeasured.

Finally, the external study has both output-format and evidence-release limits. Its public package contains derived correctness and validity indicators rather than restricted Athena raw questions and answers. Statistical reconstruction from those indicators does not independently verify their raw derivation. The failed external test limits generalization; it does not erase the primary paired observations. Equally, the primary benefit does not excuse the failed extension.

## 6. Reproducibility and closure

The existing release preserves exact compressed CTIBench prediction bytes, frozen builders and analyzers, protocols, provenance, and source terms. On September 17, the offline reproduction command passed again: **31** source artifacts were hash-verified, **40,000** CTIBench raw-output/parser/correctness rows were checked, and **23,976** external derived policy rows were verified. Every nonbootstrap statistic and both final statistical payloads matched. This fresh run used **156 archived bootstrap intervals as inputs** and regenerated zero; its [receipt](reproduction_counts/REPRODUCTION_RECEIPT.json) states that boundary.

The separately retained [full reproduction receipt](../../papers/20260914/01_cti/evidence/reproduced_full/REPRODUCTION_RECEIPT.json) records prior regeneration of all 156 intervals using the frozen 20,000-resample procedure. That prior result is not relabeled as new work. Both modes use the frozen analysis implementation, so neither is an independent statistical reimplementation or a new model replication. The fresh count trace independently verifies two decisive paired tables without importing the analysis functions.

Run from the archived package directory:

```text
python -B reproduce.py --bootstrap none --output <new-output-directory>
```

The [evidence ledger](EVIDENCE.json) provides repository-relative paths, SHA-256 hashes, and exact JSON pointers for the headline findings. The [verification receipt](VERIFICATION.json) covers this closure's checks. CTIBench and ATT&CK attribution and the existing Athena redistribution boundary remain in force. This research utilized software developed by Athena Security Group. No new paid inference, cloud job, or model execution was needed for closure.

## 7. Conclusion

Compatible source-known relationship evidence materially improved CTIBench parser accuracy in two fixed models. Query-only retrieval retained benefit on eligible questions but caused substantial mismatch losses, and a prospectively evaluated external router failed to solve the problem. The completed result is an auditable empirical account of a useful evidence treatment and its applicability boundary. It supports neither a successful new protective algorithm nor general deployment safety. The experiment and statistical record can be closed while human assessment of originality, applied contribution, and academic use remains pending.

## References

- Alam, M. T., Bhusal, D., Nguyen, L., and Rastogi, N. (2024). *CTIBench: A Benchmark for Evaluating LLMs in Cyber Threat Intelligence*. [Primary paper, v3](https://arxiv.org/abs/2406.07599v3).
- Alam, M. T., Bhusal, D., Ahmad, S., Rastogi, N., and Worth, P. (2025; revised 2026). *AthenaBench: A Dynamic Benchmark for Evaluating LLMs in Cyber Threat Intelligence*. [Primary paper, v2](https://arxiv.org/abs/2511.01144v2).
- Hamzić, D., Skopik, F., Landauer, M., Wurzenberger, M., and Rauber, A. (2026). *Beyond RAG for Cyber Threat Intelligence: A Systematic Evaluation of Graph-Based and Agentic Retrieval*. Preprint. [Primary paper, v1](https://arxiv.org/html/2604.11419v1).
- Lekssays, A., Shukla, U., Sencar, H. T., and Parvez, M. R. (2025). *TechniqueRAG: Retrieval Augmented Generation for Adversarial Technique Annotation in Cyber Threat Intelligence Text*. Findings of ACL, 20913–20926. [Primary paper](https://aclanthology.org/2025.findings-acl.1076/).
- Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS. [Primary paper](https://arxiv.org/abs/2005.11401).
- Prakash, A., Nour, B., Pourzandi, M., Assi, C., and Debbabi, M. (2026). *Evidence-Grounded Retrieval for Investigation Hunt Lead Generation from CTI Reports*. Preprint. [Primary paper, v1](https://arxiv.org/html/2609.08790v1).
