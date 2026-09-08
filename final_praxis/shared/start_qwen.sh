#!/usr/bin/env bash
set -euo pipefail
umask 077
WORK=/opt/dlami/nvme/praxis-final/20260908
PY=/opt/praxis/venvs/frontier-exp02-guardian-step-20260618/bin/python
mkdir -p "$WORK/source-v1" "$WORK/logs" "$WORK/runs"
shutdown -h +360 'Final Praxis authorized experiment compute deadline'
aws s3 cp s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/code/shared_v1.zip "$WORK/shared_v1.zip" --only-show-errors
python3 -m zipfile -e "$WORK/shared_v1.zip" "$WORK/source-v1"
cd "$WORK/source-v1"
export HF_HOME=/opt/praxis/hf_cache
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
unset TRANSFORMERS_CACHE
nohup "$PY" -m final_praxis.shared.inference_server --model-id Qwen/Qwen2.5-7B-Instruct --revision a09a35458c702b33eeacc393d103063234e8bc28 --port 8765 --batch-size 8 > "$WORK/logs/qwen-server.log" 2>&1 < /dev/null &
echo "$!" > "$WORK/qwen-server.pid"
for attempt in $(seq 1 120); do
  if curl --silent --fail http://127.0.0.1:8765/ > "$WORK/qwen-runtime.json"; then
    cat "$WORK/qwen-runtime.json"
    "$PY" - <<'PY'
from final_praxis.shared.model_adapter import HTTPAdapter
a=HTTPAdapter('http://127.0.0.1:8765','Qwen/Qwen2.5-7B-Instruct','a09a35458c702b33eeacc393d103063234e8bc28')
print(a.generate([{'role':'user','content':'For an infrastructure connection check, return exactly READY.'}],max_new_tokens=8))
PY
    aws s3 cp "$WORK/qwen-runtime.json" s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/runtime/qwen-runtime.json --only-show-errors
    exit 0
  fi
  if ! kill -0 "$(cat "$WORK/qwen-server.pid")" 2>/dev/null; then
    tail -80 "$WORK/logs/qwen-server.log"
    exit 1
  fi
  sleep 3
done
tail -80 "$WORK/logs/qwen-server.log"
exit 1
