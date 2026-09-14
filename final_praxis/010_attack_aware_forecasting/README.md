# Final Praxis 010 - Attack-aware forecasting

Current gate: **Q1 qualification PASS: all three actual model modes and CPU/source/data checks completed.** Advance only to a new prospective development experiment; the proposed novel defense remains untested. No heldout cyber efficacy or novel defense has been established.

The actual TimesFM 3 run completed in 71.03 seconds, with 0.12847-second median forecast-batch latency, 2.464 GiB peak GPU allocation, and zero repeated-forecast difference. On the fixed three-channel synthetic +2 shift, it alarmed on 3 of 256 shifted observations and on none after the first 32 shifted observations. This demonstrates adaptation on one development probe; it is not malicious-intent detection or a validated defense. Its [receipt and raw forecasts](completed_qualification/new3/QUALIFICATION_RECEIPT.json) passed [11/11 artifact checks](completed_qualification/NEW3_PARTIAL_AUDIT.json).

The original TimesFM 2.5 run completed all 20 seeds in 2,155.84 seconds. Its 8,000 admission records and 4,800 endpoint rows passed the [final 51/51 artifact checks](completed_qualification/FINAL_ARTIFACT_AUDIT.json) together with TimesFM 3 and calibration. All policies detected at least one point in all 20 attack episodes, but pointwise persistence and false alarms differed:

| Policy | Attack alarms / 600 | Clean alarms / 600 | Episodes / 20 |
|---|---:|---:|---:|
| Historical oracle blend | 200 | 3 | 20 |
| Rolling context | 138 | 3 | 20 |
| Alarm-only blend | 200 | 3 | 20 |
| Literal freeze | 246 | 64 | 20 |

These are fixed development simulations, not novel-defense results. Literal freezing increased attack alarms and also increased clean false alarms. Historical and alarm-only blending match on these endpoint totals; this does not establish equivalence beyond these simulations. The [complete original 2.5 evidence](completed_qualification/original25/QUALIFICATION_RECEIPT.json) retains every assigned endpoint and intervention.

![TimesFM 3 adapts to a predictable development-only shift](completed_qualification/figures/new3_persistence.png)

This candidate asks whether a detector can retain persistent-attack evidence while recovering after legitimate changes. Published context protection and adaptive calibration already exist. The literature-grounded [qualification protocol](QUALIFICATION_PROTOCOL.md), [precompute freeze](PROTOCOL_FREEZE.json), and [source audit](SOURCE_AUDIT.md) define the narrower work needed before investing in a new method.

- [CPU receipt](results/cpu/CPU_QUALIFICATION_RECEIPT.json): 20 independent observer simulations match released code with maximum absolute difference 0; 600 attack and 600 matched clean positions retained. All 10 predetermined persistence-control seeds pass.
- [Runtime controls](results/RUNTIME_CONTROLS.json): 22/22 synthetic/source controls pass, including causal contexts, horizon alignment and W1ACAS future-suffix checks. No pretrained model was loaded for these tests.
- [Data accessibility](results/DATA_ACCESSIBILITY.json): HAI 21.03 training1 hash verified, 216,001 chronological rows; exact shipped NAB example hash verified, 4,031 rows. No HAI test outcomes opened.
- [HAI metadata scope deviation Q1-D1](completed_qualification/HAI_METADATA_SCOPE_DEVIATION.json): after model execution began, an **unpreregistered expansion** beyond the train1-only access plan inspected timestamps from all eight public compressed files, completing at 14:35:39 UTC. Header names/counts were read, but sensor and attack-label values were not parsed or summarized. The [timestamp ledger](completed_qualification/HAI_TIMESTAMP_AUDIT.json) and audit code are now hash-frozen; prior frozen receipts remain unchanged. The benchmark filenames do **not** imply chronological order. Further HAI access has stopped. Any future date-based splits must cite this deviation/ledger and be frozen before sensor or label analysis.
- [GPU runbook](GPU_RUNBOOK.md): executable original TimesFM 2.5, native TimesFM 3 and Chronos/W1ACAS modes; root controls the shared bounded AWS runtime.
- [Cloud setup review](completed_qualification/setup/CLOUD_SETUP_REVIEW.json): all 29 downloaded asset hashes match pinned identities; 22/22 controls also passed in the isolated cloud runtime. Exact installed packages and downloaded-file receipts accompany it.
- [Runtime explanation](postrun/ORIGINAL25_RUNTIME_INTERPRETATION.md): why the original 2.5 configuration processes more work than its one-step/three-sensor interface suggests. The completed original run stayed within its 40-minute cap; final audited raw records supersede intermediate stdout observations.
- [Artifact auditor](postrun/audit_qualification.py): validates source/file identities, all assigned row universes, intervention arithmetic and report numerators without new inference; [11/11 current synthetic controls](postrun/AUDITOR_CONTROLS_A2.json) passed. A [source-review correction](postrun/AUDITOR_CORRECTION_A2.json), made before original 2.5 artifact inspection, preserves float32 blend arithmetic at the unchanged tolerance; the initial 7/7 control receipt remains archived.

