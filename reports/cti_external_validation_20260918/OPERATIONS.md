# CTI external validation: operational closeout

**One inference attempt completed, the host was verified STOPPED, and all output
files were recovered and verified locally.** No additional inference or cloud
restart was needed. Scientific accuracy and the frozen decision gates are reported
separately. The machine-readable operational record is [AWS_RUN.json](AWS_RUN.json).

## Connection and bounded execution

The existing AWS IAM Identity Center session was renewed and verified at
**2026-09-18 20:42:46.252581 UTC**. The designated existing `g5.xlarge` was stopped
before launch. Temporary credentials were managed by AWS; no access keys or tokens
were copied into the runtime bundle or these public records. Setup and future
session-renewal instructions remain in [AWS_CONNECTION.md](AWS_CONNECTION.md).

The committed protocol and runtime freeze were verified byte-for-byte before
launch at Git commit `e00c27390cc6e64df3b8241fe1f9f9f450b28615`.
One host and one SSM worker command were used. The prospective CTI envelope was
60 minutes, an absolute command deadline at minute 52, an external stop watchdog
at minute 56, and a $10 combined reserve. The attempt did not create another host,
volume, or IAM role. The run-specific watchdog was verified before start.

| Event | September 18, 2026, UTC |
|---|---|
| Controller start-request timestamp | 20:58:27.558876 |
| Normal stop requested after the result marker was observed | 21:29:21.515265 |
| STOPPED verified | **21:33:35.907775** |
| Finalize receipt recorded | 21:33:36.239709 |

Elapsed time from start request through the STOPPED observation was
**2,108.348899 seconds (35.14 minutes)**, within the one-hour ceiling. Shutdown
used the normal stop path; no force stop occurred. The controller retained the
watchdog while the instance was stopping and deleted only its own verified
schedule after observing STOPPED. The controller's `gate_failed` flag remained
false. See [the sanitized finalize receipt](AWS_FINALIZE_SANITIZED.json).

## Cost estimate

At the recorded **$1.006/hour** rate, counting the entire interval through the
STOPPED observation gives a conservative compute estimate of
**$0.589166, approximately $0.59**. This includes boot and stopping time and is
not an AWS invoice. The rate was verified on September 16 with a September 1
effective date for Linux Shared `g5.xlarge` in `us-east-1`.

Adding the **$5 incidental allowance** gives **$5.589166** against the $10 reserve.
The allowance is a budget provision, **not recorded spending**. These figures do
not represent a measured total AWS bill or independently reconciled storage,
request, transfer, or tax charges.

## Original collection failure and local recovery

The final result archive and its SHA-256 marker were downloaded successfully.
The original Windows collector then raised `FileExistsError`: the Linux archive
contained two distinct files named `outputs/RUNTIME.json` (environment metadata)
and `outputs/runtime.json` (worker execution receipt). Those names collide on a
case-insensitive Windows filesystem.

The original launch record remains `HOLD_INCOMPLETE`, with
`overall_operational_pass: false` and `HOLD_COLLECTION_FAILED`. Its original
`supervisor_success: false` field reflects the unsuccessful collection check;
the later recovered supervisor exit record contains `0`. The original record was
not rewritten. [AWS_LAUNCH_ATTEMPT_SANITIZED.json](AWS_LAUNCH_ATTEMPT_SANITIZED.json)
preserves that failure and binds its private source by SHA-256.

The separate [local recovery helper](recover_windows_collection.py) extracted to
a fresh directory. It applied exactly one mapping:

```text
outputs/RUNTIME.json -> outputs/environment_runtime.json
```

`outputs/runtime.json` retained its original name and contents. The helper rejected
traversal, links, special files, duplicate members, unsafe Windows names, and
case-insensitive collisions after mapping. It verified the archive against the
published marker and compared every extracted file's bytes with its original
archive member. The archive, prior partial extraction, frozen files, and original
launch record were preserved.

The archive contains 12 members: one directory and **11 regular files**, all
verified. Its 507,499 bytes have SHA-256:

```text
7cf1cfb38383eaf9febadd1efcb37517c34996b640239abf581cf458714b96b4
```

[COLLECTION_RECOVERY.json](COLLECTION_RECOVERY.json) records every original path,
the explicit mapping, file sizes, original-member and extracted-file hashes, and
the original failure identity. Recovery was entirely local and performed no AWS
action or model inference.

## Recovered execution inventory

The recovered supervisor exited `0`; the worker receipt reports `COMPLETE`.
Output hashes match that receipt. The inventory contains:

- **4,988 fresh predictions:** 1,247 unique question records in each of the two
  conditions for each of the two generators.
- **32 qualification records:** eight questions in each condition for each model.

Those checks establish transport integrity and inventory completeness. They do
not establish accuracy, benefit, or a passing scientific result.

## Public receipt scope

The sanitized launch and finalize receipts were created with explicit field
allowlists. They omit account/principal identifiers, instance ID, bucket/object
locations, role ARN, SSM command ID, private paths, remote logs, and credential
values. Their original private receipt hashes remain recorded for traceability.
The original failure and subsequent recovery are separate audit events.

## Original archives and publication review

[execution_archives/ARCHIVE_MANIFEST.json](execution_archives/ARCHIVE_MANIFEST.json)
binds byte-identical copies of the original `results.tar.gz` and
`CTI_RUNTIME.tar.gz`, together with their original SHA-256 marker files. The
runtime bundle SHA-256 is
`ad87167c79a6c6c2f6ce95944376c58f4ac4f0266aa0124419b3a705a78e84c1`.
The Linux filename collision remains inside the original results archive only;
the public `execution_outputs` directory uses the documented safe rename. Do not
overwrite or repack the original archive to change its filenames.

[PUBLIC_ARTIFACT_REVIEW.json](PUBLIC_ARTIFACT_REVIEW.json) records the publication
check: all 11 execution outputs and all 21 regular members across both archives
were scanned, with no credential values found. The supervisor/environment logs
were also inspected directly. The check used local files and in-memory comparison
with available credential values; it fetched no secrets and saved no credentials.
