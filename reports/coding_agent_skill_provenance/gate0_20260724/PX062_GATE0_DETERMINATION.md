# PX-062 Skill Provenance Gate 0 Determination

Status: **PASS - CONTROLLED INERT FIXTURE ONLY**

Controlled inert-fixture validation of a deterministic skill admission policy. It does not measure live coding-agent behavior, real registry compromise, cryptographic deployment security, DDIPE execution, or model hallucination prevalence.

## Full-gate result

| Metric | Result | Gate |
|---|---:|---:|
| Cases | 180 | - |
| Clean false rejects | 0/60 (0.0000) | <= 0.0500 |
| Attack escapes | 0/120 (0.0000) | <= 0.0000 |
| Decision trace completeness | 1.0000 | >= 1.0000 |

## Ablations

| Policy | Clean false-reject rate | Attack escape rate | Accuracy |
|---|---:|---:|---:|
| existence_only | 0.0000 | 0.6667 | 0.5556 |
| hash_only | 0.0000 | 0.3333 | 0.7778 |
| signature_only | 0.0000 | 0.3333 | 0.7778 |
| full | 0.0000 | 0.0000 | 1.0000 |

## Decision

Gate 0 validates the admission-policy implementation only. Proceed to a frozen public-registry Gate 1 and a separate live-model skill-name hallucination Gate 2.
