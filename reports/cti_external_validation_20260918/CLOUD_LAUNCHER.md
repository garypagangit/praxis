# CTI bounded cloud launcher

## Preparation status

These helpers prepare one attempt on the existing designated GPU host. They do
not provision instances, volumes, IAM roles, or model endpoints. Preparing the
implementation is separate from a frozen-bundle readiness check and from launch.
The `prepare` action makes **zero AWS requests**. The explicit `launch` action
starts the authorized attempt after its read-only and immutable-input gates pass.

Account, instance, bucket, role identifiers, profile, operational receipts,
generated SSM script, and downloaded results stay beside the private settings at
`C:/w/cti_external_private_20260918/settings.json`. No credential values belong in
that settings file, the manifest, the bundle, or SSM text.

## Reviewed controller provenance

`trusted_cloud_controller.py` is a byte-for-byte copy of
`final_praxis/010_d0_execution_20260915/code/cloud_d0.py` from the reviewed D0
worktree. Its SHA-256 is:

```text
b1739c6fa9b8cac8bf8740f4fe2b2cde140cede5eae3125ed36de86419f32257
```

The original file remains unchanged as provenance. The executing
`cti_cloud_controller.py` is a separately reviewed adaptation, SHA-256:

```text
75a43e4c62233b62a04768ec1366b9a9a54d34b685337116b6dc830b390473f4
```

Exactly four execution constants change: `TOTAL_SECONDS` 1800 -> 3600,
`WATCHDOG_SECONDS` 1560 -> 3360, `WORKER_DEADLINE_SECONDS` 1320 -> 3120, and
`MAX_COMMAND_SECONDS` 1200 -> 3000. The other differences are the module's D0/CTI
label, the schedule prefix `praxis-d0-` -> `praxis-cti-`, its description, the SSM
comment, and time labels in the command-timeout messages/comment. All account,
host-state, schedule-target, retry, staleness, byte-identity, reserve, failure,
stop, and cleanup logic remains identical. A local test reconstructs the adapted
file from precisely these substitutions and requires exact equality.
`cloud_runner.py` checks both hashes before launch and requires both files in the
committed bundle manifest.

The earlier 30-minute limit belongs to the D0 protocol's execution boundary and
its execution README. Before this CTI freeze or any cloud launch, the parent
workflow authorized a 60-minute CTI envelope under the current user instruction
to set up and use AWS, retaining the same $10 reserve and one-attempt constraint.
This is a prospective CTI runtime design; no D0 result or limit is being revised.

| Constraint | Value / behavior |
|---|---|
| Designated compute | Exactly one configured `g5.xlarge`, owned by the expected account, initially stopped |
| Guest shutdown behavior | Must already be `stop` |
| Host-time ceiling | 3,600 seconds from controller start-request timestamp |
| External watchdog | 3,360 seconds from that timestamp; enabled and exact target, role, input, and retry policy verified before start |
| Absolute command deadline | 3,120 seconds from that timestamp |
| Maximum SSM execution timeout | 3,000 seconds, reduced to fit the remaining absolute budget |
| Cost reserve | $10 total, including a $5 incidental allowance |
| Pinned compute estimate | $1.006/hour; 60 minutes compute is $1.006, plus the $5 allowance = $6.006; not an invoice |
| Restart behavior | Existing attempt/active-run records prohibit automatic reruns |
| Watchdog cleanup | Only this attempt's verified schedule, only after a live STOPPED observation |

The controller records ambiguous API failures, retains the watchdog, and prevents
further worker submission after a failed gate. The launcher requests stop in a
`finally` block after any start attempt that created an active-run record. It keeps
polling until STOPPED is observed or reports an unresolved shutdown with the
watchdog retained. Observation after the ceiling does not authorize more runtime;
an observed overrun cannot pass the operational gate. No forced stop is automatic.

## CTI adapter differences

The new adapter uses the fixed report directory and a fresh CTI S3 prefix. It
requires the exact committed launcher, controller, supervisor, worker, and worker
inputs in the frozen manifest, then rejects any other regular bundle file except
the protocol and freeze themselves. It validates hashes both locally and after
download, rejects archive traversal/links/special files/duplicates, and bounds
archive size and file count.

Bootstrap creates a fresh, run-specific directory on the mounted
`/opt/dlami/nvme` filesystem only after checking at least 64 GiB free. Bundle
download, verification, extraction, environment checks, and inference all count
against the outer absolute timeout. The actual outer stop epoch is fixed before
SSM submission, so delivery delays consume budget. The supervisor reserves a
further 160 seconds before that epoch for evidence preservation and publishing.
Consequently the inference budget is shorter than 52 minutes and includes model
download/load overhead. For an SSM-ready time of start+110 seconds, the send
timeout is 2,860 seconds, outer stop is start+2,940 seconds, and worker deadline is
start+2,780 seconds. Delivery, setup, download, three model loads, qualification,
and inference consume that same absolute worker budget. No margin was removed:
the worker still reserves 160 seconds before the earlier shell deadline for
evidence preservation. Completion of all 4,988 fresh responses is not guaranteed.

