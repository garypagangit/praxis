# CTI Praxis: Evidence and Development Guide

## Executive summary

**Internal AI-assisted research aid. Not a document for academic submission.** This guide helps navigate the completed CTI evidence, its reproducibility checks and the decisions needed before further Praxis development. It preserves the published study unchanged. No new model calls or experiments were performed to prepare it.

The study has a substantial empirical result. On 1,578 CTIBench questions matched to ATT&CK techniques, relationship evidence improved option-parser accuracy by 23.07 percentage points for Llama and 19.58 points for Qwen when the relevant technique was identified from benchmark source metadata. A more realistic question-based retrieval arm also improved this eligible subset. However, the same question-based retrieval harmed performance on 922 questions outside that evidence domain. The external learned router did not resolve the problem and failed its confirmation gate.

That makes this a useful investigation of the conditions under which evidence helps or harms. It does not establish a successful general-purpose defense, a deployment-ready router, or a new retrieval algorithm. The strongest next investment is in understanding and organizing the completed evidence, checking the originality argument against close prior work, and resolving the applicable authorship requirements before any academic submission.

The [completed paper and evidence package](../papers/20260914/01_cti/README.md) is the immutable scientific record. The [machine-readable evidence index](EVIDENCE_INDEX.json) links eight decisive comparisons to exact JSON locations and source hashes. The accompanying checker verifies those values and the historical statistical-reproduction receipt. A passing software check does not establish originality, academic authorization or committee approval.

### A material institutional requirement

GW's [doctoral policy page](https://online.engineering.gwu.edu/policies-procedures-doctoral) links a [generative-AI policy](https://gwu.box.com/s/ickb578cz7d75089n2j5c1y9c6gb0z2v) that restricts AI drafting, revision, editing and literature summaries for submitted academic work, including a Praxis. It permits source identification and code assistance, with attribution and student responsibility for understanding the code. The policy describes written exceptions; no applicable authorization was located in this review. Human editing of an AI draft is not, by itself, a demonstrated remedy. The policy was retrieved on September 14, 2026; its effective date was not specified in the retrieved text.

This package retains AI provenance. It is not a claim that the existing AI-assisted paper is eligible for GW submission. No document has been emailed, submitted or approved through this work.

## 1. Research decision and evidence boundaries

### Problem and purpose to investigate independently

The practical problem is deciding when a cyber-threat question should receive external evidence. Helpful information and irrelevant information can both look plausible. Average benchmark accuracy can conceal a harmful subgroup. The completed work compares evidence conditions within the same question and model, then tests a learned applicability router on a second benchmark.

For independent human development, the central questions are: Which evidence access conditions produce useful gains? Does a gain persist when source metadata is unavailable? What happens outside the evidence domain? Does a learned applicability gate improve the outcome under external conditions? These questions map to completed comparisons; this guide does not retroactively designate new preregistered hypotheses.

### What changed in the process

The primary study changed the evidence supplied to a fixed language model. It compared relationship facts, technique descriptions, random facts, empty evidence, a broad evidence seed and no evidence. Source-known retrieval used a technique identified from the question's benchmark URL. Question-based retrieval instead used the question and all four displayed options, without the answer label or source URL. Its deterministic lexical scorer combined token overlap, an evidence-kind bonus and option-phrase matches; it selected up to six facts.

These are existing retrieval and matching ideas arranged into an empirical comparison. The primary study did not fine-tune the language models. The separate external router used TF-IDF features and calibrated logistic regression. Its failure is part of the result, not an implementation success to be assumed away.

### Units and outcome definition

The primary benchmark contained 2,500 questions: 1,578 technique-eligible and 922 outside that scope. It produced 40,000 saved response records, including 5,000 duplicate vanilla records. Those are repeated observations of 2,500 question units, not 40,000 independent samples. The two configurations were Llama 3.1 8B Instruct and Qwen 2.5 7B Instruct, with version pins preserved in the completed package.

The measured outcome is correctness under the frozen option extractor. Although a function is named `strict_parse`, its behavior permits an option prefix and a limited fallback token search. The result should be called option-parser accuracy, not exact-format compliance or unconstrained reasoning quality. Invalid outputs remain incorrect in the primary analysis.

## 2. Claim-to-evidence map

Each row below has a corresponding machine entry in [EVIDENCE_INDEX.json](EVIDENCE_INDEX.json). Differences are treatment minus control. Confidence intervals are the archived paired question-bootstrap intervals, reproduced from the packaged observations; they are not new inferential estimates created for this guide.

| Comparison | Llama: correct counts; difference [95% CI] | Qwen: correct counts; difference [95% CI] |
|---|---|---|
| Source-known relationship vs vanilla; n=1,578 | 1,334 vs 970; +23.07 pp [20.53, 25.67] | 1,279 vs 970; +19.58 pp [16.92, 22.18] |
| Question-based relationship vs vanilla, eligible; n=1,578 | 1,257 vs 970; +18.19 pp [15.53, 20.85] | 1,189 vs 970; +13.88 pp [10.96, 16.73] |
| Question-based relationship vs vanilla, mismatch; n=922 | 510 vs 648; -14.97 pp [-18.00, -11.93] | 440 vs 601; -17.46 pp [-20.82, -14.10] |
| External router vs ungated evidence, ineligible; n=1,999 | 705 vs 815; -5.50 pp [-6.85, -4.20] | 566 vs 1,060; -24.71 pp [-26.61, -22.81] |

