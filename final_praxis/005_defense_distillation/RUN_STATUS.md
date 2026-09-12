# Final Praxis 005 live pilot

Snapshot: 12 September 2026, 08:45 UTC. **Actual training completed for the first adapter; reproduction/feasibility only. The novelty criterion is not met**, as documented in [NOVELTY_AMENDMENT.md](NOVELTY_AMENDMENT.md). Teacher preparation completed with 64 accepted responses from 81 attempts. Both unchanged models completed all 160 evaluations. The trained parent's held-out evaluation is now running; the two ER adaptations and safety judges remain pending. No H1/H2 conclusion is available yet.

The parent's fixed-budget math result is 12/32 correct final answers with complete outputs; ER scored 20/32. Truncation counts for harmful/benign/math panels were 23/40/18 for the parent and 4/6/6 for ER (panel sizes 64/64/32), with no empty outputs. These comparisons have substantial token-budget and response-style dependence. No refusal or harmlessness conclusion follows from generation counts.

The first `base_kd` adapter completed 32 optimizer steps, 128 training-example exposures and 14,454 supervised tokens across 1,843,200 trainable parameters. Its measured parameter-change L2 norm was 1.7628. Independent read-only inspection verified both serialized adapter-file hashes, all 144 tensors were finite, and all 72 LoRA B matrices moved from their zero initialization (combined B norm 0.8793). Peak GPU allocation was 6.97GB. Training-loss averages for the first/last four examples were 0.2734/0.1410; these are diagnostics on different examples, not a held-out learning claim. The checkpoint and generation artifacts are preserved in private S3.

The cloud job passed all 12 harness tests, qualified Torch 2.6.0+cu124/BF16 on the A10G, and reproduced the CPU freeze's five public data hashes and all 160 evaluation IDs. At this snapshot there are no tracebacks or S3 synchronization errors. After teacher preparation, it evaluates both unchanged models and independently trains/evaluates the three registered adapters, then runs the two safety judges. Manual review remains required.

- AWS instance: `i-039ed976444ade397`, `g5.xlarge`, us-east-1a.
- Scratch: encrypted 100GB gp3 `vol-02b4f3854b7ff5bc4`, mounted at `/mnt/praxis-20260912-005`; 93GB initially free. Exact serial and blank signature were verified before formatting; existing root data was preserved.
- Frozen running source: `37fdd3f154a78017f9eb313385e25379c36affde`. Later branch commits contain operations receipts only.
- Source-bundle SHA-256: `ab381d7439a706b5a3852e949588a19cfdae4394aefb7651d03c12727aa590f8`.
- Raw preregistration SHA-256 verified on AWS: `21d3fee055f08fc916f0a0fbab6a6ae4437f05e1dc4d8cd23ff2a1b13c681b9b`.
- Protocol text/settings/source-lock fingerprint: `2e3749bcc7fa4f5d1bbd9b5758608ecb5827c2546fc8ebc29fef991cb035b938`.
- Run ID/systemd unit: `fp005-20260912-37fdd3f`. It runs independently of the local chat session.
- Private artifacts: `s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260912/runs/fp005-20260912-37fdd3f/`.
- Bounds: seven-hour supervisor plus systemd timeout; guest stop at 15:49:50 UTC; independently verified AWS stop at 15:55:49 UTC (11:55:49 EDT).
- Conservative incremental eight-hour estimate: GPU up to $8.05 plus approximately $0.09 scratch storage, before small request/storage charges. This is an estimate, not an invoice. The job authorization cap is $75. Scratch costs $8/month if retained after the run; archive outputs before cleanup.

Use `python final_praxis/005_defense_distillation/cloud/monitor.py` with the authorized local AWS profile to read live status. It prints aggregate events, never raw benchmark generations. Full execution commands and AWS receipts are under `cloud/execution/`; [the preregistration](PREREGISTRATION.md) defines success, failure and interpretation limits.
# Latest observation —12September2026,09:07UTC

Read-only S3 monitor confirms the campaign remains RUNNING with no traceback or synchronization errors. The second adaptation, `er_kd`, completed32 updates with reported adapter L2 change1.667166; its fixed evaluation reached32/160. Parent, unchanged ER and adapted-parent evaluation stages have finished; replay adaptation and both safety judges remain later in the unchanged pipeline. The first saved adapter has an independent tensor/hash audit; this update does not claim an equivalent audit of the second adapter or any safety benefit. See cloud/execution/latest_status.json for the monitoring receipt.
