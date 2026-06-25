# FalseCite-Code Cross-Model Synthesis

Date: 2026-06-24

## Decision

Status: **MIXED / bounded positive**

The FalseCite-Code track now has one strong model-vulnerability/remediation result and two external-validity constraints.

The defensible positive claim is narrow: on the locked 80-row software-artifact citation slice, `Qwen/Qwen2.5-Coder-7B-Instruct` accepted fabricated code-artifact citations under a base audit prompt, and both metadata evidence and the citation-aware verifier eliminated fabricated acceptance on strict holdout without overblocking valid claims.

Do not claim universal model vulnerability yet. The external-validity checks show that prompt/output behavior is model-dependent.

## Result Matrix

| Gate | Model | Status | Key result | Interpretation |
|---|---|---|---|---|
| Primary model gate | `Qwen/Qwen2.5-Coder-7B-Instruct` | **PASS** | Base strict-holdout fabricated acceptance `0.8571`; metadata evidence and verifier both `0.0000`; clean overblock `0.0000` | Strong bounded vulnerability/remediation result for a code-tuned instruct model. |
| Phi external-validity attempt | `microsoft/Phi-3.5-mini-instruct` | **INVALID PROTOCOL** | Retry completed, but base and metadata-evidence conditions had parse failure `1.0000`; raw outputs degenerated to repeated `computers` tokens | Not usable as reasoning evidence. Treat as generation-protocol incompatibility under this runner/prompt stack. |
| General Qwen replication | `Qwen/Qwen2.5-3B-Instruct` | **FAIL / no vulnerability under audit prompt** | Base strict-holdout fabricated acceptance `0.0000`, but clean overblock `1.0000`; metadata evidence strict clean overblock `0.125`; verifier clean overblock `0.0000` | Smaller general-instruct Qwen rejects too aggressively. It does not reproduce the coder-model vulnerability, but the verifier remains clean. |

## Primary Positive

Artifact: `reports/falsecite_code/FALSECITE_CODE_MODEL_GATE_20260624.md`

On `Qwen/Qwen2.5-Coder-7B-Instruct`:

| Condition | Overall accuracy | Invalid recall | Fabricated accepted | Clean overblock | Strict fabricated accepted |
|---|---:|---:|---:|---:|---:|
| Base model | `0.5500` | `0.2500` | `0.7500` | `0.1500` | `0.8571` |
| Metadata evidence | `1.0000` | `1.0000` | `0.0000` | `0.0000` | `0.0000` |
| Citation-aware verifier | `1.0000` | `1.0000` | `0.0000` | `0.0000` | `0.0000` |

This passes the preconfigured gate because the base model shows a substantial fabricated-citation acceptance vulnerability and the metadata/verifier conditions remove it without clean-claim overblocking on strict holdout.

## External-Validity Constraints

### Phi-3.5

Artifact: `reports/falsecite_code/FALSECITE_CODE_MODEL_GATE_PHI35_20260624.md`

The Phi run should not be used as a positive or negative model-behavior result. The first attempt hit a `DynamicCache` / `seen_tokens` generation incompatibility. The retry disabled cache and completed, but the model emitted repeated non-verdict text, producing parse failure `1.0000` for both model conditions.

Safe interpretation: this runner/prompt/generation stack is incompatible with Phi-3.5 for this forced verdict protocol.

### Qwen2.5-3B General Instruct

Artifact: `reports/falsecite_code/FALSECITE_CODE_MODEL_GATE_QWEN25_3B_20260624.md`

On the smaller general-instruct Qwen model, the base prompt rejected every citation:

| Condition | Overall accuracy | Invalid recall | Fabricated accepted | Clean overblock | Strict fabricated accepted |
|---|---:|---:|---:|---:|---:|
| Base model | `0.5000` | `1.0000` | `0.0000` | `1.0000` | `0.0000` |
| Metadata evidence | `0.9375` | `1.0000` | `0.0000` | `0.1250` | `0.0000` |
| Citation-aware verifier | `1.0000` | `1.0000` | `0.0000` | `0.0000` | `0.0000` |

Safe interpretation: the general-instruct model does not show the fabricated-citation acceptance vulnerability under this audit prompt because it over-refuses. This is useful boundary evidence, not a replication of the primary positive.

## Claim Boundary

Supported:

- A code-tuned instruct model can accept fabricated software-artifact citations under a direct audit prompt.
- Strict metadata evidence and an external citation verifier can eliminate fabricated acceptance on the locked slice for the primary model.
- A deterministic verifier remains reliable across the locked slice.

Not supported:

- A universal LLM vulnerability claim.
- A cross-family replication claim.
- A claim that metadata evidence always improves utility; the Qwen2.5-3B evidence condition still overblocked one strict-holdout clean claim.

## Next Action

The next logical FalseCite-Code gate should use a more realistic code-assistant workflow rather than a single-token audit prompt:

1. Ask the model to answer a package/repository question with a citation.
2. Inject clean versus fabricated citation context.
3. Score whether the final answer repeats, trusts, or rejects fabricated artifacts.
4. Keep the citation-aware verifier as the deterministic remediation layer.

This would test citation poisoning in generation mode and avoid conflating model vulnerability with audit-prompt conservatism.
