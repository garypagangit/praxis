# CTI checker feasibility experiment

This folder contains a new local experiment over archived CTI answer pairs. It tests whether a selector can decide when to use retrieved security information. The original generators are not rerun; new neural relevance scores and new trained selection policies are computed.

## Read first

- `REPORT.md`: results and plain-language recommendation, written after execution.
- `PROTOCOL.md`: hypotheses, comparisons, thresholds and limitations specified before fitting.
- `FREEZE.json`: hashes binding the protocol, code, data and source-group split before fitting.
- `RESULTS.json`: full numerical results, intervals and pass/fail criteria.
- `BASELINES.md`: exact published relevance model and stronger comparisons not run here.
- `REVIEW.json`: independent automated integrity review; inspect its actual completion status.

This is retrospective exploration on a public benchmark already used by the project. A new split does not make the data fresh. Success would justify a follow-up; it would not establish a novel algorithm or a complete Praxis.

## Reproduce

The current machine's isolated environment is `C:/w/cti_checker_env_20260918`, created with system site packages. It adds Transformers 4.57.6 without changing the base Python environment. Exact package/model versions and hashes are in the scoring and fit receipts. Model files are cached outside this report at `C:/w/cti_checker_model_cache_20260918`.

Run these from the workspace root in PowerShell, using a **new output copy** if independently rerunning rather than overwriting the archived result:

```powershell
$pilotPython = 'C:/w/cti_checker_env_20260918/Scripts/python.exe'
$pilotDir = 'reports/cti_checker_pilot_20260918'
& $pilotPython "$pilotDir/prepare_data.py"
& $pilotPython "$pilotDir/prepare_relevance_options.py"
& $pilotPython "$pilotDir/score_relevance.py"
& $pilotPython "$pilotDir/score_relevance_options.py"
& $pilotPython "$pilotDir/run_pilot.py" freeze
& $pilotPython "$pilotDir/run_pilot.py" fit
& $pilotPython "$pilotDir/run_pilot.py" analyze
& $pilotPython "$pilotDir/verify_pilot.py" --require-post
& $pilotPython "$pilotDir/build_artifacts.py"
```

For the recorded experiment the freeze was created before selector fitting while outcome-independent relevance inference was in progress. Scoring is resumable only with identical inputs/specifications. Fitting validates completed score receipts and checks every frozen hash. The prepare script requires the original verified input files listed in `DATA_AUDIT.json`, including the canonical package at `C:/w/px_final_20260917`.

Source-grouped cross-fitting uses five outer test folds. Each fit has 1,500 training, 500 validation and 500 test questions. Related ATT&CK techniques and parts of the same source document cannot cross these partitions. Every question receives one held-out selector decision. Shared cross-validation training, known aggregate results and public-data exposure limit interpretation.

## Files

| File | Purpose |
|---|---|
| `prepare_data.py`, `data.jsonl`, `DATA_AUDIT.json` | Verified safe feature projection and paired archived outcomes |
| `prepare_relevance_options.py`, `relevance_options_projection.json` | Verifies the option-inclusive input transformation |
| `score_relevance*.py`, `relevance*_scores.jsonl`, `relevance*_metadata.json` | Pinned published neural scorer, raw predictions, timing and model hashes |
| `run_pilot.py`, `SPLITS.json`, `FEATURE_AUDIT.json` | Fixed training/threshold rules and feature exclusion checks |
| `predictions.jsonl`, `FIT_RECEIPT.json` | Every held-out score/decision and validation-selected threshold |
| `RESULTS.json` | Paired accuracy, evidence use, harms, benefits and source-group intervals |
| `verify_pilot.py`, `REVIEW.json` | Independent validation of the run and its claims |

All arms answer every question. Rejecting retrieved evidence means using the archived vanilla answer; it does not mean refusing to answer. Equal evidence-use comparisons match the number of questions receiving evidence, not total computation. Learning utility requires paired generator outputs for training; this pilot reuses those costs rather than showing they disappear in deployment.

## Literature boundary

The [MiniLM model card](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) describes the implemented general passage-ranking model. Its raw scores are not probabilities of downstream correctness. [CoRM-RAG](https://arxiv.org/html/2605.01302v1) already learns an evidence critic for robust utility, so predicting benefit rather than relevance is not itself a new research idea. This pilot evaluates a particular practical implementation and comparison; it does not establish superiority over CoRM-RAG or full CRAG.
