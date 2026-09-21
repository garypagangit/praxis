# Follow-up execution and completion

Execution started September 21, 2026. The latest published evidence is in
[the follow-up report](../results/tabular_followup_v1/REPORT.md). An interim report
does not indicate that the whole experiment has finished.

## Registered work

- Complete the original full-query TabICL and TabPFN comparison, ten seeds each.
- Challenge it with wider tree-model tuning and an abundant-benign condition:
  60 model/condition/seed cells, with the unequal label budget disclosed.
- Evaluate and independently audit the frozen rare-stage review policy and its
  single-model controls at the specified benign-review budget.
- Evaluate source-only transfer on the independent Sandworm capture. Its binary
  labels cannot independently confirm the source rare-stage outcome.
- Apply the already declared source-calibrated threshold diagnostic to those
  transfer predictions once all matching source calibration runs are complete.

## Automatic completion

`finish_followup.py` watches the existing workers and their completion receipts.
It independently checks results, evaluates the frozen policy, writes an aggregate
report, and invokes `promote_publication.py` to commit and push that report to
the existing `apt-benchmark` branch. The publication code refuses incomplete
results, mismatched provenance, private paths, and row-level data. Scientific
failure is a reportable result; it does not prevent completion.

The current watcher has a **12-hour deadline**, ending September 21 at about
9:04 p.m. America/New_York. Its temporary Windows request prevents system sleep
only while plugged in; it does not change the power plan or display settings.
Battery operation, shutdown, a worker failure, or exceeding the deadline can
leave the work incomplete. The watcher records that state instead of reporting
success. It never automatically refits, restarts, or kills a model worker.

Private monitoring files are under the existing data workspace's
`tabular_followup_v1/final_review1`: `STATE.json`, `STARTUP_RECEIPT.json`, and,
after successful audits, `RESULT_MANIFEST.json`. `ERROR.json` records an audit
failure when one occurs. `PUSHED_AND_VERIFIED` confirms the remote result commit.
If Git publication fails, the local audited artifacts remain available.

All computation launched in this follow-up is on CPU. AWS authentication was
expired when checked; no AWS resource has been started for this follow-up.
Current AWS machine state cannot be verified without a valid session.

## Validation and scope

The full benchmark software suite passed **328 tests** on September 21, 2026
(72.392 seconds). This verifies software checks, not the scientific hypotheses.
Private test output is retained outside Git. An independent audit additionally
recomputes scientific metrics from saved predictions and verifies artifact hashes.

The [novelty review](NOVELTY_POSITION.md) documents substantial existing work.
No new algorithm, operational detector, early-warning result, or independent
rare-stage improvement is established merely by executing this plan.
