# FalseCite-Code: External Verification for Software-Artifact Citation Poisoning

Research manuscript draft

Praxis ID: PX-004

Generated: 2026-07-14

Status: Bounded defense-ready positive

## Abstract

Code assistants routinely mention software packages, repositories, versions, and tags. When those citations are fabricated, a developer may trust a non-existent artifact or a package name that could later be registered by an attacker. PX-004 introduces FalseCite-Code, an 80-claim benchmark spanning PyPI versions, NPM versions, GitHub repositories, and GitHub tags. It tests whether a code-tuned assistant accepts fabricated software-artifact citations and whether deterministic external metadata verification can suppress that failure mode. In audit mode, Qwen2.5-Coder-7B-Instruct accepted fabricated strict-holdout citations at 0.8571 under base prompting. In generation mode, fabricated strict-holdout trust was 0.8333 under suggested-citation prompting. A citation-aware verifier reduced strict-holdout fabricated trust to 0.0000 in the primary gates, with verifier accuracy 1.0000 and invalid recall 1.0000 on the locked source/verifier gate. The result supports a bounded guardrail claim: external package and repository metadata verification can prevent fabricated software-artifact citation trust on the tested benchmark.

## 1. Introduction

Software-artifact references are high-impact claims. A package name, version number, repository, or release tag can drive installation, dependency selection, or vulnerability triage. Code-generating LLMs can produce plausible but false artifact citations. In a supply-chain setting, those hallucinations are more than factual errors; they can create an attack surface if an attacker registers or weaponizes plausible names.

PX-004 studies this problem at the citation-verification layer. It does not execute installs and does not claim complete package-install safety. Instead, it tests whether fabricated software-artifact claims can be detected by an external verifier before they are trusted.

## 2. Prior Work

Package hallucination research directly motivates the threat model. Spracklen et al. analyzed package hallucinations by code-generating LLMs and framed them as a supply-chain threat. Krishna et al. similarly measured package hallucination vulnerabilities across languages and model settings, emphasizing that hallucinated dependencies can introduce broad supply-chain risk.

Work on factuality and retrieval-grounded evaluation motivates the separation between model answer and external evidence. Factuality evaluation papers such as FActScore argue that generated claims should be checked against reliable sources rather than judged by fluency.

PX-004 differs from broad package-hallucination measurement. It constructs a small locked benchmark of software-artifact citation claims and tests a guardrail: deterministic verification against authoritative metadata for PyPI, NPM, and GitHub.

## 3. Experimental Design Influences

Package-hallucination papers shaped the artifact categories: PyPI, NPM, and repository references are included because language-model package recommendations create plausible supply-chain exposure.

Factuality-evaluation work shaped the verification design: the verifier is separate from the model and checks public metadata rather than asking the model to self-judge.

Security engineering concerns shaped the split design: valid and fabricated variants for the same artifact are keyed by artifact ID so paired variants stay together, reducing leakage between split conditions.

The experiment also adds generation-mode evaluation because a natural code-assistant answer is more realistic than a pure audit prompt.

## 4. Research Questions

RQ1: Do code-tuned models trust fabricated software-artifact citations under base or suggested-citation prompting?

RQ2: Does metadata evidence reduce fabricated trust?

RQ3: Does a deterministic citation-aware verifier outperform trust-all and regex-suspicion baselines?

RQ4: Does the guardrail remain effective in generation-mode answers?

## 5. Data and Methods

The locked benchmark contains 80 claims.

| Claim type | Claims |
|---|---:|
| GitHub repository | 20 |
| GitHub tag | 20 |
| NPM version | 20 |
| PyPI version | 20 |

The protocol evaluates:

| Condition | Purpose |
|---|---|
| Base or suggested citation | Tests whether the model trusts the citation |
| Metadata evidence prompt | Tests whether provided metadata changes model behavior |
| Citation-aware verifier | Checks authoritative external metadata |

The verifier checks facts such as package version existence, repository existence, and tag existence. Its output is deterministic and separated from model judgment.

## 6. Results

