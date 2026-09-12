# FP32 logic qualification: launch correction ready

Updated12 September2026,20:28 UTC. The separately frozen FP32 follow-up hit a shell-path error before supervisor startup. The operational correction is ready; its scientific protocol is unchanged. The original attempt processed zero GSM8K pilot/test questions and its [negative review remains archived](../logic_qualification/completed/RESULTS.md).

- Frozen follow-up commit: `374224c36f6bddbb802d31a28db8fa271a2bf30c` on `Final-Praxis-006-Cognitive-Expert-Containment`.
- Preserved failed deployment: `fp006-logic-374224c36f`; see [DEPLOYMENT_REPAIR.md](DEPLOYMENT_REPAIR.md).
- Protocol SHA256: `8a76f26328795c86fff99df994737490cab4f559aeec74cdeb557352422b6ad4`.
- Same untouched256 test questions x3 conditions, plus16 train-pilot questions x3:816 planned generations.
- FP32 with TF32 disabled; strict next-token equality and maximum0.001 absolute logit difference across the fixed backend/cache probes. Scientific gates remain unchanged.
- All24 local tests passed before launch. GPU qualification and study outcomes are pending.
- Each launch retains a$75 cap and an independent eight-hour stop watchdog. The first FP32 deployment requested early shutdown; a corrected launch will receive a fresh watchdog.

The corrected detached cloud supervisor will save cells, synchronize S3 and run the automatic audit independently of local connectivity. A local collector can independently audit final evidence and publish derived reviews to this numbered branch, retaining both negative and positive outcomes. It never starts further paid experiments.

Private artifacts: `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260912/runs/fp006-logic-374224c36f/`. The result will appear in `outputs/audit/RESULTS.md`; completed collection publishes this folder's `completed/RESULTS.md` and updates this status.

This remains a prerequisite capability test. It does not yet establish a new containment method or select a primary Praxis.
