# PX-057 GPU Gate 1

This job runs the frozen 50-question, six-round Qwen2.5-7B-Instruct capability pilot.

It is a readiness gate, not the final H1-H4 experiment. Promotion requires:

- usable exact-answer accuracy;
- complete six-round traces;
- at least one observable correct-to-wrong event, or a documented zero-event boundary;
- manual audit of a random sample of extraction/scoring decisions;
- no changes to the frozen dataset hash or sample seed.

Run from the repository root:

```bash
bash cloud_jobs/px057_adaptive_stopping_20260723/run_on_gpu.sh
```

The GPU machine must have outbound access to Hugging Face and enough storage for the model.
