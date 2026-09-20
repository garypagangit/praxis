# Recognizing dangerous steps with incomplete audit evidence

This suite asks whether a model can recognize a dangerous source-labeled action
when related log records disappear or arrive late. It is a development test of
existing controls, not a claim that reliable APT recognition or novelty has
already been established.

## Three experiments

| Experiment | Question | Fixed comparisons |
|---|---|---|
| E1: Meaning and earlier activity | Does the preceding activity help interpret an event? | Generic event text, typed semantic event text, and semantic event plus up to 32 linked events from the prior 120 seconds. |
| E2: Missing records | Does training on incomplete evidence help? | The same context classifier, clean-trained or trained on equally weighted clean/25%/50% record-loss views. Test 25%, 50%, 75% record loss, a 60-second missing-history stress test, and absent command-record types. |
| E3: Delayed records | What accuracy/coverage is available by each deadline? | Command records delayed 30 or 120 seconds; score at common deadlines of 0, 30 and 120 seconds. Waiting the full injected delay restores clean evidence by construction. |

All arms use logistic regression with fixed parameters and two 32,768-dimensional
hashed text blocks. The augmented arm has the same total training weight as the
clean arm. Fitted models and clean-calibration thresholds stay fixed during the
stress tests. Three deterministic removal seeds measure corruption variability,
not independent campaign replication.

## Data and literature

- **AIT-LDS** supplies already-qualified development logs. Its capture is from
  2022, with new packaging in 2026; it is not presented as a recent attack
  capture. Audit regrouping yields a new event-level task focused on escalation.
- **CasinoLimit, RAID 2025**, supplies the recent second dataset. The frozen
  selection uses all 114 author-annotated executions, split 60/18/18/18 by a
  fixed hash order. The initial 24-instance feasibility sample had insufficient
  target support, so the cohort was expanded before any Casino model fitting.
  Source process-technique annotation onsets define eligible targets;
  other nearby audit records provide prior context. Targets are T1068, T1548
  and T1105, subject to both-class support. Other annotated techniques are
  negative labels for a target; unannotated activity is not called benign.
- **CAM-LDS, published August 2026**, is the recommended later scenario-diversity
  source. It has seven scenario families and 34 variants. Its raw per-scenario
  logs still require a separate temporal-label and causal-feature adapter. It
  is not a dataset fitted by this first suite.

The [source-backed literature review](../docs/ROBUSTNESS_LITERATURE.md) links the
dataset papers, StageFinder, IMPROV, a simple-model comparison, missing-modality
learning and provenance augmentation. It explains the existing overlap: neither
adding history, dropout training, buffering nor substituting Qwen establishes
novelty on its own.

## What prevents inflated scores

- Predictions use only visible fragment fields. Hidden process identifiers
  cannot retrieve history. Future source events and equal-time siblings cannot
  enter the history, even when the decision deadline is later.
- Original evaluation targets remain in all denominators. A target with no
  surviving observed fragment receives no alarm and remains a positive miss.
- Event-time is separated from synthetic arrival time. Actual ingestion
  latency, online trigger behavior and before-impact warning are not measured.
- Random loss is shared across all arms. Record-type loss is not described as
  a physical sensor outage. The 60-second history stress test is target-relative.
- No injected true deletion mask is a model input. Record counts/types describe
  observations, not knowledge that a silent sensor failed.
- Run-specific precision, recall, F1, ROC-AUC, average precision, confusion
  counts and coverage are saved. The calibration budget is 1% other-label flags;
  actual test burden may exceed it and is reported without a risk guarantee.
- CasinoLimit's repeated challenge, possible repeat players and inherited
  process labels limit generalization. Neither recent dataset supplies a
  realistic ordinary-user workload for operational false-positive validation.

## Reproduce

Use the benchmark's pinned Python environment. Raw data and models stay outside
Git. Output directories for the runner must be new to preserve earlier results.

```powershell
python -m unittest discover -s experiments/apt_benchmark/tests -v
python -m experiments.apt_benchmark.robustness.ait_events --source-root C:/w/apt_benchmark_data_20260920/ait/partial_lds --protocol experiments/apt_benchmark/protocol.json --output C:/w/apt_benchmark_data_20260920/robustness_new/ait
python -m experiments.apt_benchmark.robustness.run --events C:/w/apt_benchmark_data_20260920/robustness_new/ait/EVENTS.jsonl --manifest C:/w/apt_benchmark_data_20260920/robustness_new/ait/MANIFEST.json --dataset ait --output C:/w/apt_benchmark_data_20260920/robustness_new/ait_run
python -m experiments.apt_benchmark.robustness.casino_events --root C:/w/apt_benchmark_data_20260920/robustness_new/casino --acquire --output C:/w/apt_benchmark_data_20260920/robustness_new/casino/casino_events.jsonl
python -m experiments.apt_benchmark.robustness.feature_cache --events C:/w/apt_benchmark_data_20260920/robustness_new/casino/casino_events.jsonl --manifest C:/w/apt_benchmark_data_20260920/robustness_new/casino/casino_events.receipt.json --protocol experiments/apt_benchmark/robustness/casino_protocol.json --output C:/w/apt_benchmark_data_20260920/robustness_new/casino_features
python -m experiments.apt_benchmark.robustness.run --events C:/w/apt_benchmark_data_20260920/robustness_new/casino/casino_events.jsonl --manifest C:/w/apt_benchmark_data_20260920/robustness_new/casino/casino_events.receipt.json --dataset casino --protocol experiments/apt_benchmark/robustness/casino_protocol.json --feature-cache C:/w/apt_benchmark_data_20260920/robustness_new/casino_features --output C:/w/apt_benchmark_data_20260920/robustness_new/casino_run
```

See the operative [protocol](protocol.json), [replay](replay.py), [runner](run.py)
and per-run pre-fit receipts. The development split is reserved; no search over
its results selected a favorable model or corruption seed in this suite.

The full Casino corpus is processed one execution at a time. The feature cache
uses the same causal replay and binds its input/protocol/code/matrix hashes; it
changes memory use without changing the experiment's information or target set.
