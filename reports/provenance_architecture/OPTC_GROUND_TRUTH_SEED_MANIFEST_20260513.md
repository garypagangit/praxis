# OpTC Ground-Truth Seed Manifest

Generated: 2026-05-13

Status: **seed manifest extracted; interval labels still require event-window attachment**

## Source

- Ground truth PDF: `external\datasets\optc\OpTCRedTeamGroundTruth.pdf`
- Parsed seed CSV: `reports\provenance_architecture\optc_ground_truth_seed_events_20260513.csv`

## Extraction Summary

| Metric | Value |
|---|---:|
| Timestamped red-team events | `101` |
| Unique host mentions | `30` |
| First timestamp | `2019-09-23T11:23:29Z` |
| Last timestamp | `2019-09-25T14:24:03Z` |

## Day Counts

| Day title | Events |
|---|---:|
| Custom Powershell Empire | `48` |
| Malicious Upgrade | `16` |
| Plain PowerShell Empire | `37` |

## Heuristic Stage Counts

| Stage | Events |
|---|---:|
| command_and_control | `25` |
| lateral_movement | `25` |
| reconnaissance | `19` |
| attack_activity | `15` |
| credential_access | `7` |
| persistence | `4` |
| execution | `3` |
| privilege_escalation | `3` |

## Decision

This clears the first feasibility check for the OpTC label path: the public ground-truth document contains timestamped red-team activity that can seed an interval manifest.

This is not yet a detector-ready label table. The next step is to map OpTC eCAR host events into the provenance window factory and attach windows around these seed timestamps. The heuristic stage labels are for triage only and must be audited before any stage-specific claim.

## Next Gate

1. Select one day and 3-5 hosts from the seed manifest.
2. Download only the matching OpTC eCAR shard(s).
3. Convert eCAR rows to the provenance window schema.
4. Attach +/- interval windows around red-team timestamps and confirmed benign intervals outside red-team activity.
5. Require >=20 benign and >=20 attack windows before detector training.