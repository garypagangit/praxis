# DARPA E5 Cadets Avro Probe

Generated: 2026-05-09

## Decision

Status: **PROVENANCE PARSER GATE UNBLOCKED FOR E5 CADETS FOLDER**.

The mirrored Cadets chunks are valid gzip-compressed Avro object containers using `com.bbn.tc.schema.avro.cdm20.TCCDMDatum`. After stable internet returned, the Google Drive mirror resumed successfully and synced the current E5 Cadets folder to S3.

## Cloud Storage

- EC2 local path: `/mnt/praxis/datasets/darpa-tc/e5/cadets/`
- S3 mirror: `s3://praxis-garypagan-272615233626-us-east-1/datasets/darpa-tc/raw/engagement-5/cadets/`
- S3 mirror count after stable-internet resume: `51` objects
- S3 mirror size after stable-internet resume: `13.0 GiB`
- Probe summary: `s3://praxis-garypagan-272615233626-us-east-1/datasets/darpa-tc/raw/engagement-5/cadets_probe_summary.json`

## Sample Probe

First sampled file:

`/mnt/praxis/datasets/darpa-tc/e5/cadets/ta1-cadets-1-e5-official-2.bin.1.gz`

Sample size: `5,000` records.

| Record type | Count |
|---|---:|
| `RECORD_EVENT` | 4,828 |
| `RECORD_SRC_SINK_OBJECT` | 47 |
| `RECORD_SUBJECT` | 38 |
| `RECORD_FILE_OBJECT` | 37 |
| `RECORD_NET_FLOW_OBJECT` | 25 |
| `RECORD_IPC_OBJECT` | 25 |

Top datum/event types:

| Datum type | Count |
|---|---:|
| `EVENT_READ` | 1,446 |
| `EVENT_CLOSE` | 662 |
| `EVENT_OPEN` | 596 |
| `EVENT_WRITE` | 467 |
| `EVENT_MMAP` | 426 |
| `EVENT_MPROTECT` | 225 |
| `EVENT_LSEEK` | 207 |
| `EVENT_FCNTL` | 145 |
| `EVENT_FLOWS_TO` | 128 |
| `EVENT_SENDTO` | 115 |
| `EVENT_RECVFROM` | 113 |

## Impacted Experiments

- **Contrastive SSL on Provenance Graphs**: moves from input-blocked to parser-scaffold-ready on the mirrored E5 Cadets folder.
- **Continuous-Time TGN for APT Provenance**: moves from input-blocked to timestamped-event scaffold-ready; sampled events include `timestampNanos`, subjects, predicate objects, and event types.
- **Stage Routing on Provenance Graphs / MAGIC-style work**: still needs labels and complete engagement context, but raw CDM parsing is now viable.

## Remaining Blockers

1. Confirm whether the mirrored E5 Cadets folder is sufficient for the first SSL/TGN pilot or whether another host stream is needed.
2. Extend the CDM-to-edge-table converter beyond the first smoke sample to emit at least:
   - `timestamp_nanos`
   - `record_type`
   - `event_type`
   - `subject_uuid`
   - `object_uuid`
   - `object2_uuid`
   - `object_path`
   - `host_id`
   - `sequence`
3. Add a label/window manifest before any supervised detector claim.

## Recommendation

Proceed with graph representation engineering against the E5 Cadets S3 mirror. Keep the first paper claim scoped to the mirrored host stream unless additional DARPA TC/OpTC subsets are added.

## Edge Conversion Smoke

Converter:

`scripts/convert_darpa_cadets_avro_to_edges.py`

Cloud sample output:

`s3://praxis-garypagan-272615233626-us-east-1/datasets/darpa-tc/processed/e5-cadets-edge-sample-20260509/`

One Cadets chunk was converted with a `100,000` record cap:

| Output | Count |
|---|---:|
| Event edges | 98,862 |
| Entity rows | 1,138 |
| Source files | 1 |

Record types in the converted sample:

| Record type | Count |
|---|---:|
| `RECORD_EVENT` | 98,862 |
| `RECORD_SRC_SINK_OBJECT` | 333 |
| `RECORD_FILE_OBJECT` | 282 |
| `RECORD_SUBJECT` | 229 |
| `RECORD_IPC_OBJECT` | 188 |
| `RECORD_NET_FLOW_OBJECT` | 106 |

This clears the immediate parser blocker for representation-learning scaffolds. The next graph step is augmentation sanity checks on `edges.jsonl` rather than more raw-format investigation.
