# Experiment Portfolio Storage Status - 2026-05-08

Bucket: `s3://praxis-garypagan-272615233626-us-east-1/`

Experiment registry:

- Local: `configs/experiment_portfolio_registry.json`
- S3: `s3://praxis-garypagan-272615233626-us-east-1/registry/experiment_portfolio_registry.json`

Dataset registry:

- Local: `configs/dataset_registry.json`
- S3: `s3://praxis-garypagan-272615233626-us-east-1/registry/dataset_registry.json`

## Note On Count

The pasted tracker says the portfolio has 17 ideas, but the pasted table contains 19 rows. I preserved all 19 rows in the registry:

- 1 tested/results-in-hand
- 2 active
- 3 newly added
- 11 untouched/still strong
- 2 shelved

## Experiment Workspace Layout

Every experiment now has an S3 workspace:

```text
experiments/<experiment-id>/configs/
experiments/<experiment-id>/inputs/
experiments/<experiment-id>/outputs/
experiments/<experiment-id>/reports/
experiments/<experiment-id>/checkpoints/
experiments/<experiment-id>/logs/
experiments/<experiment-id>/manifests/
experiments/<experiment-id>/_work/
```

## Experiment To Dataset Status

| Experiment | Status | Primary storage inputs | Blockers |
|---|---|---|---|
| Praxis 04 - Stage-Conditional Routing | Results in hand | `datasets/cic-ids-2018/raw/` | None |
| SEC-LoRD / DS-LoRD | Active | APTNotes, MITRE ATT&CK, CTIBench, NVD | NVD key optional for large historical sync |
| AI Supply Chain - Training Provenance | Active | PoisonBench, NVD, APTNotes, MITRE ATT&CK, CTIBench | NVD key optional for large historical sync |
| Test-Time Adaptation for Streaming APT | Newly added | Unraveled, CIC-IDS2018, DAPT2020, OpTC metadata | OpTC subset selection |
| Contrastive SSL on Provenance Graphs | Newly added | DARPA TC metadata, OpTC metadata, Unraveled host logs | DARPA TC / OpTC subset selection |
| APT Detector Watermarking | Newly added | Unraveled, CIC-IDS2018, PoisonBench | None for Llama access |
| SAE-for-APT | Untouched | DARPA TC metadata, Unraveled host logs | DARPA TC performer/subset selection |
| GNN Attribution - TTP Graph Embeddings | Untouched | MITRE ATT&CK, APTNotes, AnnoCTR | None |
| Stage-Conditioned Class Imbalance | Untouched | Unraveled, CIC-IDS2018, DARPA TC metadata | DARPA TC for graph variant |
| Few-Shot Attribution - Emerging APT Groups | Untouched | MITRE ATT&CK, APTNotes, AnnoCTR, CTIBench | None |
| Membership Inference Against APT Detectors | Untouched | DARPA TC metadata, APTNotes, Unraveled | DARPA TC performer/subset selection |
| Stage Routing on Provenance Graphs | Untouched | DARPA TC metadata | DARPA TC performer/subset selection |
| Cross-Detector Adversarial Robustness | Untouched | DARPA TC metadata, Unraveled, CIC-IDS2018, DAPT2020 | DARPA TC performer/subset selection |
| Concept Drift on Provenance Graph Detectors | Untouched | DARPA TC metadata, OpTC metadata | DARPA TC / OpTC subset selection |
| LLM Threat Intelligence Fusion | Untouched | APTNotes, MITRE ATT&CK, NVD, AnnoCTR, CTIBench | NVD key optional for large historical sync |
| Continuous-Time TGN for APT Provenance | Untouched | DARPA TC metadata, OpTC metadata | DARPA TC / OpTC subset selection |
| Causal GNN for Evasion-Resistant APT Detection | Untouched | DARPA TC metadata, OpTC metadata | DARPA TC / OpTC subset selection |
| Reverse TTP Extraction from Evasion Behaviour | Shelved | MITRE ATT&CK, APTNotes | Custom honeypot simulation |
| XAI for Analyst-in-the-Loop Attribution | Shelved | MITRE ATT&CK, APTNotes, AnnoCTR, CTIBench | SOC analyst collaboration |

## Access Actions

### Hugging Face / Meta Llama

Needed for:

- SEC-LoRD / DS-LoRD
- AI Supply Chain
- LLM Threat Intelligence Fusion
- APT Detector Watermarking if using the LLM watermarking variant

Status: resolved locally for Hugging Face user `garypagangit`.

Verified access:

- `meta-llama/Llama-3.1-8B-Instruct`
- `meta-llama/Llama-3.2-3B-Instruct`

Cloud jobs should use a Hugging Face token with public gated repository read access.

### NVD API Key

Needed for:

- AI Supply Chain
- LLM Threat Intelligence Fusion
- NVD feed idea

Action:

1. Request key: `https://nvd.nist.gov/developers/request-an-api-key`
2. Store it as a secret before full sync.

Small no-key pulls work. Two samples are already stored at `datasets/nvd/raw/`, including 630 CVEs for 2026-05-07 through 2026-05-08.

### DARPA TC Full Data

Needed for:

- SAE-for-APT
- Stage Routing on Provenance Graphs
- Contrastive SSL on Provenance Graphs
- Membership Inference
- Cross-Detector Adversarial Robustness
- Concept Drift
- Continuous-Time TGN
- Causal GNN

Status: public Google Drive access verified. `gdown` is installed locally, and `scripts/download_large_security_dataset.ps1` can pull E3/E5.

Action:

Choose the specific engagement/performer subset first. The public metadata repo is already mirrored, but full provenance data should be pulled deliberately because it can be large.

### OpTC Full Data

Needed for:

- Test-Time Adaptation
- Contrastive SSL
- Concept Drift
- Continuous-Time TGN
- Causal GNN

Status: public Google Drive access verified. `gdown` is installed locally, and `scripts/download_large_security_dataset.ps1` can pull the public release.

Action:

Choose an OpTC partition and mirror it deliberately. The public metadata repo is already mirrored.

## Cloud GPU

EC2 `Running On-Demand G and VT instances` quota is now `8` vCPUs in `us-east-1`, enough to proceed with a small G-family GPU instance subject to capacity.
