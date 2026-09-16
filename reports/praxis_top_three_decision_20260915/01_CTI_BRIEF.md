# CTI contribution decision brief — September 15, 2026

**Internal AI-assisted preparation aid; not academic submission prose. Original applied-contribution fit remains unresolved.**

## Problem and research question

Cyber-threat assistants need to decide when retrieved information is applicable. Plausible evidence can improve relevant answers while worsening answers outside its source domain. **Question:** How do relationship facts, access to published source metadata, and source compatibility affect frozen-model CTI accuracy, and does a fixed applicability router preserve the benefit on another corpus?

## Candidate contribution and completed evidence

**Working inference, not certified novelty:** a controlled evidence-access comparison that separates source-known from question-and-options retrieval, measures incompatible-evidence harm, and preserves a failed prospective routing test. This supports an empirical engineering decision boundary; it establishes neither a new retrieval algorithm nor a successful defense.

On 1,578 eligible CTIBench questions, source-known relationship evidence improved Llama from **970 to 1,334 correct** and Qwen from **970 to 1,279**: **+23.07/+19.58 percentage points**. Query-only retrieval gained **+18.19/+13.88 points**. On 922 mismatch questions, however, it reduced correctness **648→510** and **601→440**: **−14.97/−17.46 points**. Both mismatch arms had zero invalid outputs. [Primary analysis](C:/w/cti_dev/final_praxis/papers/20260914/01_cti/evidence/FULL_2500_ANALYSIS.json)

PX068 failed on 2,997 external questions: router precision **46.26%**, false-positive rate **52.53%**; formatting failures limit answer-quality interpretation. PX071 has no completed scientific result. The release reproduced **156 intervals**, verified **40,000 response/parser records**, and retained all negative decisions. These records represent **2,500 CTIBench question units**. [External analysis](C:/w/cti_dev/final_praxis/papers/20260914/01_cti/evidence/PX068_ANALYSIS.json), [status](C:/w/cti_dev/final_praxis/papers/20260914/01_cti/evidence/STUDY_STATUS.json), [reproduction](C:/w/cti_dev/final_praxis/papers/20260914/01_cti/evidence/reproduced_full/REPRODUCTION_RECEIPT.json)

## Closest primary comparisons

- **TechniqueRAG:** §§3.2–3.4 already combine retrieval, technique-aware reranking, and trained generation; §5.1/Table 2 evaluates annotation. CTI retrieval itself is established. [Paper, pp. 20916–20918](https://aclanthology.org/2025.findings-acl.1076.pdf)
- **Beyond RAG for CTI:** §4.1.2, Tables 11–14 already compare benefits by question type and failures under inadequate evidence, including abstention. Generic “helps versus harms” overlaps directly. [Primary study](https://arxiv.org/html/2604.11419v1)
- **AHLERT:** §II-A/B and Table I describe hybrid retrieval, stored provenance, and environment grounding for hunt leads. Generic evidence-grounded CTI is also occupied territory. [September 2026 paper](https://arxiv.org/html/2609.08790v1)

## Remaining gap and decisive gate

The smallest closure is an **author-created prior-comparison table and explanation of one eligible and one mismatch result**, followed by an actual applied-contribution scope decision. No fresh paid inference is necessary for the bounded finding. [September 15 next actions](C:/w/px010_dev/final_praxis/010_development_20260915/CTI_NEXT_ACTIONS.md)

**Advance** as an empirical foundation only when that review identifies a specific supported distinction and accepts its applied fit. **Narrow now** to measured source-access effects and mismatch failure. **Archive the present router as failed.** If a successful new process is required, current evidence does not pass; any extension needs separate novelty review, fresh source-disjoint confirmation, qualified scoring, matched controls, and frozen benefit/harm/coverage gates.

## Five skeptical defense questions

1. **Is this ordinary RAG?** Components are established; the candidate distinction is the specific access/mismatch/transport evaluation, still requiring originality review.
2. **Did retrieval see the answer?** Query retrieval saw all displayed options, not the key; source-known retrieval used source metadata. Option phrases in evidence limit reasoning claims.
3. **Is this untouched confirmation?** No: 500 questions were previously exposed; the exclusion sensitivity is post hoc. [Limitations](C:/w/cti_dev/final_praxis/papers/20260914/01_cti/PAPER.md)
4. **Did the safety intervention work?** No. The primary mismatch gate and external router confirmation failed; PX071 contributes no efficacy evidence.
5. **What was reproduced?** Archived parsing and statistics, not new model inference or benchmark truth. Source clustering remains unmodeled; public Athena evidence contains derived correctness indicators.
