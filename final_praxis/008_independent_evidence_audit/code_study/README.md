# Praxis008: truthful selective evidence in code revision

This directory contains the prospective experiment, not a claim that its candidate
policy is effective. Read MODEL_STUDY_PREREG.md for the research questions, closest
prior work, assignments, budget and decision rules. Qualification and model outcomes
are separate phases. Earlier AutoDC work remains in ../oracle_repair/ unchanged.

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

Paper-development material is in paper_package/. Its methods and historical status
can be drafted before results, but conclusions, recommendation and readiness require
the final independent artifact review. Public benchmark pretraining exposure,
bounded execution, supplied/intentional bugs and missing strong coverage-testing
baselines constrain all claims. Passing a finite outcome suite is not a proof of
semantic correctness or venue acceptance.