Historical batch-2, max-new-8 CTI summaries provide a planning reference:
[Qwen's July 5 full-bucket run](../relationship_evidence_cti_compliance/full_bucket_downstream_qwen_20260705/summary.json)
used 0.1574 seconds per vanilla row and 0.2194 per evidence row;
[Llama's July 31 v19.1 source-pointer run](../relationship_evidence_cti_compliance/confirmatory_closeout_20260731/confirmatory_500_root_audit/downloaded/llama-3-1-8b-instruct/v19-1-source-pointer-all6/summary.json)
used 0.1532 and 0.2270.
Scaling those four means to 1,247 questions yields about 944 seconds of generation
alone. That exceeds the original 30-minute adapter's practical worker allowance
once boot and loading are included. The 60-minute envelope adds cold-start margin.
This extrapolation is not a benchmark of the new questions: lengths differ, and
the new worker batches vanilla/evidence together, which may increase padding.

`run_cloud.sh` considers these existing Python environments in order, without
installing packages:

1. `/opt/praxis/venvs/sec-lord-relationship-evidence-defense-qwen25-7b-20260630/bin/python`
2. `/opt/praxis/venvs/falsecite-code-generation-gate-20260625/bin/python`
3. `/opt/pytorch/bin/python`
4. `/usr/bin/python3`

The environment must provide Python >=3.10, Torch >=2.4.0, Transformers >=4.43.0,
Accelerate >=0.30.0, huggingface-hub >=0.23.0, Safetensors >=0.4.3, and working
CUDA. These are compatibility minima, not claims of an exactly replicated package
environment. Actual versions, CUDA, GPU, and executable are recorded. The worker's
separate qualification gate controls whether fresh inference may begin.

The existing secret name `praxis/huggingface/token` is passed to the host, which
retrieves its value into `HF_TOKEN` without printing it, saving it to a file, or
putting it in a command-line argument. The worker may reuse a complete snapshot at
the frozen model revision; new downloads go to the new NVMe cache. Credentials are
unset before the final evidence archive is created.

Outputs are checkpointed to `results/partial/` approximately every 30 seconds
(plus the bounded upload duration). Checkpoints can contain an incomplete final
JSONL line and are never called a complete result. On exit, the supervisor writes
an exit record and compresses outputs. A bounded copy of an archive <=512 MiB is
attempted on the existing root EBS volume at
`/var/lib/praxis-cti-evidence/<run-id>` when free space exceeds archive size plus
128 MiB. This preserves evidence if final S3 publishing fails; it creates no new
volume. Final S3 publishing writes the archive first and its SHA marker only after
successful archive upload. The final marker denotes transport availability, not
scientific validity. An otherwise successful process returns failure if final
publishing fails.

After requesting and verifying stop, the launcher downloads the final archive,
checks SHA-256, and safely extracts it. If no final marker exists, it collects
available partial checkpoints and marks the run incomplete. Root EBS recovery, if
needed, requires a separately authorized later operation; this helper never
restarts the host to recover evidence.

## Freeze and bundle interface

`FREEZE.json` must contain this shape, with actual repository-relative paths and
SHA-256 values. Pin every dependency needed by the worker, not only the examples:

```json
{
  "files": {
    "reports/cti_external_validation_20260918/cloud_runner.py": "<sha256>",
    "reports/cti_external_validation_20260918/cti_cloud_controller.py": "<sha256>",
    "reports/cti_external_validation_20260918/trusted_cloud_controller.py": "<sha256>",
    "reports/cti_external_validation_20260918/run_cloud.sh": "<sha256>",
    "reports/cti_external_validation_20260918/inference_worker.py": "<sha256>",
    "reports/cti_external_validation_20260918/frozen_inference.py": "<sha256>",
    "reports/cti_external_validation_20260918/generator_inputs.jsonl": "<sha256>",
    "reports/cti_external_validation_20260918/qualification_inputs.jsonl": "<sha256>"
  },
  "worker_args": [
    "--inputs", "reports/cti_external_validation_20260918/generator_inputs.jsonl",
    "--qualification", "reports/cti_external_validation_20260918/qualification_inputs.jsonl"
  ]
}
```

The manifest excludes its own hash to avoid a circular dependency. Protocol and
freeze are independently bound to their exact committed Git HEAD bytes and added
to bundle validation. Every manifested file must also equal committed HEAD.
Commit and bundle the same bytes, including LF line endings for `run_cloud.sh`.
All bundle regular files must equal the manifest plus protocol and freeze;
private settings, logs, checkpoints, tokens, and unrelated files are excluded.

The launcher injects only `--output-dir` and `--deadline-epoch`. The worker receives
the frozen `--inputs` and `--qualification` arguments. Generation/model revisions,
qualification criteria, completeness, checker gates, and scientific interpretation
belong to the protocol and worker; the controller makes no scientific decision.

## Invocation and local validation

After the isolated worktree commit and bundle exist, use its executing launcher:

```powershell
python reports/cti_external_validation_20260918/cloud_runner.py prepare --settings C:/w/cti_external_private_20260918/settings.json --bundle <private-runtime.tar.gz> --bundle-sha256 <sha256> --protocol <committed-PROTOCOL.md> --freeze <committed-FREEZE.json>
```

That creates `READY_RECEIPT.json` only when all local frozen-byte checks pass.
Changing `prepare` to `launch` invokes cloud actions and is reserved for the
authorized parent workflow after fresh authentication, host/account preflight,
freeze, and readiness review. The helper does not authorize its own invocation.

Run the filesystem/mocked checks without cloud access:

```powershell
python reports/cti_external_validation_20260918/test_cloud_runner.py
& 'C:/Program Files/Git/bin/bash.exe' -n reports/cti_external_validation_20260918/run_cloud.sh
```

The tests cover both controller identities, exact adaptation differences, absolute deadlines, hostile archive
paths, secret-name-only bootstrap, STOPPED observation, partial collection,
ambiguous-start cleanup, exact manifest membership, and changed runtime bytes.
They do not establish current AWS authorization, model cache availability,
throughput, checkpoint scientific completeness, or live shutdown behavior.
