# Cloud Prompt Template

Use this as the first prompt when launching a fresh cloud run.

```text
This is a fresh cloud run for the Praxis APT experiment repo.

First read:
- CLOUD_HANDOFF.md
- configs/experiment_cloud_handoff_registry.json
- reports/EXPERIMENT_FINAL_EVALUATION_20260511.md
- reports/EXPERIMENT_DASHBOARD.md
- configs/dataset_registry.json

Treat local data/runs/checkpoints as absent unless fetched from the S3 prefixes in the registry or the experiment manifest. Preserve negative results and hold decisions. Do not move thresholds after seeing outcomes.

Experiment id: <replace-with-experiment-id>

Task:
<replace-with-specific-task>

Before running anything expensive, tell me:
- which lightweight evidence files you found
- which data/artifact prefixes you need
- whether the experiment is positive, negative, hold, blocked, later, or shelved according to the registry
- the exact command you intend to run
```
