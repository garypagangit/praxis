# Answer-change support checker: development design review

## Why test a different checker?

The frozen SecEval experiment found that the previous utility checker selected only 5 of 42 possible recoveries for Llama and 8 of 55 for Qwen, while allowing 9 and 6 harmful answer changes. A model that predicts whether a whole evidence bundle will help may overlook the specific answer change it is authorizing. This development attempt asks whether checking support for the proposed answer versus the original answer improves that decision.

SecEval has already been examined. Every result from this revision on those 1,247 questions is an **exposed-data diagnostic**, even when its numerical parameters are selected entirely on old CTIBench calibration data. It cannot restore SecEval to an untouched test set.

## Bounded engineering approach

1. Reuse the saved answers with and without evidence. Examine only questions for which they differ; unchanged answers cannot affect selection accuracy.
2. Pass the question, displayed option text and each actual retrieved fact to an independently trained natural-language inference (NLI) classifier. NLI assigns support, contradiction or insufficient information to a pair of texts.
3. Keep every per-fact result and a citation index/hash. This makes a proposed answer change auditable without treating a model score as proof.
4. For each changed answer, compare its highest support score against the original answer's highest support. Root's separate protocol fixes the threshold candidates and calibration decision before inspecting revision outputs.
5. Select thresholds only using the pre-existing CTIBench fold-0 calibration split. Apply the selected rule once to the exposed SecEval diagnostic. Preserve all unsuccessful outcomes.

The scorer reads only an explicitly projected input schema: question ID, question, all four displayed options, actual retrieved evidence text/kind/retrieval score, and optional option letters needed for comparison. It rejects extra fields. It does not read released answers, source identifiers, generator correctness, or calibration outcomes. Policy selection and final scoring are separate from NLI inference.

## Pinned published model

- Model: [`cross-encoder/nli-deberta-v3-xsmall`](https://huggingface.co/cross-encoder/nli-deberta-v3-xsmall/tree/a150876415327c80daeff35ca6f68f5ed8cf5c24)
- Revision: `a150876415327c80daeff35ca6f68f5ed8cf5c24` (resolved with the primary Hugging Face model API on 2026-09-18).
- Model card: 70.8 million parameters, Apache 2.0, trained using SNLI and MultiNLI. The author reports 91.64% SNLI test accuracy and 87.77% MNLI mismatched accuracy; those figures are **not cybersecurity checker accuracy**.
- Label order, confirmed against the pinned configuration: contradiction, entailment, neutral.
- Runtime: CPU, float32, evaluation mode, no fine-tuning, safetensors only, no remote model code.
- Primary documentation: [published model card](https://huggingface.co/cross-encoder/nli-deberta-v3-xsmall/blob/a150876415327c80daeff35ca6f68f5ed8cf5c24/README.md), [Sentence Transformers NLI documentation](https://sbert.net/docs/cross_encoder/pretrained_models.html#nli).

This is an existing NLI model used as a diagnostic comparator. It is not a newly invented algorithm or an implementation of CoRM-RAG, CRAG, PAVE or SURE-RAG.

## Fixed text transformation and qualification

The premise is one exact retrieved fact. The hypothesis is:

> The answer to the question "{question}" is "{option text}".

This bridge is a material methodological risk: an arbitrary question and answer option are not automatically a natural declarative claim, and the model was not trained to verify this template. It can also confuse "not supported" with "false," miss negation in questions, or give high support to a topically similar answer. An option containing several claims is not decomposed into independently checked propositions.

Before opening any dataset input, `semantic_checker.py` runs eight fixed synthetic examples: four ordinary entailment/contradiction pairs checking the label mapping and four examples testing the question/answer template. All eight must produce the expected highest-scoring class. A failed gate writes an immutable failure receipt and exits without reading or scoring dataset rows. Passing is only a basic engineering qualification, not a validation of cybersecurity reasoning.

The eight cases, scores and pass/fail decision are saved in `NLI_QUALIFICATION.json`; model file hashes, software versions, code hash and runtime are saved separately. The gate and template are not adjusted in response to those outcomes.

## Reproducibility and measurement limits

- Every output retains the input hash, exact hypothesis, fact text hashes, per-fact probabilities, original token count and any truncation. The complete input file and output file are bound in the receipt.
- Inputs exceeding 512 combined tokenizer tokens use `longest_first` truncation, which is explicitly counted. Any truncated pair weakens a support claim; this must be visible in the report.
- The maximum support across six facts can exaggerate one spurious match. Supporting a proposed answer also does not prove that all competing options are wrong.
- The maximum contradiction across different facts is diagnostic only: one irrelevant contradictory statement may not apply to the question. Root's policy must specify whether it uses this value.
- A selected citation index identifies what the classifier scored. It does not establish that a human reviewer would find that passage applicable or sufficient.
- Both saved generator answers were already produced. Replay selection alone cannot demonstrate end-to-end latency savings; the cost of generating both answers remains real.
- This revision keeps the same ATT&CK evidence. It does not test retrieval from Android, web-security, or other authoritative source collections. Improvements in retrieval require a distinct experiment so their contribution can be measured separately.
- Independent human review remains pending. No AI evaluation substitutes for that review, and no source-disjoint or pretraining-clean generalization claim is warranted.

## What would justify continuing?

A promising diagnostic needs more useful corrections than harmful changes, a measurable advantage over simple relevance at comparable evidence-use rates, and support that reviewers can verify in the cited facts. A qualified checker should then be frozen and evaluated on previously unused, source-controlled questions. Failure of the template qualification is useful evidence to abandon this particular generic NLI bridge before spending resources on its full benchmark run.

Generic prediction of evidence utility already overlaps [CoRM-RAG](https://arxiv.org/html/2605.01302v1). The defensible potential contribution remains a rigorously evaluated cybersecurity applicability/answer-change method with explicit condition checks and failure analysis; this development attempt does not establish that contribution or novelty.
