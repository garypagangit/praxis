# FP32 logic qualification: running

Updated12 September2026,20:37 UTC. The corrected AWS launch has produced a verified supervisor heartbeat. The FP32 checkpoint loaded exactly and passed all numerical checks; pilot generations are being saved. No capability result is available yet.

- Active run: `fp006-logic-ec92d2561c`; operational source commit `ec92d2561c3011ba525cdfba66b58b86ee758d49`.
- Scientific protocol frozen at `374224c36f6bddbb802d31a28db8fa271a2bf30c`, byte-identical after the [launcher correction](DEPLOYMENT_REPAIR.md).
- Protocol SHA256: `8a76f26328795c86fff99df994737490cab4f559aeec74cdeb557352422b6ad4`.
- 256 untouched GSM8K test questions across intact, logic ablation and social ablation;16 disjoint train-pilot questions across the same arms.816 planned generations.
- FP32 with TF32 disabled; exact next-token agreement and at most0.001 absolute logit differences on six fixed backend/cache probes.
- All27 local tests passed before the corrected launch. All10 GPU technical checks passed across the six fixed probes. Initial real pilot cells also passed independent schema/hash/route validation.
- Job cap:$75; eight-hour g5.xlarge compute bound approximately$8.05. External AWS stop deadline:13 September2026,04:30:35 UTC (12:30:35 a.m. Eastern), with earlier stop after completion/failure.

The [BF16 numerical-preflight failure](../logic_qualification/completed/RESULTS.md) and first FP32 launch error are preserved. Neither processed the planned GSM8K cohort. No failed criterion was relaxed or original result overwritten.

Private live artifacts: `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260912/runs/fp006-logic-ec92d2561c/`. The detached cloud supervisor saves cells, syncs to S3 and runs the automatic audit independently of local connectivity. `outputs/audit/RESULTS.md` will contain the decision.

The local collector is running; it independently audits stable final artifacts and publishes this folder's `completed/RESULTS.md`, provenance and updated status to the numbered Git branch, including negative or incomplete outcomes. It retries connectivity and never starts another paid experiment. Cloud processing, its audit and its stop watchdog continue without the local collector.

This tests whether a useful logic expert exists to preserve. It does not yet demonstrate a novel containment method or select a primary Praxis.

[Startup verification](STARTUP_VERIFICATION.json) records exact loading, numerical agreement, GPU memory and the initial real-cell integrity checks. No scientific accuracy or continuation decision is inferred from the pilot.
