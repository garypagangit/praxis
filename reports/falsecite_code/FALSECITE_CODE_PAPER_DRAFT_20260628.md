# FalseCite-Code: Software-Artifact Citation Poisoning in Code-Assistant Prompts

Date: 2026-06-28

PX ID: PX-004

Status: **PUBLICATION DRAFT READY - BOUNDED POSITIVE**

## Abstract

Code assistants increasingly cite software artifacts such as packages, repositories, releases, and tags. FalseCite-Code tests whether a code-tuned model will accept fabricated software-artifact citations, and whether external metadata verification can reduce that trust without relying on model self-judgment. On a locked 80-claim slice spanning PyPI versions, NPM versions, GitHub repositories, and GitHub tags, `Qwen/Qwen2.5-Coder-7B-Instruct` accepted fabricated citations at high rates under both an audit-mode verdict gate and a generation-mode answer gate. A deterministic citation-aware verifier reduced strict-holdout fabricated trust to `0.0000` in the primary gates. The supported claim is narrow: external verification can guard software-artifact citations in this locked setup. The result does not prove universal hallucination prevention or universal model vulnerability.

## Thesis

Software-artifact citations are a practical attack and reliability surface for code assistants. A model can be prompted to trust fabricated package, version, repository, or tag claims, but a separate verifier grounded in public package and repository metadata can reject those fabricated citations more reliably than model judgment alone.

## Contributions

1. A locked 80-claim software-artifact citation benchmark with train, validation, and strict-holdout splits keyed by artifact id.
2. A source/verifier readiness gate using public PyPI, NPM, and GitHub metadata rather than model-generated labels.
3. An audit-mode model gate showing high fabricated-citation acceptance for a code-tuned instruct model.
4. A generation-mode gate showing the same vulnerability in short code-assistant answers.
5. Boundary evidence showing that behavior is model-dependent and that metadata evidence can fail while the external verifier remains robust.

## Benchmark

The benchmark contains `80` claims:

| Claim type | Claims |
|---|---:|
| GitHub repository | `20` |
| GitHub tag | `20` |
| NPM version | `20` |
| PyPI version | `20` |

The split discipline uses artifact ids, so paired clean and fabricated versions of the same artifact stay in the same split. This avoids a later verifier or model condition seeing the same package in train and strict holdout.

| Split | Claims |
|---|---:|
| Train | `45` |
| Validation | `20` |
| Strict holdout | `15` |

## Method

FalseCite-Code evaluates three answer conditions:

| Condition | Description |
|---|---|
| Suggested citation / base model | The model sees a code-assistant citation context and must decide whether to trust it. |
| Metadata evidence | The prompt includes public package or repository metadata evidence. |
| Citation-aware verifier | A deterministic verifier checks the artifact claim against external metadata and supplies the final guard decision. |

The important design choice is separation of duties. The verifier is not another free-form model judgment; it checks artifact existence, version/tag availability, and repository metadata directly.

## Results

### Source/verifier readiness

The source/verifier gate passed before any model claim was promoted.

| Method | Rows | Accuracy | Invalid recall | Invalid F1 |
|---|---:|---:|---:|---:|
| Strict external verifier | `80` | `1.0000` | `1.0000` | `1.0000` |
| Trust-all baseline | `80` | `0.5000` | `0.0000` | `0.0000` |
| Regex-suspicion baseline | `80` | `0.5000` | `0.0000` | `0.0000` |

### Audit-mode model gate

Primary model: `Qwen/Qwen2.5-Coder-7B-Instruct`.

| Condition | Accuracy | Invalid recall | Fabricated accepted | Clean overblock | Strict fabricated accepted |
|---|---:|---:|---:|---:|---:|
| Base model | `0.5500` | `0.2500` | `0.7500` | `0.1500` | `0.8571` |
| Metadata evidence prompt | `1.0000` | `1.0000` | `0.0000` | `0.0000` | `0.0000` |
| Citation-aware verifier | `1.0000` | `1.0000` | `0.0000` | `0.0000` | `0.0000` |

The audit gate supports a bounded vulnerability/remediation claim for the code-tuned 7B model: fabricated citations were accepted under the base condition, and both remediation conditions eliminated strict-holdout fabricated acceptance.

