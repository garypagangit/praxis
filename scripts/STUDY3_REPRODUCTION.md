# Study 3 reproduction

This uses the original Study 3 code and evidence supplied in the desktop `study 3`
folder; it does not invent a new classifier or silently replace the frozen analysis.
The source is read-only. Prepared copies contain restricted commands, possible lab
credentials and participant evidence: keep them outside Git, control access, and
do not upload them to AWS without appropriate authorization and safeguards.

The requested v1.6 Word file was not readable on this machine when this runbook
was created. The accessible v1.11 paper and the study's decision register identify
the following paper numbering. Confirm it against v1.6 before claiming that version
has been reproduced:

| Paper | Analysis | Rule |
|---|---|---|
| H1 | Command content versus the same model without it | Higher held-out macro-F1 in at least 3 of 5 models |
| H2 | XGBoost versus the other classifiers | Highest held-out macro-F1 |
| H3 | Classification within ATT&CK stage groups | At least 3 of 5 models have permutation p <= 0.05 in each testable stage group |

These are **post-scoring revisions**. The pre-scoring hypotheses and results are
different and remain in the frozen tables. The H3 source files retain their older
`H2` names; the H2 comparison retains its older `H3` name. Stage 6 lacks sufficient
AI windows for the rule; it is descriptive only. Stage 7 combines lateral movement
and collection, so those activities are not separately tested. The nine sessions
and limited ranges do not establish generalization to real-world APTs; these tests
provide evidence, not proof.

## Environment

Use Python **3.10.12** and the supplied pinned environment:

```powershell
py -3.10 -m venv C:\private\study3-venv
C:\private\study3-venv\Scripts\python.exe -m pip install -r scripts\study3-requirements.txt
$python = 'C:\private\study3-venv\Scripts\python.exe'
$source = 'C:\Users\garyp\OneDrive\Desktop\study 3'
$runner = (Resolve-Path scripts\study3_reproduction.py).Path
```

Choose a private destination that **does not exist**. These paths are examples;
create the parent directory and restrict its permissions. Do not set `S3_ROOT`,
`S3_OUT`, `S3_TEST_CHANCE_PARTS` or `S3_LIBS` for these runs unless explicitly
needed. They can redirect inputs or shorten the permutation test.

## Replay the saved analysis

This copies the original code, frozen data, plumbing logs, held-out predictions
and stage-permutation records. It verifies all Freeze 2 entries and the accessible,
non-set-aside Freeze 1 entries; it does **not** verify the excluded raw evidence,
set-aside files, private key or test labels.

```powershell
$study = 'C:\private\study3-saved'
& $python scripts\study3_reproduction.py prepare --source $source --destination $study --mode saved
& $python scripts\study3_reproduction.py summaries --study $study
```

The second command recomputes H1/H2 from the saved held-out predictions and H3
from the saved 1,260 stage-permutation task records. It checks the original
consistency and fit-hash checks and compares the four relevant tables byte for
byte. This is a **summary replay**, not model refitting or an independent replication.
Outputs are in `results_h1_h3` and `results_h2_stage` inside the private copy.

## Refit the frozen experiment

This begins from the frozen preprocessed data and plumbing records, but excludes
saved scored predictions and stage-permutation records. It performs 1,310 scored
tasks plus 1,260 stage tasks; each task fits multiple models. The original plumbing
and stage runs took substantial CPU time. The frozen implementations use CPU, not
GPU; the commands below use four shards. Increase shard count only if the host has
enough CPU and memory, and use the same shard count consistently when resuming.

Run the probe before committing to the full refit:

```powershell
$study = 'C:\private\study3-rescore'
& $python scripts\study3_reproduction.py prepare --source $source --destination $study --mode rescore
& $python scripts\study3_reproduction.py probe --study $study
```

Only continue if the probe passes. It saves one scored task, which the full run
will reuse. On this Windows machine, the probe's held-out classifications matched
all 951 saved predictions, but its fit hash differed; this is **not** an exact
reproduction. Try a fresh preparation in a secure environment matching the
original Linux run. The same pinned versions alone do not guarantee identical
floating-point fits. A failed probe leaves its results in that copy; do not
continue it as an exact refit.

After a passing probe:

```powershell
Set-Location $study
& $python -I -B code\trials\run_trials.py score --shard 0/4 --budget 600
& $python -I -B code\trials\run_trials.py score --shard 1/4 --budget 600
& $python -I -B code\trials\run_trials.py score --shard 2/4 --budget 600
& $python -I -B code\trials\run_trials.py score --shard 3/4 --budget 600
& $python -I -B code\trials\run_trials.py status score
```

Repeat the four score commands until the status says **COMPLETE**; the commands
above are sequential, but can be run in separate terminals concurrently. Then:

```powershell
& $python -I -B code\h2_stage\run_h2_stage.py run --shard 0/4 --budget 600
& $python -I -B code\h2_stage\run_h2_stage.py run --shard 1/4 --budget 600
& $python -I -B code\h2_stage\run_h2_stage.py run --shard 2/4 --budget 600
& $python -I -B code\h2_stage\run_h2_stage.py run --shard 3/4 --budget 600
& $python -I -B code\h2_stage\run_h2_stage.py status
```

Repeat stage shards until **COMPLETE**, then run:

```powershell
& $python $runner summaries --study $study
```

The wrapper recomputes all summaries and fails if consistency, fit-hash,
frozen-input or leak checks fail; when the supplied comparison tables are
available it also requires byte-identical H1/H2/H3 tables. `status` prints
incomplete but does not signal failure via its exit code. The stage runner requires
the exact Python and library versions recorded in the plumbing log. Cross-platform
numeric differences can cause fit-hash failures; do not treat such a run as an
exact reproduction. No cloud instance is automatically created.

## Raw evidence

To make a separate working copy of the original evidence and preprocessing code:

```powershell
& $python scripts\study3_reproduction.py prepare --source $source --destination C:\private\study3-raw --mode raw
```

This copies approximately 4.4 GiB of restricted evidence. See its `code\README.md`
and `code\features\README.md` for the preprocessing and feature steps, and the
trial README for EDA, plumbing, the two explicit freeze approvals and scoring.
These frozen scripts were developed on Linux; in particular, their Freeze 1 writer
uses native path separators while later readers expect `/`. Raw preprocessing and
refreezing on Windows has not been validated; use a secure Linux environment and
validate hashes and leak checks before scoring. A newly frozen analysis is a new
run, not the original prospective design, and the post-scoring rules must remain
identified as such.
