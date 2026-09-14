# 009 GPU qualification handoff

The campaign coordinator controls AWS, the two-hour timeout and host shutdown. No package installation belongs in the shared local environment.

Use Python 3.11 in an isolated CUDA environment. A tested source-version combination to install is `transformers==5.17.0`, `peft==0.20.0`, `bitsandbytes==0.50.2`, `safetensors==0.8.0`, plus `accelerate>=0.27`, `packaging`, `rich`, `pydantic>=2`, and `pyyaml`. PyTorch must provide CUDA and hardware BF16; upstream requires at least 2.6. Select a wheel compatible with the host driver, then retain its exact version and complete `pip freeze`. The installed local 2.11 CPU environment is only for CPU controls. These import paths do not require TRL, datasets, a tokenizer download, or the Soup CLI installer. Install no vendor executable/setup script; use the pinned source through `--source`.

Fetch the exact [Soup archive](https://codeload.github.com/MakazhanAlpamys/Soup/tar.gz/b0a6338232f47d7ffabac90deb810728c2e179b4), require SHA256 `789c69de0ae95410f0847a29b8671513b16225fd60866b9acb5da0715108cf6f`, and extract outside the repository. `SOURCE_MANIFEST.json` separately checks the inspected source files before imports. Preserve the full vendor archive hash with the run receipt.

From this directory, with paths set by the coordinator:

```bash
python cpu_controls.py --source "$SOUP_SOURCE" --work "$RUN_CACHE/cpu" --output "$RUN_RESULTS/CPU_CONTROLS.json"
python gpu_qualification.py --source "$SOUP_SOURCE" --work "$RUN_CACHE/gpu" --output "$RUN_RESULTS/gpu"
```

The GPU command has no model/data network dependency. It generates its tiny checkpoint and runs 16 numerical comparisons plus four corrupted-gradient controls. Only a complete numerical pass permits nine counterbalanced timing blocks (three source arms, three rounds, two warmups and three recorded steps each). `qualification_pass` denotes numerical correctness; `instrumentation_complete` additionally requires all timing blocks. A nonzero process exit or incomplete fields stop advancement. Run under the coordinator's external wall-clock timeout; expected model execution is minutes, not hours.

`GPU_QUALIFICATION.json` preserves errors and assigned counts. Per-arm safetensors retain actual logits, gradients and adapter updates for independent replay. Tiny-model warm-cache timing establishes overhead only. It does not reproduce the paper's 8B quality result, Windows cold-disk behavior, training throughput, or laptop hardware. A future pretrained-data test requires a separately fixed adapted split, model license and quality endpoint.

The staging integration currently refuses large embedding/head pools instead of pretending their ownership has been tested. Its explicit byte bound covers owned staging tensors; it is not total process RAM or page-cache usage. Runtime's inherited disk `pinned` flag describes the original tier; the additional staging `pin` field records pinned staging allocation. Inspect both and the measured process/GPU peaks.