Local reproduction, using Python with NumPy/SciPy/Pandas/Torch/Transformers installed:

```text
python code/prepare_assets.py --cache EXTERNAL_CACHE
python code/cpu_pilot.py --cache EXTERNAL_CACHE --output NEW_CPU_RESULTS
python code/test_runtime_controls.py --cache EXTERNAL_CACHE --output NEW_CONTROL_RECEIPT.json
```

To repeat HAI accessibility, download the pinned `hai-21.03/train1.csv.gz` to EXTERNAL_CACHE/hai/hai-21.03 first, then run `python code/audit_data.py --cache EXTERNAL_CACHE --output NEW_DATA_RECEIPT.json`. Its exact upstream URL/blob/hash is in SOURCE_MANIFEST.json and results/DATA_ACCESSIBILITY.json. Full third-party source repositories, pretrained weights and HAI raw files stay outside Git. Retained calibration arrays may include derived NAB/TSB-AD observations and anomaly labels; their [data attribution and license notices](completed_qualification/licenses/NOTICE.md) accompany the release. Public-license/source restrictions remain applicable. The original June repository has no explicit code license, so this branch distributes retrieval instructions and our wrapper rather than copies of those scripts.

The Chronos/W1ACAS implementation completed in 235.82 seconds on the exact 4,031-row public NAB example. At the fixed alpha 0.01 threshold, 21/343 anomalous positions and 39/2,681 normal positions alarmed among 3,024 scored positions. This qualifies the implementation; it is a weak pointwise detection result on this development example, not reproduction of the paper's optimized aggregate performance. The pre-inference A1 amendment preserves the upstream requested-one/effective-two epoch mismatch.

A [separately authored independent review](completed_qualification/independent_review/INDEPENDENT_010_RESULTS_REVIEW.json) also passed 20,026/20,026 checks. Its source and a local replay wrapper accompany the evidence; it does not regenerate model forecasts, adaptive-optimizer p-values, latency measurements or allocator traces.

The [completed qualification summary](completed_qualification/QUALIFICATION_SUMMARY.md) and [release manifest](completed_qualification/RELEASE_MANIFEST.json) bind actual raw evidence, safe model logs, attribution, source identities, and all deviations. A tentative constrained context-update proposal needs a new frozen development protocol with benign-recovery and false-alarm limits. Bounded admission mass alone does not bound a nonlinear forecast; any mathematical influence guarantee needs explicit sensitivity or perturbation assumptions.

The historical June code uses known attack onset when enabling prediction blending. That oracle path is reported separately from deployable alarm-only policies. The calibration demo tunes a label-informed PA-F1 threshold; our fixed-threshold evaluation change is disclosed. A successful qualification permits further development, not a claim of novelty or a replacement for a completed paper.
