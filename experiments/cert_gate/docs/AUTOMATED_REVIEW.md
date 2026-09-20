# Running the automated 50-case reviewer

The bot reviews visible alert evidence, cites exact text and returns **Attack**, **Non-Attack** or **Unable to verify**. It is a separate zero-shot model from the fitted SVM classifiers. It is not a human reviewer, and agreeing with released dataset labels does not independently establish ground truth.

The [frozen protocol](../FINAL_PROTOCOL.json) pins Qwen3-4B-Instruct-2507 to revision `cdbee75f17c01a7cc42f958dc650907174af0554`, a fixed prompt, greedy decoding and limits of 16,384 input tokens and 512 output tokens. A case exceeding these limits stays in the denominator as unable; the bot does not silently truncate or try alternate prompts until it matches the label.

## Completed-run artifacts

- [Automated agreement receipt](../results/automated_review_20260920/RESULTS.json)
- [Independent aggregate recount and confusion table](../results/automated_review_20260920/RECOUNT.json)
- [Cloud execution summary](../results/automated_review_20260920/CLOUD_SUMMARY.json)
- Private readable report: `C:/w/cert_gate_data_20260920/automated_review_v1/REVIEW_RESULTS.html`
- Private frozen answers: `C:/w/cert_gate_data_20260920/automated_review_v1/cloud/collected/outputs/review/frozen/`

The readable report contains quotations and source labels, so it stays outside public Git. Every public receipt binds private inputs/outputs with hashes.

## Reproduce with new output directories

In the commands below, replace `PRIVATE/...` with an **absolute path outside the repository**, and `PUBLIC/...` with the chosen aggregate-results path. These are placeholders, not literal directories to create inside Git. From the repository root, prepare the existing blinded packet without reading its answer key:

```powershell
python -m experiments.cert_gate.auto_review prepare --cases PRIVATE/REVIEW_CASES.json --private-output PRIVATE/prepared
```

The prepared directory contains only a fixed prompt, the 50 blinded cases, requests and a manifest. Ground-truth fields and derived attack annotations are stripped again. No answer key is copied.

For a CUDA host with compatible PyTorch and Transformers 4.57.6:

```powershell
python -m experiments.cert_gate.auto_review infer --prepared PRIVATE/prepared --private-output PRIVATE/review --device cuda --allow-download
```

Use the committed guarded AWS launcher for the existing research host:

```powershell
python -m experiments.cert_gate.auto_review_cloud --settings PRIVATE/cloud/settings.json --prepared PRIVATE/prepared --protocol experiments/cert_gate/FINAL_PROTOCOL.json --freeze experiments/cert_gate/FINAL_RUNTIME.json
```

The launcher uses private AWS settings, verifies source hashes and committed bytes, installs an automatic stop, uploads an allowlisted input bundle, recovers the results, verifies the stopped instance and removes its own stop schedule. Each attempt needs a fresh private directory and unique S3 prefix. Credentials and cloud identifiers must stay private. The prepared code hash must match the frozen worker.

Only after answers are frozen, run the local grader and readable report. The following example uses direct inference; for an AWS run, replace `PRIVATE/review/frozen` with `PRIVATE/cloud/collected/outputs/review/frozen`:

```powershell
python -m experiments.cert_gate.auto_review grade --frozen PRIVATE/review/frozen --answer-key PRIVATE/ANSWER_KEY.json --public-output PUBLIC/RESULTS.json
python -m experiments.cert_gate.review_report --frozen PRIVATE/review/frozen --answer-key PRIVATE/ANSWER_KEY.json --graded PUBLIC/RESULTS.json --private-html PRIVATE/REVIEW_RESULTS.html --output PUBLIC/RECOUNT.json
```

The grader validates answer/output hashes before reading the key. Missing, malformed, duplicate, unquoted or incomplete responses become unable. Exact quotation checks establish that text exists, not that the conclusion is correct. The post-freeze report independently recounts the confusion table and creates escaped static HTML without scripts or network calls.

## Interpretation

Report agreement over all 50 cases first, then agreement among decided cases. Never remove unable cases from the primary denominator. Forty-five agreements would meet a 90% **automated** point-agreement benchmark; it would still not satisfy the historical human-review requirement. Do not use these bot decisions to silently replace the original training labels. The user-authorized automated continuation is allowed to finish with disagreement or an inconclusive checker result.