**Claim C1: evidence can help within the measured source-compatible setting.** The source-known gains exceeded the registered practical thresholds in both configurations. This supports a bounded empirical finding. It does not imply that a deployed system knows the correct source technique.

**Claim C2: removing source metadata does not remove the gain on eligible questions.** Question-based retrieval improved both eligible configurations. Because all answer options were inputs to retrieval, this is still a multiple-choice setting. It is not evidence for an equivalent open-ended task.

**Claim C3: broad application can be harmful.** Both mismatch intervals are entirely negative, and the registered mismatch noninferiority gate failed. Neither mismatch arm had invalid primary-parser outputs, so those two accuracy losses are not simply a format-failure artifact. The terminal primary status is `PASS_SOURCE_KNOWN_ONLY`.

**Claim C4: the external router was not confirmed.** PX068 evaluated 2,997 AthenaBench questions after three schema exclusions: 998 eligible and 1,999 ineligible. The router had 904 true positives, 94 false negatives, 1,050 false positives and 949 true negatives. Precision was 46.26% and false-positive rate 52.53%, failing their respective requirements. Its terminal status is `FAIL_ROUTER_CONFIRMATION`.

**Claim C5: numerical reproduction is completed, with a defined boundary.** The packaged full reproduction regenerated all 156 requested bootstrap intervals and matched both archived statistical payloads. It also verified 40,000 CTIBench parser/correctness rows and 23,976 derived Athena policy rows. Restricted Athena raw text and answers are not redistributed, so its raw-to-indicator derivation was not independently rerun by this public package. Reproducing stored observations does not reproduce model inference or validate benchmark truth labels.

**Claim C6: PX071 is unfinished science.** Prepared sources and operational freezes exist, but no completed efficacy result was located. It contributes no effect estimate to this recommendation.

## 3. Sources and questions about originality

The links in this section identify primary sources for the author's own reading. They are not an AI-written literature review for academic submission.

