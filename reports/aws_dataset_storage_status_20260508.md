# AWS Dataset Storage Status - 2026-05-08

Bucket: `s3://praxis-garypagan-272615233626-us-east-1/`
Region: `us-east-1`
Registry: `configs/dataset_registry.json`
S3 registry copy: `s3://praxis-garypagan-272615233626-us-east-1/registry/dataset_registry.json`

## Storage Layout

Each dataset has:

- `raw/`
- `processed/`
- `manifests/`
- `reports/`
- `checksums/`
- `_incoming/`
- `_work/`

Each model workspace has:

- `access-notes/`
- `adapters/`
- `eval-outputs/`
- `manifests/`
- `_incoming/`
- `_work/`

## Loaded Datasets

| Dataset | S3 prefix | Status | Notes | Experiment impact |
|---|---|---|---|---|
| Unraveled network flows | `datasets/unraveled/network-flows/` | Loaded | 173 objects, 3.5 GiB | Praxis v03, Praxis 05, TTA, Contrastive SSL |
| Unraveled host logs | `datasets/unraveled/host-logs/` | Loaded | Local source uploaded | Praxis 05, cross-telemetry extensions |
| Unraveled NIDS | `datasets/unraveled/nids/` | Loaded | Local source uploaded | Cross-telemetry extensions |
| Unraveled v02 cache | `datasets/unraveled/processed/v02/` | Loaded | Processed cache uploaded | Faster reproduction |
| Unraveled v03 cache | `datasets/unraveled/processed/v03/` | Loaded | Processed cache uploaded | Faster reproduction |
| CIC-IDS2018 | `datasets/cic-ids-2018/raw/` | Loaded | Local source uploaded | Praxis 04, TTA, Contrastive SSL |
| DAPT2020 raw | `datasets/dapt2020/raw/` | Loaded | Local source uploaded | APT transfer checks |
| DAPT2020 processed | `datasets/dapt2020/processed/` | Loaded | Local source uploaded | APT transfer checks |
| APTNotes | `datasets/aptnotes/raw/` | Loaded | Public GitHub clone uploaded | SEC-LoRD, AI Supply Chain, CTI-RCM |
| MITRE ATT&CK STIX | `datasets/mitre-attack/raw/` | Loaded | Public GitHub clone uploaded | SEC-LoRD, AI Supply Chain, CTI label grounding |
| AnnoCTR | `datasets/annoctr/raw/` | Loaded | Public GitHub clone uploaded | CTI extraction/linking, SEC-LoRD |
| CTIBench | `datasets/ctibench/raw/` | Loaded | Hugging Face parquet shards uploaded | SEC-LoRD, AI Supply Chain, CTI-RCM |
| CTI-RCM | `datasets/cti-rcm/raw/` | Loaded | CTIBench CTI-RCM shards split into dedicated prefix | CTI-RCM one-off idea |
| PoisonBench | `datasets/poisonbench/raw/` | Loaded | Hugging Face parquet uploaded | AI Supply Chain, poisoning/watermarking robustness |
| NVD CVE 2.0 | `datasets/nvd/raw/` | Partial | Public no-key API sample for 2026-05-01 to 2026-05-08 uploaded | AI Supply Chain, vulnerability feed idea |
| DARPA TC | `datasets/darpa-tc/raw/` | Metadata loaded | Public GitHub program repo uploaded; large engagement data may require targeted pull by engagement/performer | SEC-LoRD, Praxis 05, Contrastive SSL |
| OpTC | `datasets/optc/raw/` | Metadata loaded | Public GitHub repo uploaded; large data files are not fully mirrored locally | OpTC idea, TTA, Contrastive SSL |

## Gated Or Action Needed

| Item | Status | What to do | Experiment impact |
|---|---|---|---|
| NVD API key | Not required for small pulls, recommended for full/incremental sync | Request a key at `https://nvd.nist.gov/developers/request-an-api-key`, then store it as a secret before running large paginated pulls | AI Supply Chain, NVD feed idea |
| Llama 3.1 8B Instruct | Gated on Hugging Face/Meta terms | Log into Hugging Face, open `https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct`, accept the model terms, then run `hf auth login` locally/cloud | SEC-LoRD, AI Supply Chain, Watermarking |
| Llama 3.2 3B Instruct | Gated on Hugging Face/Meta terms | Log into Hugging Face, open `https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct`, accept the model terms, then run `hf auth login` locally/cloud | Smaller LLM runs, SEC-LoRD, AI Supply Chain, Watermarking |
| DARPA TC full engagement data | Metadata present; full dataset should be pulled deliberately by engagement | Start from the public DARPA TC repo and choose only needed performers/engagements to avoid uncontrolled storage growth | SEC-LoRD, Praxis 05 |
| OpTC full telemetry | Metadata present; full data should be pulled deliberately | Follow the OpTC repo instructions and mirror only selected partitions first | OpTC idea, cross-dataset telemetry |

## Cloud GPU Status

The EC2 quota request for `Running On-Demand G and VT instances` in `us-east-1` is applied at `8` vCPUs. This should allow a small G-family GPU instance such as a `g5.xlarge`, subject to capacity and final instance-family checks.

## Source References

- APTNotes: `https://github.com/kbandla/APTnotes`
- MITRE ATT&CK STIX: `https://github.com/mitre-attack/attack-stix-data`
- DARPA TC: `https://github.com/darpa-i2o/Transparent-Computing`
- OpTC: `https://github.com/FiveDirections/OpTC-data`
- AnnoCTR: `https://github.com/boschresearch/anno-ctr-lrec-coling-2024`
- CTIBench: `https://huggingface.co/datasets/AI4Sec/cti-bench`
- PoisonBench: `https://huggingface.co/datasets/TingchenFu/PoisonBench`
- NVD CVE API: `https://nvd.nist.gov/developers/vulnerabilities`
- Llama 3.1 8B Instruct: `https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct`
- Llama 3.2 3B Instruct: `https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct`
