#!/usr/bin/env bash
# Hash-checked, blinded, standalone bot review; no answer key or live SOC action.
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
    (( storage_free_bytes >= 21474836480 )) ||
    { storage_error "EBS needs at least 20 GiB free before creating the run directory: mount=$required_mount free_bytes=$storage_free_bytes"; return 1; }
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
prepare_run_storage /mnt/praxis-20260912-004 praxis-cert-gate "$run_id" /mnt/praxis-20260912-004
cd "$run_dir"
export AWS_DEFAULT_REGION=us-east-1
publish() {
  rc=$?
  trap - EXIT
  set +e
  if ! assert_run_storage; then
    printf 'PUBLICATION FAILED: verified storage identity changed; exit=%s.\n' "$rc" >&2
    if [[ "$rc" -eq 0 ]]; then rc=91; fi
    exit "$rc"
  fi
  python3 - "$rc" <<'PY'
import json,sys
from pathlib import Path
rc=int(sys.argv[1])
frozen=Path('outputs/review/frozen/FROZEN.json')
complete=rc == 0 and frozen.is_file()
record={'status':'COMPLETE' if complete else 'INCOMPLETE','exit_code':rc,
        'scope':'AUTOMATED_BOT_REVIEW_ONLY','human_review_performed':False,
        'answer_key_accessed':False,'frozen_review_present':frozen.is_file()}
Path('outputs/WORKER_STATUS.json').write_text(json.dumps(record,indent=2)+'\n')
PY
  if ! { printf '%s\n' "$rc" > "$run_dir/outputs/WORKER_EXIT.txt" &&
    tar -czf "$run_dir/result.tar.gz" -C "$run_dir" outputs &&
    sha256sum "$run_dir/result.tar.gz" | cut -d ' ' -f1 > "$run_dir/result.sha256" &&
    assert_run_storage &&
    timeout 120 aws s3 cp "$run_dir/result.tar.gz" "${output_uri}/result.tar.gz" --only-show-errors &&
    timeout 30 aws s3 cp "$run_dir/result.sha256" "${output_uri}/result.sha256" --only-show-errors; }; then
    printf 'PUBLICATION FAILED: private archive/checksum/upload; original exit=%s.\n' "$rc" >&2
    rc=91
  fi
  exit "$rc"
}
trap publish EXIT
mkdir -- "$run_dir/tmp" "$run_dir/pip-cache" "$run_dir/hf-cache"
export TMPDIR="$run_dir/tmp"
export PIP_CACHE_DIR="$run_dir/pip-cache"
export HF_HOME="$run_dir/hf-cache"
export HF_HUB_DISABLE_TELEMETRY=1
export TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
export CERT_GATE_BUNDLE_SHA256="$bundle_sha"
timeout 180 aws s3 cp "$bundle_uri" "$run_dir/bundle.tar.gz" --only-show-errors
assert_run_storage
printf '%s  %s\n' "$bundle_sha" "$run_dir/bundle.tar.gz" | sha256sum -c -
python3 - <<'PY'
from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
root=Path.cwd().resolve()
allowed={'auto_review.py','BUNDLE_MANIFEST.json','records/FINAL_PROTOCOL.json','records/FINAL_RUNTIME.json',
         'prepared/CASES.json','prepared/REQUESTS.jsonl','prepared/PROMPT.txt','prepared/PREPARED.json'}
with tarfile.open('bundle.tar.gz','r:gz') as archive:
    seen=set(); total=0; members=archive.getmembers()
    for member in members:
        name=member.name; path=PurePosixPath(name)
        if name not in allowed or name in seen or not member.isfile() or path.is_absolute() or '..' in path.parts:
            raise ValueError('Unexpected, duplicate, or unsafe bot bundle member')
        seen.add(name); total+=member.size
        if total>128*1024*1024 or len(seen)>8:
            raise ValueError('Bot bundle exceeds its fixed bound')
    if seen != allowed:
        raise ValueError('Incomplete bot bundle')
    for member in members:
        target=root/member.name
        target.parent.mkdir(parents=True,exist_ok=True)
        with archive.extractfile(member) as source, target.open('xb') as output:
            while block:=source.read(1024*1024): output.write(block)
