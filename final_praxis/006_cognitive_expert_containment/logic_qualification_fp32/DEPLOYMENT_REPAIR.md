# Preserved launch failure and operational correction

The FP32 protocol was frozen at `374224c36f6bddbb802d31a28db8fa271a2bf30c`. Its first deployment, run `fp006-logic-374224c36f`, returned an active systemd unit but never produced a supervisor heartbeat. Inspection found that both shell wrappers still constructed the predecessor folder path `logic_qualification`, while the bundle contained `logic_qualification_fp32`. The supervisor could not find its preregistration at that path. The wrapper requested host shutdown. No FP32 model or GSM8K generation was established; the protocol and cohort were not changed.

The correction derives each wrapper's study directory from its own script location. The launcher now requires a matching supervisor heartbeat in S3 after the systemd deployment, within180 seconds, and requests an early host stop if none appears. This checks actual supervisor startup instead of relying only on a briefly active unit.

The corrected operational code is committed before its launch. The FP32 preregistration, data, model, prompts, numerical and scientific gates are byte-identical to the first FP32 deployment. The original failed package remains in private S3 and its local launch/deployment receipts are retained. The next run has its own source commit, run ID and bounded watchdog.
