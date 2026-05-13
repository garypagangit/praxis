# Dataset Access Blocker Resolution - 2026-05-08

Bucket: `s3://praxis-garypagan-272615233626-us-east-1/`

## Resolved

| Dataset / dependency | Status | What was done | Experiments unblocked |
|---|---|---|---|
| Hugging Face / Meta Llama 3.1 8B | Resolved | Verified `garypagangit` can dry-run download `meta-llama/Llama-3.1-8B-Instruct` config | SEC-LoRD, AI Supply Chain, LLM Threat Intelligence Fusion, Watermarking LLM variant |
| Hugging Face / Meta Llama 3.2 3B | Resolved | Verified `garypagangit` can dry-run download `meta-llama/Llama-3.2-3B-Instruct` config | SEC-LoRD, AI Supply Chain, LLM Threat Intelligence Fusion, smaller GPU pilots |
| NVD CVE API small pulls | Resolved | Added `scripts/sync_nvd_cves.ps1`; fetched and synced 630 CVEs for 2026-05-07 through 2026-05-08 without API key | AI Supply Chain, LLM Threat Intelligence Fusion, NVD feed idea |
| DARPA TC public access | Resolved as public, not yet mirrored in full | Verified public Google Drive folder is reachable; installed `gdown`; added guarded script for full E3/E5 folder download | SAE-for-APT, Stage Routing on Provenance Graphs, Contrastive SSL, MIA, Cross-Detector Robustness, Concept Drift, TGN, Causal GNN |
| OpTC public access | Resolved as public, not yet mirrored in full | Verified public Google Drive folder is reachable; installed `gdown`; added guarded script for full OpTC folder download | TTA, Contrastive SSL, Concept Drift, TGN, Causal GNN |

## Scripts Added

### NVD

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\sync_nvd_cves.ps1 `
  -StartDate 2026-05-07 `
  -EndDate 2026-05-08 `
  -SyncToS3
```

Optional API key:

```powershell
$env:NVD_API_KEY = "YOUR_KEY"
powershell -ExecutionPolicy Bypass -File .\scripts\sync_nvd_cves.ps1 `
  -StartDate 2025-01-01 `
  -EndDate 2025-12-31 `
  -SyncToS3
```

S3 destination:

```text
s3://praxis-garypagan-272615233626-us-east-1/datasets/nvd/raw/
```

### DARPA TC / OpTC Large Google Drive Releases

These are intentionally guarded because DARPA TC and OpTC can be very large.

DARPA TC Engagement 5:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\download_large_security_dataset.ps1 `
  -Dataset darpa-tc-e5 `
  -SyncToS3
```

DARPA TC Engagement 3:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\download_large_security_dataset.ps1 `
  -Dataset darpa-tc-e3 `
  -SyncToS3
```

OpTC:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\download_large_security_dataset.ps1 `
  -Dataset optc `
  -SyncToS3
```

## Still Needs A Choice, Not Permission

| Dataset | Decision needed | Why |
|---|---|---|
| DARPA TC E5 | Choose performer/subset first: `cadets`, `theia`, `trace`, etc. | Full mirror can be large; Praxis 05/MAGIC likely needs a targeted performer such as Cadets before broad mirroring |
| DARPA TC E3 | Choose whether older E3 data is necessary now | E5 is more natural for current MAGIC/Praxis 05 framing |
| OpTC | Choose `ecar`, `ecar-bro`, or `bro`, and benign/evaluation/short split | Full release is roughly terabyte-scale compressed JSON |

## Still Needs External Action

| Item | Action | Impact |
|---|---|---|
| NVD API key | Request at `https://nvd.nist.gov/developers/request-an-api-key` | Makes large historical NVD syncs faster and less fragile |
| SOC analyst collaboration | Needs partner/evaluation plan | XAI for Analyst-in-the-Loop Attribution |
| Honeypot simulation environment | Needs custom simulator design | Reverse TTP Extraction from Evasion Behaviour |

## Recommended Next Dataset Action

Do not mirror all DARPA TC / OpTC data locally through OneDrive. For the next graph/provenance experiment, start with one targeted cloud download:

1. DARPA TC E5 Cadets for MAGIC/Praxis 05-style provenance graph work.
2. OpTC `ecar` evaluation subset for streaming/TTA and concept drift.

Once the EC2 GPU box is running, run large downloads on the EC2 data volume and sync from there to S3, rather than pulling terabyte-scale data through this laptop.
