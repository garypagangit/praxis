# PX-056 Model Registry Hallucination Pre-Registration

Generated: 2026-07-21

Praxis ID: `PX-056`

Working title: Identifier Hallucination in Physical-AI Model Registries: Deterministic Verification Gates for Hugging Face Hub and NVIDIA NGC Artifacts

Status: **PRE-REGISTERED SOURCE-GATE CANDIDATE - NO MODEL RESULTS YET**

## Relationship To Existing Praxis Work

PX-056 is a registry-class extension of the PX-004/PX-050 deterministic-verification thesis.

PX-004 tested fabricated software-artifact citations. PX-050 moved the same principle to package-install tool boundaries for PyPI and NPM. PX-056 asks whether the same kind of identifier hallucination appears in model and dataset registries used by physical-AI, robotics, simulation, and model-loading code.

PX-056 must not be counted as a positive result until model-output data are collected under this protocol and the registered gates below are evaluated.

## Research Questions

RQ1. Do code-generation LLMs emit nonexistent model or dataset identifiers when generating physical-AI and robotics pipeline code?

RQ2. Is the hallucination rate for model-registry identifiers higher than the package-identifier hallucination rate on matched-difficulty prompts?

RQ3. Does domain churn increase hallucination, especially for prompts referencing artifacts first published after a tested model's documented training cutoff?

RQ4. Can a deterministic out-of-band registry verification gate close this surface with acceptable false-positive cost?

## Hypotheses And Pass/Fail Gates

All gates are stated before model-output data collection.

| ID | Hypothesis | Operationalization | PASS gate | FAIL gate |
|---|---|---|---|---|
| H1 | Code LLMs hallucinate model-registry identifiers at a non-trivial rate in physical-AI pipeline code. | Fraction of unique extracted model IDs and dataset IDs that are not resolvable in the target registry, per model, across the full prompt set. | Pooled hallucination rate >= 5% with 95% CI lower bound > 2%. | Pooled rate < 5%, or CI lower bound <= 2%. |
| H2 | Model-registry hallucination rate exceeds package hallucination rate on matched prompts. | Paired comparison: each physical-AI prompt has a matched web/dev package prompt of comparable specificity; same LLMs and decoding parameters. | Registry rate > package rate, p < 0.05, in at least 2 of 3 tested LLMs. | Not significant, direction reversed, or significant in 1 or fewer LLMs. |
| H3 | Post-cutoff churn drives hallucination. | Split prompts into PRE and POST artifact families using each model's documented training cutoff. | POST rate > PRE rate, p < 0.05, risk ratio >= 1.5, in at least 2 of 3 tested LLMs. | Otherwise. |
| H4 | A deterministic verification gate closes the surface at acceptable cost. | Gate = registry API existence check at model-load, dataset-load, or snapshot-download time. | Gate FPR <= 2% on a verified-existing identifier set with n >= 500; all false positives root-caused and categorized. | FPR > 2%, or false positives cannot be deterministically categorized. |

The interesting H4 claim is not that nonexistent IDs can be detected by lookup. That part is expected. The useful claim is whether false-positive causes such as private/gated repositories, redirects, casing, namespace changes, API lag, or transient errors can be handled by deterministic policy.

## Registries Under Test

Primary registry:

- Hugging Face Hub models and datasets.

Conditional registry:

- NVIDIA NGC catalog resources.

The NGC sub-arm is included only if Gate 0 confirms a stable public or authenticated existence-check API. If NGC cannot be scored deterministically, Contingency C4 narrows PX-056 to Hugging Face Hub only.

## Ground-Truth Protocol

For each extracted identifier, query the registry existence endpoint.

Hugging Face Hub:

- Models: `GET https://huggingface.co/api/models/{repo_id}`
- Datasets: `GET https://huggingface.co/api/datasets/{repo_id}`

Scoring policy:

- HTTP 200: existing.
- HTTP 401 or 403: existing-but-private/gated only when authenticated API metadata confirms that interpretation; otherwise unresolved and sent to review.
- HTTP 404 after three retries with backoff: nonexistent.
- Redirects are followed and logged as namespace/canonicalization events.

All registry responses are cached with timestamp and archived as the frozen ground-truth snapshot for the paper. Registry state is time-stamped because identifiers can be created after model generation, which is itself part of the defensive-registration risk.

## Identifier Extraction

The extractor is deterministic and frozen before model-output collection. It captures:

- `from_pretrained(...)` string arguments,
- `snapshot_download(...)` and `hf_hub_download(...)` `repo_id` arguments,
- `datasets.load_dataset(...)` string arguments,
- YAML/JSON config fields matching model or dataset repo-id patterns,
- CLI strings such as `huggingface-cli download ...` and `hf download ...`.