| Source to read | Comparison question for the author |
|---|---|
| [CTIBench, Alam et al., 2024](https://arxiv.org/abs/2406.07599) and [public dataset](https://huggingface.co/datasets/AI4Sec/cti-bench) | Which task, answer contract and source categories does the completed study inherit? |
| [Retrieval-Augmented Generation, Lewis et al., 2020](https://arxiv.org/abs/2005.11401) | Which parts of the approach are standard retrieval plus generation? |
| [MITRE ATT&CK design and philosophy](https://www.mitre.org/news-insights/publication/mitre-attck-design-and-philosophy) | What does a technique relationship encode, and what does it leave unresolved? |
| [TechniqueRAG, Lekssays et al., 2025](https://aclanthology.org/2025.findings-acl.1076/) | How does the claimed contribution differ from existing technique-aware CTI retrieval? |
| [Beyond RAG for CTI, Hamzic et al., 2026 preprint](https://arxiv.org/abs/2604.11419) | Which retrieval comparisons and boundaries overlap with the completed study? |
| [AthenaBench, Alam et al., 2025](https://arxiv.org/abs/2511.01144) and [pinned repository](https://github.com/Athena-Software-Group/athenabench/tree/39d3a74eaf84b93e21dde0a4b60ddd4f08620eaf) | How do its source mix, answer grammar and producer lineage constrain external confirmation? |

The plausible originality argument concerns the controlled characterization of source compatibility and a documented failure of applicability routing. It needs a direct comparison against the closest prior experiments, including their cohorts, controls and failure criteria. A claim of the first CTI retrieval system, novel graph retrieval, or a successful new defense is unsupported. The external dataset is different, but its overlapping research lineage does not establish replication by an independent benchmark producer.

### Fit with the actual D.Eng. guidance

GW's [October 2025 D.Eng. guidelines](https://online.engineering.gwu.edu/sites/g/files/zaxdzs5816/files/2025-10/deng-student-guidelinesOct6_2025.pdf) frame the Praxis as an original applied response to a practical problem. They call for a defined problem, goals, available data and a detailed method, with originality judged by the committee. The body is expected to be approximately 80 pages, with a 150-page overall cap. The completed 20-page research paper is therefore a foundation, not a full Praxis submission. Advisor, academic-integrity and committee approval are not established here.

There is enough completed evidence to develop the empirical argument. There is not an automatic demonstration that the failed router supplies the original practical solution an advisor may require. The author should resolve that substantive fit before treating additional formatting or pages as sufficient progress.

## 4. Questions for independent preparation

**What exactly is the contribution?** Locate the controlled evidence comparisons, the eligible/mismatch distinction, the operationally limited source-known result and the failed external gate. Explain what those observations add beyond ordinary retrieval. Keep a separate list of claims that the close-prior comparison does not yet support.

**Did the system have access to the answer?** Inspect the prompt and retrieval builders in the frozen package. Source-known retrieval used benchmark source metadata; question-based retrieval used all displayed options. Neither mechanism should be described as an unconstrained, source-blind deployment. The option-phrase signal also prevents attributing the effect solely to deeper relational reasoning.

**Was this an untouched test set?** No. Earlier work exposed the first 500 CTIBench questions. The later full-run protocol was internally frozen, but this is not an externally preregistered untouched benchmark. The analysis excluding those 500 items is post hoc sensitivity evidence, not a replacement confirmatory split.

**How strong is the mechanism claim?** The comparisons establish changes in the measured output under the tested evidence conditions. They do not isolate whether the gain comes from relational reasoning, lexical clues, memorization or other mechanisms. Public benchmark training exposure is unknown.

**Why not report just the average gain?** The eligible and mismatch conditions lead to different conclusions. A pooled average can conceal the mismatch losses. Subgroup definitions, sample sizes and scope must accompany any aggregate figure.

**Does the external study repair this weakness?** No. PX068 failed. Its severe baseline formatting failures also limit causal and practical interpretation. The frozen legacy analysis had a valid-E parsing defect; the package preserves that history and reports intended-grammar validity separately. Quietly replacing a parser would erase an important boundary.

**What are the independent units?** Primarily questions. Repeated conditions, duplicated vanilla runs and derived routing policies do not multiply the independent sample. Correlations among questions that share a source or technique were not resolved by the question-level bootstrap.

**What can another researcher reproduce?** They can run the packaged statistical and parser checks without paying for inference. Exact model behavior under a new environment is a separate replication task. Athena's restricted raw corpus adds a documented public reproduction limit.

**Is a negative routing result enough for a doctoral contribution?** It can support a useful bounded empirical paper. Whether the overall study meets this author's doctoral requirements depends on the originality argument and the applicable academic review. Software cannot decide that question.

## 5. Human-authorship handoff and unrun remedy

### Work that can begin from this evidence

The author can independently read the primary sources, examine the code and reproduce the archived results. A human-authored development record can then track: the practical problem; the claimed gap against each close prior source; the exact outcome definition; results with their scope; alternative explanations; and the engineering recommendation justified by the failed gates. This guide and the earlier AI-assisted manuscript must not be represented as independently human-authored work.

The official [2026 Praxis template](https://gwu.box.com/s/ne153n4y8hdmmr1tgezc1zbuk554sut3) provides a five-chapter structure: introduction, literature review, methodology, results, and discussion/conclusions. Its sample certification language is a template, not evidence of anyone's approval. The [university formatting page](https://gradpostdoc.gwu.edu/gw-etd-formatting) specifies Times New Roman 12-point text and 1.25-inch side margins for portrait pages. This internal guide uses those basic dimensions without claiming final-template compliance.

**Suggested evidence destinations for independently written chapters:** use study status and source access definitions in the introduction; original primary papers for the author's literature comparison; frozen protocols, model pins and executable parsers in methods; the complete analysis JSON files and failed gates in results; and exposure, producer lineage, format limitations and unrun work in discussion. The results chapter must include PX068 and must not count PX071 as completed.

### Conditional next research: status UNRUN

If the committee requires a more substantial process contribution, a candidate question is whether evidence admission can be made robust to irrelevant answer-option presentation. One candidate is an applicability gate that combines source compatibility with retrieval stability under answer-option permutations. This is a research candidate, not an established novel method or a promised successful remedy.

A future design would have to compare compatibility-only, stability-only, combined and coverage-matched simple gates. It would need a qualified output grammar, source-disjoint calibration and test groups, matched retrieval/model budgets, frozen thresholds before outcome access, and correctness assessed on all assigned questions. Coverage and harm must be evaluated together so that rejecting every item cannot count as success. Source-cluster uncertainty and external benchmark lineage would require explicit treatment.

No thresholds, success margins or sample size are retrospectively selected here. The existing failed results cannot serve simultaneously as development feedback and fresh confirmation. The closest prior art on selective prediction, calibration, retrieval confidence and permutation stability must be reviewed before investing in this candidate. PX071 may supply technical material, but it supplies no completed scientific result and is not automatically the right confirmation set.

## 6. Reproduction and document-use record

From this directory, run `python check_consistency.py` and `python -m unittest test_consistency.py`. The first command checks exact values, source hashes and the existing full-reproduction receipt. The second tests that altered counts, a fabricated approval, a relabelled router failure, missing comparisons and altered hashes are rejected. Both use only local files.

For the underlying analysis, follow the [completed package instructions](../papers/20260914/01_cti/README.md). Its `reproduce.py --bootstrap all` recomputes all 156 intervals from archived observations. Repeating that expensive local bootstrap is unnecessary for verifying this guide's source pointers; the existing full receipt is preserved and hash checked.

**AI assistance record:** Codex helped identify official sources, write the evidence-indexing and verification code, and prepare this internal navigation aid. The human author remains responsible for understanding any code used and for following the applicable GW rules. This package records no written academic exception, no submission and no successful defense. Its automated PASS status applies only to the explicitly listed technical checks.