Source/verifier readiness:

| Method | Rows | Accuracy | Invalid recall | Invalid F1 |
|---|---:|---:|---:|---:|
| Strict external verifier | 80 | 1.0000 | 1.0000 | 1.0000 |
| Trust-all baseline | 80 | 0.5000 | 0.0000 | 0.0000 |
| Regex-suspicion baseline | 80 | 0.5000 | 0.0000 | 0.0000 |

Audit-mode primary gate:

| Condition | Accuracy | Invalid recall | Fabricated accepted | Clean overblock | Strict fabricated accepted |
|---|---:|---:|---:|---:|---:|
| Base model | 0.5500 | 0.2500 | 0.7500 | 0.1500 | 0.8571 |
| Metadata evidence prompt | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| Citation-aware verifier | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |

Generation-mode primary gate:

| Condition | Accuracy | Fabricated trusted | Clean overblock | Parse failure | Strict fabricated trusted |
|---|---:|---:|---:|---:|---:|
| Suggested citation answer | 0.5190 | 0.6923 | 0.2750 | 0.0125 | 0.8333 |
| Metadata evidence answer | 0.9750 | 0.0000 | 0.0500 | 0.0000 | 0.0000 |
| Citation-aware verifier guard | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

Boundary evidence showed that vulnerability and metadata-prompt remediation are model/prompt dependent, but the external verifier remained the strongest repeated remediation.

## 7. Discussion

PX-004 shows why software-artifact citation checking should not be left to model fluency. The model can accept fabricated citations at high rates, particularly in strict holdout conditions. Metadata evidence can help, but the most reliable intervention is the deterministic verifier.

The result is intentionally bounded. PX-004 is not a general package-install gate and does not prevent every supply-chain attack. It demonstrates that fabricated citation trust can be reduced to zero on a locked artifact-citation benchmark when the final decision is delegated to external metadata checks.

## 8. Threats to Validity

The benchmark has 80 claims, so it is a compact controlled slice rather than a broad ecosystem survey. The result depends on the availability and correctness of public metadata APIs. Model behavior can vary with prompt format and model family. The experiment verifies citation claims, not arbitrary shell commands or dependency graphs.

## 9. Conclusion

FalseCite-Code supports a practical guardrail claim: code-assistant software-artifact citations should be checked externally before being trusted. On the measured benchmark, the citation-aware verifier closed the fabricated-trust gap in both audit and generation modes.

## Repository Artifacts

- `reports/falsecite_code/FALSECITE_CODE_SHORT_PAPER_20260628.md`
- `reports/falsecite_code/FALSECITE_CODE_SOURCE_VERIFIER_GATE_20260623.md`
- `reports/falsecite_code/FALSECITE_CODE_MODEL_GATE_20260624.md`
- `reports/falsecite_code/FALSECITE_CODE_GENERATION_GATE_VERBOSE160_20260625.md`
- `reports/falsecite_code/FALSECITE_CODE_LOCKED_CLAIMS_20260623.jsonl`
- `scripts/run_falsecite_code_gate.py`
- `scripts/run_falsecite_code_model_gate.py`
- `scripts/run_falsecite_code_generation_gate.py`

## References

Krishna, A., Galinkin, E., Derczynski, L., & Martin, J. (2025). Importing phantoms: Measuring LLM package hallucination vulnerabilities. arXiv. https://arxiv.org/abs/2501.19012

Min, S., Krishna, K., Lyu, X., Lewis, M., Yih, W., Koh, P. W., Iyyer, M., Zettlemoyer, L., & Hajishirzi, H. (2023). FActScore: Fine-grained atomic evaluation of factual precision in long form text generation. Proceedings of EMNLP 2023. https://aclanthology.org/2023.emnlp-main.741/

Spracklen, J., Wijewickrama, R., Sakib, A. H. M. N., Maiti, A., Viswanath, B., & Jadliwala, M. (2024). We have a package for you! A comprehensive analysis of package hallucinations by code generating LLMs. arXiv. https://arxiv.org/abs/2406.10279

