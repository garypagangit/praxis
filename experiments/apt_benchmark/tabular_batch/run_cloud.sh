#!/usr/bin/env bash
# Existing-host E1 foundation worker. Controller owns the 60-minute cap/watchdog.
set -euo pipefail
test "$#" -eq 5
bundle_uri="$1"
bundle_sha="$2"
output_uri="$3"
run_id="$4"
deadline_epoch="$5"
[[ "$bundle_uri" =~ ^s3://[a-zA-Z0-9._/-]+$ ]]
[[ "$output_uri" =~ ^s3://[a-zA-Z0-9._/-]+$ ]]
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
export OPENBLAS_NUM_THREADS=4
export NUMEXPR_NUM_THREADS=4
export PYTHONUNBUFFERED=1
export HF_HUB_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1
export TABPFN_DISABLE_TELEMETRY=1
export APT_FROZEN_BUNDLE_SHA256="$bundle_sha"
worker_pid=""
publish() {
  rc=$?
  trap - EXIT TERM INT
  if test -n "$worker_pid" && kill -0 "$worker_pid" 2>/dev/null; then
    kill -TERM "$worker_pid" 2>/dev/null || true
    wait "$worker_pid" 2>/dev/null || true
  fi
  cd "$run_dir"
  printf '%s\n' "$rc" > outputs/WORKER_EXIT.txt
  # 150 seconds reserved before the absolute worker deadline for publication.
  timeout --kill-after=5s 30 tar -czf result.tar.gz outputs || exit 90
  sha256sum result.tar.gz | cut -d ' ' -f1 > result.sha256
  timeout --kill-after=5s 90 aws s3 cp result.tar.gz "${output_uri}/result.tar.gz" --only-show-errors &&
    timeout --kill-after=5s 15 aws s3 cp result.sha256 "${output_uri}/result.sha256" --only-show-errors || rc=91
  exit "$rc"
}
trap publish EXIT
trap 'exit 124' TERM INT
bounded() {
  maximum="$1"
  shift
  remaining=$((deadline_epoch - $(date +%s) - 150))
  test "$remaining" -ge 15
  if test "$maximum" -gt "$remaining"; then maximum="$remaining"; fi
  timeout --signal=TERM --kill-after=10s "${maximum}s" "$@"
}
bounded 180 aws s3 cp "$bundle_uri" bundle.tar.gz --only-show-errors
printf '%s  bundle.tar.gz\n' "$bundle_sha" | sha256sum -c -
bounded 60 python3 - <<'PY'
import hashlib,json,tarfile
from pathlib import Path,PurePosixPath
root=Path.cwd().resolve()
with tarfile.open('bundle.tar.gz','r:gz') as archive:
    seen=set();total=0
    for member in archive.getmembers():
        name=member.name;parts=PurePosixPath(name).parts
        target=(root/name).resolve()
        if (name in seen or '\\' in name or not parts or parts[0] not in {'repo','data','model_cache','BUNDLE_CONTENTS.json'}
            or any(p in {'..','.'} for p in parts) or not target.is_relative_to(root) or not member.isfile()):
            raise ValueError('Invalid runtime bundle member')
        seen.add(name);total+=member.size
        if len(seen)>40 or total>500_000_000:
            raise ValueError('Oversize runtime bundle')
    archive.extractall(root)
manifest=json.loads((root/'BUNDLE_CONTENTS.json').read_text())
expected=set(manifest['files'])|{'BUNDLE_CONTENTS.json'}
if seen!=expected:
    raise ValueError('Runtime bundle whitelist mismatch')
for name,receipt in manifest['files'].items():
    path=root/name
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    if path.stat().st_size!=receipt['bytes'] or h.hexdigest()!=receipt['sha256']:
        raise ValueError('Runtime member hash mismatch')
(root/'outputs'/'BUNDLE_CONTENTS.json').write_text(json.dumps(manifest,indent=2))
PY
python_bin=""
for candidate in \
 /opt/praxis/venvs/sec-lord-relationship-evidence-defense-qwen25-7b-20260630/bin/python \
 /opt/praxis/venvs/falsecite-code-generation-gate-20260625/bin/python \
 /opt/pytorch/bin/python; do
  printf 'Checking %s\n' "$candidate" >> outputs/ENV_SELECTION.log
  if test -x "$candidate" && bounded 45 "$candidate" -c 'import sys,torch; assert sys.version_info >= (3,10); assert torch.cuda.is_available()' >> outputs/ENV_SELECTION.log 2>&1; then
    python_bin="$candidate"
    break
  fi
done
test -n "$python_bin"
# Per-run writes are isolated. Existing site packages are read-only; exact pinned
# versions below take precedence in this new environment.
bounded 90 "$python_bin" -m venv --system-site-packages "$run_dir/venv" > outputs/VENV_SETUP.log 2>&1
base_torch_site=$(bounded 30 "$python_bin" -c 'import pathlib,torch;print(pathlib.Path(torch.__file__).resolve().parent.parent)')
python_bin="$run_dir/venv/bin/python"
bounded 30 "$python_bin" - "$base_torch_site" <<'PY'
from pathlib import Path
import sys,sysconfig
source=Path(sys.argv[1]).resolve(strict=True)
(Path(sysconfig.get_paths()['purelib'])/'praxis_existing_torch.pth').write_text(str(source)+'\n')
PY
if ! bounded 30 "$python_bin" -c 'import torch; assert torch.__version__.split("+")[0]=="2.5.1"; assert torch.cuda.is_available()' > outputs/TORCH_REUSE.log 2>&1; then
  bounded 600 "$python_bin" -m pip install --only-binary=:all: --no-input --disable-pip-version-check \
    torch==2.5.1 --index-url https://download.pytorch.org/whl/cu121 > outputs/TORCH_INSTALL.log 2>&1
fi
bounded 600 "$python_bin" -m pip install --only-binary=:all: --no-input --disable-pip-version-check \
  -r repo/experiments/apt_benchmark/tabular_batch/requirementsfoundation.txt \
  -r repo/experiments/apt_benchmark/tabular_batch/requirements_baselines.txt > outputs/DEPENDENCIES.log 2>&1
bounded 30 "$python_bin" -m pip freeze > outputs/PIP_FREEZE.txt
bounded 30 nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv > outputs/GPU.txt
bounded 90 "$python_bin" repo/experiments/apt_benchmark/tabular_batch/cloud_runtime.py \
  --probe --root "$run_dir" > outputs/ENVIRONMENT.json
remaining=$((deadline_epoch - $(date +%s) - 150))
test "$remaining" -ge 120
cd repo
timeout --signal=TERM --kill-after=10s "${remaining}s" "$python_bin" -u \
  experiments/apt_benchmark/tabular_batch/cloud_runtime.py --run \
  --data "$run_dir/data/DATA.npz" \
  --protocol experiments/apt_benchmark/tabular_batch/protocol.json \
  --output "$run_dir/outputs/foundations" \
  --models tabicl_v2,tabpfn_2_5_synthetic --device cuda \
  --model-cache "$run_dir/model_cache" > "$run_dir/outputs/worker.log" 2>&1 &
worker_pid=$!
set +e
while kill -0 "$worker_pid" 2>/dev/null; do
  sleep 15
  timeout --kill-after=5s 15 aws s3 cp "$run_dir/outputs/worker.log" "${output_uri}/worker.log" --only-show-errors
done
wait "$worker_pid"
worker_rc=$?
worker_pid=""
set -e
exit "$worker_rc"
