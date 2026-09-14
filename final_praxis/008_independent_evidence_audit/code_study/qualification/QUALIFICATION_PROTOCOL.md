# HumanEvalPack / HumanEval+ source and execution qualification

This protocol is written before executing downloaded programs. It qualifies a public code-repair benchmark for a subsequent model-decision study; it does not establish a novel intervention or publishable result by itself.

**RQ-Q:** Do the pinned Python HumanEvalPack canonical/buggy program pairs support reproducible repair and answer-corruption outcomes under their original tests and independently extended HumanEval+ inputs, with exact task/signature alignment and separate tool/outcome input pools?

**H-Q:** At least 100 of the 164 source pairs, including at least 60 held-out tasks, will meet the prespecified eligibility rule below. This is a feasibility threshold, not a claim that all published canonical implementations are correct under an extended contract. Every task remains in the qualification report, including failures and exclusions. Policy outcomes play no role in eligibility.

The base paper is [OctoPack / HumanEvalPack](https://arxiv.org/abs/2308.07124), which releases human-written bugs alongside canonical solutions across coding tasks. [EvalPlus](https://arxiv.org/abs/2305.01210) motivates extended testing because sparse original tests can accept incorrect programs. Both are public benchmarks, so training exposure and memorization remain possible. Reserved outcomes here mean withheld from the study's tools and intervention design, not private or guaranteed unseen during model training.

## Frozen sources and source-only amendment

- HumanEvalPack Python: Hugging Face revision `9a41762f73a8cb23bb5811b73d5aab164efcf378` (164 rows), loaded as Parquet data without remote dataset code.
- OctoPack source: `e17a8f6470264286bc6a52eb8263582083bf3bf6`; paper evaluation-harness branch: `fd7f6ed8841140e5923b48a96a48809c14d991a0`.
- HumanEval+ data release: `v0.1.10`, compressed artifact SHA256 recorded in `SOURCE_MANIFEST.json`.
- EvalPlus evaluator: `26d6d00bb1fd0fa37f39c99d5290da67891d1c5e`.

The initial source probe used evaluator v0.3.1 (`e5d0ed0bab96280b60b637ec7f15b5e4841b0cb2`). Static review found that its `find_zero` successful residual check continued before marking its per-test success. The current pinned upstream revision records success/progress before continuing. The evaluator pin is amended before any program execution; no task gold or model output motivated the change. The residual oracle, rather than equality to a particular root, is retained and independently controlled.

## Identity and split rules

Numeric task IDs map `Python/n` to `HumanEval/n`, for exactly `n=0..163`. Entry-point names and AST callable signatures (arguments/defaults/annotations/return annotations) must match. Source syntax errors, missing/duplicate IDs, or signature mismatches are retained and make that pair ineligible.

The shared split seed is `praxis008-code-study-v1`. Rank all task IDs by SHA256 of `seed + "|task|" + Python/n`; the first 41 are development and the remaining 123 held out. The pilot is the first eight development tasks in this fixed order. This task split is fixed before execution or eligibility filtering.

All EvalPlus base-input fingerprints are assigned to the tool side. Direct literal positional argument calls that can be statically extracted from HumanEvalPack `example_test` are also forced to that side; extraction coverage and unsupported call forms are reported. Among other unique plus-input fingerprints, rank SHA256 of `seed + "|input|" + task_id + "|" + fingerprint` and assign the first floor(25%) to tools and the remainder to reserved outcomes. Fingerprints use canonical JSON with sorted object keys and preserved scalar types. Cross-base/plus and repeated-input duplicates remain on one side. This is structural input disjointness, not a claim that every publicly disclosed input or semantic equivalent was recognized. Original HumanEvalPack test bodies are a separate qualification diagnostic and are not a study tool pool.

## Eligibility and failure accounting

A pair is eligible only when identity/signatures align, the HumanEvalPack canonical program passes its complete original test suite and every reserved HumanEval+ outcome, the EvalPlus reference produces valid outputs for every reserved input, and the HumanEvalPack buggy program fails at least one reserved outcome. A program exception or timeout is a failing outcome; infrastructure errors, missing results, or unattempted cases do not count as a demonstrated buggy failure. All canonical reserved cases must be attempted. Empty outcome pools are ineligible. Original and augmented results are reported separately.

The evaluator compares against the separately released EvalPlus canonical implementation. Its float comparison uses the pinned evaluator's tolerance semantics, including the polynomial-residual special oracle for `find_zero`. Original test assertions retain their pass/fail behavior; trace instrumentation records encountered assertions and stops on the same first failing assertion. Unreached original assertions and budget-censored augmented cases remain explicit.

One Linux worker runs one program variant for one task. Reference/variant namespaces are separate, inputs are copied per test, and no missing output is replaced by another program. Per-input canonical-reference cap is 5 seconds; variant cap is min(5 seconds, max(0.2 seconds, 4 times reference runtime)). Each task/variant has a 120-second wall budget and 2 GiB address-space cap. Original test suite cap is 10 seconds. Exceeding a task budget marks remaining cases unattempted; it does not silently drop them. A full qualification run uses at most three concurrent task chains. These limits can only be amended with a recorded protocol change and a complete rerun of affected controls before study decisions.

## Execution isolation and receipts

Downloaded programs run only in AWS Linux Docker containers as UID/GID 10001, with no network, no AWS credentials or host home mounts, all capabilities dropped, no-new-privileges, a read-only root filesystem, bounded memory/CPU/PIDs, and per-worker resource/time limits. Input code/data mounts are read-only; only the private result directory is writable. Windows performs source downloads, parsing, AST inspection, hash verification, and packaging only.

The Python image tag and installed package versions are recorded; the cloud build must additionally record the pulled base image digest and resulting image ID before execution. Source/data/script hashes, command arguments, runtime versions, per-input IDs/statuses, all 164 task outcomes, and exclusion reasons are retained. Pilot and full runs have separate immutable result directories. There are no model calls, policy result comparisons, or AWS mutations in this qualification package.