manifest=json.loads(Path('BUNDLE_MANIFEST.json').read_text())
if set(manifest['files']) != allowed-{'BUNDLE_MANIFEST.json'}:
    raise ValueError('Bundle content manifest is incomplete')
for name,record in manifest['files'].items():
    raw=Path(name).read_bytes()
    if len(raw)!=record['bytes'] or hashlib.sha256(raw).hexdigest()!=record['sha256']:
        raise ValueError('Bundle member integrity failure')
Path('outputs/BUNDLE_RECEIPT.json').write_text(json.dumps(manifest,indent=2)+'\n')
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
torch_site=$("$python_bin" -c 'import pathlib,torch; print(pathlib.Path(torch.__file__).resolve().parent.parent)')
timeout 90 "$python_bin" -m venv --system-site-packages "$run_dir/venv" > outputs/VENV_SETUP.log 2>&1
python_bin="$run_dir/venv/bin/python"
"$python_bin" - "$torch_site" <<'PY'
import pathlib,sys,sysconfig
source=pathlib.Path(sys.argv[1]).resolve(strict=True)
(pathlib.Path(sysconfig.get_paths()['purelib'])/'praxis_existing_torch.pth').write_text(str(source)+'\n')
PY
timeout 300 "$python_bin" -m pip install --only-binary=:all: --no-input --disable-pip-version-check \
 transformers==4.57.6 accelerate==1.12.0 safetensors==0.7.0 \
 > outputs/DEPENDENCIES.log 2>&1
"$python_bin" - <<'PY' > outputs/ENVIRONMENT.json
import json,sys,platform,torch,transformers,accelerate,safetensors
if (transformers.__version__,accelerate.__version__,safetensors.__version__) != ('4.57.6','1.12.0','0.7.0'):
    raise ValueError('Dependency versions differ from frozen worker')
if not torch.cuda.is_available(): raise ValueError('CUDA unavailable')
print(json.dumps({'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
 'transformers':transformers.__version__,'accelerate':accelerate.__version__,'safetensors':safetensors.__version__,
 'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0)},indent=2))
PY
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv > outputs/GPU.txt
printf '%s\n' "$python_bin" > outputs/PYTHON.txt
remaining=$((deadline_epoch - $(date +%s) - 240))
test "$remaining" -ge 120
assert_run_storage
timeout --signal=TERM --kill-after=20s "${remaining}s" "$python_bin" -u auto_review.py infer \
 --prepared "$run_dir/prepared" --private-output "$run_dir/outputs/review" \
 --model-id Qwen/Qwen3-4B-Instruct-2507 --revision cdbee75f17c01a7cc42f958dc650907174af0554 \
 --device cuda --max-input-tokens 16384 --max-new-tokens 512 --allow-download \
 > "$run_dir/outputs/worker.log" 2>&1 &
worker_pid=$!
publish_progress() {
  python3 - <<'PY'
from pathlib import Path
import json,datetime
path=Path('outputs/review/WORKER_OUTPUTS.jsonl')
count=0
if path.exists():
    with path.open(encoding='utf-8') as stream: count=sum(1 for line in stream if line.strip())
record={'cases_completed':count,'total_cases':50,'scope':'AUTOMATED_BOT_REVIEW',
        'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
Path('outputs/.PROGRESS.tmp').write_text(json.dumps(record)+'\n')
Path('outputs/.PROGRESS.tmp').replace('outputs/PROGRESS.json')
PY
  timeout 10 aws s3 cp "$run_dir/outputs/worker.log" "${output_uri}/worker.log" --only-show-errors
  timeout 10 aws s3 cp "$run_dir/outputs/PROGRESS.json" "${output_uri}/PROGRESS.json" --only-show-errors
}
set +e
while kill -0 "$worker_pid" 2>/dev/null; do
  sleep 20
  publish_progress
done
wait "$worker_pid"
worker_rc=$?
publish_progress
set -e
exit "$worker_rc"
