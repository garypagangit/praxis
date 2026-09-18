#!/usr/bin/env bash
# CTI supervisor; outer controller timeout includes setup, inference and publishing.
set -Eeuo pipefail
umask 077
: "${CTI_RUNROOT:?}" "${CTI_S3_RESULT_PREFIX:?}" "${CTI_DEADLINE_EPOCH:?}"
: "${CTI_PERSIST_ROOT:?}" "${CTI_FREEZE_REL:?}" "${CTI_HF_SECRET_ID:?}"
EXECROOT="$CTI_RUNROOT/reports/cti_external_validation_20260918"
OUTPUT="$CTI_RUNROOT/outputs"
mkdir -p "$OUTPUT" "$CTI_RUNROOT/tmp" "$CTI_RUNROOT/hf"
export TMPDIR="$CTI_RUNROOT/tmp" HF_HOME="$CTI_RUNROOT/hf"
export HF_HUB_CACHE="$HF_HOME/hub" HUGGINGFACE_HUB_CACHE="$HF_HOME/hub"
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false
export CUDA_VISIBLE_DEVICES=0 CUBLAS_WORKSPACE_CONFIG=:4096:8
export HF_HUB_DISABLE_PROGRESS_BARS=1
SYNC_PID=''

finish() {
  code=$?
  trap - EXIT TERM INT
  set +e
  unset HF_TOKEN HUGGINGFACE_HUB_TOKEN
  if [ -n "$SYNC_PID" ]; then kill "$SYNC_PID" 2>/dev/null; wait "$SYNC_PID" 2>/dev/null; fi
  printf '%s\n' "$code" > "$OUTPUT/SUPERVISOR_EXIT.txt"
  date -u +%FT%TZ > "$OUTPUT/SUPERVISOR_ENDED_UTC.txt"
  archive_ok=1
  timeout --kill-after=2 20 tar -czf "$CTI_RUNROOT/results.tar.gz" -C "$CTI_RUNROOT" outputs || archive_ok=0
  upload_code=1
  if [ "$archive_ok" -eq 1 ]; then
    sha256sum "$CTI_RUNROOT/results.tar.gz" | awk '{print $1}' > "$CTI_RUNROOT/results.sha256"
    archive_bytes=$(stat -c %s "$CTI_RUNROOT/results.tar.gz")
    root_free=$(df -B1 --output=avail /var/lib | tail -n 1 | tr -d ' ')
    # Preserve evidence on existing EBS before instance-store data disappears.
    if [ "$archive_bytes" -le 536870912 ] && [ "$root_free" -ge $((archive_bytes + 134217728)) ]; then
      if mkdir -m 700 -p /var/lib/praxis-cti-evidence && mkdir -m 700 -- "$CTI_PERSIST_ROOT"; then
        if timeout --kill-after=2 10 cp -- "$CTI_RUNROOT/results.tar.gz" "$CTI_RUNROOT/results.sha256" "$CTI_PERSIST_ROOT/"; then
          printf '%s  %s\n' "$(cat "$CTI_PERSIST_ROOT/results.sha256")" "$CTI_PERSIST_ROOT/results.tar.gz" | timeout --kill-after=2 10 sha256sum -c -
          timeout --kill-after=2 5 sync
        fi
      fi
    fi
    timeout --kill-after=2 45 aws s3 cp "$CTI_RUNROOT/results.tar.gz" "$CTI_S3_RESULT_PREFIX/results.tar.gz" --only-show-errors
    upload_code=$?
    if [ "$upload_code" -eq 0 ]; then
      timeout --kill-after=2 10 aws s3 cp "$CTI_RUNROOT/results.sha256" "$CTI_S3_RESULT_PREFIX/results.sha256" --only-show-errors
      upload_code=$?
    fi
  fi
  echo "CTI supervisor exit=$code archive=$archive_ok upload=$upload_code; scheduling guest stop"
  /sbin/shutdown -h +1
  # Transport failure must not masquerade as operational success.
  if [ "$code" -eq 0 ] && [ "$upload_code" -ne 0 ]; then code=74; fi
  exit "$code"
}
trap finish EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
exec > >(tee -a "$OUTPUT/supervisor.log") 2>&1
date -u +%FT%TZ > "$OUTPUT/SUPERVISOR_STARTED_UTC.txt"
df -Pk "$CTI_RUNROOT" > "$OUTPUT/DISK.txt"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv > "$OUTPUT/GPU.txt"
cp "$CTI_RUNROOT/$CTI_FREEZE_REL" "$OUTPUT/FREEZE.json"

