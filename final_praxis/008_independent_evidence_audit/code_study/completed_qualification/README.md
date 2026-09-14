# Completed HumanEvalPack / HumanEval+ qualification

**The prespecified feasibility gate passed: 135 of 164 program pairs qualify, including 101 heldout pairs. All 29 exclusions remain in the results.** This establishes a usable benchmark cohort for the separately frozen Praxis model-decision study. It does not establish intervention efficacy or sufficient novelty for publication.

The base is [OctoPack / HumanEvalPack](https://arxiv.org/abs/2308.07124), extended using [EvalPlus](https://arxiv.org/abs/2305.01210). The preregistered question asks whether canonical/buggy pairs support reproducible repair and corruption outcomes with exact source identity and separate tool/outcome input pools. The threshold was at least 100 eligible pairs, including 60 heldout pairs. Eligibility requires canonical original-suite and reserved-outcome success, valid reference outputs on every reserved input, and at least one demonstrated reserved failure by the buggy program. Missing or unattempted results cannot supply that failure.

| Cohort | Assigned | Eligible | Excluded |
|---|---:|---:|---:|
| Development | 41 | 34 | 7 |
| Heldout | 123 | 101 | 22 |
| Total | 164 | 135 | 29 |

The fixed split seed is `praxis008-code-study-v1`. All 164 task IDs and callable signatures align. The 123,981 unique inputs comprise 32,090 tool inputs and 91,891 reserved outcomes before eligibility filtering. All base-input fingerprints, and matching fingerprints from confidently extracted literal example calls, are forced to the tool side. Remaining unique plus inputs use a deterministic 25%/75% split. Structural duplicates never cross sides. Public benchmark training exposure and unrecognized semantic equivalents remain possible; “reserved” describes the experiment's information boundary.

## What completed and what was excluded

Full qualification took **282.68 seconds** on the bounded AWS Docker workload. All 492 assigned task/variant records are retained: 490 workers completed and two reference workers exited before writing their summaries. The public archive has 371,943 normalized case records; 371,796 were present in worker output, and 147 missing rows remain explicitly unknown. Worker completion does not imply that every case passed or was attempted: task-budget and unavailable-reference statuses remain in the vectors.

The 29 excluded tasks fall into these disjoint descriptive groups:

| Group | Tasks | Interpretation |
|---|---:|---|
| Reference unavailable or erroneous | 4 | Python/15, /83, /130, /139 lack a valid full reserved reference |
| Canonical reserved disagreement or exception, with reference available | 16 | Incompatibility with the pinned extended evaluation; exceptions and comparison failures are retained separately |
| Canonical reserved timeout | 7 | Resource-dependent exclusion under the frozen time caps |
| Original-suite namespace compatibility only | 2 | Python/38 and /50; explained below |

The frozen reason counts overlap: 4 reference failures/incompleteness, 27 canonical reserved non-pass cases, and 3 original-suite exceptions. These are not 34 distinct tasks. [TASK_RESULTS.json](TASK_RESULTS.json) contains every reason and test-status count; [RESULTS.json](RESULTS.json) contains the disjoint grouping and exact IDs.

**Partial reference workers:** Python/15 and Python/130 each reached the 64 MiB output-file limit, exited with code 1 and `OSError: File too large`, and left a truncated JSONL tail. They retain 56 and 91 missing outcomes, respectively, as `not_run_worker_incomplete`; both tasks are excluded. Python/83 and Python/139 instead completed their workers with 29 and 49 recorded `ValueError` cases. Those records do not identify the precise stage responsible for each error, so this package does not label them canonical semantic defects. No qualified buggy worker is missing a summary.

**Original-test namespace compatibility, identified after the main-study freeze:** the released original tests for Python/32, /38, and /50 call `poly`, `encode_cyclic`, and `encode_shift`. Those helpers exist in their canonical programs. The frozen [worker](../qualification/worker.py#L115) creates a separate original-test namespace containing the entry point and assertion recorder at line 116, then executes the tests at line 119; it does not bind these helpers. All three original suites therefore record `NameError`. Python/38 and /50 are excluded solely for this compatibility issue; Python/32 also has reserved disagreement/exception. This is not evidence that those canonical programs are semantically wrong. [RESULTS.json](RESULTS.json) records helper-definition and call line numbers plus per-program/test hashes. The 135-pair cohort and frozen code remain unchanged; any namespace correction belongs to a separately versioned follow-up. The eligible cohort's canonical original and reserved outcomes passed the recorded gate.

## Automated review and ordering

The independent full audit passed **7,075/7,075 checks**, covering hashes, all assigned identities, process receipts, normalization, exact exclusion reasons, and the eligibility threshold. The amended auditor explicitly distinguishes missing summaries from completion; 12/12 synthetic metadata controls and 372/372 pilot regression checks passed. The original auditor had assumed every worker would write a summary and stopped at the first missing file. Its audit-only correction was included in commit `162d2ab` before the main model-study launch; qualification execution, reference outputs, eligibility, and frozen worker code were unchanged.

The generated-proposal coordinator passed **31/31 integration checks** on four known-code controls: admitted canonical positive, admitted buggy negative, wrong declared hash, and invalid placeholder. Exactly two were executed in isolated Docker; the latter two were rejected without execution. Their outcomes were true, false, unknown, and unknown as required. These were infrastructure controls with zero model calls, not experimental model results.

Before qualification execution, source review also amended the EvalPlus evaluator pin from v0.3.1 to upstream `26d6d00...`, which records successful `find_zero` residual cases before continuing. The independent residual comparator and original-assertion trace controls were frozen before execution. See the [qualification protocol](../qualification/QUALIFICATION_PROTOCOL.md), [find-zero review](../review/FIND_ZERO_REVIEW.md), and [source review receipt](../review/SOURCE_REVIEW_RECEIPT.json).

## Reproduce and inspect

- [Qualification README](../qualification/README.md): fetch/prepare, bundle and isolated pilot/full commands.
- [Source manifest](SOURCE_MANIFEST.json), [run configuration](RUN_CONFIGURATION.json), and [receipt](RECEIPT.json): source, task, worker, runtime-image, and output hashes.
- [Full independent audit](FULL_INDEPENDENT_AUDIT.json), [auditor](../review/audit_qualification_results.py), and [metadata controls](AUDITOR_METADATA_CONTROLS.json).
- [Coordinator control receipt](GENERATED_COORDINATOR_CONTROLS.json) and [control preparation/verification script](../review/generated_controls.py).
- [All per-case status records](CASES.jsonl.gz): 21,212,815-byte gzip, 371,943 rows. Every row was checked to contain only IDs, split/membership metadata, statuses, timings, or error types. Inputs, expected values, programs, and private gold outputs are absent.
- [Package manifest](PACKAGE_MANIFEST.json): SHA256 of each packaged artifact. The original frozen files were copied byte-for-byte.

HumanEvalPack is pinned to [revision 9a41762...](https://huggingface.co/datasets/bigcode/humanevalpack/tree/9a41762f73a8cb23bb5811b73d5aab164efcf378), [OctoPack source e17a8f6...](https://github.com/bigcode-project/octopack/tree/e17a8f6470264286bc6a52eb8263582083bf3bf6), [HumanEval+ release v0.1.10](https://github.com/evalplus/humanevalplus_release/releases/tag/v0.1.10), and [EvalPlus evaluator 26d6d00...](https://github.com/evalplus/evalplus/tree/26d6d00bb1fd0fa37f39c99d5290da67891d1c5e). Qualification bundle SHA256 is `08a5fc6ed73f2332b9732d1effeb90d62c830ac2d38120bc3494728761eccf88`; worker SHA256 is `b79d909af1358a0bf1676806f65e9816f6418abbcd43fec40649b51de2010354`. Remaining source and image hashes are in [RESULTS.json](RESULTS.json).

## Compute accounting

Qualification made zero model calls. At the captured Linux g5.xlarge on-demand rate of **$1.006/hour**, full-run wall time corresponds to approximately **$0.079**, and pilot plus full wall time to approximately **$0.082**. These are workload-time equivalents, not an AWS invoice or total instance spend. They exclude setup, image building, downloads, idle time, control execution, the subsequent model study, storage, and transfer. The [rate capture](RATE_CAPTURE.json) and exact calculation inputs are retained in [RESULTS.json](RESULTS.json).
