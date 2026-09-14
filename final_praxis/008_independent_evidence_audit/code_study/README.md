# Praxis008: truthful selective evidence in code revision

The original experiment and its prospective schema extension have completed.
The result supports an empirical paper about **selective disclosure of executed
tests**: schema-constrained Qwen accepted 12/101 harmful native revisions with
selected testimony versus 4/101 with uniform testimony (+7.92 percentage points;
Holm-adjusted p=.015625). Devstral's corresponding contrast is unsupported.
The proposed hybrid verification policy failed its success criteria, and neither
model showed a disclosure contrast in the smaller generated-harm cohort.

Start with the [final results and portfolio summary](paper_package/FINAL_RESULTS_SUMMARY.md),
[manuscript starter](paper_package/MANUSCRIPT_STARTER.md), and
[detailed results](paper_package/RESULTS_AND_INVESTMENT.md).
The [automated readiness receipt](paper_package/PAPER_READINESS.md) records evidence
closure separately from scientific support. The complete treatment includes
withholding failures and possibly showing no records; it does not isolate a
geometric selection heuristic. The original and extension protocols retain all
research questions, assignments and decision rules.

The base is public HumanEvalPack/HumanEvalFix from OctoPack plus pinned HumanEvalPlus
inputs and evaluator predicates. qualification/SOURCE_MANIFEST.json binds releases;
qualification/fetch_prepare.py reconstructs inputs without executing downloaded
programs. qualification/QUALIFICATION_PROTOCOL.md states alignment and eligibility.
qualification/SPLIT_MANIFEST.json contains the41 development/123 heldout task split.
Raw test inputs, expected outputs and model messages are execution artifacts; they
must not accidentally become selector arguments.

The implementation separates source-only selectors (policies.py), typed model
interfaces (prompts.py), credential-bearing AWS orchestration (study_runner.py and
bedrock_adapter.py), isolated program execution (qualification/worker.py and
generated_execution.py), and preregistered analyses (analysis.py/offline_analysis.py).
The generated-code admission filter is a bounded semantic-defect contract, not a
proof against arbitrary hostile Python. Docker receives no network or credentials.

Run Python unit controls with `python -m unittest discover -p 'test_*.py'` from this
directory. Independent review scripts and source-bound receipts are in review/.
Linux worker/coordinator controls must run under the required nonroot, network-none
Docker settings; do not execute benchmark or generated programs directly on a host.

The authorized campaign host uses Ubuntu22.04/Python3.10 orchestration, pinned
requirements.txt, and python:3.11.9-slim-bookworm with NumPy1.26.4/psutil5.9.8 in Docker.
The qualification image ID is recorded in every run. Managed Bedrock model weights
and decoding seeds cannot be hash-pinned: model IDs, timestamps, raw requests,
responses, AWS request IDs and actual provider token counters are retained instead.

The model source bundle must contain MODEL_SOURCE_FREEZE.json and every file it
hashes, including qualification/SPLIT_MANIFEST.json. After an independently audited
full qualification and passing generated-coordinator controls, the cloud supervisor
runs `bash run_study.sh ABSOLUTE_CAMPAIGN_ROOT FROZEN_PROTOCOL_SHA256`. This checks
source hashes, freezes expected-value files, runs development before heldout,
enforces the per-model technical gates, and emits every planned assignment.
No permission or manual-review workflow is part of this authorized execution.

The campaign root contains bundle/, full/, orchestrator_env/, model_code/, study/
and generated_development/heldout/. run_study.sh is resumable with identical files:
request/assignment hashes prevent changed prompts from reusing cached responses.
Interrupted phases retain receipts and a process-status artifact. The trusted
outer supervisor supplies a six-hour timeout, periodic S3 snapshots and an external
eight-hour instance-stop watchdog; neither candidate code nor the Docker container
controls those protections. API cost ledger is capped at$30, total job envelope$100.

finalize_results.py checks the exact9,456 review assignments,328 model proposals,
656 proposal directions and131,200 offline assignments. Gated/budget/invalid/missing
outputs remain distinct from completed calls. Summary JSON/Markdown and flow/cost
receipts are written to study/public_results; bulky vectors and raw inference
receipts belong in archived artifacts rather than ordinary Git text files.

Public compressed result packages are in completed_models/; use the
[reproduction guide](paper_package/REPRODUCTION_GUIDE.md) to reproduce both versions
without AWS inference. Full source/evidence audits, accounting, and a disclosed
secondary floating-point [erratum](postrun_review/roundoff_amendment/README.md)
are in postrun_review/. The original result bytes and initial failed audit are
preserved; the correction changes no primary result or overall recommendation.

Paper-development material is in paper_package/. Public benchmark pretraining exposure,
bounded execution, supplied/intentional bugs and missing strong coverage-testing
baselines constrain all claims. Passing a finite outcome suite is not a proof of
semantic correctness or venue acceptance.
