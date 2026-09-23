# New data qualification: ProvICS and Windows-APT 2025

**Checked September 23, 2026. This is an acquisition/measurement qualification, not a completed external model evaluation.**

## Acquisition status

The primary candidate is [ProvICS](https://huggingface.co/datasets/trucyberlab/multimodal-ICS-provenance), linked to the authors' [July 2026 preprint](https://arxiv.org/abs/2607.05989). The intended small subset contains the README, two physical-state CSV files, and four campaign annotation CSV files. No large provenance graph or PCAP was requested.

The local Python and curl requests to Hugging Face timed out, including the IPv4 route and all four currently resolved service addresses. The public dataset card remained visible through the research browser, but source-card access is not a signal-file download. [Acquisition receipts](results/provics_acquisition.json) and [qualification output](results/provics_qualification.json) are authoritative for the completed byte acquisition. The downloader records hashes only for files actually present.

The alternative [Windows-APT 2025 version 4](https://data.mendeley.com/datasets/b8fmtzvpy8/4) has a [peer-reviewed 2026 Data in Brief paper](https://doi.org/10.1016/j.dib.2026.112569) and a CC BY 4.0 landing-page license. Its ordinary local download/API requests returned HTTP 403 with an interactive Cloudflare challenge. That access attempt was stopped; no challenge was bypassed. No Windows-APT event rows were acquired in this task. Its paper's observable stage limitations still require checking against actual release bytes, and scenario names cannot substitute for completed exfiltration evidence.

## What the visible ProvICS annotations establish

The source card states CC BY-NC 4.0 and describes four campaign scripts within one testbed attack recording. Raw files remain outside Git. Physical-only measurements would not establish authentication acquisition cost, log arrival times, or enterprise exfiltration outcomes.

The public annotation preview includes three explicit exceptions to successful stage execution:

| Campaign / phase | Observed qualification issue | Required treatment |
|---|---|---|
| C2 / historian_tamper | Token capture failed and the action was aborted. | Preserve attempted/aborted status; do not score as completed impact. |
| C4 / lateral_influxdb | Credential acquisition is marked `token=FAILED`. | A movement-stage name does not certify successful movement. |
| C4 / historian_poison | The action is explicitly marked `SKIPPED`. | Exclude from completed-action positives; do not relabel as benign automatically. |

The C2 credential-collection annotation lasts approximately 0.010 seconds; the card states 1 Hz physical sampling. Compute actual interval coverage before fitting. A nearby anomalous window cannot establish that a skipped action occurred.

These are preview observations, not downloaded rows or reproduced results. The 32 labeled phases are not 32 verified successful attacks. No classification or exfiltration count was measured here.

## Reproducible qualification

```powershell
& 'C:/w/tabular_batch_env_20260921/Scripts/python.exe' `
  'experiments/praxis_next/data_qualification/acquire_provics.py' `
  --data-root 'C:/w/apt_benchmark_data_20260920/praxis_next/newdata/provics' `
  --report-dir 'experiments/praxis_next/data_qualification/results'
```

The acquisition is bounded to seven files, three parallel connections, and 100 MB per file. The script stores source URLs and byte hashes, checks clocks and numeric columns, calculates physical rows falling within annotation intervals, and screens explicit skipped/failed language without certifying success. It never enables model fitting automatically. A successful download still requires outcome review, leakage inspection, and a frozen execution-level split.

## Decision

**New-data confirmation is not ready.** Continue the separately identified development experiments on already qualified data and label them as development. A fresh-data validation becomes eligible only after actual signals are acquired and their clocks, target observability, annotations, and independent execution units pass qualification. A cloud GPU cannot resolve unavailable evidence or increase the number of independent campaigns.