# Only existing environments are considered. No install or root-cache growth.
# The worker's pre-fresh qualification is a separate model readiness gate.
PY=''
for candidate in \
  /opt/praxis/venvs/sec-lord-relationship-evidence-defense-qwen25-7b-20260630/bin/python \
  /opt/praxis/venvs/falsecite-code-generation-gate-20260625/bin/python \
  /opt/pytorch/bin/python \
  /usr/bin/python3; do
  [ -x "$candidate" ] || continue
  if timeout 25 "$candidate" - "$OUTPUT/RUNTIME.json" <<'CTI_RUNTIME_CHECK'
import importlib.metadata as md
import json, platform, sys
from pathlib import Path
from packaging.version import Version
minimum = {'torch':'2.4.0','transformers':'4.43.0','accelerate':'0.30.0',
           'huggingface-hub':'0.23.0','safetensors':'0.4.3'}
versions = {name: md.version(name) for name in minimum}
if sys.version_info < (3, 10): raise SystemExit(2)
if any(Version(versions[name]) < Version(value) for name, value in minimum.items()): raise SystemExit(2)
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
if not torch.cuda.is_available(): raise SystemExit(2)
receipt = {'python':platform.python_version(),'executable':sys.executable,
           'packages':versions,'minimum_compatibility':minimum,'cuda':torch.version.cuda,
           'gpu':torch.cuda.get_device_name(0),'packages_installed_by_supervisor':False}
Path(sys.argv[1]).write_text(json.dumps(receipt,indent=2)+'\n')
CTI_RUNTIME_CHECK
  then PY="$candidate"; break; fi
done
if [ -z "$PY" ]; then echo 'No compatible existing GPU Python environment'; exit 76; fi

# Read the existing secret on the host. Its value never enters SSM text, a file,
# a command-line argument, the runtime bundle or log output. Do not enable xtrace.
HF_TOKEN=$(timeout 25 aws secretsmanager get-secret-value --secret-id "$CTI_HF_SECRET_ID" --query SecretString --output text)
export HF_TOKEN
if [ -z "$HF_TOKEN" ] || [ "$HF_TOKEN" = None ]; then echo 'HF secret unavailable'; exit 77; fi

# Checkpoints are advisory: an append in progress may leave their final line
# incomplete. Only the final archive+SHA is a completed transport artifact.
(
  trap 'exit 0' TERM INT
  while true; do
    timeout --signal=TERM --kill-after=3 20 aws s3 sync "$OUTPUT/" "$CTI_S3_RESULT_PREFIX/partial/" --only-show-errors --no-follow-symlinks >/dev/null 2>&1 || true
    sleep 30
  done
) &
SYNC_PID=$!

CTI_WORKER_DEADLINE_EPOCH=$((CTI_DEADLINE_EPOCH - 160))
export CTI_WORKER_DEADLINE_EPOCH
remaining=$((CTI_WORKER_DEADLINE_EPOCH - $(date -u +%s)))
if [ "$remaining" -lt 90 ]; then echo 'Insufficient time for bounded qualification/inference'; exit 75; fi

# Launch argv as data. The freeze permits inputs/qualification only; the
# supervisor alone supplies output placement and the absolute worker deadline.
timeout --signal=TERM --kill-after=10 "$remaining" "$PY" - "$CTI_RUNROOT" "$CTI_FREEZE_REL" "$OUTPUT" <<'CTI_INVOKE'
import json, os, sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
frozen=json.loads((root/sys.argv[2]).read_text())
args=frozen['worker_args']
if not isinstance(args,list) or len(args)!=4 or args[::2]!=['--inputs','--qualification']:
    raise SystemExit('Invalid frozen worker argv')
for index in (1,3):
    path=(root/args[index]).resolve(strict=True)
    if not path.is_relative_to(root): raise SystemExit('Worker input escaped bundle')
    args[index]=str(path)
worker=root/'reports/cti_external_validation_20260918/inference_worker.py'
argv=[sys.executable,str(worker),*args,'--output-dir',sys.argv[3],
      '--deadline-epoch',os.environ['CTI_WORKER_DEADLINE_EPOCH']]
os.execv(sys.executable,argv)
CTI_INVOKE
