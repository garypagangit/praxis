# PX-062 Public-Corpus Provenance Gate 1

Status: **FAIL**

Offline admission-policy evaluation over the authors' 1,070 released poisoned SKILL.md files and 44 clean OpenAI skill snapshots. Files are hashed and parsed but never executed. Registry signatures are modeled as valid/invalid evidence states; this is not a production cryptographic implementation or a live-agent execution study.

## Corpus

- PoisonedSkills release: 1070 SKILL.md files
- Clean OpenAI snapshot: 44 SKILL.md files
- Poisoned archive SHA-256: `241ab288483ed77af2357f967c4018a59f5a407d5432b14ab6fc61a7cb33ad63`
- OpenAI skills commit: `49f948faa9258a0c61caceaf225e179651397431`

## Primary provenance-only policy

| Condition | N | Allowed | Escape/allow rate |
|---|---:|---:|---:|
| authentic_poison_signed | 1070 | 1070 | 1.0000 |
| clean_exact | 44 | 44 | 1.0000 |
| clean_tampered | 44 | 0 | 0.0000 |
| nonexistent | 1070 | 0 | 0.0000 |
| poison_tampered | 1070 | 0 | 0.0000 |

- Clean false-reject rate: `0.0000`

## Policy comparison

| Policy | Authentic signed poison allowed | Tampered poison allowed | Nonexistent allowed | Clean false rejects |
|---|---:|---:|---:|---:|
| no_gate | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| provenance_full | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| provenance_plus_publisher_allowlist | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| semantic_oracle | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## Determination

FAIL for provenance-only defense against authentic poisoned skills: all 1070 correctly identified, hash-matching, signed poisoned skills remain admissible. PASS for tamper and nonexistent-name rejection, with no false rejects on the clean snapshot.

Hash pinning, existence verification, and registry signatures establish identity and integrity; they do not establish that authenticated content is benign. PX-062 therefore rejects the original hypothesis that provenance alone is a sufficient defense against the paper's attack class. It remains useful as one layer against name hallucination, substitution, rollback, and post-publication tampering.
