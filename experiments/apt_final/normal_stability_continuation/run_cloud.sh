#!/usr/bin/env bash
# Called with a new run id, private input/output S3 URIs, bundle SHA, and deadline.
set -euo pipefail
test "$#" -eq 5
bundle_uri="$1"
bundle_sha="$2"
output_uri="$3"
run_id="$4"
deadline_epoch="$5"
[[ "$run_id" =~ ^[a-zA-Z0-9_-]+$ ]]
[[ "$bundle_sha" =~ ^[0-9a-f]{64}$ ]]
[[ "$deadline_epoch" =~ ^[0-9]+$ ]]
test -d /opt/dlami/nvme
run_dir="/opt/dlami/nvme/$run_id"
test ! -e "$run_dir"
mkdir "$run_dir"
cd "$run_dir"
mkdir outputs
export AWS_DEFAULT_REGION=us-east-1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
export APT_FROZEN_BUNDLE_SHA256="$bundle_sha"
publish() {
  rc=$?
  trap - EXIT
  cd "$run_dir"
  printf '%s\n' "$rc" > outputs/WORKER_EXIT.txt
  tar -czf result.tar.gz outputs
  sha256sum result.tar.gz | cut -d ' ' -f1 > result.sha256
  timeout 120 aws s3 cp result.tar.gz "${output_uri}/result.tar.gz" --only-show-errors &&
    timeout 30 aws s3 cp result.sha256 "${output_uri}/result.sha256" --only-show-errors || rc=91
  exit "$rc"
}
trap publish EXIT
timeout 180 aws s3 cp "$bundle_uri" bundle.tar.gz --only-show-errors
printf '%s  bundle.tar.gz\n' "$bundle_sha" | sha256sum -c -
python3 - <<'PY'
from pathlib import Path
import tarfile
root=Path.cwd().resolve()
with tarfile.open('bundle.tar.gz','r:gz') as archive:
    seen=set()
    total=0
    for member in archive.getmembers():
        name=member.name
        target=(root/name).resolve()
        key=str(target).casefold()
        if key in seen or not target.is_relative_to(root) or not (member.isfile() or member.isdir()):
            raise ValueError('Invalid bundle member')
        seen.add(key)
        total+=member.size
        if len(seen)>2000 or total>4_000_000_000:
            raise ValueError('Oversize runtime bundle')
    archive.extractall(root)
PY
python_bin=""
for candidate in \
 /opt/praxis/venvs/sec-lord-relationship-evidence-defense-qwen25-7b-20260630/bin/python \
 /opt/praxis/venvs/falsecite-code-generation-gate-20260625/bin/python \
 /opt/pytorch/bin/python; do
  printf 'Checking %s\n' "$candidate" >> outputs/ENV_SELECTION.log
  if test -x "$candidate" && timeout 45 "$candidate" -c 'import sys,torch; assert sys.version_info >= (3,10); assert torch.cuda.is_available()' >> outputs/ENV_SELECTION.log 2>&1; then
    python_bin="$candidate"
    break
  fi
done
test -n "$python_bin"
torch_site=$($python_bin -c 'import pathlib,torch; print(pathlib.Path(torch.__file__).resolve().parent.parent)')
timeout 90 "$python_bin" -m venv --system-site-packages "$run_dir/venv" > outputs/VENV_SETUP.log 2>&1
python_bin="$run_dir/venv/bin/python"
"$python_bin" - "$torch_site" <<'PY'
import pathlib,sys,sysconfig
source=pathlib.Path(sys.argv[1]).resolve(strict=True)
target=pathlib.Path(sysconfig.get_paths()['purelib'])/'praxis_existing_torch.pth'
target.write_text(str(source)+'\n')
PY
timeout 240 "$python_bin" -m pip install --only-binary=:all: --no-input --disable-pip-version-check \
  numpy==1.26.4 scipy==1.14.1 scikit-learn==1.5.2 joblib==1.4.2 threadpoolctl==3.5.0 \
  > outputs/DEPENDENCIES.log 2>&1
"$python_bin" -c 'import numpy,scipy,sklearn,torch; assert torch.cuda.is_available()'
printf '%s\n' "$python_bin" > outputs/PYTHON.txt
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv > outputs/GPU.txt
"$python_bin" - <<'PY' > outputs/ENVIRONMENT.json
import json,sys,platform,numpy,scipy,sklearn,torch
print(json.dumps({'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
 'numpy':numpy.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__,
 'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0)},indent=2))
PY
remaining=$((deadline_epoch - $(date +%s) - 240))
test "$remaining" -ge 120
cd repo
timeout --signal=TERM --kill-after=20s "${remaining}s" "$python_bin" -u \
  -m experiments.apt_final.normal_stability_continuation.worker \
  --data-dir "$run_dir/data" --output "$run_dir/outputs" \
  --original-registration experiments/apt_final/normal_stability/REGISTRATION.json \
  --reuse-dir "$run_dir/reuse" \
  --registration experiments/apt_final/normal_stability_continuation/REGISTRATION.json \
  > "$run_dir/outputs/worker.log" 2>&1 &
worker_pid=$!
set +e
while kill -0 "$worker_pid" 2>/dev/null; do
  sleep 20
  timeout 30 aws s3 cp "$run_dir/outputs/worker.log" "${output_uri}/worker.log" --only-show-errors
done
wait "$worker_pid"
worker_rc=$?
set -e
cd "$run_dir"
exit "$worker_rc"
