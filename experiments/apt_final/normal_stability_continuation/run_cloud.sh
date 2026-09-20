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
# BEGIN_STABLE_STORAGE_GUARDS
# These functions are qualified separately without downloading or running science.
storage_error() { printf 'STORAGE GUARD: %s\n' "$*" >&2; return 1; }
storage_filesystem_path() {
  local target="$1" mounted_on device
  mounted_on=$(findmnt -rn -o TARGET -T "$target") || return 1
  device=$(findmnt -rn -o MAJ:MIN -T "$target") || return 1
  [[ "$mounted_on" == "$storage_expected_mount" && "$device" == "$storage_device" ]] ||
    storage_error "Path is no longer on the verified filesystem: path=$target expected_mount=$storage_expected_mount actual_mount=$mounted_on"
}
prepare_run_storage() {
  local base="$1" parent_name="$2" requested_id="$3" required_mount="${4:-/}"
  local canonical block_sysfs block_device backing_disks parent
  [[ "$parent_name" =~ ^[a-zA-Z0-9_-]+$ && "$requested_id" =~ ^[a-zA-Z0-9_-]+$ ]] ||
    { storage_error 'Invalid storage directory identifier'; return 1; }
  [[ "$base" == /* && -d "$base" && ! -L "$base" ]] ||
    { storage_error 'Storage base must be an existing absolute non-symlink directory'; return 1; }
  canonical=$(readlink -f -- "$base") || return 1
  [[ "$canonical" == "$base" ]] ||
    { storage_error 'Storage base must contain no symlink components'; return 1; }
  [[ "$required_mount" == /* && -d "$required_mount" && ! -L "$required_mount" &&
     "$(readlink -f -- "$required_mount")" == "$required_mount" ]] ||
    { storage_error 'Required mount must be an existing canonical non-symlink directory'; return 1; }
  storage_expected_mount="$required_mount"
  storage_device=$(findmnt -rn -o MAJ:MIN -T "$required_mount") || return 1
  [[ "$storage_device" =~ ^[0-9]+:[0-9]+$ ]] ||
    { storage_error "Cannot identify block device for mount=$required_mount"; return 1; }
  # Exact TARGET matching prevents an absent data mount from silently using root.
  storage_filesystem_path "$required_mount" && storage_filesystem_path "$base" || return 1
  storage_stat=$(stat -Lc '%d' -- "$required_mount") || return 1
  [[ "$(stat -Lc '%d' -- "$base")" == "$storage_stat" ]] ||
    { storage_error "Storage base device differs from mount=$required_mount"; return 1; }
  # Resolve device aliases through sysfs; lsblk -s follows partition
  # and device-mapper ancestry. NVMe names are valid for both EBS and instance store.
  block_sysfs=$(readlink -f -- "/sys/dev/block/$storage_device") || return 1
  [[ -d "$block_sysfs" ]] ||
    { storage_error "Block device has no sysfs entry for mount=$required_mount"; return 1; }
  block_device="/dev/${block_sysfs##*/}"
  backing_disks=$(lsblk -sn -o TYPE,MODEL -- "$block_device") || return 1
  printf '%s\n' "$backing_disks" | awk '
    $1 == "disk" { count++; $1=""; gsub(/[[:space:]]/, ""); if ($0 != "AmazonElasticBlockStore") bad=1 }
    END { exit (count == 0 || bad) }
  ' || { storage_error "Backing disks are not all verified Amazon EBS for mount=$required_mount"; return 1; }
  storage_free_bytes=$(df -PB1 -- "$base" | awk 'NR==2 {print $4}') || return 1
  [[ "$storage_free_bytes" =~ ^[0-9]+$ ]] &&
    (( storage_free_bytes >= 10737418240 )) ||
    { storage_error "EBS needs at least 10 GiB free before creating the run directory: mount=$required_mount free_bytes=$storage_free_bytes"; return 1; }
  parent="$base/$parent_name"
  [[ ! -L "$parent" ]] || { storage_error 'Storage parent is a symlink'; return 1; }
  if [[ ! -e "$parent" ]]; then mkdir -- "$parent" || return 1; fi
  [[ -d "$parent" && "$(readlink -f -- "$parent")" == "$parent" ]] ||
    { storage_error 'Storage parent is not a canonical directory'; return 1; }
  storage_filesystem_path "$parent" || return 1
  run_dir="$parent/$requested_id"
  [[ ! -e "$run_dir" && ! -L "$run_dir" ]] ||
    { storage_error 'Refusing an existing run directory'; return 1; }
  mkdir -- "$run_dir" || return 1
  mkdir -- "$run_dir/outputs" || return 1
  storage_run_identity=$(stat -Lc '%d:%i' -- "$run_dir") || return 1
  storage_outputs_identity=$(stat -Lc '%d:%i' -- "$run_dir/outputs") || return 1
  assert_run_storage || return 1
  printf 'Verified EBS storage: path=%s mount=%s device=%s free_bytes_before_run=%s run_identity=%s outputs_identity=%s\n' \
    "$run_dir" "$storage_expected_mount" "$storage_device" "$storage_free_bytes" "$storage_run_identity" "$storage_outputs_identity" \
    >> "$run_dir/outputs/ENV_SELECTION.log" || return 1
}
assert_run_storage() {
  [[ -d "$run_dir" && ! -L "$run_dir" && -d "$run_dir/outputs" && ! -L "$run_dir/outputs" ]] ||
    { storage_error 'Run or output directory disappeared or became a symlink'; return 1; }
  [[ "$(readlink -f -- "$run_dir")" == "$run_dir" ]] ||
    { storage_error 'Run path canonical identity changed'; return 1; }
  storage_filesystem_path "$run_dir" && storage_filesystem_path "$run_dir/outputs" || return 1
  [[ "$(stat -Lc '%d:%i' -- "$run_dir")" == "$storage_run_identity" &&
     "$(stat -Lc '%d:%i' -- "$run_dir/outputs")" == "$storage_outputs_identity" ]] ||
    { storage_error 'Run or output directory device/inode changed'; return 1; }
  [[ "$(stat -Lc '%d' -- "$run_dir")" == "$storage_stat" ]] ||
    { storage_error 'Run directory device no longer matches verified mount'; return 1; }
}
# END_STABLE_STORAGE_GUARDS
prepare_run_storage /mnt/praxis-20260912-004 praxis-apt-final "$run_id" /mnt/praxis-20260912-004
cd "$run_dir"
mkdir -- "$run_dir/tmp" "$run_dir/pip-cache"
export TMPDIR="$run_dir/tmp"
export PIP_CACHE_DIR="$run_dir/pip-cache"
export AWS_DEFAULT_REGION=us-east-1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
export APT_FROZEN_BUNDLE_SHA256="$bundle_sha"
publish() {
  rc=$?
  trap - EXIT
  set +e
  if ! assert_run_storage; then
    printf 'PUBLICATION FAILED: storage identity changed; original exit=%s. Evidence path was not recreated.\n' "$rc" >&2
    if [[ "$rc" -eq 0 ]]; then rc=91; fi
    exit "$rc"
  fi
  if ! { printf '%s\n' "$rc" > "$run_dir/outputs/WORKER_EXIT.txt" &&
    tar -czf "$run_dir/result.tar.gz" -C "$run_dir" outputs &&
    sha256sum "$run_dir/result.tar.gz" | cut -d ' ' -f1 > "$run_dir/result.sha256" &&
    assert_run_storage &&
    timeout 120 aws s3 cp "$run_dir/result.tar.gz" "${output_uri}/result.tar.gz" --only-show-errors &&
    timeout 30 aws s3 cp "$run_dir/result.sha256" "${output_uri}/result.sha256" --only-show-errors; }; then
    printf 'PUBLICATION FAILED: archive, checksum, or upload failed; original exit=%s.\n' "$rc" >&2
    rc=91
  fi
  exit "$rc"
}
trap publish EXIT
timeout 180 aws s3 cp "$bundle_uri" "$run_dir/bundle.tar.gz" --only-show-errors
assert_run_storage
printf '%s  %s\n' "$bundle_sha" "$run_dir/bundle.tar.gz" | sha256sum -c -
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
assert_run_storage
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
