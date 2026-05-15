# Provenance Label Path Decision

Generated: 2026-05-13

Status: **architecture ready; first targeted OpTC label gate cleared**

## Bottom Line

The next provenance move is labels, not models. The full E5 Cadets run scaled, but PIDSMaker node-touch labels collapse almost every window into attack-touch:

| Source | Windows | Attack-touch | Benign/unlabeled |
|---|---:|---:|---:|
| Full E5 Cadets | `9611` | `9609` | `2` |

That cannot support supervised benign-vs-attack, stage-routing, concept-drift, MIA, watermarking, or adversarial robustness claims.

## Minimum Label Gate

Use `reports/provenance_architecture/PROVENANCE_LABEL_REQUIREMENTS_20260512.md` as the gate:

| Check | Minimum |
|---|---:|
| Real classes | at least `2` |
| Benign windows | `>= 20` |
| Attack/anomaly windows | `>= 20` |
| Stage-specific claim | `>= 20` windows for that stage |
| Split support | train/validation/test each contain claimed positive class |
| Label source | interval truth, confirmed benign spans, or trusted release annotation |

## Candidate Paths

| Path | What it means | Strength | Risk | Publishable downstream claim |
|---|---|---|---|---|
| A. Confirmed intervals on existing Cadets | Create or obtain `start_ns,end_ns,label` intervals for known benign/attack spans in current Cadets windows. | Fastest reuse of existing 480M-event run; uses current pipeline. | Manual labeling can become weak if not tied to source truth; current node-touch labels are not enough. | Small but honest provenance anomaly/stage detector if intervals pass support gates. |
| B. Another labeled host stream | Find a host/provenance stream with trusted benign/attack intervals. | Could avoid Cadets label collapse. | Discovery/setup time; unknown schema conversion cost. | Stronger detector/drift claim if labels are clean. |
| C. Targeted OpTC subset | Build a small OpTC parser/window subset from public OpTC ground truth. | Best fit for honest labels: OpTC has red-team ground truth and benign activity. | More setup and data volume; Windows eCAR schema differs from Cadets. | Publishable "label-faithful provenance window detector/drift benchmark" if subset is clean. |

## Recommended Decision

Start with **Path C: targeted OpTC subset**, while keeping Path A as a fallback.

Reason:

- Existing Cadets is already proven label-blocked for supervised claims.
- Manual Cadets labels can work only if tied to source truth, but that may become a small bespoke subset.
- OpTC has a public ground-truth artifact and a larger enterprise-style setting, which is better aligned with defensible provenance detector claims.

## 2026-05-13 Feasibility Check

The first OpTC metadata check is complete:

| Artifact | Result |
|---|---|
| Local metadata | `external/datasets/optc/README.md`, `ecar.md`, and `OpTCRedTeamGroundTruth.pdf` are present locally and ignored from Git. |
| Ground-truth parser | `scripts/build_optc_ground_truth_seed_manifest.py` extracts timestamped seed events from the red-team PDF. |
| Seed manifest report | `reports/provenance_architecture/OPTC_GROUND_TRUTH_SEED_MANIFEST_20260513.md` |
| Timestamped red-team events | `101` |
| Covered days | `Plain PowerShell Empire`, `Custom Powershell Empire`, `Malicious Upgrade` |
| Unique normalized host mentions | `30` |

Decision: OpTC remains the best first provenance-label path. The first targeted host/day (`sysclient0501`, day 2) has now cleared the minimum label-support gate, but it is still only a feasibility result until another host/day or benign shard supports chronological or cross-host checks.

## 2026-05-14 Label Acquisition Plan

The label path is concrete in `reports/provenance_architecture/OPTC_LABEL_ACQUISITION_PLAN_20260514.md`, and the first gate result is recorded in `reports/provenance_architecture/OPTC_WINDOW_LABEL_GATE_RESULT_20260514.md`.

How labels are obtained:

1. Use the OpTC red-team ground-truth PDF as attack seed truth.
2. Expand each timestamped red-team event into a padded interval, default `-15` to `+15` minutes.
3. Download the matching OpTC `ecar/evaluation/<day>` host/day shard from the public release.
4. Convert eCAR JSON to normalized provenance edges with `scripts/convert_optc_ecar_to_edges.py`.
5. Build windows with `scripts/build_optc_window_gate.ps1`, passing `-Labels runs\optc-label-acquisition-20260514\optc_attack_intervals.csv`.
6. After windowing, count attack-window, background/no-red-team-overlap, and gray-buffer support.

First target shortlist from the seed manifest:

| Host | Day | Seed events | Suggested folder |
|---|---:|---:|---|
| `sysclient0501` | `2` | `28` | `external/datasets/optc/ecar/evaluation/24Sep19` |
| `sysclient0201` | `1` | `18` | `external/datasets/optc/ecar/evaluation/23Sep19-red` |
| `sysclient0051` | `3` | `12` | `external/datasets/optc/ecar/evaluation/25Sept` |

Claim guard: this gives window-level red-team interval overlap, not perfect event-level malicious labels. Non-overlap windows should be called `background/no-red-team-overlap` unless a stronger third-party label source is audited.

## Half-Day Investigation Plan

| Step | Action | Pass condition |
|---:|---|---|
| 1 | Fetch OpTC metadata and ground-truth document, not full data yet. | **Done.** Ground-truth seed timestamps were extracted. |
| 2 | Identify the smallest host/time subset containing both benign and red-team intervals. | Expected `>=20` benign and `>=20` attack windows after windowing. |
| 3 | Map OpTC eCAR fields to the existing window factory schema. | Event type, process/exec, subject/object ids, timestamp available. |
| 4 | Run a 1-host or 1-day smoke conversion. | **Done.** `sysclient0501` day 2 converted `625,000` eCAR edges into `125` windows. |
| 5 | Attach interval labels and require support. | **Done for first target.** Support is `82` attack, `21` background, `22` gray-buffer. |
| 6 | Run a detector-registry smoke. | **Done as feasibility only.** Stratified split works, but chronological generalization is not shown because attack windows precede gray/background windows. |
| 5 | Attach intervals and run detector-zoo gate. | Gate passes support checks before any supervised model claim. |

## Fallback Plan

If OpTC setup stalls:

1. Use Cadets full windows for weak-proxy prioritization only.
2. Manually label a small Cadets subset only where source truth supports intervals.
3. Treat the result as a labeling/protocol paperlet, not as a full detector claim.

## Experiments Reopened Only After Label Gate

| Experiment | Reopen condition |
|---|---|
| Concept drift | Chronological windows with real benign/attack or anomaly labels. |
| TGN | Anomaly/window prediction target beats trivial previous-event baselines. |
| SSL | Positive/negative view separation improves with meaningful node features. |
| Stage routing | Stage labels or reliable stage intervals exist. |
| MIA | Stable detector suite trained on honest labels exists. |
| Watermarking | Stable detector utility baseline exists. |
| Adversarial robustness | Two to four trained detector families exist. |

## Do Not Do

- Do not train supervised detectors on node-touch labels alone.
- Do not call density proxy detection an attack detector.
- Do not spend GPU on TGN/GraphCL before adding another OpTC host/day or benign shard.

## External Note

The public OpTC release includes red-team ground truth and was produced as a DARPA Transparent Computing scale-up dataset. Treat the ground truth as imperfect but more defensible than node-touch proxies for supervised window labels.
