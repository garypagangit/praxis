#!/usr/bin/env bash
# Invoked inside a controller-bounded timeout; the external stop schedule is separate.
set -Eeuo pipefail
: "${D0_RUNROOT:?}" "${D0_S3_RESULT_PREFIX:?}" "${D0_DEADLINE_EPOCH:?}" "${D0_PERSIST_ROOT:?}"
EXECROOT="$D0_RUNROOT/final_praxis/010_d0_execution_20260915"
PLANROOT="$D0_RUNROOT/final_praxis/010_development_20260915"
OUTPUT="$D0_RUNROOT/output"
mkdir -p "$OUTPUT" "$D0_RUNROOT/tmp" "$D0_RUNROOT/pip-cache"
export TMPDIR="$D0_RUNROOT/tmp" PIP_CACHE_DIR="$D0_RUNROOT/pip-cache"
export HF_HOME="$D0_RUNROOT/hf" AWS_DEFAULT_REGION=us-east-1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 TORCHINDUCTOR_COMPILE_THREADS=1
export TOKENIZERS_PARALLELISM=false CUDA_VISIBLE_DEVICES=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8

finish() {
  code=$?
  trap - EXIT TERM INT
  set +e
  printf '%s\n' "$code" > "$OUTPUT/SUPERVISOR_EXIT.txt"
  date -u +%FT%TZ > "$OUTPUT/SUPERVISOR_ENDED_UTC.txt"
  tar -czf "$D0_RUNROOT/results.tar.gz" -C "$D0_RUNROOT" output
  sha256sum "$D0_RUNROOT/results.tar.gz" | awk '{print $1}' > "$D0_RUNROOT/results.sha256"
  # Instance-store data disappears on stop. Keep one small persistent evidence
  # copy before network upload; packages, source, and weights stay on NVMe.
  archive_bytes=$(stat -c %s "$D0_RUNROOT/results.tar.gz")
  root_free=$(df -B1 --output=avail /var/lib | tail -n 1 | tr -d ' ')
  if [ "$archive_bytes" -le 536870912 ] && [ "$root_free" -ge $((archive_bytes + 134217728)) ]; then
    if mkdir -m 700 -p /var/lib/praxis-d0-evidence && mkdir -m 700 -- "$D0_PERSIST_ROOT"; then
      cp -- "$D0_RUNROOT/results.tar.gz" "$D0_RUNROOT/results.sha256" "$D0_PERSIST_ROOT/"
      printf '%s  %s\n' "$(cat "$D0_PERSIST_ROOT/results.sha256")" "$D0_PERSIST_ROOT/results.tar.gz" | sha256sum -c -
      sync
      echo "Persistent evidence copy: $D0_PERSIST_ROOT"
    fi
  else
    echo 'Persistent evidence fallback unavailable: archive size or root free-space check failed'
  fi
  timeout 100 aws s3 cp "$D0_RUNROOT/results.tar.gz" "$D0_S3_RESULT_PREFIX/results.tar.gz" --only-show-errors
  upload_code=$?
  if [ "$upload_code" -eq 0 ]; then
    timeout 30 aws s3 cp "$D0_RUNROOT/results.sha256" "$D0_S3_RESULT_PREFIX/results.sha256" --only-show-errors
  fi
  echo "D0 supervisor exit=$code upload=$upload_code; scheduled guest shutdown in one minute"
  /sbin/shutdown -h +1
  exit "$code"
}
trap finish EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
exec > >(tee -a "$OUTPUT/supervisor.log") 2>&1
date -u +%FT%TZ > "$OUTPUT/SUPERVISOR_STARTED_UTC.txt"
df -Pk "$D0_RUNROOT" > "$OUTPUT/DISK.txt"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv > "$OUTPUT/GPU.txt"
python3 -m venv "$D0_RUNROOT/venv"
PY="$D0_RUNROOT/venv/bin/python"
"$PY" -m pip install --disable-pip-version-check 'pip==25.2'
"$PY" -m pip install --disable-pip-version-check 'torch==2.6.0+cu124' --index-url https://download.pytorch.org/whl/cu124
"$PY" -m pip install --disable-pip-version-check -r "$EXECROOT/code/requirements-gpu.txt"
"$PY" -m pip freeze > "$OUTPUT/PIP_FREEZE.txt"
"$PY" "$EXECROOT/code/prepare_cloud_assets.py" --assets "$D0_RUNROOT/assets" --spec "$PLANROOT/D0_SPEC.json"
cp "$D0_RUNROOT/assets/ASSET_RECEIPT.json" "$OUTPUT/ASSET_RECEIPT.json"
cp "$EXECROOT/RUNTIME_FREEZE.json" "$OUTPUT/RUNTIME_FREEZE.json"
cp "$EXECROOT/SOURCE_COMMIT.json" "$OUTPUT/SOURCE_COMMIT.json"

isolated() {
  env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN -u AWS_PROFILE \
    AWS_EC2_METADATA_DISABLED=true HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    unshare --net -- "$@"
}
isolated "$PY" "$EXECROOT/code/test_d0_worker.py" --source-root "$D0_RUNROOT/assets/timesfm_full" > "$OUTPUT/WORKER_TESTS.txt" 2>&1
isolated "$PY" "$EXECROOT/code/test_audit_d0.py" > "$OUTPUT/AUDITOR_TESTS.txt" 2>&1
isolated "$PY" "$EXECROOT/code/d0_worker.py" --mode prepare --csv "$D0_RUNROOT/assets/source.csv" \
  --runtime-freeze "$EXECROOT/RUNTIME_FREEZE.json" --output "$OUTPUT/prepared"
isolated "$PY" "$EXECROOT/code/audit_d0.py" --prepared-only --run-dir "$OUTPUT/prepared" \
  --source-csv "$D0_RUNROOT/assets/source.csv" --output-dir "$OUTPUT/prepared_audit"
remaining=$((D0_DEADLINE_EPOCH - $(date -u +%s) - 160))
if [ "$remaining" -lt 240 ]; then
  echo 'Insufficient time remaining for a complete bounded screen'
  exit 75
fi
if [ "$remaining" -gt 1000 ]; then remaining=1000; fi
isolated "$PY" "$EXECROOT/code/d0_worker.py" --mode run --prepared "$OUTPUT/prepared" \
  --source-root "$D0_RUNROOT/assets/timesfm_full" --source-archive "$D0_RUNROOT/assets/timesfm_source.zip" \
  --weights "$D0_RUNROOT/assets/model/model.safetensors" --runtime-freeze "$EXECROOT/RUNTIME_FREEZE.json" \
  --output "$OUTPUT/run" --max-seconds "$remaining"
isolated "$PY" "$EXECROOT/code/audit_d0.py" --run-dir "$OUTPUT/run" \
  --source-csv "$D0_RUNROOT/assets/source.csv" --source-archive "$D0_RUNROOT/assets/timesfm_source.zip" \
  --output-dir "$OUTPUT/audit"
