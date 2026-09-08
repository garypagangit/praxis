#!/usr/bin/env bash
set -euo pipefail
umask 077
WORK=/opt/dlami/nvme/praxis-final/20260908
PY=/opt/praxis/venvs/sec-lord-relationship-evidence-defense-qwen25-7b-20260630/bin/python
cd "$WORK/source-v1"
"$PY" -m pip install --disable-pip-version-check --only-binary=:all: --target "$WORK/runtime-deps" protobuf==5.29.5
export HF_HOME="$WORK/hf-cache"
export PYTHONPATH="$WORK/runtime-deps:$PWD"
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
unset TRANSFORMERS_CACHE
"$PY" -c 'import google.protobuf,json; print(json.dumps({"added_dependency":"protobuf","version":google.protobuf.__version__,"scope":"isolated Final Praxis runtime-deps directory"}))' > "$WORK/mistral-runtime-dependency.json"
aws s3 cp "$WORK/mistral-runtime-dependency.json" s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/runtime/mistral-runtime-dependency.json --only-show-errors
nohup "$PY" -m final_praxis.shared.inference_server --model-id mistralai/Mistral-7B-Instruct-v0.3 --revision c170c708c41dac9275d15a8fff4eca08d52bab71 --port 8766 --batch-size 8 > "$WORK/logs/mistral-server-r2.log" 2>&1 < /dev/null &
echo "$!" > "$WORK/mistral-server.pid"
for attempt in $(seq 1 200); do
  if curl --silent --fail http://127.0.0.1:8766/ > "$WORK/mistral-runtime.json"; then
    cat "$WORK/mistral-runtime.json"
    "$PY" - <<'PY'
from final_praxis.shared.model_adapter import HTTPAdapter
a=HTTPAdapter('http://127.0.0.1:8766','mistralai/Mistral-7B-Instruct-v0.3','c170c708c41dac9275d15a8fff4eca08d52bab71')
print(a.generate([{'role':'user','content':'For an infrastructure connection check, return exactly READY.'}],max_new_tokens=8))
PY
    aws s3 cp "$WORK/mistral-runtime.json" s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/runtime/mistral-runtime.json --only-show-errors
    exit 0
  fi
  if ! kill -0 "$(cat "$WORK/mistral-server.pid")" 2>/dev/null; then
    tail -80 "$WORK/logs/mistral-server-r2.log"
    exit 1
  fi
  sleep 3
done
tail -80 "$WORK/logs/mistral-server-r2.log"
exit 1
