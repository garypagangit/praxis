# Checking the reason for an AI answer change

**The revised checker did not improve the observed score in both models. It does not justify a claim that the evidence-applicability problem is solved. Preserve this outcome and use human error review before selecting another design.**

Recorded status: `EXPOSED_DIAGNOSTIC_MIXED_OR_NO_GAIN`. September 18, 2026.

## What changed

The previous checker estimated whether the whole six-fact bundle would help. The revision compares support for the model's original answer with support for its evidence-based answer. A published natural-language inference model scores each actual fact against a fixed question/option template. The policy permits a change only when the proposed answer's support exceeds the original answer's support by the frozen margin.

This is a generic semantic-checking adaptation. It does not yet explicitly verify every platform, version, time, or other condition, and it does not change retrieval. Supporting fact indices and text hashes make the scores traceable; they do not prove that the passages are sufficient.

## Design and qualification

- Published verifier: `cross-encoder/nli-deberta-v3-xsmall`, revision `a150876415327c80daeff35ca6f68f5ed8cf5c24`, CPU float32.
- All eight fixed qualification cases passed. Eight implementation tests passed. These establish basic execution, not cybersecurity efficacy.
- Thresholds were chosen only on the old 500-question CTIBench calibration split and frozen before the SecEval verifier run. Selected minimum support: **0**; strict support advantage: **>0.1**.
- Calibration mean gain was +5.40 points. It was used for selection and is not a heldout result.
- The scorer processed 280 calibration disagreement questions / 3,720 fact-option pairs, then 234 SecEval disagreement questions / 2,904 pairs. Every one of the 1,247 SecEval questions remains in accuracy denominators; same-answer cases keep the original answer.
- One old calibration question has an unused empty D option. The initial invocation stopped before scoring any pair. The [documented input-contract correction](ENGINEERING_AMENDMENT.md) retained the question and all its original strings; no score-dependent method change occurred.

## Complete development results

Accuracy is agreement with released SecEval answers. Changes are percentage points, not relative percentages.

| Policy | Llama accuracy | Qwen accuracy | Mean change from no extra facts, pp [95% CI] |
|---|---:|---:|---:|
| No extra facts | 86.53% | 87.09% | +0.00 [+0.00, +0.00] |
| Always add facts | 84.20% | 85.24% | -2.09 [-3.45, -0.76] |
| Previous utility checker | 86.21% | 87.25% | -0.08 [-0.52, +0.40] |
| Previous simple relevance checker | 86.29% | 87.81% | +0.24 [-0.20, +0.72] |
| Revised answer-change checker | 86.77% | 87.01% | +0.08 [-0.24, +0.40] |

| Model | Accepted answer changes | Corrections | New errors | Useful corrections rejected |
|---|---:|---:|---:|---:|
| Llama | 8 | 5 | 2 | 37 |
| Qwen | 8 | 3 | 4 | 52 |

## Paired comparisons

| Compared with | Llama difference, pp | Qwen difference, pp | Mean difference, pp [95% CI] |
|---|---:|---:|---:|
| No extra facts | +0.24 | -0.08 | +0.08 [-0.24, +0.40] |
| Always add facts | +2.57 | +1.76 | +2.17 [+0.88, +3.49] |
| Previous utility checker | +0.56 | -0.24 | +0.16 [-0.40, +0.72] |
| Previous simple relevance checker | +0.48 | -0.80 | -0.16 [-0.72, +0.40] |

The comparisons use the same question outcomes. Their confidence intervals resample questions within the fixed coarse-source counts, preserving both models together (5,000 draws, seed 20260918). They are not source-document cluster intervals or multiplicity-adjusted confirmation.

## What this can and cannot establish

SecEval was examined before this revision was designed. It remains **exposed development data**, even though no SecEval labels entered the NLI scorer or threshold selection. The [previous frozen external failure](../cti_external_validation_20260918/REPORT.md) remains unchanged. This revision cannot retroactively turn that result into a pass.

The verifier has generic NLI training, and the question/option hypothesis template has not been independently validated as a cybersecurity support test. Taking the strongest of six fact scores may accept a spurious match or miss a necessary combination of facts. Published benchmark labels may also be wrong or version-dependent; no completed human review is claimed.

Both original and evidence-based generator answers were already available. The revision makes no fresh generator calls, so it tests answer selection, not an end-to-end deployment's total cost. It is not an equal-cost comparison with the previous pre-generation checker. Accepted answer changes are not answer coverage, abstention, or measured retrieval savings.

Calibration verifier inference took 287.69 CPU seconds; external diagnostic inference took 274.76 seconds. Truncated fact-option pairs: 0 calibration and 0 external. No new AWS instance was started for this revision.

## Next action

Complete the existing [blinded human-review handoff](../cti_external_validation_20260918/REVIEW_HANDOFF.md). Then decide whether the failure concerns evidence retrieval, support verification, question/answer labels, or a combination. Test appropriate-source retrieval and answer checking in separate conditions, then together, under a new frozen protocol on untouched source-controlled questions. The [confirmation plan](NEXT_CONFIRMATION.md) specifies that distinction and stopping rules. Improved retrieval and untouched confirmation have not been run here.

The generic idea overlaps [CoRM-RAG](https://arxiv.org/html/2605.01302v1), [PAVE](https://arxiv.org/html/2603.20673v1), and [SURE-RAG](https://arxiv.org/html/2605.03534v2). None is reproduced in full by this experiment. Better development accuracy alone does not establish novelty.

## Reproducible record

[Protocol](PROTOCOL.md), [model and design review](DESIGN_REVIEW.md), [input audit](INPUT_AUDIT.json), [frozen calibration policy](POLICY_FREEZE.json), [full results](RESULTS.json), [per-question decisions](revision_decisions.jsonl), and [independent arithmetic audit](INDEPENDENT_AUDIT.json).

Reproduce the independent audit from the repository root with `python reports/cti_checker_revision_20260918/audit_revision.py --output INDEPENDENT_AUDIT_RECHECK.json`, choosing a new output filename if that file already exists. The audit uses the included byte-identical calibration archives and repository-relative external-test records. The policy/scoring/analysis scripts refuse to overwrite scientific outputs; work in a separate copy for a new run. Model weights are not included; the exact public revision and model file hashes are recorded in the receipts.
