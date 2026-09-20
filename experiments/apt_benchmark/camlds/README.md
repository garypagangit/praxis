# CAM-LDS: independent scenario-family evaluation preparation

## Source and role

[Landauer et al. (2026), *International Journal of Information Security*, 25, 148](https://doi.org/10.1007/s10207-026-01318-x) is the peer-reviewed source. The pinned [Zenodo version 18861762](https://zenodo.org/records/18861762) supplies raw scenario archives under CC-BY 4.0. It contains 34 executions from seven scenario families. Its ordinary-user workload is absent; logs combine attack manifestations and idle system activity. This preparation uses complete defender audit files from the raw scenario archives, not the filtered manifestation exports. Those exports use corpus-wide filtering and can duplicate records across technique groupings. [Author artifact documentation](https://github.com/ait-aecid/attack-manifestations-interpretation/tree/44028d8bd40a4a1d8bbbc6ee33261d47cb433827).

This is an independent dataset source for a **qualified manifestation-window recognition proxy**. It does not provide independently verified malicious-event labels or realistic benign false-alert rates. It cannot independently confirm all three CasinoLimit targets across enough scenario families.

## Frozen before preparation and model fitting

The allocation is the SHA256 order of `camlds-robustness-v2:` plus each family with author T1105 labels. The first two families train; the next three supply development, calibration, and test respectively. No feature or model outcomes influenced this rule.

| Role | Families | Source runs |
|---|---|---:|
| Fit | 3, 6 | 11 |
| Development | 2 | 2 |
| Calibration | 4 | 1 |
| Test | 1 | 18 |
| Reserved, outside the experiment | 5, 7 | 2 |

There is only **one calibration and one test family**. The 18 test variants repeat one family and do not create 18 independent attack families. Confidence statements must respect that limitation.

Source label metadata permits T1105 (transfer of attack tools) in five families. T1068 appears only in family 1, and T1548 in families 1 and 4. Therefore only **T1105** is eligible for this family-separated follow-up; the other two are reported as unsupported for this design. Actual audit/interval join support is checked separately, before fitting.

## Prediction unit and supervision

1. Reconstruct audit events by scenario, host, timestamp, and original audit serial number. Preserve record-type fragments separately. Deduplicate only identical raw fragments of the same event.
2. On each host, choose the first source event ordered by `(timestamp, event_id)` in each fixed ten-second UTC bin. Choose this roster **before consulting any interval labels**. Bins are never anchored to attack onset or step boundaries.
3. A roster event is eligible for supervision only when its timestamp belongs to an author-defined manifestation window. The endpoint rule is `start <= timestamp < end`, matching the source audit extraction. We use the union of source technique labels where windows overlap; that is an explicit local convention. The author extractor rejects overlapping non-collectd windows rather than applying this union.
4. All other events within the complete replay envelope remain context. Unannotated events are unknown, not benign negatives. Other annotated intervals are negatives only for the specific target technique.
5. Missingness and delay do not change the frozen target roster. An entirely unobserved target remains a missed recognition opportunity. This remains an offline source-event roster, not an online trigger for invisible activity.

The source `attack_times.csv` has 904 interval occurrences and 883 distinct step identifiers. Repeated identifiers denote repeated executions; the adapter preserves each interval separately and verifies its technique set against the author's pinned `labels.json`.

**Label meaning:** a positive is membership in an **author-designated T1105 manifestation window**. The pinned extraction script begins windows at command time minus two seconds and ends them at output completion plus four seconds, with manual start/end shifts and sleep-based extensions. These are not literal active-step times. The queried event need not transfer an attack tool. Scenario windows apply across all defender hosts, so unrelated or idle activity on another host can inherit window membership. This target definition differs from CasinoLimit's process-annotation onset proxy; do not pool or directly compare absolute F1 values. No before-impact or early-warning claim follows from it. [Pinned author window construction and extraction](https://github.com/ait-aecid/attack-manifestations-interpretation/blob/44028d8bd40a4a1d8bbbc6ee33261d47cb433827/extract_attack_logs.py#L583).

## Causal features and information excluded

The existing Casino lexical audit representation is reused, followed by fixed testbed-identity masking. Only local raw-record fields determine a fragment's text and entity links. The adapter passes neither attacker execution logs nor stage labels, source step identifiers, interval boundaries, host identity, or scenario identity into feature text. Technique-marked audit rule keys are excluded by the lexical allowlist. Fragment-local links remain separate so deleting a record cannot expose its hidden process identifier through another record.

Retained context spans the complete earliest-label-minus-120-seconds to latest-label-end envelope. This removes old machine-image logs that cannot precede any eligible query by at most 120 seconds. The cutoff is 120 seconds before the first supervised time, so it cannot truncate the first event in any supervised ten-second bin. Replay applies the stricter per-query causal horizon. Timestamps substitute for native record arrival, which is unmeasured. All injected delays are synthetic; later source events must remain unavailable to an earlier query even when its decision waits.

## Acquisition and execution

Private data root: `C:/w/apt_benchmark_data_20260920/camlds_v1`.

```powershell
python -m experiments.apt_benchmark.camlds.acquire --output C:/w/apt_benchmark_data_20260920/camlds_v1 --all --selected-audit-members --workers 3
python -m experiments.apt_benchmark.camlds.events --source C:/w/apt_benchmark_data_20260920/camlds_v1 --output C:/w/apt_benchmark_data_20260920/camlds_v1/prepared
python -m unittest experiments.apt_benchmark.tests.test_camlds -v
```

Selected ZIP members are CRC32 checked and SHA256 hashed. Archive publisher checksums are recorded; whole-archive checksum verification is **not** claimed for range-acquired members. No downloaded executable or dataset attack script is run. Raw logs, private labels, event streams, and model predictions stay outside Git.

`SELECTION.json` is written before target support counts. `MANIFEST.json` binds prepared events, adapter code, author label sources, split membership, source-member receipts, channel counts, query coverage, and per-target support. Existing evidence outputs are never overwritten. The root robustness-v2 protocol controls actual model arms and inference; this adapter does not fit or score a model.
