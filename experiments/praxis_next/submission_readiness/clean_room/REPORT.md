# Clean-extraction reviewer check

**Completed September 23, 2026. Public numerical reproduction passed. A single archive-link packaging defect was found and resolved in the review copy without changing any original evidence file.** Both the initial failure and the repaired pass remain recorded.

## What was tested

The completed public evidence ZIP was copied into the new directory `C:/w/praxis_review_cleanroom_20260923T194852766389Z`, its member paths were validated, and its contents were extracted into a new `extracted` subdirectory. The wrapper rejected absolute paths, traversal, Windows drive/alternate-stream/device names, case-colliding paths, symlinks, encrypted members and excessive expanded size before writing archived members.

| Property | Observed value |
|---|---|
| Original archive | `apt_evaluation_praxis_evidence.zip` |
| Original archive SHA-256 | `3dcc1e67dad8a74eebca1ac71c7fce3d1dd721ea67901c3f4ad869b126055bd3` |
| Compressed size | 2,588,607 bytes |
| Extracted original members | 209 |
| Expanded size | 10,473,011 bytes |
| Scientific/package manifest entries checked | 206 |
| Original members changed by either check | 0 |
| Model fits / AWS operations | 0 / 0 |

The fresh virtual environment used **Python 3.11.9 and NumPy 2.2.6**. Its installed distributions were NumPy, pip 24.0 and setuptools 65.5.0; `include-system-site-packages` was false. Both extracted verifiers ran with Python `-I -B`, a fresh working directory, no project analysis imports, and a Python-level file-open allowlist covering only the extracted bundle, fresh result/venv directories and base Python runtime. No denied accesses occurred.

This is a fresh local runtime and extracted-file check, **not** a container, operating-system sandbox, separate physical machine or external researcher replication. NumPy installation used the normal package installer during setup. The Python audit hook observes Python file-open events; it is not a complete operating-system I/O monitor.

## Initial unchanged extraction

The initial run completed from `19:48:52` to `19:49:40 UTC`. The full result is [CLEAN_ROOM_RECEIPT.json](CLEAN_ROOM_RECEIPT.json).

| Check | Outcome |
|---|---|
| Public arithmetic verifier from extracted files | **PASS** |
| Independent check of all 206 manifest hashes | **PASS** |
| Preservation of all original extracted bytes | **PASS** |
| Original archive remained unchanged | **PASS** |
| Package verifier and relative-link scan | **FAIL: one missing README archive link** |

The missing target was exactly `apt_evaluation_praxis_evidence.zip`, relative to the extracted manuscript directory. A ZIP cannot contain its own final bytes, so the original ZIP had deliberately excluded that member. However, the unchanged package verifier also required every README link to exist after extraction. This was a delivery inconsistency, not a mismatch in scientific calculations or hashes.

The recorded exception was:

```text
ValueError: Missing local link: apt_evaluation_praxis_evidence.zip
```

The independent relative-link scan found no other missing target. The initial package run's output and traceback remain in the clean-room receipt; its [file-access log](PACKAGE_FILE_ACCESS.json) records 244 observed open events and zero denials.

## Packaging-only repair

The unchanged downloaded archive was copied into the extracted manuscript directory at the README's linked location. No original extracted member, original repository artifact or original archive was edited. The added archive's SHA-256 equals the original archive's SHA-256 above.

The unchanged extracted package verifier was rerun and passed at **19:50:53 UTC**:

- All **206 manifest hashes** matched.
- Linked completed computational audit receipts passed.
- The **24-page** manuscript/render receipt binding passed.
- All **74 local manuscript and handoff links** resolved.
- The only added member was the original ZIP at its linked path; **zero original members changed**.

See [LINK_REPAIR_RECEIPT.json](LINK_REPAIR_RECEIPT.json) and [REPAIRED_PACKAGE_VERIFICATION.json](REPAIRED_PACKAGE_VERIFICATION.json). The added ZIP remains an original historical artifact inside the review copy; no infinite nesting or rewritten source ZIP is needed. A subsequent reviewer delivery can include this original ZIP alongside the extracted original evidence files.

## What a reviewer can reproduce from public files

The [public verifier receipt](PUBLIC_VERIFICATION.json) independently recomputed the following using only the bundled confusion counts and bootstrap plan:

| Public calculation | Verified quantity |
|---|---:|
| Published prediction aggregate tables | 66 |
| Declared paired comparisons | 36 |
| Recomputed metric intervals | 720 |
| Regenerated bootstrap draws | 2,000 |
| Three-seed mean groups | 12 |
| Stage-direction summaries | 6 |
| Private files opened | 0 |
| Project analysis modules imported | 0 |

The computation verifies point metrics, error-destination accounting, support conditions, paired aggregate differences, bootstrap intervals, seed means, direction counts and linkage to original receipts. The package check also verifies paper assembly inputs, rendered artifact hashes and recorded visual-review status. It does not independently repeat visual inspection.

Public aggregates cannot independently establish original row identities/pairing, probability-to-label conversion, author ground-truth validity, source preparation, or model-fitting provenance beyond the linked receipts. They also cannot turn five capture fragments into independent campaigns. The private-row dataset-qualification sweep cannot be newly recomputed without its specified source CSVs; this check verifies the published qualification evidence bindings rather than claiming access to those missing source rows.

## Reproduce this check

Runnable wrappers are [run_clean_room.py](run_clean_room.py) and [run_link_repair.py](run_link_repair.py). They intentionally preserve prior receipts. For another run, copy both wrappers into a **new empty output directory**, then execute them there with an absolute path to the original ZIP. This creates a new timestamped work directory and fresh virtual environment:

```powershell
python run_clean_room.py --archive C:/path/to/apt_evaluation_praxis_evidence.zip --work-parent C:/w
python run_link_repair.py --receipt CLEAN_ROOM_RECEIPT.json
```

For this original archive, the first wrapper exits nonzero because it records the missing self-link; the second tests only the documented packaging repair and exits successfully. Receipt outputs are written beside the copied wrappers and in the new work directory. Existing records and work directories are never deleted.

The official extracted reviewer commands, using the new venv Python and extracted root as working directory, remain:

```powershell
python -I -B experiments/praxis_next/measurement_praxis/evidence/paired_reanalysis/verify_public.py
python -I -B experiments/praxis_next/measurement_praxis/verify_package.py
```

The wrapper additionally instruments Python open events and saves new receipts outside the immutable extraction. [MANIFEST.json](MANIFEST.json) binds the wrappers, run records, logs and this report. The minimal dependency installation, exact commands, runtime version, actual stdout/stderr and elapsed times are retained in the receipts.
