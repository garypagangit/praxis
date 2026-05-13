# Continuous-Time TGN for APT Provenance - Input Gate

Date: 2026-05-09

Branch: `experiment/continuous-time-tgn-apt-provenance`

## Data Check

The full TGN idea needs timestamped provenance edges: process, file, socket, user, and host interactions over time. Current AWS status is the same blocker observed for graph SSL:

| Dataset | S3 status | TGN readiness |
|---|---|---|
| DARPA TC | Metadata/program repo only, `52.3 KiB` under `datasets/darpa-tc/raw/` | Blocked |
| OpTC | Metadata/repo plus ground-truth PDF only, `904.7 KiB` under `datasets/optc/raw/` | Blocked |
| Unraveled network flows | Local and S3 mirror available | Temporal-flow proxy only |

Unraveled network-flow CSVs do contain continuous timestamps and endpoint identifiers, including:

- `src_ip`, `src_port`, `dst_ip`, `dst_port`, `protocol`
- `bidirectional_first_seen_ms`, `bidirectional_last_seen_ms`, `bidirectional_duration_ms`
- directional timing fields such as `src2dst_first_seen_ms` and `dst2src_first_seen_ms`
- labels: `Activity`, `Stage`, `DefenderResponse`, `Signature`

## Gate Decision

| Gate | Status | Notes |
|---|---|---|
| Temporal-flow proxy | PASS | Unraveled can support a temporal interaction graph over IP/port endpoints. |
| True provenance TGN | BLOCKED | DARPA/OpTC typed provenance edges are not mirrored yet. |
| New Praxis candidate | NOT YET | The contribution is only novel if applied to real provenance graph edges, not merely NetFlow-style edges. |

## Interpretation

This experiment should not start GPU work yet. A flow-level TGN proxy would be a useful engineering rehearsal for batching, temporal memory, and negative sampling, but it would not validate the stated paper claim of replacing MAGIC/Kairos-style static provenance snapshots with continuous-time provenance memory.

## Recommended Next Step

Use AWS to mirror one targeted DARPA TC or OpTC subset before any TGN training. Once a subset exists, the first real gate should verify:

1. typed temporal edges are present,
2. timestamps are monotonic or repairable,
3. process/file/socket node IDs are recoverable,
4. benign and attack windows can be split without future leakage.

Until then, keep this in `input-blocked / proxy-ready` status.
