# Completed second-stage execution

See [STATUS.md](STATUS.md) for the investment decision and [FINAL_CLOSEOUT.json](execution/FINAL_CLOSEOUT.json) for independently verified completion, S3 checksums and stopped hosts. No additional inference is required to reproduce the reported aggregate audits.

| Run | Source commit | Outcome |
|---|---|---|
| `fp005-20260912-37fdd3f` | `37fdd3f` plus environment repair `09f90d7` | Original training and generations retained; missing tokenizer dependency repaired; both judges and report complete |
| `fp006-containment-20260912-dd8a05a` | `dd8a05a` | Synthetic-fault control comparison complete |
| `fp007-selective-20260912-1c47aca` | `1c47aca` | Both calibrations complete; Devstral test complete; Qwen test withheld after original formatting failure |
| `fp007-inline-20260912-648cdcd` | `648cdcd` | Calibration responses replayed without model calls; fresh Qwen test complete; exposed Devstral test skipped |
| `fp006-empathy-20260912-5c33bc4` | `5c33bc4` | Validation-only capability qualification complete; no held-out test inference |

The numbered branches contain the source code, prospective research questions/hypotheses, frozen data and model revisions, tests, results and limitations. Original failures and the separate amendment remain in Git history. The initial campaign status is retained in the history of STATUS.md.

The four CPU output archives are listed in [stage2_archive_receipt.json](execution/stage2_archive_receipt.json). Each contains result JSON/JSONL, request lineage where applicable, the cloud status and bundle manifest; source bundles remain under the sibling S3 `bundles/` prefix. Protected 005 generations, teacher data and adapters remain under its original private run prefix. Its branch contains the before/after repair-integrity receipt and completed independent audit.

For receipt-only analysis, use `fetch_artifacts.py --run RUN_ID --out LOCAL_DIRECTORY`; `--small` omits individual cells and request receipts. The script uses the existing `praxis-build` AWS profile, refuses changed existing files, and saves SHA-256 download receipts. It does not run inference. For example, the portable 006 empathy audit accepts `--outputs LOCAL_DIRECTORY/outputs --data BRANCH/empathy_qualification/data --out AUDIT_DIRECTORY`. Full cells are required for that audit. Keep raw private outputs out of Git.

`monitor_stage2.py` is read-only and refreshes `execution/stage2_latest.json`. Archived deployment scripts and builders record the exact launches and hard limits; they contain historical host paths, run IDs and timers and are not a generic relaunch command. Adapt a new protocol and fresh run ID before future experiments. `close_stage2.py` documents verified stop, type restoration and removal of the two obsolete CPU schedules, including bounded polling for EC2 attribute propagation.

The final API estimate for 007 is $1.3891592 for 8,448 unique successful requests. Copied calibration cells are not charged twice. EC2 and storage are separate. Both hosts are stopped; retained volumes still incur storage charges.
