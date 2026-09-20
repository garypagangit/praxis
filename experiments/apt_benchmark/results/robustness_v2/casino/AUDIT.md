# Independent v2 calculation audit

**PASS** for saved computations, source bindings, and calibration thresholds. This is an AI/code audit, not human label review or external confirmation.

Dataset: **casino**. Verified 378 condition/model results, pooled and per execution, at both operating points; 18 calibration thresholds.

- Checked source/code/model/cache hashes and saved target identity/order.
- Independently recomputed confusion counts, precision, recall, F1, ROC-AUC, AP, and observation coverage.
- Independently derived strict sorted-negative calibration thresholds from saved clean calibration scores.
- Saved-model calibration-only inference: True. No fitting, tuning, or test-model inference.

## Limits

- Computational audit only; author labels are not independently human-adjudicated.
- Feature replay/cache semantics are reused; artifact hashes and coverage are verified, not a second complete feature implementation.
- Previously inspected AIT/Casino runs are development data, not external confirmation.
- Other-label flags are not independently established benign alarms or host-hour rates.
- Calibration budgets and descriptive gates do not imply population guarantees.
- Synthetic delay recovery is expected buffering behavior, not a learned-method success.
- Receipt hashes bind source bytes; they do not independently attest execution time.
