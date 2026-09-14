# Top three Praxis recommendations

September 14, 2026. **Prioritize CTI for the strongest completed empirical foundation, finish the new Final-008 paper as the strongest currently closed code-revision study, and retain PX-055 as a conditional mechanistic alternative.** These ranks distinguish evidence strength, paper readiness and fit to your interests; they do not certify novelty or publication acceptance.

The review covered the **PX-001–071 catalog and Final-Praxis-001–008**, using the catalog to locate studies and later receipts to determine their status. The catalog includes proposals, merged directions and failures; it is not 71 completed independent studies. Historical PX numbers and the newer Final-Praxis numbers identify different programs. Latest adjudications supersede stale positive badges. [CTI audit](portfolio_review/CTI_REVIEW.md), [remaining portfolio audit](portfolio_review/PORTFOLIO_REVIEW.md).

| Rank | Candidate | Best supported contribution | Readiness |
|---|---|---|---|
| **1** | **CTI: historical PX-003/PX-034** | Relationship evidence helps source-compatible questions and harms incompatible questions across two model families | Full August draft exists; bounded scope can be completed through editorial and evidence packaging |
| **2** | **Final-008: selective disclosure of executed tests** | A controlled disclosure effect in one reviewer configuration, with unsuccessful verification and transfer results | Experiments and evidence closure complete; new full manuscript written |
| **3** | **PX-055: refusal-related geometry under quantization** | Bounded precision invariance across three families and three precisions | Conditional alternative; construct validity and direct prior art need focused validation before primary-thesis commitment |

## 1. CTI: strongest completed empirical breadth

**Question:** When does relationship-specific ATT&CK evidence improve answers, and when does source mismatch make it harmful?

The final study uses the complete **2,500-question CTIBench release**, split by provenance into **1,578 ATT&CK questions and 922 mismatch questions**. It compares source-known evidence, query-only retrieval and evidence-form controls in two pinned model families. There are 40,000 inference rows, including 5,000 duplicate-vanilla checks, rather than 40,000 independent questions. Public foundations are [CTIBench](https://arxiv.org/abs/2406.07599) and versioned MITRE ATT&CK data.

Source-known relationship evidence improves accuracy by **23.1 percentage points for Llama**, CI **[20.5,25.7]**, and **19.6 points for Qwen**, CI **[16.9,22.2]**. Query-only retrieval also helps ATT&CK questions, but harms mismatch questions by **15.0 and 17.5 points**. The terminal result is **PASS_SOURCE_KNOWN_ONLY**, with mismatch safety failing both models. [Frozen machine analysis](C:/Users/garyp/OneDrive/Documents/codex/reports/relationship_evidence_cti_compliance/confirmatory_closeout_20260731/full_2500_analysis/analysis.json).

The contribution is the controlled evidence-form, provenance and mismatch evaluation. It supports neither the first CTI RAG claim nor a successful automatic safety router. The external **PX-068 router failed** on 2,997 AthenaBench questions, including 46.26% precision and 52.53% false-positive rate, with severe output-format confounding. **PX-071 has no completed scientific result**; its preparation and signed operational freezes are not external confirmation.

**Remaining work:** update and package the existing [August 18 full Praxis draft](C:/Users/garyp/OneDrive/Documents/codex/output/doc/top_three_praxis_final_20260818/PX003_PX034_Final_Praxis_Paper_20260818_DRAFT_QA.docx), reconcile the exact archived evidence, and correct literal “strict-format compliance” wording to the actual frozen option-parser endpoint. Retain prior-item exposure and oracle-provenance limitations. The bounded paper does not require pretending PX-071 finished; a stronger external-confirmation claim would require its separate completion.

## 2. Final-008: strongest currently closed code-revision study

**Question:** Can selective disclosure of genuine test observations change a model's revision decision, and does independent verification prevent harmful changes while preserving repairs?

Public **HumanEvalPack/HumanEvalFix and HumanEvalPlus** provide 164 source problems; qualification admits 135 pairs, including **101 heldout problems**. Schema-constrained Qwen accepts **12/101 harmful revisions under selected disclosure versus 4/101 under uniform disclosure**: **+7.92 points**, CI **[2.97,13.86]**, Holm-adjusted p **.015625**. Both arms have 101 valid decisions. Useful-repair acceptance is 100/101 in both. [Full new paper](PRAXIS_008_PAPER.md).

This is a bounded empirical disclosure finding. Seven of eight additional harmful acceptances coincide with withholding a failing record; two selected messages contain no tests. The treatment therefore includes omission. Devstral does not establish the same effect, the hybrid-defense **H2 fails**, and the smaller **34-harmful-proposal** generated cohort shows no disclosure contrast. Public-benchmark exposure and finite test oracles limit generalization.

**Remaining work:** adapt the completed manuscript to your committee's presentation and submission requirements. The full 26-page paper has passed text review and visual review of every rendered page. Experimental evidence closure and exact public-package statistical reproduction have passed; the [automated readiness receipt](../PAPER_READINESS.json) concerns bounded paper development. It does not validate a new defense. The manuscript's contribution and limitations are checked in its [evidence review](FINAL_MANUSCRIPT_REVIEW.json); [Word](PRAXIS_008_PAPER.docx) and [PDF](PRAXIS_008_PAPER.pdf) versions are available.

## 3. PX-055: best conditional mechanistic alternative

**Question:** Does quantization preserve refusal-related representation geometry, and does preserved geometry predict actual refusal behavior?

The latest adjudication covers **9/9 model–precision cells**: Qwen, Llama and Gemma at FP16, INT8 and NF4. It reports **H1_PRECISION_INVARIANT_BOUNDED**, 116 safe-text geometry rows per model, a maximum principal angle of **15.43 degrees**, and minimum directed transfer ratio **0.975**. Public behavioral data are **450 XSTest rows**; the geometry corpus is locally constructed. [Independent adjudication](C:/Users/garyp/OneDrive/Documents/codex/reports/refusal_direction_quantization/e1_e4_20260831/closeout_r3/PX055_R3_INDEPENDENT_ADJUDICATION.json).

**This is not equally paper-ready as a causal safety thesis.** Safe-text geometry and phrase-lexicon behavior scoring leave a style-versus-semantic-refusal gap. The restoration proxy is not positive. [Single-direction refusal work](https://arxiv.org/abs/2406.11717) and [compressed-model refusal research](https://arxiv.org/abs/2504.04215) are direct prior art. Before primary-thesis commitment, validate the construct and identify the precise contribution beyond those papers; any subsequent study needs independently labeled behavior, separated estimation/outcome sets and prospective causal controls.

## Why the other leading candidates rank lower

**FalseCite-Code** has a useful 6/7-to-zero fabricated-acceptance result, but only seven fabricated holdout claims and a strong metadata prompt that ties the guard on the main model. **Selective TTA** has a large original-domain benefit but failed its preregistered UNSW external replication, passing 0/6 criteria. **PX-057 stopping** fails its final harm ceiling under both extraction methods. Preserve these bounded results; their older optimistic badges do not justify replacing the three priorities above. Exact receipts and scope limits are linked in the [portfolio audit](portfolio_review/PORTFOLIO_REVIEW.md).
