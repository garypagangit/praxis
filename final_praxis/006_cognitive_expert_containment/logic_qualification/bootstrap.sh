#!/bin/bash
set -euo pipefail
runroot="$1"
scratch=/mnt/praxis-20260912-005
case "$runroot" in "$scratch"/fp006-logic-*) ;; *) exit 70;; esac
mountpoint -q "$scratch"
export TMPDIR="$scratch/tmp006logic"
export HF_HOME="$scratch/hf006logic"
export HF_HUB_CACHE="$HF_HOME/hub"
export XDG_CACHE_HOME="$scratch/xdg006logic"
export PIP_CACHE_DIR="$scratch/pip_cache"
export TOKENIZERS_PARALLELISM=false
export HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_DISABLE_XET=1
export PYTHONUNBUFFERED=1
mkdir -p "$TMPDIR" "$HF_HOME" "$XDG_CACHE_HOME" "$PIP_CACHE_DIR" "$runroot/outputs"
study="$runroot/code/final_praxis/006_cognitive_expert_containment/logic_qualification"
python3.10 -m venv "$scratch/venv006logic"
python="$scratch/venv006logic/bin/python"
# Audit always runs on an inference/setup failure and can never promote an incomplete job.
finish_audit() {
  code=$?
  set +e
  "$python" "$study/audit.py" --run-dir "$runroot/outputs" --data "$study/data.json" --protocol "$study/protocol.json" --technical "$runroot/outputs/technical.json" --report-dir "$runroot/outputs/audit"
  auditcode=$?
  if [ "$code" -eq 0 ] && [ "$auditcode" -ne 0 ]; then code=$auditcode; fi
  exit "$code"
}
trap finish_audit EXIT
"$python" -m pip install --disable-pip-version-check torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
"$python" -m pip install --disable-pip-version-check -r "$study/requirements.txt"
"$python" -m pip freeze > "$runroot/outputs/python_environment.txt"
"$python" -m unittest discover -s "$study" -p 'test_*.py' -v
"$python" "$study/run_study.py" --out "$runroot/outputs" --artifacts "$runroot/artifacts" --preflight-only > "$runroot/outputs/offline_preflight.json"
"$python" "$study/run_study.py" --out "$runroot/outputs" --artifacts "$runroot/artifacts"
