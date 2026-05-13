# Contrastive SSL on Provenance Graphs - Input Gate

Date: 2026-05-09

Branch: `experiment/contrastive-ssl-provenance-graphs`

Run artifacts:

- `scripts/run_contrastive_ssl_input_gate.py`
- `runs/contrastive-ssl-input-gate-20260509/report.md`
- `runs/contrastive-ssl-input-gate-20260509/contrastive_ssl_input_gate_summary.json`

## AWS Storage Status

| Dataset | S3 status | Decision |
|---|---|---|
| DARPA TC | Metadata/program repo only, `52.3 KiB` under `datasets/darpa-tc/raw/` | Blocked for provenance-graph SSL. |
| OpTC | Metadata/repo and ground-truth PDF only, `904.7 KiB` under `datasets/optc/raw/` | Blocked for provenance-graph SSL. |
| Unraveled host logs | Full local/S3 mirror available; host logs are part of the `4.5 GiB` Unraveled S3 mirror | Usable as a proxy event-sequence graph source. |

## Local Proxy Gate

The gate sampled local Unraveled host logs from:

`imports/unraveled/data/host-logs`

Summary:

- Files available locally: `59`
- Files sampled: `59`
- Rows sampled: `266362`
- Sampled bytes: `712334481`
- Files matching the simple expected schema: `36/59`

The host logs contain useful event text and labels such as `Activity`, `Stage`, `DefenderResponse`, and `Signature`. Some Windows/event logs contain multiline records that break naive CSV parsing, so any proxy constructor needs robust log-specific parsing before graph construction.

## Gate Decision

| Gate | Status | Notes |
|---|---|---|
| Unraveled host-log proxy | PASS | Enough data exists for a cheap temporal event/co-occurrence graph spike. |
| DARPA TC / OpTC provenance graph SSL | BLOCKED | Full typed process/file/socket provenance data is not mirrored yet. |
| New Praxis candidate | NOT YET | The novelty claim depends on true provenance graphs, not a proxy event-log graph. |

## Interpretation

The experiment is still scientifically attractive, but it should not consume GPU time until a real DARPA TC or OpTC subset is mirrored. The Unraveled proxy could be useful if we want a low-cost engineering spike for augmentation choices: node masking, edge dropping, temporal-window subgraph sampling, and label-scarce fine-tuning. It would not prove the venue-level provenance-graph claim.

## Recommended Next Step

Download or mirror one targeted DARPA TC E3/E5 or OpTC subset into AWS, then build a minimal graph parser that emits typed temporal edges. Until that subset exists, keep this experiment in `input-blocked / proxy-ready` status.
