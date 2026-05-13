# SEC-LoRD / DS-LoRD EDA and Access Gate

Updated: 2026-05-09

## Branch

`experiment/sec-lord-ds-lord`

## Portfolio Claim

Domain-seeded cold-start triggering should extend LoRD-style model extraction
to security-specialized LLMs. The planned comparison is vanilla LoRD versus
domain-seeded LoRD on CTI tasks such as AnnoCTR TTP extraction and CTIBench.

## Staged Inputs

S3 bucket: `s3://praxis-garypagan-272615233626-us-east-1/`

| Input | S3 prefix | Status | Size / count |
|---|---|---|---:|
| APTNotes | `datasets/aptnotes/` | Loaded | 339 objects, 1.02 GB |
| MITRE ATT&CK | `datasets/mitre-attack/` | Loaded | 154 objects, 1.45 GB |
| CTIBench | `datasets/ctibench/` | Loaded | 14 objects, 2.70 MB |
| AnnoCTR | `datasets/annoctr/` | Loaded | 6,653 objects, 635 MB |
| NVD | `datasets/nvd/` | Loaded | 18 objects, 1.82 GB |

CTIBench parquet shards are present for:

- `cti-ate`
- `cti-mcq`
- `cti-rcm`
- `cti-rcm-2021`
- `cti-taa`
- `cti-vsp`

AnnoCTR has the most directly relevant TTP-linking material, including
`linking_mitre_only` JSON files with contrastive and negative variants.

## Access Status

Previous dataset-blocker report says Meta Llama access was verified for
`garypagangit`:

- `meta-llama/Llama-3.1-8B-Instruct`
- `meta-llama/Llama-3.2-3B-Instruct`

Current attempt to rerun the local HF check timed out under sporadic
connectivity, so the historical verified status stands, but this should be
rechecked from the cloud runtime before any GPU job starts.

## Blocker

This repository currently has registry entries and a test-plan summary, but no
runnable LoRD / DS-LoRD implementation scaffold was found.

Concrete missing pieces:

- Victim model wrapper for Foundation-Sec-8B or a chosen substitute victim.
- Query generation protocol for vanilla LoRD.
- Domain-seeded prefix generator using ATT&CK technique names and APTNotes
  vocabulary.
- Surrogate training loop and MLE baseline.
- Evaluation adapter for AnnoCTR / CTIBench task metrics.
- Cloud GPU job wrapper with HF token/terms verification.

## Decision

Do not run SEC-LoRD compute yet.

Flag as:

- `blocked_missing_implementation`
- `data_ready`
- `model_access_probably_ready_but_recheck_needed`
- `not_yet_new_praxis_result`

Recommended unblock path:

1. Build a tiny non-LLM scaffold first: load `cti-taa` or AnnoCTR examples and
   produce domain seed vocabularies from ATT&CK names.
2. Recheck HF access from the target cloud runtime.
3. Implement a minimal black-box extraction smoke using a small open model
   before attempting Foundation-Sec-8B or Llama-scale runs.

Until those exist, continuing to the next experiment is the better use of time.
