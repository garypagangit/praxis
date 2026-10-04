#!/bin/bash
set -euo pipefail
input_url="$1"
input_sha="$2"
output_url="$3"
run_name="$4"
base=/opt/dlami/nvme
test -d "$base"
mkdir -p "$base/$run_name"
cd "$base/$run_name"
mkdir -p outputs/data
publish() {
  rc=$?
  echo "$rc" > outputs/WORKER_EXIT.txt
  tar -czf result.tar.gz outputs
  sha256sum result.tar.gz | cut -d ' ' -f1 > result.sha256
  aws s3 cp result.tar.gz "$output_url/result.tar.gz" --only-show-errors || true
  aws s3 cp result.sha256 "$output_url/result.sha256" --only-show-errors || true
  if test -n "${ollama_pid:-}"; then kill "$ollama_pid" || true; fi
  exit "$rc"
}
trap publish EXIT
nvidia-smi > outputs/gpu.txt
aws s3 cp "$input_url" bundle.tar.gz --only-show-errors
echo "$input_sha  bundle.tar.gz" | sha256sum -c -
tar -xzf bundle.tar.gz
cp inputs/receipts.json inputs/narrative_inputs.json outputs/data/
python3 -m venv --system-site-packages venv
venv/bin/python -m pip install requests > outputs/install.log 2>&1
cache=/opt/praxis/ollama-017
mkdir -p "$cache"
df -h > outputs/disk.txt
if ! test -x "$cache/bin/ollama"; then
  curl -fL --retry 2 https://github.com/ollama/ollama/releases/download/v0.17.0/ollama-linux-amd64.tar.zst -o ollama.tar.zst
  tar --zstd -xf ollama.tar.zst -C "$cache"
fi
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_MODELS="$cache/models"
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_KEEP_ALIVE=30m
ollama_cmd() { sudo -H --preserve-env=OLLAMA_HOST,OLLAMA_MODELS,OLLAMA_NUM_PARALLEL,OLLAMA_KEEP_ALIVE "$cache/bin/ollama" "$@"; }
ollama_cmd serve > outputs/ollama.log 2>&1 &
ollama_pid=$!
for attempt in $(seq 1 30); do curl -sf http://127.0.0.1:11434/api/version > outputs/ollama_version.json && break; sleep 1; done
venv/bin/python -c 'import json; assert json.load(open("outputs/ollama_version.json"))["version"]=="0.17.0"'
ollama_cmd pull qwen2.5:3b > outputs/model_pull.log 2>&1
curl -fsS http://127.0.0.1:11434/api/generate -d '{"model":"qwen2.5:3b","prompt":"Return JSON: {\"status\":\"ready\"}","format":"json","stream":false,"options":{"temperature":0,"num_predict":24}}' > outputs/warmup.json
curl -fsS http://127.0.0.1:11434/api/ps > outputs/gpu_allocation.json
venv/bin/python -c 'import json; a=json.load(open("outputs/gpu_allocation.json")); assert any(m.get("size_vram",0)>0 for m in a["models"]), "No GPU allocation"'
export PRAXIS_DATA="$PWD/outputs/data"
export PRAXIS_RESULTS="$PWD/outputs"
export PRAXIS_MODEL_DIGEST=357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b
timeout --signal=TERM --kill-after=10s 900 venv/bin/python -u run_language.py > outputs/run.log 2>&1 &
worker_pid=$!
while kill -0 "$worker_pid" 2>/dev/null; do
  tail -c 2500 outputs/run.log > outputs/progress.txt
  timeout 10 aws s3 cp outputs/progress.txt "$output_url/progress.txt" --only-show-errors || true
  sleep 10
done
wait "$worker_pid"
