# PX-085: Calibrating stage-conditioned missed-warning risk

Status: COMPLETE_EXPLORATORY_REPLAY_AND_AWS_AUDIT.

Stage calibration did not repair the primary exfiltration misses; movement absent from calibration; no deployment guarantee.

[Results](../warning_control_20260930/RESULTS.md) | [Interpretation](../warning_control_20260930/INTERPRETATION.md) | [All arms](../warning_control_20260930/results/ALL_ARMS.csv) | [Protocol](../warning_control_20260930/PROTOCOL.md)

Full replay ran locally; two AWS CPU processes independently audited aggregate metrics and the rank rule after large S3 transfers failed. No new model fitting. This is previously exposed development data; novelty and independent-campaign benefit remain unconfirmed.
