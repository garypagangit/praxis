# CTI evidence, completion and Praxis suitability

Reviewed 2026-09-14. **CTI is a serious top-three candidate and already has a substantial completed empirical result plus a full Praxis draft.** Its strongest completed result is the July 31 full-2,500 CTIBench study, **`PASS_SOURCE_KNOWN_ONLY`**. The prospective external router study, PX-068, completed with **`FAIL_ROUTER_CONFIRMATION`**. The later parser-free external replication, PX-071, has substantial source preparation and operational engineering but no completed scientific result located in this audit.

For an existing, bounded mechanism-and-harm paper, I provisionally rank CTI above 008 on effect breadth and replication across model families. 008 has the stronger newly completed end-to-end evidence-closure package. Neither program demonstrates that its proposed safety intervention succeeded. This is a comparison of CTI and 008, not a completed ranking of every historical experiment; the coordinator owns that wider review.

The scope was local reports, preserved Git objects, machine summaries and manuscript content, with primary-source verification of the base paper and closest literature. No AWS operation, inference, candidate execution, modification of older artifacts, new significance test or full raw-response reanalysis was performed. DOCX text and tables were inspected; this is not a fresh visual-layout approval. Exact hashes, selected machine results and five passing integrity spot checks are in [CTI_REVIEW.json](C:/Users/garyp/OneDrive/Documents/codex/reports/praxis_paper_008_20260914/CTI_REVIEW.json).

## The completed research question and contribution

The defensible central question is: **When does relationship-specific ATT&CK evidence improve a frozen language model's CTI answers, and when does supplying that evidence cause harm because the question comes from a different source domain?**

The completed protocol separates six questions: relationship evidence versus vanilla; relationships versus technique descriptions; negative evidence/format controls; query-only retrieval without published source pointers; non-ATT&CK mismatch safety; and transfer of a prospective source-compatibility router to another corpus.

The process modification is concrete: construct relationship facts from a fixed ATT&CK snapshot, distinguish an oracle-provenance retrieval arm from a query-only arm, compare evidence forms within each model/question, and test source mismatch as a binding safety endpoint. The source-conflict taxonomy and prospective router are evaluated separately from answer quality. There is no new training algorithm or mathematical theorem demonstrated here. The useful contribution is a controlled empirical mechanism and safety boundary, including a failed attempt to turn that boundary into an automatic router.

