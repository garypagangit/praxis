# Published comparator and scope

Reviewed September 18, 2026. This pilot uses a released general relevance model. It does not implement the full CRAG, CoRM-RAG or Ahlert systems.

## Comparator implemented

`cross-encoder/ms-marco-MiniLM-L6-v2`, revision `233902d25c440f23af6f7d6e94d2946bac0bee0a`, is a published MS MARCO passage-ranking cross-encoder. Its 22.7 million parameters occupy approximately 90.9 MB in safetensors. The [official model card](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) documents question/passage pair scoring and the [published files](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2/tree/233902d25c440f23af6f7d6e94d2946bac0bee0a) supply the weights.

`score_relevance.py` scores the original question against each original retrieved fact separately. Options, gold source metadata and answer outcomes do not enter this neural scorer. The downstream pilot may use all options for separate input features; those features must be described separately. Raw logits, their mean, maximum, minimum and population standard deviation are retained. A logit is not a calibrated probability that the document will improve the answer.

Inference uses CPU FP32, four Torch threads, batches of 32 pairs, and at most 512 tokens per pair. Longest-first truncation and all token losses are recorded. The original evidence order is preserved. Per-question timing allocates each batch's tokenization/inference duration equally across its pairs; it is not an independently measured single-question latency. Model loading/download and overall elapsed time are reported separately.

The cache records the input file and individual row hashes, exact model revision, inference specification and implementation hash. A resume rejects changed input or settings. Model-file hashes and package versions are written to `relevance_metadata.json`. Runtime results are in `relevance_scores.jsonl`; this document alone does not establish that inference completed.

### Input-access parity sensitivity

Before selector fitting, an independent review identified that the learned selectors see all displayed options, while the standard question/passage relevance input sees only the question. A second, explicitly adapted relevance arm therefore receives the question followed by every displayed option in sorted letter order. It sees no correct-answer key. This tests whether the additional visible question information accounts for an apparent checker advantage.

`prepare_relevance_options.py` creates `data_relevance_options.jsonl`, verifies that only the question field changed, and writes the source/transformed hashes and exact text transformation to `relevance_options_projection.json`. It preserves the original scorer and creates `score_relevance_options.py`, changing only the input description and three default file paths. Model, inference settings, fact order and aggregation remain identical. Its outputs are `relevance_options_scores.jsonl` and `relevance_options_metadata.json`. Compare both relevance arms at the candidate's evidence-use count; neither arm is a full CRAG reproduction.

## Important comparisons still outstanding

| Published method | Available artifact | Why it matters / resource limitation |
|---|---|---|
| CRAG retrieval evaluator | [Official repository](https://github.com/HuskyInSalt/CRAG) and its [released weights](https://drive.google.com/drive/folders/1CRFGsyNguXJwKSvFvJm_82GOOlkWSkW7) | T5-large sequence-classification regression model. Public config access was verified; Drive lists the safetensors file at 2.8G. It is substantially larger than the selected CPU comparator. Using that evaluator alone would still be a component adaptation, not full corrective retrieval and generation. |
| CoRM-RAG Evidence Critic | [Official repository](https://github.com/PeiYangLiu/CoRM-RAG), [checkpoint](https://huggingface.co/PeiyangLiu/CoRM-RAG) | Closer prior work because it learns robust evidence utility. The released `critic-v12-mixed/checkpoint-latest/state.pt` is 5,208,606,507 bytes, revision `4d93b6b28cc20873928f1db24729db1850351be4`; the backbone is DeBERTa-v3-large. Its released scoring code uses question/document pairs and a sigmoid over a learned CLS head. Evaluating this critic is an important stronger comparison before asserting methodological superiority. |
| BGE reranker v2 M3 | [Official model card](https://huggingface.co/BAAI/bge-reranker-v2-m3) | A larger general relevance comparator: approximately 568 million parameters and 2.27 GB of safetensors. This remains a relevance model rather than a guarantee of downstream answer improvement. |

The original CRAG evaluator and CoRM-RAG checkpoint are publicly released. Their omission from this local pilot is a resource/scope choice, not a claim that their weights are unavailable. The local environment has CPU-only Torch and limited free RAM. The compact comparator makes the immediate experiment feasible without cloud jobs.

## How to interpret the pilot

- A selector that beats this comparator offers a reason to investigate further; it does not establish superiority over current evidence checkers or algorithmic novelty.
- Selection thresholds and learned parameters must be fit on development data only. Held-out outcomes cannot choose the final policy.
- Report evidence-use coverage and correctness together. Reducing harm by rejecting almost all evidence does not by itself preserve useful evidence benefit.
- Gold source identifiers and released answers are evaluation information, not operational features.
- Reusing archived with-evidence and without-evidence answers measures the policy over those recorded outcomes. New checker inference is real new computation, but it is not a fresh end-to-end CTI answer-generation experiment.
- Source-disjoint splitting reduces a known leakage channel; it does not erase prior benchmark exposure, unknown pretraining contamination, or the exploratory nature of this pilot.
