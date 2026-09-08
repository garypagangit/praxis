# Final Praxis parallel execution record

Date: 2026-09-08. Branch: `Final-Praxis-Proposals`.

## Authorization and scope

The user authorized prechecks, construction and execution of Final Praxis 001-003,
truthful results, defensible Praxis reports, and dashboard updates as experiments
finish. This authorization is recorded from the current conversation; the older
PX-057/PX-071 spending authorization is not treated as permission for these studies.

Only inert generated security scenarios and public model weights are used. No
experiment performs an action against an external security target. The source
proposals and prior claims remain as evidence; dated amendments must explain any
pre-outcome protocol completion or repair. Fixture results are infrastructure
checks, never scientific evidence.

## Compute envelope

- Existing EC2 `g5.xlarge` GPU instance `i-039ed976444ade397`, initially stopped.
- Second existing `g5.xlarge` `i-07178e293e8df2a60` only if needed for a separate model.
- Region: `us-east-1`; S3 bucket: `praxis-garypagan-272615233626-us-east-1`.
- Current AWS Pricing API on-demand Linux rate: USD 1.006 per instance-hour.
- Planned maximum: six hours per started GPU, at most two GPUs (USD 12.072 compute).
- Existing storage remains in place; no new volumes or security-group rules planned.
- Independent six-hour shutdown timer and final shutdown after artifact upload.
- Raw evidence is synchronized to a distinct `final-praxis/20260908/` S3 prefix.

## Pinned runtime and execution order

Qwen discovery: `Qwen/Qwen2.5-7B-Instruct` revision
`a09a35458c702b33eeacc393d103063234e8bc28`.

Distinct 001 primary judge: `mistralai/Mistral-7B-Instruct-v0.3` revision
`c170c708c41dac9275d15a8fff4eca08d52bab71`, resolved from the model repository API
before outcome collection.

Generation uses BF16 weights, SDPA attention, greedy decoding and seed 20260908.
Software and hardware versions are captured from the actual loaded runtime.
The loopback inference service batches up to eight requests. Batching concurrency
and floating-point hardware may prevent bit-for-bit replay; all raw generations,
request identities and model revisions remain auditable. Inputs are never silently
truncated; model-identity mismatch and inference errors stop the affected run.

All three implementations and prechecks proceed concurrently. Qwen inference can
be shared across their independent workflows. 001 runs agent and judge phases
separately so the distinct judge does not require both models in one GPU's memory.
Infrastructure pilots precede frozen discovery; thresholds cannot be changed after
their outcomes. Scientific classification requires independent raw-output checks.

## Reporting

Each experiment gets a final determination, independent verification, claim
boundary, and Praxis report with abstract, problem/significance, research questions,
related work, methodology, results, discussion, limitations, conclusion and
references. Reports distinguish structural properties of the generated benchmark,
model observations, statistical uncertainty and untested external validity.

The Markdown and HTML dashboards are updated at infrastructure and scientific
milestones, including blocked, negative, mixed and protocol-invalid outcomes.

## Byte preservation and runtime correction

The prior checkout used Git `core.autocrlf=true`. The frozen manifests bind actual
working-file bytes, including line endings. `.gitattributes` now disables text
conversion under `final_praxis/` so fresh checkouts preserve those audited bytes.
This can show line-ending-only diffs in older proposal files; their wording and
scientific thresholds remain unchanged. Exact source bundles are also retained in
S3. `git diff --ignore-space-at-eol` distinguishes substantive changes.

The separate Mistral environment initially lacked `protobuf`. Before any judge
outcomes, version 5.29.5 was installed into the isolated task `runtime-deps` folder;
the existing Python environment was not altered. Startup attempt 1 and its error
are retained. Attempt 2 passed the unrelated READY connection check with the frozen
model revision. This repairs infrastructure without a model or protocol change.
