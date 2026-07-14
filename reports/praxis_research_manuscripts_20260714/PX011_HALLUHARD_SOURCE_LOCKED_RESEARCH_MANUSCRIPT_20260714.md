# Source-Locked HalluHard Verification with Extractive Claim Generation

Research manuscript draft

Praxis ID: PX-011

Generated: 2026-07-14

Status: Bounded source-locked positive

## Abstract

Open-ended hallucination benchmarks expose a persistent problem: LLMs can produce plausible factual claims that are not grounded in cited sources. PX-011 evaluates a constrained HalluHard-style pipeline that locks citation metadata to retrieved source records and restricts the model to extractive claim content. In the successful gate, the controller copies DOI, arXiv ID, title, year, and source identity from the source record, while Qwen2.5-7B-Instruct generates only a short `claimed_content` phrase from the source abstract. The verifier evaluates both source-locked supported rows and shifted-source negatives. On the HalluHard research-questions lane, the system produced 250 generations and 500 evaluation pairs, with extraction-valid rate 1.0000, supported rate 0.8080, verifier accuracy 0.9040, and macro F1 0.9031. This result supports a bounded claim: source-locked retrieval/control plus extractive claim generation can produce verifier-ready citation claims and detect shifted-source hallucinations. It does not support freeform citation generation or broad HalluHard coverage.

## 1. Introduction

Citation hallucination is especially difficult because a generated answer can contain plausible source metadata and plausible content while still being unsupported. Multi-turn settings make the problem worse because early grounding errors can persist. PX-011 approaches the problem by narrowing the generation boundary: the model does not invent metadata. It only extracts content from a retrieved source record.

This design turns hallucination control into a systems problem. A controller supplies source identity and citation fields; the model contributes a short content phrase; the verifier checks whether the content is grounded in the source and rejects shifted-source pairs.

## 2. Prior Work

HalluHard motivates the benchmark setting. Fan et al. introduce a hard multi-turn hallucination benchmark with seed questions across legal cases, research questions, medical guidelines, and coding. Their evaluation emphasizes groundedness and citation support.

FActScore motivates claim-level verification against reliable sources. Min et al. argue that long-form factuality evaluation benefits from decomposing generated text into supportable units and checking them against sources.

Retrieval-augmented generation motivates separating parametric generation from source access. PX-011 adopts the retrieval/control principle but narrows the generation role more aggressively than standard RAG: citation metadata are copied, not generated.

## 3. Experimental Design Influences

HalluHard shaped the source-grounding task and the shifted-source negative idea. The experiment tests not only whether a supported source-locked claim passes, but also whether plausible content attached to the wrong source is rejected.

FActScore shaped the focus on claim support rather than answer fluency. The model output is reduced to a small content claim that can be verified.

RAG shaped the retrieval/control architecture, but PX-011 intentionally goes beyond normal retrieval prompting by locking citation metadata outside the model.

The earlier failed/freeform HalluHard gates shaped the final constrained design. The viable result appeared only after the model was prevented from inventing citation fields.

## 4. Research Questions

RQ1: Can source-locked citation metadata plus extractive model-generated content produce verifier-ready claims?

RQ2: Can the verifier detect shifted-source hallucinations?

RQ3: Does the constrained pipeline outperform trivial always-supported and field-presence baselines?

RQ4: Is the positive result limited to the research-questions lane?

## 5. Data and Methods

PX-011 uses the HalluHard `research_questions` lane only. The controller copies DOI, arXiv ID, title, year, and source identity from each retrieved source record. Qwen2.5-7B-Instruct generates only the extractive `claimed_content` phrase from the abstract.

The verifier evaluates:

- supported source-locked pairs,
- shifted-source negative pairs,
- extraction validity,
- source support,
- macro F1 against trivial baselines.

## 6. Results

| Metric | Value |
|---|---:|
| Model | Qwen/Qwen2.5-7B-Instruct |
| HalluHard lane | research_questions only |
| Generations | 250 |
| Evaluation pairs | 500 |
| Extraction-valid rows | 250 / 250 |
| Extraction-valid rate | 1.0000 |
| Supported claims passing verifier | 202 / 250 |
| Supported rate | 0.8080 |
| Verifier accuracy | 0.9040 |
| Verifier macro F1 | 0.9031 |
| Always-supported macro F1 | 0.3333 |
| Field-presence macro F1 | 0.3333 |
| Wall time | 256.8 seconds |

Gate checks passed for minimum generations, extraction-valid rate, supported rate, macro F1, and both baseline comparisons.

## 7. Discussion

PX-011 demonstrates that the strongest HalluHard result in this portfolio is not freeform citation generation. The successful contribution is source-locked control. The controller prevents invented DOI, arXiv ID, title, year, and source identity; the model performs only extractive content generation; the verifier tests source support and shifted-source negatives.

The result is publishable only inside this boundary. It is useful because it gives a clear system design for reducing citation hallucination: move citation metadata out of the model's generative surface and verify content against the paired source.

## 8. Threats to Validity

The experiment uses the research-questions lane only. It does not test legal, medical, coding, or broad HalluHard coverage. The generation task is constrained and extractive, so results should not be generalized to open-ended source discovery. The supported rate of 0.8080 shows that even constrained generation is not perfect.

## 9. Conclusion

PX-011 supports a bounded source-locked hallucination-verification claim. When citation metadata are copied from retrieved evidence and the model is limited to extractive content, the verifier can separate supported claims from shifted-source hallucinations with macro F1 0.9031.

## Repository Artifacts

- `reports/halluhard_source_verifier/PX011_SOURCE_LOCKED_CONSTRAINED_GATE_20260701.md`
- `reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/report.md`
- `reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/summary.json`
- `reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/halluhard_constrained_rows.csv`
- `reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/halluhard_constrained_rows.jsonl`
- `cloud_jobs/halluhard_constrained_20260701/run_halluhard_constrained_gate.py`
- `cloud_jobs/halluhard_constrained_20260701/run_on_instance.sh`

## References

Fan, D., Delsad, S., Flammarion, N., & Andriushchenko, M. (2026). HalluHard: A hard multi-turn hallucination benchmark. arXiv. https://arxiv.org/abs/2602.01031

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Kuttler, H., Lewis, M., Yih, W., Rocktaschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. Advances in Neural Information Processing Systems, 33. https://arxiv.org/abs/2005.11401

Min, S., Krishna, K., Lyu, X., Lewis, M., Yih, W., Koh, P. W., Iyyer, M., Zettlemoyer, L., & Hajishirzi, H. (2023). FActScore: Fine-grained atomic evaluation of factual precision in long form text generation. Proceedings of EMNLP 2023. https://aclanthology.org/2023.emnlp-main.741/

Qwen Team. (2024). Qwen2.5 technical report. arXiv. https://arxiv.org/abs/2412.15115

