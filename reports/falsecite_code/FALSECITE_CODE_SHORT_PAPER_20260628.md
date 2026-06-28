# FalseCite-Code: External Verification for Software-Artifact Citation Poisoning

Date: 2026-06-28

PX ID: PX-004

Status: **FINAL SHORT PAPER - BOUNDED POSITIVE**

## Abstract

Code assistants often cite software artifacts such as packages, repositories, versions, and tags. FalseCite-Code tests whether fabricated software-artifact citations can be trusted by code-tuned language models, and whether an external verifier grounded in public metadata can reduce that trust. On a locked 80-claim benchmark spanning PyPI versions, NPM versions, GitHub repositories, and GitHub tags, `Qwen/Qwen2.5-Coder-7B-Instruct` accepted fabricated citations at high rates in both audit-mode and generation-mode gates. A citation-aware verifier reduced strict-holdout fabricated trust to `0.0000` in the primary gates. The result supports a narrow, practical claim: software-artifact citations can be guarded with external verification. It does not support universal hallucination prevention or universal model-vulnerability claims.

## 1. Problem

Code-assistant answers frequently lean on references to software artifacts: a package exists, a repository is maintained, a version includes a feature, or a tag points to a release. These references are easy to fabricate and hard for a model to verify from language alone.

FalseCite-Code asks a bounded question:

Can a code-tuned assistant be induced to trust fabricated software-artifact citations, and can a separate verifier using public package and repository metadata reduce that trust?

## 2. Benchmark

The benchmark contains `80` locked claims with balanced artifact types.

| Claim type | Claims |
|---|---:|
| GitHub repository | `20` |
| GitHub tag | `20` |
| NPM version | `20` |
| PyPI version | `20` |

The data split is keyed by artifact id, so paired valid and fabricated variants of the same artifact stay in the same split.

| Split | Claims |
|---|---:|
| Train | `45` |
| Validation | `20` |
| Strict holdout | `15` |

Labels are derived from public metadata checks, not model judgment.

## 3. Method

FalseCite-Code evaluates three conditions:

| Condition | Purpose |
|---|---|
| Base / suggested citation | Tests whether the model trusts the provided software-artifact citation. |
| Metadata evidence prompt | Tests whether adding public metadata evidence changes model behavior. |
| Citation-aware verifier | Uses a deterministic metadata checker as the final guard. |

The key design choice is separation. The verifier does not ask the same model to judge its own citation; it checks external package and repository facts.

## 4. Results

### 4.1 Source/verifier readiness

The source/verifier gate passed before any model result was promoted.

| Method | Rows | Accuracy | Invalid recall | Invalid F1 |
|---|---:|---:|---:|---:|
| Strict external verifier | `80` | `1.0000` | `1.0000` | `1.0000` |
| Trust-all baseline | `80` | `0.5000` | `0.0000` | `0.0000` |
| Regex-suspicion baseline | `80` | `0.5000` | `0.0000` | `0.0000` |

### 4.2 Audit-mode model gate

Primary model: `Qwen/Qwen2.5-Coder-7B-Instruct`.

| Condition | Accuracy | Invalid recall | Fabricated accepted | Clean overblock | Strict fabricated accepted |
|---|---:|---:|---:|---:|---:|
| Base model | `0.5500` | `0.2500` | `0.7500` | `0.1500` | `0.8571` |
| Metadata evidence prompt | `1.0000` | `1.0000` | `0.0000` | `0.0000` | `0.0000` |
| Citation-aware verifier | `1.0000` | `1.0000` | `0.0000` | `0.0000` | `0.0000` |

In audit mode, the base model accepted fabricated citations on the strict holdout at `0.8571`. The citation-aware verifier reduced that to `0.0000`.

### 4.3 Generation-mode model gate

Primary model: `Qwen/Qwen2.5-Coder-7B-Instruct`, verbose 160-token answer setting.

| Condition | Accuracy | Fabricated trusted | Clean overblock | Parse failure | Strict fabricated trusted |
|---|---:|---:|---:|---:|---:|
| Suggested citation answer | `0.5190` | `0.6923` | `0.2750` | `0.0125` | `0.8333` |
| Metadata evidence answer | `0.9750` | `0.0000` | `0.0500` | `0.0000` | `0.0000` |
| Citation-aware verifier guard | `1.0000` | `0.0000` | `0.0000` | `0.0000` | `0.0000` |

The generation-mode gate matters because it is closer to a code-assistant answer. The model still trusted fabricated citations under the suggested-citation condition, while the verifier reduced strict-holdout fabricated trust to zero.

### 4.4 Boundary evidence

| Gate | Model | Status | Key result |
|---|---|---|---|
| General instruct audit gate | `Qwen/Qwen2.5-3B-Instruct` | Boundary | Base strict fabricated acceptance `0.0000`, but clean overblock `1.0000`. |
| Phi audit attempt | `microsoft/Phi-3.5-mini-instruct` | Invalid protocol | Parse failure `1.0000` for base and metadata conditions. |
| Coder 3B generation gate | `Qwen/Qwen2.5-Coder-3B-Instruct` | Boundary | Base strict fabricated trust `0.8571`; metadata evidence failed at `1.0000`; verifier reduced trust to `0.0000`. |

The boundary evidence narrows the claim. The vulnerability is not universal under every prompt/model pair. Metadata evidence can fail. The strongest repeated remediation is the external verifier.

## 5. Supported Claim

For code-tuned assistants on the locked software-artifact citation slice, fabricated citations can be accepted at high rates under base prompting, and an external citation-aware verifier can suppress fabricated-citation trust to zero on the tested strict holdout.

## 6. Claim Boundary

This result does not claim:

1. Universal LLM vulnerability to citation poisoning.
2. Universal hallucination prevention.
3. General package-installation safety.
4. That metadata evidence always works as a remediation.
5. Transfer across all code assistants or model families.

The practical claim is narrower: software-artifact citation trust can be guarded by external metadata verification, and that guard can outperform model-only trust decisions on this locked benchmark.

## 7. Reproducibility Record

| Artifact | Purpose |
|---|---|
| `FALSECITE_CODE_LOCKED_CLAIMS_20260623.jsonl` | Locked 80-claim benchmark. |
| `FALSECITE_CODE_SOURCE_VERIFIER_GATE_20260623.md` | Source/verifier readiness result. |
| `FALSECITE_CODE_MODEL_GATE_20260624.md` | Primary audit-mode result. |
| `FALSECITE_CODE_GENERATION_GATE_VERBOSE160_20260625.md` | Primary generation-mode result. |
| `FALSECITE_CODE_GENERATION_GATE_QWEN25_CODER3B_20260626.md` | Code-tuned 3B boundary result. |
| `FALSECITE_CODE_CROSS_MODEL_SYNTHESIS_20260624.md` | Cross-model synthesis and limits. |
| `FALSECITE_CODE_USEFULNESS_DECISION_20260625.md` | Final usefulness decision. |
| `FALSECITE_CODE_DASHBOARD_20260625.html` | Per-experiment dashboard. |
| `../../scripts/run_falsecite_code_gate.py` | Source/verifier runner. |
| `../../scripts/run_falsecite_code_model_gate.py` | Audit-mode runner. |
| `../../scripts/run_falsecite_code_generation_gate.py` | Generation-mode runner. |

## 8. Conclusion

FalseCite-Code is a useful bounded Praxis result. It shows a concrete software-artifact citation poisoning failure mode in a code-tuned assistant and a practical mitigation path through external verification. The work should be presented as a narrow citation-verification result, not as a broad hallucination or model-safety solution.
