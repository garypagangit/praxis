# SEC-LoRD / DS-LoRD CTI Adapter Scaffold

Generated: 2026-05-09

## Decision

Status: **UNBLOCKED FOR SCAFFOLD WORK**. The CTI inputs are readable and now have normalized JSONL query files for LoRD/DS-LoRD prompt construction. This does not yet run model extraction; it removes the data-adapter blocker.

## Emitted Artifacts

- `cti_taa_queries`: `runs\sec-lord-cti-scaffold-20260509\cti_taa_queries.jsonl`
- `cti_mcq_queries`: `runs\sec-lord-cti-scaffold-20260509\cti_mcq_queries.jsonl`
- `annoctr_linking_queries`: `runs\sec-lord-cti-scaffold-20260509\annoctr_linking_queries.jsonl`
- `combined_queries`: `runs\sec-lord-cti-scaffold-20260509\combined_queries.jsonl`
- `domain_seed_bank`: `runs\sec-lord-cti-scaffold-20260509\domain_seed_bank.json`
- `summary`: `runs\sec-lord-cti-scaffold-20260509\summary.json`

## Input Summary

| Source | Rows available | Rows emitted | Notes |
|---|---:|---:|---|
| ctibench/cti-taa | 50 | 50 | schema readable |
| ctibench/cti-mcq | 2500 | 500 | GT distribution {'B': 812, 'D': 385, 'C': 928, 'A': 374, 'b': 1} |
| annoctr/linking | 44 | 44 | entity types {'CON': 3, 'GROUP': 4, 'LOC': 6, 'MALWARE': 1, 'ORG': 9, 'SECTOR': 1, 'TECHNIQUE': 20} |

## DS-LoRD Seed Bank

- Seed terms emitted: `100`
- Top seed terms: `Command Execution, APT41, Travelex, Network Segmentation, APT32, Privileged Account Management, Endpoint Denial of Service, APT29, Process Creation, Execution Prevention, Command, Execution, DDoS, Persistence, Lazarus Group`

## Next Gate

Build a tiny extraction harness that uses these files to compare vanilla prompts against domain-seeded prompts on CTI tasks. The first honest compute gate should use a small open model or verified Llama access, write every query/response to S3, and score CTI-MCQ exact match plus AnnoCTR entity-link accuracy before attempting full LoRD extraction.
