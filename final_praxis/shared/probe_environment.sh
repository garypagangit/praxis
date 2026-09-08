#!/usr/bin/env bash
set -eu
find /opt/praxis/venvs -maxdepth 3 -name pyvenv.cfg -print | head -20
find /opt/praxis/hf_cache -maxdepth 4 -type d -name snapshots -print | head -15
find /opt/praxis/hf_cache -maxdepth 5 -type d -name 'a09a35458c702b33eeacc393d103063234e8bc28' -print | head -5
ls -d /opt/pytorch/* /home/ubuntu/.cache/huggingface/hub/models--Qwen* /opt/conda/envs/* 2>/dev/null || true
python3 -c 'import importlib.util; print({x:bool(importlib.util.find_spec(x)) for x in ["torch","transformers","accelerate","boto3"]})'
for py in /opt/praxis/venvs/*/bin/python; do
  "$py" -c 'import torch,transformers,sys; print(sys.executable, torch.__version__, transformers.__version__)' 2>/dev/null || true
done