### Generation-mode gate

Primary model: `Qwen/Qwen2.5-Coder-7B-Instruct`, verbose 160-token answer setting.

| Condition | Accuracy | Fabricated trusted | Clean overblock | Parse failure | Strict fabricated trusted |
|---|---:|---:|---:|---:|---:|
| Suggested citation answer | `0.5190` | `0.6923` | `0.2750` | `0.0125` | `0.8333` |
| Metadata evidence answer | `0.9750` | `0.0000` | `0.0500` | `0.0000` | `0.0000` |
| Citation-aware verifier guard | `1.0000` | `0.0000` | `0.0000` | `0.0000` | `0.0000` |

This gate shows the vulnerability outside a one-token audit prompt. In short answer generation, the model still trusted fabricated citations under the suggested-citation condition, while the citation-aware verifier reduced strict-holdout fabricated trust to zero.

### External-validity and boundary evidence

| Gate | Model | Status | Key result |
|---|---|---|---|
| General instruct audit gate | `Qwen/Qwen2.5-3B-Instruct` | Boundary / no vulnerability under audit prompt | Base strict fabricated acceptance `0.0000`, but clean overblock `1.0000`. |
| Phi audit attempt | `microsoft/Phi-3.5-mini-instruct` | Invalid protocol | Parse failure `1.0000` for base and metadata conditions. |
| Coder 3B generation gate | `Qwen/Qwen2.5-Coder-3B-Instruct` | Boundary | Base strict fabricated trust `0.8571`; metadata evidence failed at `1.0000`; verifier reduced trust to `0.0000`. |

These checks narrow the claim. The vulnerability and remediation pattern is not universal, and prompt compatibility matters. The strongest repeated signal is the external verifier, not the metadata-evidence prompt.

## Supported Claim

For code-tuned assistants on the locked software-artifact citation slice, fabricated citations can be accepted at high rates under base prompting, and an external citation-aware verifier can suppress fabricated-citation trust to zero on the tested strict holdout.

## Claim Boundary

This paper draft does not claim:

1. Universal LLM vulnerability to citation poisoning.
2. Universal hallucination prevention.
3. General package-installation safety.
4. That metadata evidence always works as a remediation.
5. That the results transfer across all code assistants or all model families.

The safe claim is narrower and still useful: software-artifact citations can be guarded with external verification, and that verifier can outperform model-only trust decisions on the locked benchmark.

## Reproducibility Record

| Artifact | Purpose |
|---|---|
| `FALSECITE_CODE_LOCKED_CLAIMS_20260623.jsonl` | Locked 80-claim dataset. |
| `FALSECITE_CODE_SOURCE_VERIFIER_GATE_20260623.md` | Source/verifier readiness report. |
| `FALSECITE_CODE_MODEL_GATE_20260624.md` | Primary audit-mode model result. |
| `FALSECITE_CODE_GENERATION_GATE_VERBOSE160_20260625.md` | Primary generation-mode result. |
| `FALSECITE_CODE_GENERATION_GATE_QWEN25_CODER3B_20260626.md` | Code-tuned 3B boundary result. |
| `FALSECITE_CODE_CROSS_MODEL_SYNTHESIS_20260624.md` | Cross-model synthesis and limitations. |
| `FALSECITE_CODE_USEFULNESS_DECISION_20260625.md` | Final usefulness decision. |
| `FALSECITE_CODE_DASHBOARD_20260625.html` | Experiment-specific dashboard. |
| `../../scripts/run_falsecite_code_gate.py` | Source/verifier gate runner. |
| `../../scripts/run_falsecite_code_model_gate.py` | Audit-mode model gate runner. |
| `../../scripts/run_falsecite_code_generation_gate.py` | Generation-mode model gate runner. |

## Next Work

The immediate next step is not another rescue run. It is polishing this into a short paper or portfolio chapter with one figure for the benchmark pipeline, one table for the primary audit/generation results, and one limitation table for boundary evidence.

If scope expansion is needed, the next experiment should be a pre-registered second code-tuned model gate. The promotion rule should keep the verifier as the primary remediation and should not weaken the strict-holdout thresholds after seeing results.