The public base is [CTIBench](https://arxiv.org/abs/2406.07599), whose [author repository](https://github.com/maveryn/cti-bench) supplies CTI-MCQ data and evaluation code. The final study retains its full 2,500-question release, rather than only the earlier first-500 scaffold. Released row URLs define 1,578 ATT&CK-technique questions and 922 non-ATT&CK questions. The final retrieval corpus is a frozen ATT&CK 19.1 multidomain bundle; the earlier 106/500-row studies used Enterprise 12.0. MITRE provides [versioned ATT&CK source data](https://github.com/mitre-attack/attack-stix-data).

The full study pins Qwen2.5-7B-Instruct revision `a09a35458c702b33eeacc393d103063234e8bc28` and Llama-3.1-8B-Instruct revision `0e9e39f249a16976918f6564b8830bc894c89659`. The CTI-MCQ parquet hash is `42f8cb0c1d804945cbdcf890411ca6ede3a1e0222fb91966804fed7dc1a19acb`; the final ATT&CK bundle hash is `bca81a8d69218ace1f7b5c706c605d22ad77d64425375b3d7804fdaf87c2ded9`. These are recorded source identities, not a claim that the present audit freshly downloaded or rebuilt both corpora.

## Final primary result: substantial benefit and substantial mismatch harm

These are the existing frozen results, not newly calculated estimates. Intervals are the registered deterministic 20,000-replicate row-paired bootstrap intervals; exact McNemar tests and the frozen Holm families accompany the machine analysis.

| Comparison | Llama | Qwen |
|---|---|---|
| Source-known relationship evidence versus vanilla, 1,578 ATT&CK questions | 1,334/1,578 versus 970/1,578; **+23.1 pp**, CI **[20.5,25.7]** | 1,279/1,578 versus 970/1,578; **+19.6 pp**, CI **[16.9,22.2]** |
| Relationship evidence versus technique-only, same 1,578 questions | **+20.3 pp**, CI **[18.0,22.7]** | **+17.4 pp**, CI **[15.0,19.8]** |
| Query-only relationship evidence versus vanilla, same 1,578 questions | 1,257 versus 970 correct; **+18.2 pp**, CI **[15.5,20.8]** | 1,189 versus 970 correct; **+13.9 pp**, CI **[11.0,16.7]** |
| Query-only mismatch treatment versus vanilla, 922 non-ATT&CK questions | 510/922 versus 648/922; **−15.0 pp**, CI **[−18.0,−11.9]** | 440/922 versus 601/922; **−17.5 pp**, CI **[−20.8,−14.1]** |

Benefit gates A–D and all registered invalid-output safety scopes passed in both families. Mismatch non-inferiority failed in both. The source-versus-vanilla Holm-adjusted p-values are approximately 3.14e-64 and 1.16e-44; the cross-model adjusted query-only p-values are 3.81e-39 and 1.11e-20. These small values do not override the failed safety gate.

The run contains **40,000 inference rows**, comprising **35,000 distinct model/question/condition cells and 5,000 duplicate-vanilla reproducibility rows**. They are not 40,000 independent experimental units. The independently executed vanilla copies agree on all 2,500 parsed answers and correctness labels in each model.

The primary [machine analysis](C:/Users/garyp/OneDrive/Documents/codex/reports/relationship_evidence_cti_compliance/confirmatory_closeout_20260731/full_2500_analysis/analysis.json) and its [archived separate rerun](C:/Users/garyp/OneDrive/Documents/codex/reports/relationship_evidence_cti_compliance/confirmatory_closeout_20260731/full_2500_root_audit/analysis.json) are byte-identical at `c6a949b82adfe00abb3b3f1acbe04dc9277bda3b2d062a42e89a29d6cce3e181`; both comparison CSVs are also byte-identical. This audit verified those equalities. The historical rerun used the same analyzer; it is deterministic reproduction, not an independent implementation or dataset replication.

## The router and external replication do not turn this into a successful defense

**PX-068 completed on 2,997 retained AthenaBench questions and failed.** Its frozen router accepted 1,954 questions. Precision was 46.26% against a minimum 90%; false-positive rate was 52.53% against a maximum 5%; treatment coverage was 65.20% against a 15%–45% interval. Recall passed, but did not compensate for the failed requirements.

On 1,999 ineligible questions, routed-minus-ungated accuracy was **−5.50 pp**, CI **[−6.85,−4.20]**, for Llama and **−24.71 pp**, CI **[−26.61,−22.81]**, for Qwen. The absolute baseline format failures were also severe: an independent mechanical audit reported vanilla invalid rates of 78.98% and 97.76%. The relative invalid-rate safety gate could pass despite this. Consequently, nominal strict-endpoint gains cannot establish semantic answer improvement. The [terminal completeness audit](C:/Users/garyp/OneDrive/Documents/codex/reports/relationship_evidence_cti_compliance/px068_source_compatibility_router_20260731/PX068_TERMINAL_COMPLETENESS_AUDIT_V3_20260801.json) retains the failed result and confirms all registered gates without mismatches. Its referenced analysis hash matches the local result in this audit.

**PX-071 is an unfinished follow-on, not another positive result.** Its planned SecKnowledge-Eval external test uses forced-choice sequence likelihoods, four cyclic answer rotations, two model families, 709 public adversarial CTI items, and 167 CWE control items. The 26 control items with duplicate distractors remain a disclosed sensitivity, with 141 distinct-option items in the clean control. There are 7,008 answer-free prompt rows per model, not 7,008 independent questions. Its provenance gate is an oracle gate, not a learned production router.

The inspected August preparation and September 2 V16 receipts certify source/build or model-free operational work. The latest inspected probe ledger contains an attempt-reservation event, not a completed inference/result receipt. No terminal likelihood analysis or completed external efficacy result was located. Historical `DRAFT_UNFROZEN_NOT_RUN` prose is stale as a literal freeze-state description because later signed operational freezes exist; its **absence of a scientific result** remains the relevant boundary. This was not a live cloud-state audit.

## Which manuscript is near completion?

The strongest existing document is [the August 18 full Praxis draft](C:/Users/garyp/OneDrive/Documents/codex/output/doc/top_three_praxis_final_20260818/PX003_PX034_Final_Praxis_Paper_20260818_DRAFT_QA.docx), titled *When Retrieved Cyber-Threat Evidence Helps—and When It Hurts*. It incorporates the full-2,500 study, failed PX-068 router and pending PX-071. It already has research questions, methods, results, limitations, references and an evidence map. It is explicitly `DRAFT_QA`; its filename and a repository commit containing “Publish” do not establish institutional approval or external publication.

The older [LaTeX article](C:/Users/garyp/OneDrive/Documents/codex/paper/relationship_evidence_cti/main.tex), last path-specific commit June 22, contains the May 106-row study and omits the later full-data result. The [July 14 manuscript](C:/Users/garyp/OneDrive/Documents/codex/reports/praxis_research_manuscripts_20260714/PX003_PX034_CTI_EVIDENCE_ROUTING_RESEARCH_MANUSCRIPT_20260714.md) adds Qwen and the first-500 audit but predates the final full-data and failed-router result. Neither should be treated as the latest final scientific account. The portfolio registry's 106-row summary is similarly stale.

Several authoritative report Markdown files are absent from this checkout but present as preserved Git objects at commit **`720d9e76a6142aae95ad1c31153d9ac38499fbb0`**. This audit read those objects without restoring or changing the checkout:

| Git-relative artifact | SHA-256 of exact Git bytes |
|---|---|
| `reports/relationship_evidence_cti_compliance/confirmatory_closeout_20260731/PX003_PX034_FINAL_FULL_2500_PRAXIS_REPORT_20260731.md` | `52a266cd3b48a9f7c35e247e53b76d21646679f9f2e071cb420930afb257c9ef` |
| `reports/relationship_evidence_cti_compliance/confirmatory_closeout_20260731/PX003_PX034_FULL_2500_SEPARATE_DETERMINISTIC_RERUN_AUDIT_20260731.md` | `85c3c57841743fff8e97d10a0e3584280979bba64c380cc316f9e07e779bd6cc` |
| `reports/relationship_evidence_cti_compliance/px068_source_compatibility_router_20260731/PX068_FINAL_PRAXIS_REPORT_20260801.md` | `dbcb39084a82a1d7e5b2f17717caf2d70a537e5c1c402bb96a7381c632fbaaf9` |

All local manuscript and machine-result hashes, including the August DOCX, are recorded in [the evidence receipt](C:/Users/garyp/OneDrive/Documents/codex/reports/praxis_paper_008_20260914/CTI_REVIEW.json). A paper package should expose these exact source artifacts coherently instead of relying on whatever happens to be checked out.

## Material boundaries for a defensible final paper

1. **Literal parser wording needs correction.** The full-study frozen runner, verified at hash `cd94f3da527c0e35ce2c408b2d03865d62cb195c608656eb11a08ccc187178f9`, takes an option letter near the beginning of the first nonempty line and permits more than exact `Answer: X` syntax. Call the primary endpoint *accuracy under the frozen option parser*, not literal one-line schema compliance. This does not erase the observed primary gains; it defines what was actually measured. PX-068 used a different, more restrictive parser and has its separately documented confound.
2. **Mixed exposure remains.** Of 1,578 ATT&CK questions, 500 had been used previously. The 1,078-item sensitivity was specified after outputs existed and is not a fresh confirmatory holdout. The July 31 freeze chronology is internal, not an external registration or independent proof of noninspection.
3. **Evidence access is part of the treatment.** The source-known arm uses published provenance. Query-only retrieval sees all four options. Correct-option phrases appeared in retrieved evidence for 785/1,578 ATT&CK rows. Benefits therefore do not establish latent relational reasoning.
4. **No qualified deployable safety router exists.** The final mismatch gate and prospective router both fail. A provenance restriction is a supported condition for the observed benefit, not a validated automatic deployment mechanism.
5. **Novelty must remain specific.** [TechniqueRAG](https://aclanthology.org/2025.findings-acl.1076/) already applies retrieval to ATT&CK technique annotation. [Beyond RAG for CTI](https://arxiv.org/abs/2604.11419) compares graph, agentic and hybrid retrieval on 3,300 CTI QA pairs. The defensible distinction is this frozen evidence-form/source-access/mismatch evaluation and its failed transport, not the first CTI RAG, first relationship-aware QA, or a proven superior retriever. This targeted comparison is not exhaustive novelty certification.
6. **Completion depends on scope.** The existing bounded CTI mechanism-and-safety-boundary paper can be completed honestly using available results and an explicitly unfinished PX-071 extension. A claim of parser-free external confirmation requires completing that separate study; operational preparation does not fill the gap.

Compared with 008, CTI has a larger complete-data study, consistent benefits and mismatch harm in two open-model families, multiple substantive evidence controls, and an existing fuller manuscript. 008 has a more direct current fit to the user's selective-evidence/code-revision interest and a tightly closed contemporary experiment, but its positive H1 is limited to one native model configuration, its hybrid H2 fails and its generated transfer contrast is absent. **Keep CTI in the primary shortlist; do not demote it based on the stale 106-row registry, and do not promote its unfinished external study or failed router.**


Archive note: copied for the September 14 manuscript release. Relative older-artifact links were expanded to their original local paths; reported findings and evidence hashes are unchanged.
