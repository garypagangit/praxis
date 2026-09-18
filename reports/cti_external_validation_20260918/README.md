# CTI external validation

This experiment tests whether the checker from the completed CTI pilot helps on a different public security benchmark. The practical problem is simple: retrieved security facts can be correct yet make the AI choose a worse answer because they do not apply to the question.

## Read first

- `REPORT.md` and `STATUS.md` contain the actual result after the complete run is scored. Their absence means no completed external result has been published here.
- [PROTOCOL.md](PROTOCOL.md) fixes the question, models, comparisons and decision rules before new generator answers.
- [AWS_CONNECTION.md](AWS_CONNECTION.md) records the working AWS connection and renewal procedure.
- [HUMAN_REVIEW.md](HUMAN_REVIEW.md) describes the remaining independent human review. Prepared forms are not completed reviews.
- [human_review.html](human_review.html) is the offline form for reviewers: open it, enter judgments and download the completed response file. No reference answers or model results are embedded.

## Evidence and execution

| File | Purpose |
|---|---|
| `DATA_AUDIT.json` | Pinned dataset, filtering, historical exposure checks, corpus/retriever hashes and label/source invariance. |
| `test_inputs.jsonl` | 1,247 safe question/options/evidence records, without reference answers or source labels. |
| `sealed_labels.jsonl` | Released benchmark answers and coarse source metadata, used only for evaluation. |
| `DEPLOYMENT_METADATA.json` | Single old-data training/calibration fit and fixed cutoffs. |
| `CHECKER_VALIDATION.json` | Completed relevance-score and frozen-decision verification. |
| `policy_predictions.jsonl` | Fixed checker scores and choices before generator inference. |
| `PROMPT_VERIFICATION.json` | All 2,500 historical prompt pairs reproduced exactly; new and qualification prompt hashes. |
| `ANALYSIS_REVIEW.json` | Independent pre-inference implementation review and synthetic-test results. |
| `SCIENTIFIC_FREEZE.json` | Hashes of prepared scientific files before fresh generator answers. |
| `FREEZE.json` | Exact committed GPU runtime files and bounded operational plan. |
| `RESULTS.json` | Full validated benchmark results only after all expected outputs are present. |
| `scored_records.jsonl` | Per-question reconstruction of policy outcomes. |

Private AWS settings, credentials-managed session details, launch receipts and downloaded raw outputs live outside the Git report at `C:/w/cti_external_private_20260918`. No credential values belong in the report or runtime archive. The cloud launcher preserves output archives and verifies the host is stopped.

## Reproduce the analysis

The analysis requires the original complete output directory containing `runtime.json`, `qualification.jsonl` and `predictions.jsonl`, together with every file bound in `SCIENTIFIC_FREEZE.json`:

```powershell
python reports/cti_external_validation_20260918/analyze_external.py --outputs <complete-output-directory>
python reports/cti_external_validation_20260918/summarize_external.py
```

The first command rejects incomplete inventories, altered frozen files, mismatched input/model receipts and parser discrepancies. The report generator does not change thresholds or rescore answers.

Generator replay requires the pinned model weights and compatible GPU environment. The archived runtime bundle supplies prompts and generation code; it excludes reference labels and checker outcomes. The original source reconstruction scripts additionally require the historical project inputs and frozen builder files at the paths whose hashes are recorded in `DATA_AUDIT.json`. A new generator attempt requires its own explicit operational record and protocol amendment; do not overwrite this attempt.

## Attribution and claim limits

SecEval: Guancheng Li, Yifeng Li, Guannan Wang, Haoyu Yang and Yang Yu, *SecEval: A Comprehensive Benchmark for Evaluating Cybersecurity Knowledge of Foundation Models* (2023), [official repository](https://github.com/XuanwuAI/SecEval), [pinned dataset](https://huggingface.co/datasets/XuanwuAI/SecEval/tree/205dab7b0888a06f4b53ca7d9c7093e1326683e1). Its dataset is CC BY-NC-SA 4.0; code licensing is separate. Preserve this attribution and the dataset's license conditions for distributed derived question/evidence records.

Published-reference answer agreement is not independent security truth. The benchmark authors used GPT-4 to generate and calibrate questions. Public-data pretraining exposure, shared source documents and source-version differences remain possible. The broader idea of evaluating evidence usefulness already appears in [CoRM-RAG](https://arxiv.org/html/2605.01302v1). This experiment does not establish a novel algorithm or superiority over the complete CRAG or CoRM-RAG systems. The previous positive pilot remains a separate, bounded result in `../cti_checker_pilot_20260918/REPORT.md`.
