# Independent postrun artifact review

**Closeout amendment:** the original audit source bundle remains in this directory.
The full V2 audit used the separately hashed bundle in
[roundoff_amendment](roundoff_amendment/README.md) after identifying one secondary
exact-zero/floating-point flag discrepancy. Current reviewer source validates the
archived machine arithmetic while retaining the exact-arithmetic correction as a
warning. The original failed audit, result bytes and frozen experiment sources
remain unchanged. See [paper readiness](../paper_package/PAPER_READINESS.md) for
the final completed receipt chain. The historical preparation account below
describes the original review source; the root coordinator authored the disclosed
amendment after inspecting results.

These files were prepared after the original study launch using frozen source,
synthetic controls and qualification artifacts only. They do not alter the frozen
study. Main-study result files must be supplied explicitly by the coordinator;
the reviewer has not opened them during preparation.

By default `audit_results.py` targets original commit `162d2ab` and protocol
`11b620786e74a374158c93181024e1bfec216fc8edfa3c4178bbd12bd234610a`.
It deliberately rejects a different protocol in original mode. Explicit extension
mode uses `extension_checks.py` to verify the separately registered protocol and
fixed reuse; it never silently substitutes extension results for original results.

Run after the completed original archive is released for scientific review:

```text
python postrun_review/audit_results.py --campaign EXTRACTED_CAMPAIGN --output ORIGINAL_ARTIFACT_AUDIT.json
```

The campaign should contain `study`, `generated_development`, `generated_heldout`,
`full`, `model_code`, and `bundle/data/tasks.jsonl`. Existing independently retained
qualification/source files can be supplied through `--study`, `--qualification`,
`--code`, and `--tasks`. No file is modified except the requested audit report.

After the original audit passes and the extension archive is released, run:

```text
python postrun_review/audit_results.py --campaign EXTRACTED_CAMPAIGN --extension --original-audit ORIGINAL_ARTIFACT_AUDIT.json --extension-protocol-sha256 9e6ba43fd988b47273c13ae4a5dc569640d210d2178103afaab964ed2bf236c3 --output EXTENSION_ARTIFACT_AUDIT.json
```

Extension mode defaults to `study_v2`, reuses `generated_development`, and reads new
`generated_v2_heldout` execution artifacts. `--extension-code` can supply the wrapper
source directory. It validates the extension freeze, a successful original audit
bound to the exact original result receipt, unchanged original inputs, all fixed
Devstral/development-proposal imports, Qwen request prefixes and exact schema,
synthetic warmup provenance and exclusion, both-cohort effective Qwen gates, and
separate/new/combined cost accounting. Imported observations retain their original
raw provenance and are never counted as new independent observations.

The audit checks source/protocol and public-result hashes, exact source bytes used
for provenance, the 9,456-job universe, 328 generated proposals, raw request and
response binding, terminal JSON parsing, development gates, per-attempt costs and
the $30 ledger. It checks W/A/H input disjointness, committed supplier acquisition,
independent test membership and budgets, saved evidence against reference and
execution records, proposed-code hashes, reserved-outcome labels and enforcement
flags. By default it replays the frozen static selectors on their permitted inputs;
it never executes candidate code. `--skip-policy-replay` is a diagnostic shortcut
and is explicitly reported as a limitation.

`statistical_checks.py` separately recomputes denominators, paired cells, exact
binomial tails, Holm-4 correction, offline source-task means and gate arithmetic.
Its author also wrote the original analysis, so separate implementation is not
independent authorship. The reviewer's manual controls and review are independent.
Published confidence intervals are treated as numerical inputs; this checker does
not certify bootstrap regeneration or population coverage.

An integrity pass means the stated checks passed. It does not mean the method
worked, the study has sufficient novelty, or the paper is ready. Missing terminal
API attempts remain cost reservations. Original ineligible offline/flow rows may
encode unknown outcomes as `other`; interpret unknowns from nullable Y0/Y1 instead
of calling these measured same-state transitions.

`qualification_followup.py` independently recounted the included cohort and
checked the selected helper-namespace caveat. `QUALIFICATION_FOLLOWUP.json` records
549/549 checks: 135 eligible tasks, 34 development and 101 heldout, all included
canonical original and canonical/reference reserved checks passing. The prior
complete qualification audit reports 7,075/7,075 checks and 31/31 coordinator
controls; these are separate checks and should not be presented as extra study
observations.

Run synthetic controls without opening experiment results:

```text
python postrun_review/test_audit_results.py
python postrun_review/test_statistical_checks.py
python postrun_review/test_cross_implementation.py
python postrun_review/test_extension_checks.py
```

The original namespace issue is described in
`NAMESPACE_COMPATIBILITY_LIMITATION.md`. Frozen code/cohort membership is retained.
