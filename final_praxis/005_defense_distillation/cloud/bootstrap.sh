#!/bin/bash
set -eu
scratch="$1"
run_root="$2"
case "$scratch" in /mnt/praxis-20260912-005) ;; *) exit 70;; esac
case "$run_root" in "$scratch"/fp005-*) ;; *) exit 71;; esac
export TMPDIR="$scratch/tmp"
export HF_HOME="$scratch/hf_cache"
export XDG_CACHE_HOME="$scratch/xdg_cache"
export PIP_CACHE_DIR="$scratch/pip_cache"
export TOKENIZERS_PARALLELISM=false
export HF_HUB_DISABLE_TELEMETRY=1
export PYTHONUNBUFFERED=1
mkdir -p "$TMPDIR" "$HF_HOME" "$XDG_CACHE_HOME" "$PIP_CACHE_DIR"
code="$run_root/code"
study="$code/final_praxis/005_defense_distillation"
python3.10 -m venv "$scratch/venv"
python="$scratch/venv/bin/python"
"$python" -m pip install --disable-pip-version-check torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
"$python" -m pip install --disable-pip-version-check -r "$study/requirements.txt"
mkdir -p "$run_root/outputs"
"$python" -m pip freeze > "$run_root/outputs/python_environment.txt"
"$python" -m pytest "$study/tests" -q
"$python" -c 'import torch,json; assert torch.cuda.is_available(); assert torch.cuda.get_device_properties(0).total_memory >= 22_000_000_000; print(json.dumps({"event":"cuda_qualified","torch":torch.__version__,"gpu":torch.cuda.get_device_name(0),"bf16":torch.cuda.is_bf16_supported()}))'
exec "$python" "$study/run.py" all --out "$run_root/outputs"
