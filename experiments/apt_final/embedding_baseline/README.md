# Recognizing unusual behavior with frozen graph models

This follow-up tests whether a better anomaly score can recover useful detections from the already trained models. It compares nearest-neighbor distances in frozen GIN/MLP embeddings and local features, using separate normal calibration data. Previous reconstruction and Isolation Forest results remain paired controls.

The study is development work prompted by an inspected negative result. Nearest-neighbor anomaly scoring is existing research, and this comparison does not establish novelty or reproduce the full MAGIC architecture.

## Completed result

The GPU/CPU scoring run and independent audit completed. **THEIA graph-model recall rose from 0.043% to 90.334%**, with mean F1 0.8324 and FPR 2.021%. CADETS was unstable, and no new fixed arm passed every prospective readiness requirement. The low-degree checker also discarded useful graph detections. [Full report and per-repeat evidence](results/gpu_scoring_20260920/REPORT.md).

The next experiment should separate reference-bank variability from encoder variability and validate normal-score stability on explicitly reserved graphs before designing a new checker. [Follow-up design and literature](results/gpu_scoring_20260920/FOLLOWUP_LITERATURE_AND_DESIGN.md). [AWS closeout](results/gpu_scoring_20260920/AWS_CLOSEOUT.json).

## Design and execution

- [Prospective protocol](PROTOCOL.md), [configuration](config.json), and [literature review](LITERATURE_AND_DESIGN.md).
- [Hash-bound predecessor inventory](PREDECESSOR.json); private arrays and original trained checkpoints stay outside Git.
- `engine.py` extracts frozen bottlenecks; `scoring.py` implements exact CPU nearest-neighbor search.
- `runner.py` freezes training-only reference banks and normal calibration before this run's evaluation-label access.
- `launch.py` reuses the existing bounded AWS controller with an independent stop schedule and final shutdown verification.

For a new run, commit operative files first, create a new registration with `provenance register --data-dir ... --prior-dir ... --registration ...`, then commit that registration. Use `launch --settings ... --data-dir ... --prior-dir ... --registration ...`. All module commands are under `python -m experiments.apt_final.embedding_baseline`. The private predecessor directory must exactly match the declared hashes; each output directory must be new.

GPU extraction and CPU scoring are measured separately. No comparative hardware speedup, deployment readiness, untouched confirmation or new algorithm is claimed.
