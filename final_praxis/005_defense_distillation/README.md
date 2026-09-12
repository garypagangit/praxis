# Final Praxis 005: benign-distillation defense retention

This is a preregistered **feasibility gate**, using a published 3B defense and actual benign teacher generation, three independent LoRA adaptations, five held-out evaluations and two semantic safety judges. It does not develop or execute a refusal-removal attack. A completed pilot cannot establish novel abliteration resistance.

Protocol: [PREREGISTRATION.md](PREREGISTRATION.md). Original freeze `bb5f372`; pre-outcome interpretation/path corrections [AMENDMENTS.md](AMENDMENTS.md), latest freeze `ec18486`. Immutable public models/data and licensing metadata: [sources.lock.json](sources.lock.json). `protocol.sha256` fingerprints canonical LF versions of the preregistration, settings and source lock. Do not rerun `pin_sources.py` into this frozen protocol.

## Runtime

Use one A10G 24GB GPU, Python 3.11, and at least 60GB free disk. No bitsandbytes, FlashAttention, custom model Python or external judge API is required. Models load with Safetensors and `trust_remote_code=False`. All model IDs/revisions are pinned and ungated. The Qwen parent has a research license; do not redistribute checkpoints without checking applicable terms.

In a fresh Linux virtual environment:

```bash
python3.11 -m venv /opt/praxis/fp005-venv
/opt/praxis/fp005-venv/bin/python -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
/opt/praxis/fp005-venv/bin/python -m pip install -r final_praxis/005_defense_distillation/requirements.txt
export HF_HOME=/opt/praxis/fp005-hf-cache
export TOKENIZERS_PARALLELISM=false
/opt/praxis/fp005-venv/bin/python -m pytest final_praxis/005_defense_distillation/tests -q
/opt/praxis/fp005-venv/bin/python final_praxis/005_defense_distillation/run.py prepare --out /opt/praxis/fp005-run/outputs
/opt/praxis/fp005-venv/bin/python final_praxis/005_defense_distillation/run.py all --out /opt/praxis/fp005-run/outputs
```

Root coordinates the actual AWS launch and host shutdown timer after all experiment preregistrations freeze. The `all` command has an eight-hour subprocess budget and launches each GPU stage in a fresh process to release memory. The common cloud supervisor can wrap this command, enforce its own shorter wall-time limit, and copy receipts to the campaign's private S3 prefix. Adapters live under `outputs/checkpoints/` so that supervisor's checkpoint allowlist includes them. Dependency installation is separate from the experiment's inference budget; the host shutdown timer bounds both.

`prepare` downloads public data only and runs on CPU. It records SHA-256 receipts, schema checks, duplicate-removal attrition, selected IDs and immutable prepared-file hashes. It never starts inference. Model stages explicitly require CUDA. Estimated cache is approximately 35–45GB, plus Python/Torch and output artifacts; actual available disk and GPU memory must be checked on the host. The models load sequentially in BF16 on A10G, including the independent 7B judge.

## Outputs and recovery

Each stage also runs separately: `distill`, `train --arm base_kd|er_kd|er_replay`, `evaluate --arm base|er|base_kd|er_kd|er_replay`, `judge --judge qwen|md`, `report`. Use the same `--out` directory. Completed teacher/evaluation/judgment records resume by immutable example identity. Incomplete training restarts from its original public checkpoint and logs a new attempt ID. Training has no outcome-dependent checkpoint selection.

- `prepared.json`: source receipts, attrition, frozen test IDs and hashes.
- `teacher_complete.json`: verified teacher counts and generated training-data hash; no gold-answer fallback.
- `checkpoints/*/train_complete.json`: actual nonzero adapter change, steps, losses, exposure/token counts, peak GPU memory and adapter-file hashes.
- `summary.json` and `REPORT.md`: automated provisional results, paired prompt-bootstrap intervals, judge disagreement, invalidity and truncation. The judge envelope is **not a bound on true harmfulness**.
- `manual_review_blinded.json`: deterministic response review queue; arm mapping is separately stored in `manual_review_key.json`. Review cannot overwrite original automated labels.

Raw benchmark prompts, generations and review text remain ignored run artifacts. Status logs and the human-facing report do not print harmful completions. `complete_nonrefusal` means a valid, complete response labeled non-refusal; it does not measure answer correctness. Math accuracy separately checks a held-out answer key. The fixed 256-token math budget may reduce accuracy or teacher eligibility; report it as designed instead of silently extending it.

If teacher acceptance is below 32, eligible safety examples below 32, updates are zero, judges have more than 5% invalid assessments, or arms are incomplete, report a technical failure. If the small pilot shows no measurable retention problem or ordinary replay resolves it, the complex-defense idea has not earned more investment. All scientific conclusions remain conditional on the preregistered manual check and one-seed limitations.
