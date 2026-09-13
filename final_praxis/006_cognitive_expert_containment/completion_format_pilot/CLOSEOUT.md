# Completion-format pilot: implementation closed

The 64-response pilot completed on 13 September 2026 at01:02UTC and its independent automated review was published as commit `7ab16c9`. The cloud and local audits agree: all64 cells are valid, all numerical checks pass, and there are zero integrity or synchronization errors.

| Format | Correct, all nontruncated | Capped responses | Numeric extraction |
|---|---:|---:|---:|
| Raw |10/32|3/32|32/32|
| Chat |9/32|7/32|32/32|

The chat candidate fails its preregistered maximum of3 capped responses. Its extraction and completed-correct gates pass, but qualification requires every gate. This is a completed scientific failure, not an execution failure. Paired uncertainty and all fixed thresholds remain in [completed/RESULTS.md](completed/RESULTS.md).

**Decision: close this fixed implementation.** Do not proceed to the proposed fresh256 test study, increase generation length, search additional prompts/checkpoints automatically, or select raw posthoc because its32-item diagnostic happens to meet the cap threshold. The larger predecessor study's useful logic contribution remains a valid separate finding; it does not override either failed completion screen.

No further model processing was started for this closeout. The next step is a literature and reproducibility reassessment of the broader corrupted-specialist research direction before any new paid study. A future candidate needs a reproducible capable baseline, objective outcomes and a distinct mechanism beyond published expert ablation or generic evidence-gated revision.

The final cloud run has exit-state COMPLETED. AWS authentication was restored, and a live check at 23:17:08 UTC on 13 September 2026 verified that both experiment hosts (`i-039ed976444ade397` and `i-07178e293e8df2a60`) are stopped `g5.xlarge` instances. No schedules matched `praxis-20260912-stop-`. The reconnect and verification started no experiments. [CLOSEOUT.json](CLOSEOUT.json) records the review and verified host states, and [the campaign status](https://github.com/garypagangit/praxis/blob/Final-Praxis-004-Specialist-Revision/final_praxis/shared_20260912/STATUS.md) records the subsequent investment decision.