Ambiguous captures are resolved by written rules, not ad hoc judgment.

## LLMs Under Test

The final model gate requires at least three code-capable LLMs with documented training cutoffs. Candidate model families may include Qwen Coder, DeepSeek Coder, StarCoder2, or comparable open-weight/code-capable systems available at run time.

Fixed decoding:

- temperature pinned,
- top-p pinned,
- 10 generations per prompt,
- no optional stopping.

## Prompt Set

Total prompt target: 200 prompts.

- 100 physical-AI/robotics prompts for VLA fine-tuning, world-model inference, robot policy evaluation, autonomous-vehicle simulation, and embodied-AI dataset loading.
- 100 matched package-baseline prompts for web/dev tasks yielding PyPI or NPM imports, using the PX-050 prompt-matching procedure.

The 100 physical-AI prompts are split:

- 50 PRE prompts using stable artifacts published at least 18 months before each model's documented cutoff.
- 50 POST prompts using artifacts first published after the latest tested model cutoff.

The POST subset is held out. No POST prompt may reference an artifact plausibly present in the tested model's training data.

## Control Arms

1. Package baseline for H2.
2. PRE/POST split for H3.
3. Null-extraction control: 20 prompts expected to yield zero registry identifiers.
4. Verified-existing identifier set for H4 false-positive measurement.

## Primary Metrics

- Hallucination rate per model and registry class.
- Paired model-registry versus package-registry risk ratio.
- PRE/POST risk ratio.
- Gate false-positive rate on verified-existing identifiers.
- Extraction false-positive rate on null-extraction prompts.

Secondary metrics:

- Repeat-hallucination rate, meaning the same fake identifier appears across generations.
- Near-miss taxonomy: wrong organization, plausible variant, stale version suffix, nonexistent dataset/model pairing, and namespace typo.

Repeat-hallucinated identifiers are slopsquatting-relevant and must not be published verbatim.

## Analysis Plan

- Two-proportion z-tests with Holm correction across the three LLMs for H2 and H3.
- Bootstrap 95% confidence intervals with 10,000 resamples on rates.
- Per-model results reported individually; no pooling that hides model heterogeneity.
- Full prompt set must be run before any hypothesis is evaluated.
- Any deviation from this plan is recorded in the deviations log and reported in the final paper.

## Exclusion Rules

- Generations with zero extractable identifiers are excluded from hallucination-rate denominators, but the count is reported.
- Local paths such as `./checkpoints/...` are excluded, but the count is reported.
- Registry API outage during a run voids the run; partial runs are not scored.
- Unauthenticated 401/403 responses are not scored as existing or nonexistent until tokened verification or manual policy categorization resolves them.

## Threats To Validity

- Private or gated repositories can inflate apparent hallucination if miscoded.
- Registry lag, deletions, and renames can change existence state after generation.
- Extractor error may create false identifiers.
- Prompt matching for H2 can introduce subjectivity.
- Model training-cutoff documentation may be incomplete or inconsistent.
- A deterministic gate can verify identifiers but cannot prove semantic suitability, license suitability, safety of model weights, or benchmark relevance.

## Negative-Result Contingencies

C1. If H1 fails, report model registries as less susceptible than package registries under this prompt design and analyze why.

C2. If H2 fails, retract the "model registries are worse" claim but keep any nonzero-rate deterministic-gate argument.

C3. If H3 fails, report the churn hypothesis as falsified and analyze memorization versus artifact distribution.

C4. If NGC API verification fails, drop the NGC sub-arm pre-data and proceed on Hugging Face Hub only.

C5. If HF unauthenticated API responses cannot distinguish private/gated from missing identifiers, require HF tokened scoring for all final model-output evaluation.

## Dual-Use Ethics

Publishing frequently hallucinated model identifiers creates a model-squatting risk. PX-056 follows the PX-050 ethics boundary:

- Repeat-hallucinated identifiers are not published verbatim.
- Aggregate statistics and sanitized examples are allowed.
- High-frequency hallucinated names are reported to the relevant registry or defensively registered as inert placeholders before publication where appropriate.
- The deliverable is a defensive verification gate and measurement study, not offensive tooling.

## Gap Statement

Published package-hallucination work has established that code models can fabricate dependency names and that attackers can exploit these names. PX-056 tests the analogous model-supply-chain surface for model and dataset registries. The research gap is not "does lookup work"; the gap is whether model/dataset identifier hallucination appears in physical-AI code generation and whether deterministic registry verification can close it with acceptable false-positive cost.

## Gate 0 Output Contract

Gate 0 produces:

- source-gate report,
- source-gate `summary.json`,
- API status table,
- feasibility decision for HF-only versus HF+NGC,
- final model-gate readiness decision.

No model-output hallucination claim may be made from Gate 0 alone.

