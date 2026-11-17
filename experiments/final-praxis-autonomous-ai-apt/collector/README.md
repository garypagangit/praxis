# Restricted telemetry collector

This is the project's initial read-only export tool. It collects explicitly named CloudWatch Logs groups or existing CloudWatch-style JSONL exports from any combination of operator, target, network, service, infrastructure and cloud sources. It never discovers or modifies AWS resources, runs commands from logs, assigns labels, or invokes a classifier.

## Security and scope

**Every output is restricted raw evidence.** Messages can contain terminal recordings, command arguments, credentials, identities and other sensitive data. Select an existing private parent directory outside every Git worktree, set and verify its OS access controls before running, and do not publish its contents. The tool rejects output inside Git worktrees and never overwrites an existing output directory. Directory permissions are subject to the operating system and inherited ACLs; on Windows, `mode=0o700` does not itself establish a private ACL.

The source configuration is also sensitive: keep it in the restricted directory, not in Git. CloudWatch requires read-only `logs:FilterLogEvents` access to the selected groups and may incur AWS charges. Groups must already exist and contain the required streams; VPC Flow Logs or CloudTrail are available here only if they have been sent to the selected CloudWatch groups. Local inputs must already be JSONL in the event format below. This version does not read S3, EVTX or native auditd archives directly.

## Configure and run

Install the collector's dependency in an appropriate existing Python environment:

```powershell
python -m pip install -r requirements.txt
```

In a restricted file such as `C:\restricted\collector-sources.json`, specify only the sources to include. This example uses placeholders; actual group names, streams and local files must be verified for the lab:

```json
[
  {"id":"operator", "category":"operator", "kind":"cloudwatch", "log_group":"REPLACE_WITH_OPERATOR_LOG_GROUP"},
  {"id":"target", "category":"target", "kind":"cloudwatch", "log_group":"REPLACE_WITH_TARGET_LOG_GROUP"},
  {"id":"network", "category":"network", "kind":"local", "path":"C:\\restricted\\network-export.jsonl"}
]
```

Categories are `operator`, `target`, `network`, `service`, `infrastructure` and `cloud`. IDs are unique, case-insensitively, and may contain only letters, digits, underscores and hyphens. To limit a CloudWatch group to specific streams, add `"log_stream_names": ["STREAM_NAME"]`. Empty sources fail the export unless `"allow_empty": true` is explicitly set for that source.

Each local input line must be a JSON object with the CloudWatch `eventId`, `timestamp`, `ingestionTime`, `logStreamName` and `message` fields. Timestamps are integer milliseconds since the Unix epoch. Every event in a local input must already lie within the requested interval; out-of-window events are rejected, not silently discarded. Additional event fields are retained.

From this directory:

```powershell
python collector.py collect --sources C:\restricted\collector-sources.json --output C:\restricted\run-001 --start 2026-10-19T00:00:00Z --end 2026-10-20T00:00:00Z --profile praxis-build --region us-east-1
```

The start is inclusive and the end exclusive, using event time, at millisecond precision. CloudWatch calls use the corresponding inclusive end of `end - 1 ms` and follow all paginator pages. Keep the printed manifest SHA-256 in a separate trusted register outside the package, then verify:

```powershell
python collector.py verify --package C:\restricted\run-001 --anchor-sha256 REPLACE_WITH_PRINTED_SHA256
```

The package contains `raw\<source-id>.jsonl` and `MANIFEST.json` with source origins, counts, window and file hashes. Raw messages are retained in canonical JSON, not sanitized. If collection fails, no manifest is produced; the newly created directory can contain partial sensitive data and must be treated as incomplete. A retry requires a new output directory.

## Verification boundaries

The verifier checks the externally anchored manifest hash, exact package file set, per-source hashes and counts, event shape, unique IDs per source, and half-open event-time bounds. It cannot prove the source was complete, that AWS had ingested every event at export time, or that labels and provenance are correct. It does **not** implement the paper's tagged/raw fidelity, sanitized-copy, session reconstruction, CloudTrail continuity, journal-chain, expert-review or other Appendix E checks.

This collector also does not generate the paper's 30-second feature table or reproduce its classifiers. The separate [legacy engineering harness](../pipeline/README.md) uses a different trial-level synthetic schema and cannot accept these raw events as paper-equivalent features. A qualified parser, privacy review and independent verification are required before real data is used for model development.
