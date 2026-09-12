# Final Praxis 005 live pilot

Snapshot: 12 September 2026, 08:11 UTC. **Running actual CUDA inference.** The defended teacher generated 56 fixed GSM8K training responses; 43 passed the preregistered numeric-answer, length and nontruncation checks. This exceeds the minimum of 32; generation continues unchanged toward 64. These are training-data feasibility counts, not held-out utility or safety-retention results. No H1/H2 conclusion is available yet.

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
