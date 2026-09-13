# Closeout and proposed research pivot

Reviewed 2026-09-13. Read-only source and artifact inspection; no model calls, cloud changes, or Git writes.

**Recommendation: close the current MiCRo implementation and conduct one no-model source/data/evaluator qualification of AutoDCWorkflow before funding a new specialist-corruption experiment.** The candidate question is whether a corrupted specialist can cause harmful revisions using truthful but selectively chosen evidence, and whether independently chosen checks preserve useful corrections. This is a proposed research direction, not verified novelty or an approved next inference run.

## What the completed pilot establishes

The independent final report for `fp006-format-811d7cc4a6` contains all 64 registered cells, with no integrity errors or missing cells and all technical checks passed. Chat produced 9/32 flexible-correct, nontruncated answers and 7/32 truncated outputs. The registered truncation limit was 3/32, so the decision is **DO_NOT_ADVANCE_CURRENT_QUALIFICATION**. Raw produced 10/32 correct and 3/32 truncated, but was diagnostic only and cannot replace the failed candidate. This training-split pilot does not qualify another held-out run. Source: `C:/w/fp006/final_praxis/006_cognitive_expert_containment/completion_format_pilot/completed/RESULTS.md` and `AUDIT.json`.

The previous FP32 study demonstrated a substantial logic-expert contribution within this implementation, but failed completion requirements. The new pilot does not erase that causal observation; it closes this attempted qualification. Neither result establishes that specialist containment generally cannot work.

## Closest primary work: the easy novelty claims are already occupied

- **PBRC, April 2026:** externally validated witnesses authorize belief revision; conservative fallback prevents unsupported changes. Crucially, Section 9.2 already identifies cherry-picked tool inputs and selective evidence forwarding, and sketches query-policy contracts, diversification, and mandatory counter-evidence queries. Section 14 leaves end-to-end acquisition/dissemination guarantees open. A witness gate or compulsory counter-query alone would closely overlap. Its empirical evidence does not establish a general deployed solution to misleading but valid evidence. [Paper, current v1](https://arxiv.org/html/2604.15558v1), [author artifact](https://github.com/alqithami/PBRC).
- **When Helping Hurts, June 2026:** already combines a separate code-executing critic with selective acceptance of evidence-backed feedback. Its reported +5.3 percentage-point improvement is **factual consistency defined as targeting existing columns**, not demonstrated improvement in purpose-answer correctness. Section 8.5 says its scripts, result JSONs and deterministic executor are supplementary; I did not verify a publicly accessible supplementary artifact. Do not call our next study a reproduction of those exact scripts. [Paper, current v1, Sections 3 and 7?8](https://arxiv.org/html/2606.02866v1).
- **Rethinking LLM Verification, August 2026:** targeted ontology grounding after abstention is already proposed and evaluated. Generic uncertainty-triggered evidence acquisition is insufficient differentiation. [Primary paper](https://arxiv.org/abs/2608.10725).
- **TAMAS** provides a relevant released adversarial multi-agent benchmark, but its evaluation scripts require model APIs. It is useful threat-model context rather than our preferred independent task-success oracle. [Author repository](https://github.com/microsoft/TAMAS/tree/545c112af9aab93b7ef2b0b60831d93c81c365c3).

This bounded review includes recent primary work through the review date. It does not establish an absence of overlapping work.

## One public base worth auditing

Select the **original AutoDCWorkflow** artifact, not the unverified June supplementary package. The base paper reports 142 purposes over 96 tables, with raw/clean tables, human-curated workflows, and purpose answers. Its released baseline separates column selection, quality inspection and operation generation, which gives a concrete specialist interface. The paper evaluates Llama 3.1, Mistral and Gemma 2. [AutoDCWorkflow v3, EMNLP Findings 2025](https://arxiv.org/abs/2412.06724v3).

Pinned repository: [`LanLi2017/LLM4DC` at `082dcbf5304329ef1ff08f5830e4116256b00a59`](https://github.com/LanLi2017/LLM4DC/tree/082dcbf5304329ef1ff08f5830e4116256b00a59). GitHub tree inspection found raw and cleaned datasets, saved model outputs, prompts, OpenRefine integration and evaluation scripts. Reading `dataset-all - all_purposes.csv` confirmed 142 rows with `ID`, `Purposes`, `tg_columns`, `Operations`, and `Category`. The repository has no detected top-level license; reuse terms and original data provenance remain unresolved, so public accessibility should not be described as a verified permissive release.

Important evaluator findings from source inspection:

1. [`answer_analysis.py`](https://github.com/LanLi2017/LLM4DC/blob/082dcbf5304329ef1ff08f5830e4116256b00a59/evaluation/answer_analysis.py) handles floats, strings, lists and dictionaries, but has no integer branch. Equal integer inputs therefore retain initialized zero scores.
2. [`q_execution.py`](https://github.com/LanLi2017/LLM4DC/blob/082dcbf5304329ef1ff08f5830e4116256b00a59/evaluation/q_execution.py) returns integers for several purposes, including maximum page count and a mean explicitly converted to `int`. These contracts need reconciliation before reusing answer scores; inspecting source is not yet an end-to-end reproduction.
3. [`data_compare.py`](https://github.com/LanLi2017/LLM4DC/blob/082dcbf5304329ef1ff08f5830e4116256b00a59/evaluation/data_compare.py) compares target columns by row index, skips null gold values and averages per-column ratios. Row reordering, deletion and all-null columns need explicit behavior. This metric alone is not a complete task-success oracle.

## Candidate question and decisive boundaries

**RQ:** With a useful intact specialist and a fixed verification budget, can a controller prevent damage from selectively presented valid evidence while retaining corrections that require the specialist?

A possible mechanism is to freeze the proposed edit, then choose checks independently from the original task and its affected data regions. Record both the peer-selected evidence and the independent checks. Test honest feedback, misleading interpretation, and truthful selective evidence as distinct conditions. Evidence provenance alone cannot establish relevance or completeness.

Required comparisons would include the intact pipeline, specialist bypass, ordinary evidence gating, fixed task-based checks and independent check selection at matched tool/token budgets. Primary outcomes must be executed purpose-answer correctness and preservation of already-correct data, with correct-to-wrong and wrong-to-correct transitions reported separately. Split by source table, not merely purpose, to avoid sharing near-identical data between development and evaluation.

The potentially publishable contribution would have to be an acquisition policy or a convincing characterization of verification failure under this threat model. It cannot be another claim that evidence beats persuasion. Reject the candidate if the intact specialist adds no useful capability, simple bypass/fixed checks dominate, independent task outcomes cannot be scored reliably, or the mechanism reduces to PBRC?s already described query contract.

## The next action, before any new inference

Produce **one offline artifact qualification package** for the pinned AutoDCWorkflow release: trace each purpose to raw/clean tables and saved outputs; establish data provenance and reuse terms; review the query executor; and specify an independently checked purpose-answer scorer with positive, negative, reordered-row, integer, missing-value and execution-error controls. Preserve upstream scores separately from any corrected evaluator. Assess existing released outputs without generating new model answers. Freeze source-table splits and a narrow corruption/evidence-acquisition protocol only if that package passes. Otherwise reject this base before spending on models.
